"""First rigorous Taylor/interval enclosure for Li's equation (29).

This is deliberately a *first* certificate.  It proves the algebraic
constant-skeleton identity for G_1, constructs rational Taylor models for the
linear-sieve delay equations, and encloses the remaining one-, two-, and
three-dimensional correction integrals by inner/outer box sums.  The final
interval is allowed to miss Li's printed upper bound; when it does, the JSON
records the first quantified unresolved width rather than claiming success.

Every decisive endpoint in the Taylor construction and every box bound is a
``fractions.Fraction``.  Large sums are accumulated after outward rounding to
a common dyadic denominator, so their rounding direction is inspectable.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path


def frac(x: Q) -> str:
    return f"{x.numerator}/{x.denominator}"


def floor_q(x: Q, scale: int) -> int:
    return x.numerator * scale // x.denominator


def ceil_q(x: Q, scale: int) -> int:
    return -((-x.numerator * scale) // x.denominator)


def decimal_floor(x: Q, places: int) -> str:
    scale = 10**places
    n = floor_q(x, scale)
    sign = "-" if n < 0 else ""
    n = abs(n)
    whole, tail = divmod(n, scale)
    return f"{sign}{whole}.{tail:0{places}d}"


def decimal_ceil(x: Q, places: int) -> str:
    scale = 10**places
    n = ceil_q(x, scale)
    sign = "-" if n < 0 else ""
    n = abs(n)
    whole, tail = divmod(n, scale)
    return f"{sign}{whole}.{tail:0{places}d}"


def interval_record(lo: Q, hi: Q, places: int = 15) -> dict[str, str]:
    assert lo <= hi
    return {
        "lower_exact": frac(lo),
        "upper_exact": frac(hi),
        "lower_decimal_directed": decimal_floor(lo, places),
        "upper_decimal_directed": decimal_ceil(hi, places),
        "width_upper_decimal": decimal_ceil(hi - lo, places),
    }


def outward_dyadic(lo: Q, hi: Q, bits: int) -> tuple[Q, Q]:
    scale = 1 << bits
    return Q(floor_q(lo, scale), scale), Q(ceil_q(hi, scale), scale)


def log_interval(x: Q, terms: int = 128) -> tuple[Q, Q]:
    """Positive-term atanh series with an explicit geometric tail."""

    if x <= 0:
        raise ValueError("log domain")
    if x == 1:
        return Q(0), Q(0)
    if x < 1:
        lo, hi = log_interval(1 / x, terms)
        return -hi, -lo
    z = (x - 1) / (x + 1)
    z2 = z * z
    power = z
    partial = Q(0)
    for k in range(terms):
        partial += power / (2 * k + 1)
        power *= z2
    partial *= 2
    tail = 2 * power / ((2 * terms + 1) * (1 - z2))
    return partial, partial + tail


def exp_interval(lo: Q, hi: Q, terms: int = 48) -> tuple[Q, Q]:
    """Directed exp enclosure for 0 <= lo <= hi < 1."""

    assert 0 <= lo <= hi < 1

    def partial(x: Q) -> tuple[Q, Q]:
        term = Q(1)
        total = Q(1)
        for k in range(1, terms + 1):
            term *= x / k
            total += term
        next_term = term * x / (terms + 1)
        # For j>=0 the ratio between successive omitted terms is at most
        # x/(terms+2), hence this geometric majorant is rigorous.
        tail = next_term / (1 - x / (terms + 2))
        return total, total + tail

    elo, _ = partial(lo)
    _, ehi = partial(hi)
    return elo, ehi


BERNOULLI_EVEN = {
    2: Q(1, 6),
    4: Q(-1, 30),
    6: Q(1, 42),
    8: Q(-1, 30),
    10: Q(5, 66),
    12: Q(-691, 2730),
    14: Q(7, 6),
    16: Q(-3617, 510),
    18: Q(43867, 798),
}


def euler_gamma_interval(log_terms: int = 128) -> tuple[Q, Q]:
    """Euler--Maclaurin bracket at n=64, followed by no float use.

    The harmonic-number expansion is a Stieltjes series: truncation after a
    negative Bernoulli term is below gamma, and after the following positive
    term is above gamma.  At n=64 its term magnitudes are decreasing through
    B_18, which is checked exactly below.
    """

    n = 64
    harmonic = sum((Q(1, k) for k in range(1, n + 1)), Q(0))
    log2_lo, log2_hi = log_interval(Q(2), log_terms)
    base_lo = harmonic - 6 * log2_hi - Q(1, 2 * n)
    base_hi = harmonic - 6 * log2_lo - Q(1, 2 * n)
    terms = []
    for k in range(1, 10):
        value = BERNOULLI_EVEN[2 * k] / (2 * k * n ** (2 * k))
        terms.append(value)
    assert all(abs(terms[i + 1]) < abs(terms[i]) for i in range(len(terms) - 1))
    lower = base_lo + sum(terms[:8], Q(0))
    upper = base_hi + sum(terms[:9], Q(0))
    assert lower < upper
    return lower, upper


@dataclass(frozen=True)
class TaylorModel:
    coeff: tuple[Q, ...]
    error: Q


def poly_value(coeff: tuple[Q, ...], x: Q) -> Q:
    ans = Q(0)
    for value in reversed(coeff):
        ans = ans * x + value
    return ans


def shifted_range(model: TaylorModel, lo: Q, hi: Q) -> tuple[Q, Q]:
    """Range a polynomial by its exact midpoint Taylor coefficients."""

    assert 0 <= lo <= hi
    mid = (lo + hi) / 2
    radius = (hi - lo) / 2
    degree = len(model.coeff) - 1
    shifted = []
    for k in range(degree + 1):
        value = Q(0)
        for n in range(k, degree + 1):
            value += model.coeff[n] * math.comb(n, k) * mid ** (n - k)
        shifted.append(value)
    rad = model.error
    for k in range(1, degree + 1):
        rad += abs(shifted[k]) * radius**k
    return shifted[0] - rad, shifted[0] + rad


class DelayTaylor:
    """Rational Taylor models for a=sF/(2e^gamma), b=sf/(2e^gamma)."""

    def __init__(self, mesh: int, degree: int, max_s: int):
        if mesh < 2 or degree < 4:
            raise ValueError("mesh>=2 and degree>=4 required")
        self.mesh = mesh
        self.h = Q(1, mesh)
        self.degree = degree
        self.max_s = max_s
        zero_coeff = (Q(0),) * (degree + 1)
        one_coeff = (Q(1),) + (Q(0),) * degree
        self.a: dict[int, TaylorModel] = {}
        self.b: dict[int, TaylorModel] = {}
        # Only [1,2] is required as delayed seed data.
        for j in range(mesh, 2 * mesh):
            self.a[j] = TaylorModel(one_coeff, Q(0))
            self.b[j] = TaylorModel(zero_coeff, Q(0))
        for j in range(2 * mesh, max_s * mesh + 1):
            if j == 2 * mesh:
                a_start, a_start_error = Q(1), Q(0)
                b_start, b_start_error = Q(0), Q(0)
            else:
                a_prev = self.a[j - 1]
                b_prev = self.b[j - 1]
                a_start = poly_value(a_prev.coeff, self.h)
                b_start = poly_value(b_prev.coeff, self.h)
                a_start_error = a_prev.error
                b_start_error = b_prev.error
            source_b = self.b[j - mesh]
            source_a = self.a[j - mesh]
            c = Q(j - mesh, mesh)
            self.a[j] = self._integrate_quotient(source_b, c, a_start, a_start_error)
            self.b[j] = self._integrate_quotient(source_a, c, b_start, b_start_error)

    def _integrate_quotient(
        self, source: TaylorModel, c: Q, start: Q, start_error: Q
    ) -> TaylorModel:
        # Q(u) matches source(u)/(c+u) through degree d-1.  The unmatched
        # coefficient gives an exact rational remainder formula.
        q = [source.coeff[0] / c]
        for n in range(1, self.degree):
            q.append((source.coeff[n] - q[n - 1]) / c)
        residual_coeff = source.coeff[self.degree] - q[self.degree - 1]
        derivative_error = source.error / c + abs(residual_coeff) * self.h**self.degree / c
        coeff = [start]
        coeff.extend(q[n] / (n + 1) for n in range(self.degree))
        return TaylorModel(tuple(coeff), start_error + self.h * derivative_error)

    def shape_point(self, which: str, s: Q) -> tuple[Q, Q]:
        if which == "a" and s <= 2:
            return Q(1), Q(1)
        if which == "b" and s <= 2:
            return Q(0), Q(0)
        j = floor_q(s, self.mesh)
        if j == self.max_s * self.mesh and s == self.max_s:
            j -= 1
        if j not in self.a:
            raise ValueError(f"argument outside Taylor table: {s}")
        x0 = Q(j, self.mesh)
        model = self.a[j] if which == "a" else self.b[j]
        value = poly_value(model.coeff, s - x0)
        return value - model.error, value + model.error

    def max_model_error(self) -> tuple[Q, Q]:
        return max(m.error for m in self.a.values()), max(m.error for m in self.b.values())


@dataclass(frozen=True)
class FixedTaylorModel:
    # Every coefficient interval and error is in units of 1/scale.
    coeff: tuple[tuple[int, int], ...]
    error: int


class FixedDelayTaylor:
    """Fast, rigorous fixed-dyadic version of the Taylor recurrence.

    Unlike binary floating point, every operation here is integer arithmetic
    followed by an explicit floor or ceiling.  Coefficient rounding is kept as
    an interval; the sole uniform remainder is the exact unmatched quotient
    term from the degree truncation.
    """

    def __init__(self, mesh: int, degree: int, max_s: int, dyadic_bits: int):
        if mesh < 2 or degree < 4:
            raise ValueError("mesh>=2 and degree>=4 required")
        self.mesh = mesh
        self.degree = degree
        self.max_s = max_s
        self.scale = 1 << dyadic_bits
        exact_zero = ((0, 0),) * (degree + 1)
        exact_one = ((self.scale, self.scale),) + ((0, 0),) * degree
        self.a: dict[int, FixedTaylorModel] = {}
        self.b: dict[int, FixedTaylorModel] = {}
        for j in range(mesh, 2 * mesh):
            self.a[j] = FixedTaylorModel(exact_one, 0)
            self.b[j] = FixedTaylorModel(exact_zero, 0)
        for j in range(2 * mesh, max_s * mesh + 1):
            if j == 2 * mesh:
                a_start, b_start = (self.scale, self.scale), (0, 0)
            else:
                a_start = self._point_range(self.a[j - 1], Q(1, mesh))
                b_start = self._point_range(self.b[j - 1], Q(1, mesh))
            c = Q(j - mesh, mesh)
            self.a[j] = self._integrate_quotient(self.b[j - mesh], c, a_start)
            self.b[j] = self._integrate_quotient(self.a[j - mesh], c, b_start)

    @staticmethod
    def _sub(x: tuple[int, int], y: tuple[int, int]) -> tuple[int, int]:
        return x[0] - y[1], x[1] - y[0]

    @staticmethod
    def _add(x: tuple[int, int], y: tuple[int, int]) -> tuple[int, int]:
        return x[0] + y[0], x[1] + y[1]

    @staticmethod
    def _mul_q(x: tuple[int, int], q: Q) -> tuple[int, int]:
        if q >= 0:
            return floor_q(Q(x[0]) * q, 1), ceil_q(Q(x[1]) * q, 1)
        return floor_q(Q(x[1]) * q, 1), ceil_q(Q(x[0]) * q, 1)

    def _point_range(self, model: FixedTaylorModel, u: Q) -> tuple[int, int]:
        value = (0, 0)
        for coeff in reversed(model.coeff):
            value = self._add(self._mul_q(value, u), coeff)
        return value[0] - model.error, value[1] + model.error

    def _integrate_quotient(
        self, source: FixedTaylorModel, c: Q, start: tuple[int, int]
    ) -> FixedTaylorModel:
        quotient = self._quotient_model(source, c)
        coeff = [start]
        coeff.extend(self._mul_q(quotient.coeff[n], Q(1, n + 1)) for n in range(self.degree))
        integrated_error = ceil_q(Q(quotient.error, self.mesh), 1)
        return FixedTaylorModel(tuple(coeff), integrated_error)

    def _quotient_model(self, source: FixedTaylorModel, c: Q) -> FixedTaylorModel:
        q = [self._mul_q(source.coeff[0], 1 / c)]
        for n in range(1, self.degree):
            q.append(self._mul_q(self._sub(source.coeff[n], q[n - 1]), 1 / c))
        residual = self._sub(source.coeff[self.degree], q[self.degree - 1])
        max_residual = max(abs(residual[0]), abs(residual[1]))
        error = ceil_q(Q(source.error, 1) / c, 1)
        error += ceil_q(Q(max_residual, 1) * Q(1, self.mesh) ** self.degree / c, 1)
        return FixedTaylorModel(tuple(q) + ((0, 0),), error)

    def cell_range(self, which: str, j: int) -> tuple[int, int]:
        if j < 2 * self.mesh:
            if which == "a":
                return self.scale, self.scale
            return 0, 0
        model = self.a[j] if which == "a" else self.b[j]
        mid = Q(1, 2 * self.mesh)
        radius = mid
        shifted: list[tuple[int, int]] = []
        for k in range(self.degree + 1):
            value = (0, 0)
            for n in range(k, self.degree + 1):
                term = self._mul_q(model.coeff[n], Q(math.comb(n, k)) * mid ** (n - k))
                value = self._add(value, term)
            shifted.append(value)
        center = shifted[0]
        rad = model.error
        for k in range(1, self.degree + 1):
            rad += ceil_q(Q(max(abs(shifted[k][0]), abs(shifted[k][1]))) * radius**k, 1)
        return center[0] - rad, center[1] + rad

    def ratio_cell_range(self, which: str, j: int) -> tuple[int, int]:
        """Range a(s)/s or b(s)/s without destroying their correlation."""

        if j < 2 * self.mesh:
            source = self.a[j] if which == "a" else self.b[j]
        else:
            source = self.a[j] if which == "a" else self.b[j]
        ratio = self._quotient_model(source, Q(j, self.mesh))
        mid = Q(1, 2 * self.mesh)
        radius = mid
        shifted: list[tuple[int, int]] = []
        for k in range(self.degree + 1):
            value = (0, 0)
            for n in range(k, self.degree + 1):
                term = self._mul_q(ratio.coeff[n], Q(math.comb(n, k)) * mid ** (n - k))
                value = self._add(value, term)
            shifted.append(value)
        center = shifted[0]
        rad = ratio.error
        for k in range(1, self.degree + 1):
            rad += ceil_q(Q(max(abs(shifted[k][0]), abs(shifted[k][1]))) * radius**k, 1)
        return center[0] - rad, center[1] + rad

    def shape_point(self, which: str, s: Q) -> tuple[int, int]:
        if s <= 2:
            return (self.scale, self.scale) if which == "a" else (0, 0)
        j = floor_q(s, self.mesh)
        if j == self.max_s * self.mesh and s == self.max_s:
            j -= 1
        x0 = Q(j, self.mesh)
        model = self.a[j] if which == "a" else self.b[j]
        return self._point_range(model, s - x0)

    def max_model_error(self) -> tuple[int, int]:
        return max(m.error for m in self.a.values()), max(m.error for m in self.b.values())


class RangeTable:
    """Dyadically rounded whole-cell ranges and sparse min/max queries."""

    def __init__(
        self,
        delay: FixedDelayTaylor,
        egamma: tuple[Q, Q],
        dyadic_bits: int,
    ):
        self.mesh = delay.mesh
        self.max_s = delay.max_s
        self.scale = delay.scale
        count = self.max_s * self.mesh
        f_lo = [0] * count
        f_hi = [0] * count
        F_lo = [0] * count
        F_hi = [0] * count
        elo, ehi = egamma
        for j in range(count):
            x0, x1 = Q(j, self.mesh), Q(j + 1, self.mesh)
            if x1 <= 0:
                continue
            if x0 < 2:
                # f=0.  F is only used far above 2 in this certificate; a
                # harmless wide value avoids a singular special case at 0.
                f_low, f_high = Q(0), Q(0)
                if x0 == 0:
                    F_low, F_high = Q(0), Q(10**9)
                else:
                    F_low, F_high = 2 * elo / x1, 2 * ehi / x0
            else:
                arlo, arhi = delay.ratio_cell_range("a", j)
                brlo, brhi = delay.ratio_cell_range("b", j)
                # arlo etc. enclose a(s)/s or b(s)/s in units 1/scale.
                # Multiplying the target by scale cancels that denominator.
                def scaled_range(ratio_lo: int, ratio_hi: int) -> tuple[int, int]:
                    values = [
                        2 * e * ratio
                        for e in (elo, ehi)
                        for ratio in (ratio_lo, ratio_hi)
                    ]
                    return floor_q(min(values), 1), ceil_q(max(values), 1)

                f_lo[j], f_hi[j] = scaled_range(brlo, brhi)
                F_lo[j], F_hi[j] = scaled_range(arlo, arhi)
                continue
            f_lo[j], f_hi[j] = floor_q(f_low, self.scale), ceil_q(f_high, self.scale)
            F_lo[j], F_hi[j] = floor_q(F_low, self.scale), ceil_q(F_high, self.scale)
        self.f_min, self.f_max = self._sparse(f_lo, f_hi)
        self.F_min, self.F_max = self._sparse(F_lo, F_hi)

    @staticmethod
    def _sparse(lows: list[int], highs: list[int]) -> tuple[list[list[int]], list[list[int]]]:
        mins = [lows]
        maxs = [highs]
        width = 1
        while 2 * width <= len(lows):
            prev_lo, prev_hi = mins[-1], maxs[-1]
            usable = len(lows) - 2 * width + 1
            mins.append([min(prev_lo[i], prev_lo[i + width]) for i in range(usable)])
            maxs.append([max(prev_hi[i], prev_hi[i + width]) for i in range(usable)])
            width *= 2
        return mins, maxs

    def _query(self, tables: tuple[list[list[int]], list[list[int]]], lo: Q, hi: Q) -> tuple[int, int]:
        assert 0 <= lo <= hi <= self.max_s
        left = max(0, floor_q(lo, self.mesh))
        right = min(self.max_s * self.mesh - 1, floor_q(hi, self.mesh))
        if hi == self.max_s:
            right = self.max_s * self.mesh - 1
        length = right - left + 1
        level = length.bit_length() - 1
        width = 1 << level
        mins, maxs = tables
        return min(mins[level][left], mins[level][right - width + 1]), max(
            maxs[level][left], maxs[level][right - width + 1]
        )

    def f_range(self, lo: Q, hi: Q) -> tuple[int, int]:
        return self._query((self.f_min, self.f_max), lo, hi)

    def F_range(self, lo: Q, hi: Q) -> tuple[int, int]:
        return self._query((self.F_min, self.F_max), lo, hi)


# Goldbach specialization alpha=1, theta=7/32.
A0 = Q(1, 500)
C0 = Q(25, 128)
LEVEL0 = Q(19101, 32000)
S0 = 500 * LEVEL0


def phi_range(lo: Q, hi: Q) -> tuple[Q, Q]:
    """Exact range of vartheta_1(t) on an interval in the used domain."""

    peak_x = C0

    def phi(x: Q) -> Q:
        if x <= peak_x:
            return (1 + x) / 2
        return Q(57, 64) - 3 * x / 2

    values = [phi(lo), phi(hi)]
    if lo <= peak_x <= hi:
        values.append(phi(peak_x))
    return min(values), max(values)


def psi_range(x: tuple[Q, Q], y: tuple[Q, Q]) -> tuple[Q, Q]:
    xlo, xhi = x
    ylo, yhi = y
    if xlo >= yhi:
        return xlo, xhi
    if xhi < ylo:
        return Q(0), Q(0)
    return Q(0), max(Q(0), xhi)


def affine_decreasing_range(const: Q, slope: Q, lo: Q, hi: Q) -> tuple[Q, Q]:
    assert slope >= 0
    return const - slope * hi, const - slope * lo


def min_ranges(*ranges: tuple[Q, Q]) -> tuple[Q, Q]:
    return min(x[0] for x in ranges), min(x[1] for x in ranges)


def theta3_range(
    t: tuple[Q, Q], u: tuple[Q, Q], v: tuple[Q, Q]
) -> tuple[Q, Q]:
    """Inclusion enclosure for Lichtman's enhanced vartheta_1(t,u,v)."""

    tlo, thi = t
    ulo, uhi = u
    vlo, vhi = v
    candidates = [
        phi_range(tlo, thi),
        phi_range(ulo, uhi),
        phi_range(tlo + ulo, thi + uhi),
        phi_range(tlo + ulo + vlo, thi + uhi + vhi),
    ]

    def w_range(
        first: tuple[Q, Q], second: tuple[Q, Q], third: tuple[Q, Q]
    ) -> tuple[Q, Q]:
        xlo, xhi = first
        ylo, yhi = second
        zlo, zhi = third
        inner = min_ranges(
            affine_decreasing_range(Q(66, 107), Q(34, 107), zlo, zhi),
            affine_decreasing_range(Q(153, 256), Q(3, 8), zlo, zhi),
            affine_decreasing_range(Q(1), Q(2), ylo, yhi),
        )
        threshold = ((1 + xlo) / 2, (1 + xhi) / 2)
        return psi_range(inner, threshold)

    candidates.append(w_range(t, u, v))
    candidates.append(w_range(t, v, u))
    candidates.append(
        psi_range(phi_range(tlo + vlo, thi + vhi), (tlo + 2 * ulo + vlo, thi + 2 * uhi + vhi))
    )
    candidates.append(
        psi_range(phi_range(ulo + vlo, uhi + vhi), (2 * tlo + ulo + vlo, 2 * thi + uhi + vhi))
    )
    return max(x[0] for x in candidates), max(x[1] for x in candidates)


def argument_range(
    theta: tuple[Q, Q],
    variables: list[tuple[Q, Q]],
    denominator: Q,
) -> tuple[Q, Q]:
    qlo = theta[0] - sum((x[1] for x in variables), Q(0))
    qhi = theta[1] - sum((x[0] for x in variables), Q(0))
    return max(Q(0), qlo / denominator), max(Q(0), qhi / denominator)


def correction_interval(
    table: RangeTable,
    boxes_per_doubling: int,
    adaptive_splits: int,
) -> tuple[dict[str, tuple[Q, Q]], dict[str, object]]:
    """Inner/outer rational sums for the stable G1 correction formula."""

    scale = table.scale
    # A multiplicative mesh is essential here: on a uniform t mesh the first
    # diagonal box begins at 1/500 but is much wider than that cutoff, and its
    # t3^-2 outer majorant destroys the bound.  Subdivide each exact rational
    # doubling band into equal pieces.  All endpoints remain small rationals.
    intervals: list[tuple[Q, Q]] = []
    band_lo = A0
    while band_lo < C0:
        band_hi = min(2 * band_lo, C0)
        step = (band_hi - band_lo) / boxes_per_doubling
        intervals.extend(
            (band_lo + i * step, band_lo + (i + 1) * step)
            for i in range(boxes_per_doubling)
        )
        band_lo = band_hi
    boxes = len(intervals)

    def mul_iv(x: tuple[Q, Q], y: tuple[Q, Q]) -> tuple[Q, Q]:
        values = (x[0] * y[0], x[0] * y[1], x[1] * y[0], x[1] * y[1])
        return min(values), max(values)

    def add_iv(x: tuple[Q, Q], y: tuple[Q, Q]) -> tuple[Q, Q]:
        return x[0] + y[0], x[1] + y[1]

    weight_bits = 128
    log_weights = [outward_dyadic(*log_interval(hi / lo, 24), weight_bits) for lo, hi in intervals]

    def weight_for(
        kind: str,
        I1: tuple[Q, Q],
        I2: tuple[Q, Q],
        I3: tuple[Q, Q],
        cached_logs: tuple[tuple[Q, Q], tuple[Q, Q], tuple[Q, Q]] | None = None,
    ) -> tuple[Q, Q]:
        l1, h1 = I1
        l2, h2 = I2
        l3, h3 = I3
        if cached_logs is None:
            L1, L2, L3 = (
                outward_dyadic(*log_interval(h / l, 24), weight_bits)
                for l, h in (I1, I2, I3)
            )
        else:
            L1, L2, L3 = cached_logs
        if kind == "off":
            invdiff = 1 / l3 - 1 / h3
            value = mul_iv(mul_iv(L1, L2), (invdiff, invdiff))
        elif kind == "eq12":
            square = mul_iv(L1, L1)
            invdiff = 1 / l3 - 1 / h3
            value = mul_iv((square[0] / 2, square[1] / 2), (invdiff, invdiff))
        elif kind == "eq23":
            # int_l^h dt2/t2 int_l^t2 dt3/t3^2
            # = log(h/l)/l + 1/h - 1/l.
            inner = (
                L2[0] / l2 + 1 / h2 - 1 / l2,
                L2[1] / l2 + 1 / h2 - 1 / l2,
            )
            value = mul_iv(L1, inner)
        else:
            assert kind == "eq123"
            # Exact ordered three-variable weight on one diagonal cell.
            square = mul_iv(L1, L1)
            value = (
                square[0] / (2 * l1) + 1 / l1 - 1 / h1 - L1[1] / l1,
                square[1] / (2 * l1) + 1 / l1 - 1 / h1 - L1[0] / l1,
            )
        value = outward_dyadic(*value, weight_bits)
        assert value[0] >= 0
        return value

    def triple_weight(i1: int, i2: int, i3: int) -> tuple[Q, Q]:
        if i1 > i2 > i3:
            kind = "off"
        elif i1 == i2 and i2 > i3:
            kind = "eq12"
        elif i1 > i2 and i2 == i3:
            kind = "eq23"
        else:
            kind = "eq123"
        # For base cells all logarithms are already certified and cached.
        return weight_for(
            kind,
            intervals[i1],
            intervals[i2],
            intervals[i3],
            (log_weights[i1], log_weights[i2], log_weights[i3]),
        )

    def correction_f(slo: Q, shi: Q) -> tuple[Q, Q]:
        flo, fhi = table.f_range(slo, shi)
        return Q(scale - fhi, scale), Q(scale - flo, scale)

    def correction_F(slo: Q, shi: Q) -> tuple[Q, Q]:
        Flo, Fhi = table.F_range(slo, shi)
        return Q(Flo - scale, scale), Q(Fhi - scale, scale)

    # One-dimensional correction: 500 integral (1-f)/t dt.
    one_lo = Q(0)
    one_hi = Q(0)
    one_negative_lower_cells = 0
    for index, (lo, hi) in enumerate(intervals):
        theta = theta3_range((lo, hi), (A0, A0), (A0, A0))
        slo, shi = argument_range(theta, [(lo, hi)], Q(1, 500))
        dlo, dhi = correction_f(slo, shi)
        if dlo < 0:
            one_negative_lower_cells += 1
        contribution = mul_iv((dlo, dhi), log_weights[index])
        one_lo += 500 * contribution[0]
        one_hi += 500 * contribution[1]

    # Two-dimensional correction with the positive weight integrated exactly
    # on every off-diagonal or diagonal ordered box.
    two_lo = Q(0)
    two_hi = Q(0)
    for i1, (l1, h1) in enumerate(intervals):
        for i2 in range(i1 + 1):
            l2, h2 = intervals[i2]
            theta = theta3_range((l1, h1), (l2, h2), (A0, A0))
            slo, shi = argument_range(theta, [(l1, h1), (l2, h2)], Q(1, 500))
            dlo, dhi = correction_F(slo, shi)
            if i2 < i1:
                weight = mul_iv(log_weights[i1], log_weights[i2])
            else:
                square = mul_iv(log_weights[i1], log_weights[i1])
                weight = square[0] / 2, square[1] / 2
            weight = outward_dyadic(*weight, weight_bits)
            contribution = mul_iv((dlo, dhi), weight)
            two_lo += 500 * contribution[0]
            two_hi += 500 * contribution[1]

    # Three-dimensional correction with 1/(t1*t2*t3^2) integrated exactly on
    # each ordered cell.  Only the range of 1-f is taken independently.
    three_lo = Q(0)
    three_hi = Q(0)
    max_argument_hi = Q(0)
    min_argument_lo = Q(10**9)
    # Heap entries are (-width, serial, kind, I1, I2, I3, lo, hi, slo, shi).
    heap: list[tuple[Q, int, str, tuple[Q, Q], tuple[Q, Q], tuple[Q, Q], Q, Q, Q, Q]] = []
    serial = 0
    type_counts = {"off": 0, "eq12": 0, "eq23": 0, "eq123": 0}

    def evaluate_cell(
        kind: str,
        I1: tuple[Q, Q],
        I2: tuple[Q, Q],
        I3: tuple[Q, Q],
        cached_weight: tuple[Q, Q] | None = None,
    ) -> tuple[Q, Q, Q, Q]:
        theta = theta3_range(I1, I2, I3)
        qlo = theta[0] - I1[1] - I2[1] - I3[1]
        qhi = theta[1] - I1[0] - I2[0] - I3[0]
        slo = max(Q(0), qlo / I3[1])
        shi = max(Q(0), qhi / I3[0])
        dlo, dhi = correction_f(slo, shi)
        weight = cached_weight if cached_weight is not None else weight_for(kind, I1, I2, I3)
        lo, hi = mul_iv((dlo, dhi), weight)
        return lo, hi, slo, shi

    def push_cell(
        kind: str,
        I1: tuple[Q, Q],
        I2: tuple[Q, Q],
        I3: tuple[Q, Q],
        evaluated: tuple[Q, Q, Q, Q],
    ) -> None:
        nonlocal serial
        lo, hi, slo, shi = evaluated
        heapq.heappush(heap, (-(hi - lo), serial, kind, I1, I2, I3, lo, hi, slo, shi))
        serial += 1
        type_counts[kind] += 1

    for i1, (l1, h1) in enumerate(intervals):
        for i2 in range(i1 + 1):
            l2, h2 = intervals[i2]
            for i3 in range(i2 + 1):
                l3, h3 = intervals[i3]
                if i1 > i2 > i3:
                    kind = "off"
                elif i1 == i2 and i2 > i3:
                    kind = "eq12"
                elif i1 > i2 and i2 == i3:
                    kind = "eq23"
                else:
                    kind = "eq123"
                I1, I2, I3 = (l1, h1), (l2, h2), (l3, h3)
                evaluated = evaluate_cell(kind, I1, I2, I3, triple_weight(i1, i2, i3))
                lo, hi, slo, shi = evaluated
                max_argument_hi = max(max_argument_hi, shi)
                min_argument_lo = min(min_argument_lo, slo)
                three_lo += lo
                three_hi += hi
                push_cell(kind, I1, I2, I3, evaluated)

    initial_three_lo, initial_three_hi = three_lo, three_hi
    initial_leaf_count = len(heap)

    def halves(I: tuple[Q, Q]) -> tuple[tuple[Q, Q], tuple[Q, Q]]:
        mid = (I[0] + I[1]) / 2
        return (I[0], mid), (mid, I[1])

    def split_options(
        kind: str, I1: tuple[Q, Q], I2: tuple[Q, Q], I3: tuple[Q, Q]
    ) -> list[tuple[str, list[tuple[str, tuple[Q, Q], tuple[Q, Q], tuple[Q, Q]]]]]:
        options: list[tuple[str, list[tuple[str, tuple[Q, Q], tuple[Q, Q], tuple[Q, Q]]]]] = []
        if kind == "off":
            for dim, label in enumerate(("t1", "t2", "t3")):
                pieces = halves((I1, I2, I3)[dim])
                children = []
                for piece in pieces:
                    data = [I1, I2, I3]
                    data[dim] = piece
                    children.append(("off", data[0], data[1], data[2]))
                options.append((label, children))
        elif kind == "eq12":
            low, high = halves(I1)
            options.append(("shared12", [("eq12", low, low, I3), ("off", high, low, I3), ("eq12", high, high, I3)]))
            low3, high3 = halves(I3)
            options.append(("t3", [("eq12", I1, I2, low3), ("eq12", I1, I2, high3)]))
        elif kind == "eq23":
            low1, high1 = halves(I1)
            options.append(("t1", [("eq23", low1, I2, I3), ("eq23", high1, I2, I3)]))
            low, high = halves(I2)
            options.append(("shared23", [("eq23", I1, low, low), ("off", I1, high, low), ("eq23", I1, high, high)]))
        else:
            assert kind == "eq123"
            low, high = halves(I1)
            options.append(
                (
                    "shared123",
                    [
                        ("eq123", low, low, low),
                        ("eq23", high, low, low),
                        ("eq12", high, high, low),
                        ("eq123", high, high, high),
                    ],
                )
            )
        return options

    split_axis_counts: dict[str, int] = {}
    for _ in range(adaptive_splits):
        if not heap:
            break
        neg_width, _, kind, I1, I2, I3, old_lo, old_hi, _, _ = heapq.heappop(heap)
        candidates = []
        for label, specs in split_options(kind, I1, I2, I3):
            evaluated_children = [(spec, evaluate_cell(*spec)) for spec in specs]
            total_width = sum((value[1] - value[0] for _, value in evaluated_children), Q(0))
            candidates.append((total_width, label, evaluated_children))
        _, label, chosen = min(candidates, key=lambda item: (item[0], item[1]))
        three_lo -= old_lo
        three_hi -= old_hi
        type_counts[kind] -= 1
        for spec, evaluated in chosen:
            three_lo += evaluated[0]
            three_hi += evaluated[1]
            push_cell(*spec, evaluated)
        split_axis_counts[label] = split_axis_counts.get(label, 0) + 1

    final_widest = heapq.nsmallest(24, heap)

    return (
        {
            "one_dimensional": (one_lo, one_hi),
            "two_dimensional": (two_lo, two_hi),
            "three_dimensional": (three_lo, three_hi),
        },
        {
            "box_count_per_axis": boxes,
            "boxes_per_exact_doubling_band": boxes_per_doubling,
            "parameter_mesh": "equal rational subdivisions of [a,2a], [2a,4a], ... with final clipping at c",
            "one_dimensional_cells_with_negative_model_lower_correction": one_negative_lower_cells,
            "triple_argument_domain_outer": [frac(min_argument_lo), frac(max_argument_hi)],
            "simplex_bracketing": (
                "The positive measure dt1/t1 dt2/t2 dt3/t3^2 is integrated "
                "exactly (with directed log intervals) on off-diagonal, one-pair "
                "diagonal, and full-diagonal ordered cells; only the F/f correction "
                "factor is ranged independently."
            ),
            "weight_log_terms": 24,
            "weight_dyadic_bits": weight_bits,
            "adaptive": {
                "requested_splits": adaptive_splits,
                "performed_splits": adaptive_splits,
                "initial_leaf_count": initial_leaf_count,
                "final_leaf_count": len(heap),
                "selection_rule": (
                    "Pop the active leaf with largest certified interval width; "
                    "among every order-preserving midpoint split option choose "
                    "the option with least sum of child widths, ties by axis label."
                ),
                "coverage_rule": (
                    "Off-diagonal rectangles split into two. eq12/eq23 ordered "
                    "wedges split into two diagonal children plus one cross rectangle; "
                    "eq123 splits into eq123, eq23, eq12, eq123. These are disjoint "
                    "apart from measure-zero faces and exactly cover the parent."
                ),
                "initial_three_interval": interval_record(initial_three_lo, initial_three_hi, 15),
                "final_three_interval": interval_record(three_lo, three_hi, 15),
                "split_axis_counts": split_axis_counts,
                "final_leaf_type_counts": type_counts,
            },
            "widest_triple_cells": [
                {
                    "kind": kind,
                    "t1": [frac(I1[0]), frac(I1[1])],
                    "t2": [frac(I2[0]), frac(I2[1])],
                    "t3": [frac(I3[0]), frac(I3[1])],
                    "argument_outer": [frac(slo), frac(shi)],
                    "width_decimal_upper": decimal_ceil(-neg_width, 18),
                }
                for neg_width, _, kind, I1, I2, I3, _, _, slo, shi in final_widest
            ],
        },
    )


def build(args: argparse.Namespace) -> dict[str, object]:
    gamma = outward_dyadic(*euler_gamma_interval(args.log_terms), 192)
    egamma = outward_dyadic(*exp_interval(*gamma, terms=args.exp_terms), 192)
    delay = FixedDelayTaylor(args.mesh, args.degree, args.max_s, args.dyadic_bits)
    table = RangeTable(delay, egamma, args.dyadic_bits)
    aerr, berr = delay.max_model_error()

    # Correct reading of Li (29): 500*F(500*vartheta_{1/500}), with no -1
    # inside the argument and vartheta_{1/500}=19101/32000.
    alo, ahi = delay.shape_point("a", S0)
    Flo = 2 * egamma[0] * alo / (delay.scale * S0)
    Fhi = 2 * egamma[1] * ahi / (delay.scale * S0)
    zero = (500 * (Flo - 1), 500 * (Fhi - 1))

    corrections, geometry = correction_interval(table, args.boxes, args.adaptive_splits)
    skeleton = Q(1, C0)  # exact: 1/c=128/25
    total_lo = skeleton + zero[0] + sum((x[0] for x in corrections.values()), Q(0))
    total_hi = skeleton + zero[1] + sum((x[1] for x in corrections.values()), Q(0))
    paper = Q(606_932, 100_000)
    sharp = total_hi < paper
    widths = {name: bounds[1] - bounds[0] for name, bounds in corrections.items()}
    first_unclosed = max(widths, key=widths.get)

    # Exact constant-skeleton check.  It is the value obtained after replacing
    # every F and f by 1, and removes the apparent cancellation of thousands.
    log_lo, log_hi = log_interval(C0 / A0, args.log_terms)
    # Symbolically: 1/a-L/a+L^2/(2a) minus
    # [L^2/(2a)-L/a+1/a-1/c] = 1/c.  The log interval is reported only as
    # an audit datum; it is not used in the identity.
    return {
        "schema": "li-g1-rational-taylor-certificate-v1",
        "verdict": "SHARP_BOUND_CERTIFIED" if sharp else "PARTIAL_STRICT_CERTIFICATE",
        "paper_claim": "G1 < 6.06932",
        "paper_upper_exact": frac(paper),
        "source_semantics": {
            "equation": 29,
            "vartheta_1_over_500_exact": frac(LEVEL0),
            "first_F_argument_exact": frac(S0),
            "first_F_argument_decimal": decimal_floor(S0, 9),
            "audit_correction": (
                "The prior coarse script used 19037/64=500*(19101/32000)-1. "
                "The PDF has no '-1'; the correct argument is 19101/64."
            ),
        },
        "stable_decomposition": {
            "identity": (
                "G1=1/c+500(F(s0)-1)+500*int(1-f)/t+"
                "500*double_int(F-1)/(t1*t2)+"
                "triple_int(1-f)/(t1*t2*t3^2)"
            ),
            "a_exact": frac(A0),
            "c_exact": frac(C0),
            "constant_skeleton_exact": frac(skeleton),
            "constant_skeleton_decimal": decimal_floor(skeleton, 9),
            "log_c_over_a_audit": interval_record(log_lo, log_hi, 12),
        },
        "transcendentals": {
            "gamma": interval_record(*gamma, 20),
            "exp_gamma": interval_record(*egamma, 20),
            "basis": (
                "Euler-Maclaurin alternating bracket at n=64 through B18; "
                "positive exp series with geometric tail"
            ),
        },
        "delay_taylor": {
            "normalization": "a=sF/(2e^gamma), b=sf/(2e^gamma)",
            "mesh": args.mesh,
            "degree": args.degree,
            "max_s": args.max_s,
            "a_max_uniform_model_error": frac(Q(aerr, delay.scale)),
            "b_max_uniform_model_error": frac(Q(berr, delay.scale)),
            "a_max_uniform_model_error_decimal_upper": decimal_ceil(Q(aerr, delay.scale), 18),
            "b_max_uniform_model_error_decimal_upper": decimal_ceil(Q(berr, delay.scale), 18),
            "method": (
                "On each rational mesh cell, formally divide the previous "
                "cell polynomial by c+u through degree d-1; bound the exact "
                "unmatched u^d/(c+u) term and propagate a symmetric uniform error."
            ),
        },
        "corrections": {
            "zero_dimensional_500_F_minus_1": interval_record(*zero, 15),
            **{name: interval_record(*bounds, 15) for name, bounds in corrections.items()},
        },
        "geometry": geometry,
        "G1_certified_interval": interval_record(total_lo, total_hi, 15),
        "strictly_below_paper_upper": sharp,
        "paper_slack_if_certified_or_deficit": (
            decimal_floor(paper - total_hi, 15)
            if sharp
            else decimal_ceil(total_hi - paper, 15)
        ),
        "first_unclosed_component_by_interval_width": {
            "component": first_unclosed,
            "width_exact": frac(widths[first_unclosed]),
            "width_decimal_upper": decimal_ceil(widths[first_unclosed], 15),
        },
        "limitations": [
            "A PARTIAL_STRICT_CERTIFICATE verdict does not certify Li's printed 6.06932.",
            "The inner/outer simplex sums deliberately over/under-resolve diagonal mesh strips; their difference is a proved discretization width, not a sampling error estimate.",
            "The Taylor table independently encloses the delay equations but does not re-prove the upstream sieve reduction leading to Li (29).",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh", type=int, default=8)
    parser.add_argument("--degree", type=int, default=16)
    parser.add_argument("--max-s", type=int, default=300)
    parser.add_argument("--boxes", type=int, default=12, help="boxes per exact doubling band")
    parser.add_argument("--adaptive-splits", type=int, default=0)
    parser.add_argument("--dyadic-bits", type=int, default=96)
    parser.add_argument("--log-terms", type=int, default=128)
    parser.add_argument("--exp-terms", type=int, default=48)
    args = parser.parse_args()
    certificate = build(args)
    args.output.write_text(json.dumps(certificate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": certificate["verdict"],
                "G1_certified_interval": certificate["G1_certified_interval"],
                "strictly_below_paper_upper": certificate["strictly_below_paper_upper"],
                "first_unclosed_component": certificate[
                    "first_unclosed_component_by_interval_width"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
