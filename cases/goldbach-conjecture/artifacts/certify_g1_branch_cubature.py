"""Branch analysis and a rigorous cubature prototype for Li (29), G_1.

The script is intentionally separate from the R030/R031 certificate program.
It identifies the actually active affine pieces of Lichtman's enhanced level,
proves two global dominance reductions, and measures the residual obstruction
to a branch-cut/high-order certificate.  Heuristic lattice counts are clearly
labelled and never used as proof endpoints.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("g1base", HERE / "certify_g1_taylor.py")
assert SPEC and SPEC.loader
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

A0 = Q(1, 500)
C0 = Q(25, 128)


@dataclass(frozen=True)
class Affine:
    c: Q
    x: Q = Q(0)
    y: Q = Q(0)
    z: Q = Q(0)

    def at(self, x: Q, y: Q, z: Q) -> Q:
        return self.c + self.x * x + self.y * y + self.z * z

    def __add__(self, other: "Affine") -> "Affine":
        return Affine(self.c + other.c, self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Affine") -> "Affine":
        return Affine(self.c - other.c, self.x - other.x, self.y - other.y, self.z - other.z)

    def scale(self, q: Q) -> "Affine":
        return Affine(q * self.c, q * self.x, q * self.y, q * self.z)


ONE = Affine(Q(1))
X = Affine(Q(0), Q(1))
Y = Affine(Q(0), Q(0), Q(1))
Z = Affine(Q(0), Q(0), Q(0), Q(1))


def iv_add(a: tuple[Q, Q], b: tuple[Q, Q]) -> tuple[Q, Q]:
    return a[0] + b[0], a[1] + b[1]


def iv_sub(a: tuple[Q, Q], b: tuple[Q, Q]) -> tuple[Q, Q]:
    return a[0] - b[1], a[1] - b[0]


def iv_mul(a: tuple[Q, Q], b: tuple[Q, Q]) -> tuple[Q, Q]:
    values = (a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1])
    return min(values), max(values)


def iv_scale(a: tuple[Q, Q], q: Q) -> tuple[Q, Q]:
    return (a[0] * q, a[1] * q) if q >= 0 else (a[1] * q, a[0] * q)


def affine_range(a: Affine, I1: tuple[Q, Q], I2: tuple[Q, Q], I3: tuple[Q, Q]) -> tuple[Q, Q]:
    lo = a.c
    hi = a.c
    for coefficient, interval in ((a.x, I1), (a.y, I2), (a.z, I3)):
        if coefficient >= 0:
            lo += coefficient * interval[0]
            hi += coefficient * interval[1]
        else:
            lo += coefficient * interval[1]
            hi += coefficient * interval[0]
    return lo, hi


def phi_affine(
    r: Affine, I1: tuple[Q, Q], I2: tuple[Q, Q], I3: tuple[Q, Q], label: str
) -> tuple[Affine | None, str | None]:
    lo, hi = affine_range(r, I1, I2, I3)
    if hi <= C0:
        return ONE.scale(Q(1, 2)) + r.scale(Q(1, 2)), None
    if lo >= C0:
        return Affine(Q(57, 64)) - r.scale(Q(3, 2)), None
    return None, f"phi_surface:{label}=c"


def classify_box(
    I1: tuple[Q, Q], I2: tuple[Q, Q], I3: tuple[Q, Q]
) -> tuple[str | None, Affine | None, str | None]:
    """Certify one affine maximizer on a rectangular parameter box."""

    candidates: list[tuple[str, Affine | None, tuple[Q, Q], str | None]] = []
    for label, r in (
        ("phi_t", X),
        ("phi_tu", X + Y),
        ("phi_tuv", X + Y + Z),
        ("phi_tv", X + Z),
        ("phi_uv", Y + Z),
    ):
        rlo, rhi = affine_range(r, I1, I2, I3)
        value, reason = phi_affine(r, I1, I2, I3, label)
        candidates.append((label, value, BASE.phi_range(rlo, rhi), reason))
    # On the full ordered domain, the gates in w and psi disappear after
    # taking the outer maximum; see the proof recorded in the companion
    # report.  Thus beta(v) and both psi phi-values are unconditional
    # candidates in the flattened six-piece representation.
    beta = Affine(Q(153, 256), z=Q(-3, 8))
    candidates.append(("beta_v", beta, affine_range(beta, I1, I2, I3), None))

    winners = []
    for label, value, _, _ in candidates:
        if value is None:
            continue
        dominates = True
        for _, other, other_range, _ in candidates:
            if other is not None:
                dominates = dominates and affine_range(value - other, I1, I2, I3)[0] >= 0
            else:
                dominates = dominates and affine_range(value, I1, I2, I3)[0] >= other_range[1]
            if not dominates:
                break
        if dominates:
            winners.append((label, value))
    if not winners:
        best_lower = max(bounds[0] for _, _, bounds, _ in candidates)
        relevant_folds = [
            reason
            for _, value, bounds, reason in candidates
            if value is None and reason is not None and bounds[1] >= best_lower
        ]
        return None, None, relevant_folds[0] if relevant_folds else "max_surface"
    winners.sort(key=lambda item: item[0])
    return winners[0][0], winners[0][1], None


def flattened_theta_range(
    I1: tuple[Q, Q], I2: tuple[Q, Q], I3: tuple[Q, Q]
) -> tuple[Q, Q]:
    """Inclusion range from the exact flattened six-candidate maximum."""

    bounds: list[tuple[Q, Q]] = []
    for r in (X, X + Y, X + Y + Z, X + Z, Y + Z):
        rlo, rhi = affine_range(r, I1, I2, I3)
        bounds.append(BASE.phi_range(rlo, rhi))
    beta = Affine(Q(153, 256), z=Q(-3, 8))
    bounds.append(affine_range(beta, I1, I2, I3))
    return max(item[0] for item in bounds), max(item[1] for item in bounds)


def fixed_branch_s_range(
    theta: Affine, I1: tuple[Q, Q], I2: tuple[Q, Q], I3: tuple[Q, Q]
) -> tuple[Q, Q]:
    values = []
    for x in I1:
        for y in I2:
            for z in I3:
                values.append((theta.at(x, y, z) - x - y - z) / z)
    return min(values), max(values)


LOG_CACHE: dict[tuple[Q, int], tuple[Q, Q]] = {}


def log_iv(x: Q, terms: int = 48) -> tuple[Q, Q]:
    key = (x, terms)
    cached = LOG_CACHE.get(key)
    if cached is None:
        cached = BASE.outward_dyadic(*BASE.log_interval(x, terms), 160)
        LOG_CACHE[key] = cached
    return cached


class DelayShapeRanges:
    """Sparse whole-cell range queries for the certified delay shapes a,b."""

    def __init__(self, delay: BASE.FixedDelayTaylor):
        self.delay = delay
        self.mesh = delay.mesh
        self.max_s = delay.max_s
        self.scale = delay.scale
        count = self.max_s * self.mesh
        a_lo: list[int] = []
        a_hi: list[int] = []
        b_lo: list[int] = []
        b_hi: list[int] = []
        for j in range(count):
            if j + 1 <= 2 * self.mesh:
                ar = (self.scale, self.scale)
                br = (0, 0)
            else:
                ar = delay.cell_range("a", j)
                br = delay.cell_range("b", j)
            a_lo.append(ar[0])
            a_hi.append(ar[1])
            b_lo.append(br[0])
            b_hi.append(br[1])
        self.tables = {
            "a": BASE.RangeTable._sparse(a_lo, a_hi),
            "b": BASE.RangeTable._sparse(b_lo, b_hi),
        }

    def query(self, which: str, lo: Q, hi: Q) -> tuple[Q, Q]:
        assert which in ("a", "b")
        assert 0 <= lo <= hi <= self.max_s
        if hi <= 2:
            return (Q(1), Q(1)) if which == "a" else (Q(0), Q(0))
        left = max(0, BASE.floor_q(lo, self.mesh))
        right = min(self.max_s * self.mesh - 1, BASE.floor_q(hi, self.mesh))
        if hi == self.max_s:
            right = self.max_s * self.mesh - 1
        length = right - left + 1
        level = length.bit_length() - 1
        width = 1 << level
        mins, maxs = self.tables[which]
        low = min(mins[level][left], mins[level][right - width + 1])
        high = max(maxs[level][left], maxs[level][right - width + 1])
        return Q(low, self.scale), Q(high, self.scale)


def delay_point(delay: BASE.FixedDelayTaylor, which: str, s: Q) -> tuple[Q, Q]:
    lo, hi = delay.shape_point(which, s)
    return Q(lo, delay.scale), Q(hi, delay.scale)


def positive_weight(
    kind: str, I1: tuple[Q, Q], I2: tuple[Q, Q], I3: tuple[Q, Q]
) -> tuple[Q, Q]:
    l1, h1 = I1
    l2, h2 = I2
    l3, h3 = I3
    L1, L2, L3 = log_iv(h1 / l1), log_iv(h2 / l2), log_iv(h3 / l3)
    if kind == "off":
        value = iv_scale(iv_mul(L1, L2), 1 / l3 - 1 / h3)
    elif kind == "eq12":
        value = iv_scale(iv_mul(L1, L1), (1 / l3 - 1 / h3) / 2)
    elif kind == "eq23":
        inner = (L2[0] / l2 + 1 / h2 - 1 / l2, L2[1] / l2 + 1 / h2 - 1 / l2)
        value = iv_mul(L1, inner)
    else:
        assert kind == "eq123"
        square = iv_mul(L1, L1)
        value = (
            square[0] / (2 * l1) + 1 / l1 - 1 / h1 - L1[1] / l1,
            square[1] / (2 * l1) + 1 / l1 - 1 / h1 - L1[0] / l1,
        )
    value = BASE.outward_dyadic(*value, 144)
    assert value[0] >= 0
    return value


def exact_f_second_order(
    theta: Affine,
    I1: tuple[Q, Q],
    I2: tuple[Q, Q],
    I3: tuple[Q, Q],
    egamma: tuple[Q, Q],
) -> tuple[Q, Q]:
    """Second-order weighted Taylor enclosure for 1-f(s), 2<=s<=3.

    This routine is only called on off-diagonal rectangular boxes with one
    certified affine theta branch.
    """

    l1, h1 = I1
    l2, h2 = I2
    l3, h3 = I3
    L1, L2 = log_iv(h1 / l1), log_iv(h2 / l2)
    Z2 = 1 / l3 - 1 / h3
    Z3 = (1 / (l3 * l3) - 1 / (h3 * h3)) / 2
    Z4 = (1 / l3**3 - 1 / h3**3) / 3
    W = iv_scale(iv_mul(L1, L2), Z2)

    k0 = theta.c
    kx = theta.x - 1
    ky = theta.y - 1
    d = theta.z - 1
    dx, dy = h1 - l1, h2 - l2
    x2 = (h1 * h1 - l1 * l1) / 2
    y2 = (h2 * h2 - l2 * l2) / 2
    K1 = iv_add(
        iv_add(iv_scale(iv_mul(L1, L2), k0), iv_scale(L2, kx * dx)),
        iv_scale(L1, ky * dy),
    )
    raw1 = iv_add(iv_scale(K1, Z3), iv_scale(W, d))
    K2 = iv_scale(iv_mul(L1, L2), k0 * k0)
    K2 = iv_add(K2, iv_scale(L2, kx * kx * x2))
    K2 = iv_add(K2, iv_scale(L1, ky * ky * y2))
    K2 = iv_add(K2, iv_scale(L2, 2 * k0 * kx * dx))
    K2 = iv_add(K2, iv_scale(L1, 2 * k0 * ky * dy))
    K2 = iv_add(K2, (2 * kx * ky * dx * dy, 2 * kx * ky * dx * dy))
    raw2 = iv_add(iv_add(iv_scale(K2, Z4), iv_scale(K1, 2 * d * Z3)), iv_scale(W, d * d))

    slo, shi = fixed_branch_s_range(theta, I1, I2, I3)
    q = (slo + shi) / 2
    M1 = iv_sub(raw1, iv_scale(W, q))
    M2 = iv_add(iv_sub(raw2, iv_scale(raw1, 2 * q)), iv_scale(W, q * q))
    M2 = max(Q(0), M2[0]), M2[1]
    assert M2[1] >= 0

    logq = log_iv(q - 1, 80)
    hq = iv_scale(logq, 1 / q)
    g0 = iv_sub((Q(1), Q(1)), iv_scale(iv_mul(egamma, hq), 2))
    hp = iv_sub((1 / (q * (q - 1)), 1 / (q * (q - 1))), iv_scale(logq, 1 / (q * q)))
    g1 = iv_scale(iv_mul(egamma, hp), -2)

    logs = (log_iv(slo - 1, 80)[0], log_iv(shi - 1, 80)[1])
    term1 = ((3 * slo - 2) / (shi * shi * (shi - 1) ** 2), (3 * shi - 2) / (slo * slo * (slo - 1) ** 2))
    term2 = (2 * logs[0] / shi**3, 2 * logs[1] / slo**3)
    g2 = iv_scale(iv_mul(egamma, iv_sub(term1, term2)), 2)
    result = iv_add(iv_add(iv_mul(W, g0), iv_mul(M1, g1)), iv_scale(iv_mul(M2, g2), Q(1, 2)))
    return BASE.outward_dyadic(*result, 128)


def delay_f_second_order(
    theta: Affine,
    I1: tuple[Q, Q],
    I2: tuple[Q, Q],
    I3: tuple[Q, Q],
    egamma: tuple[Q, Q],
    delay: BASE.FixedDelayTaylor,
    shapes: DelayShapeRanges,
) -> tuple[Q, Q]:
    """Weighted second-order enclosure for 1-f(s) on any fixed branch.

    The certified delay system obeys

        b'(s)=a(s-1)/(s-1),
        b''(s)=b(s-2)/((s-2)(s-1))-a(s-1)/(s-1)^2,

    with the first term interpreted as zero for s<=3.  These identities,
    together with f(s)=2*exp(gamma)*b(s)/s, give a rigorous interval for
    g''=(1-f)'' on the whole argument interval.  The same exact weighted
    moments used by the elementary 2<=s<=3 routine then bound the remainder.
    """

    l1, h1 = I1
    l2, h2 = I2
    l3, h3 = I3
    L1, L2 = log_iv(h1 / l1), log_iv(h2 / l2)
    Z2 = 1 / l3 - 1 / h3
    Z3 = (1 / (l3 * l3) - 1 / (h3 * h3)) / 2
    Z4 = (1 / l3**3 - 1 / h3**3) / 3
    W = iv_scale(iv_mul(L1, L2), Z2)

    k0 = theta.c
    kx = theta.x - 1
    ky = theta.y - 1
    d = theta.z - 1
    dx, dy = h1 - l1, h2 - l2
    x2 = (h1 * h1 - l1 * l1) / 2
    y2 = (h2 * h2 - l2 * l2) / 2
    K1 = iv_add(
        iv_add(iv_scale(iv_mul(L1, L2), k0), iv_scale(L2, kx * dx)),
        iv_scale(L1, ky * dy),
    )
    raw1 = iv_add(iv_scale(K1, Z3), iv_scale(W, d))
    K2 = iv_scale(iv_mul(L1, L2), k0 * k0)
    K2 = iv_add(K2, iv_scale(L2, kx * kx * x2))
    K2 = iv_add(K2, iv_scale(L1, ky * ky * y2))
    K2 = iv_add(K2, iv_scale(L2, 2 * k0 * kx * dx))
    K2 = iv_add(K2, iv_scale(L1, 2 * k0 * ky * dy))
    K2 = iv_add(K2, (2 * kx * ky * dx * dy, 2 * kx * ky * dx * dy))
    raw2 = iv_add(iv_add(iv_scale(K2, Z4), iv_scale(K1, 2 * d * Z3)), iv_scale(W, d * d))

    slo, shi = fixed_branch_s_range(theta, I1, I2, I3)
    assert 2 <= slo <= shi <= delay.max_s
    q = (slo + shi) / 2
    M1 = iv_sub(raw1, iv_scale(W, q))
    M2 = iv_add(iv_sub(raw2, iv_scale(raw1, 2 * q)), iv_scale(W, q * q))
    M2 = max(Q(0), M2[0]), M2[1]
    assert M2[1] >= 0

    bq = delay_point(delay, "b", q)
    aq1 = delay_point(delay, "a", q - 1)
    bpq = iv_scale(aq1, 1 / (q - 1))
    hq = iv_scale(bq, 1 / q)
    hpq = iv_sub(iv_scale(bpq, 1 / q), iv_scale(bq, 1 / (q * q)))
    g0 = iv_sub((Q(1), Q(1)), iv_scale(iv_mul(egamma, hq), 2))
    g1 = iv_scale(iv_mul(egamma, hpq), -2)

    b = shapes.query("b", slo, shi)
    a1 = shapes.query("a", slo - 1, shi - 1)
    bp = (a1[0] / (shi - 1), a1[1] / (slo - 1))
    if shi <= 3:
        lead = (Q(0), Q(0))
    else:
        b2 = shapes.query("b", max(Q(0), slo - 2), shi - 2)
        lead_lo = Q(0) if slo <= 3 else b2[0] / ((shi - 2) * (shi - 1))
        lead_hi = b2[1] / ((max(slo, Q(3)) - 2) * (max(slo, Q(3)) - 1))
        lead = lead_lo, lead_hi
    trailing = (a1[0] / (shi - 1) ** 2, a1[1] / (slo - 1) ** 2)
    bpp = iv_sub(lead, trailing)
    hpp = iv_add(
        iv_add(
            iv_mul(bpp, (1 / shi, 1 / slo)),
            iv_scale(iv_mul(bp, (1 / shi**2, 1 / slo**2)), -2),
        ),
        iv_scale(iv_mul(b, (1 / shi**3, 1 / slo**3)), 2),
    )
    g2 = iv_scale(iv_mul(egamma, hpp), -2)
    result = iv_add(iv_add(iv_mul(W, g0), iv_mul(M1, g1)), iv_scale(iv_mul(M2, g2), Q(1, 2)))
    return BASE.outward_dyadic(*result, 128)


def phi_piece(r: Q) -> tuple[str, Q]:
    if r <= C0:
        return "rise", (1 + r) / 2
    return "fall", Q(57, 64) - 3 * r / 2


def point_candidates(x: Q, y: Q, z: Q) -> dict[str, Q]:
    """Exact point values in the flattened six-candidate representation."""

    return {
        "phi_t": phi_piece(x)[1],
        "phi_tu": phi_piece(x + y)[1],
        "phi_tuv": phi_piece(x + y + z)[1],
        "beta_v": Q(153, 256) - 3 * z / 8,
        "phi_tv": phi_piece(x + z)[1],
        "phi_uv": phi_piece(y + z)[1],
    }


def active_at(x: Q, y: Q, z: Q) -> tuple[str, ...]:
    values = point_candidates(x, y, z)
    best = max(values.values())
    return tuple(sorted(name for name, value in values.items() if value == best))


def lattice_inventory(parts: int) -> dict[str, object]:
    """Exploratory exact-rational lattice inventory; not a proof of coverage."""

    counts: dict[str, int] = {}
    ties = 0
    total = 0
    for i in range(parts + 1):
        x = A0 + (C0 - A0) * i / parts
        for j in range(i + 1):
            y = A0 + (C0 - A0) * j / parts
            for k in range(j + 1):
                z = A0 + (C0 - A0) * k / parts
                active = active_at(x, y, z)
                key = "+".join(active)
                counts[key] = counts.get(key, 0) + 1
                ties += len(active) > 1
                total += 1
    return {
        "status": "HEURISTIC_INVENTORY_ONLY",
        "parts": parts,
        "points": total,
        "tie_points": ties,
        "active_counts": dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))),
    }


def parse_q(text: str) -> Q:
    numerator, denominator = text.split("/")
    return Q(int(numerator), int(denominator))


def branch_cubature(boxes_per_doubling: int, refine_depth: int) -> dict[str, object]:
    gamma = BASE.outward_dyadic(*BASE.euler_gamma_interval(128), 192)
    egamma = BASE.outward_dyadic(*BASE.exp_interval(*gamma, terms=48), 192)
    delay = BASE.FixedDelayTaylor(8, 16, 300, 96)
    table = BASE.RangeTable(delay, egamma, 96)
    shapes = DelayShapeRanges(delay)
    scale = table.scale

    intervals: list[tuple[Q, Q]] = []
    band_lo = A0
    while band_lo < C0:
        band_hi = min(2 * band_lo, C0)
        step = (band_hi - band_lo) / boxes_per_doubling
        intervals.extend((band_lo + i * step, band_lo + (i + 1) * step) for i in range(boxes_per_doubling))
        band_lo = band_hi

    total_lo = Q(0)
    total_hi = Q(0)
    counts: dict[str, int] = {}
    widths: dict[str, Q] = {}
    kind_widths: dict[str, Q] = {}
    branch_counts: dict[str, int] = {}
    ambiguity_counts: dict[str, int] = {}
    cells = 0
    leaf_cells = 0
    refined_nodes = 0

    def add(kind: str, mode: str, contribution: tuple[Q, Q]) -> None:
        nonlocal total_lo, total_hi
        total_lo += contribution[0]
        total_hi += contribution[1]
        counts[mode] = counts.get(mode, 0) + 1
        widths[mode] = widths.get(mode, Q(0)) + contribution[1] - contribution[0]
        kind_key = f"{kind}:{mode}"
        kind_widths[kind_key] = kind_widths.get(kind_key, Q(0)) + contribution[1] - contribution[0]

    def halves(interval: tuple[Q, Q]) -> tuple[tuple[Q, Q], tuple[Q, Q]]:
        lo, hi = interval
        mid = (lo + hi) / 2
        return (lo, mid), (mid, hi)

    def refined_children(
        kind: str,
        I1: tuple[Q, Q],
        I2: tuple[Q, Q],
        I3: tuple[Q, Q],
    ) -> list[tuple[str, tuple[Q, Q], tuple[Q, Q], tuple[Q, Q]]]:
        """Exact ordered-domain decomposition after one dyadic bisection."""

        if kind == "off":
            return [("off", J1, J2, J3) for J1 in halves(I1) for J2 in halves(I2) for J3 in halves(I3)]
        if kind == "eq12":
            assert I1 == I2
            low, high = halves(I1)
            children = []
            for J3 in halves(I3):
                children.extend(
                    [("eq12", low, low, J3), ("off", high, low, J3), ("eq12", high, high, J3)]
                )
            return children
        if kind == "eq23":
            assert I2 == I3
            low, high = halves(I2)
            children = []
            for J1 in halves(I1):
                children.extend(
                    [("eq23", J1, low, low), ("off", J1, high, low), ("eq23", J1, high, high)]
                )
            return children
        assert kind == "eq123" and I1 == I2 == I3
        low, high = halves(I1)
        return [
            ("eq123", low, low, low),
            ("eq23", high, low, low),
            ("eq12", high, high, low),
            ("eq123", high, high, high),
        ]

    def process_cell(
        kind: str,
        I1: tuple[Q, Q],
        I2: tuple[Q, Q],
        I3: tuple[Q, Q],
        depth: int,
    ) -> None:
        nonlocal leaf_cells, refined_nodes
        label, theta, reason = classify_box(I1, I2, I3)
        if theta is not None:
            slo, shi = fixed_branch_s_range(theta, I1, I2, I3)
        else:
            theta_iv = flattened_theta_range(I1, I2, I3)
            qlo = theta_iv[0] - I1[1] - I2[1] - I3[1]
            qhi = theta_iv[1] - I1[0] - I2[0] - I3[0]
            slo = max(Q(0), qlo / I3[1])
            shi = max(Q(0), qhi / I3[0])
        assert shi <= delay.max_s

        needs_refinement = shi > 2 and (theta is None or slo < 2 or kind != "off")
        if depth > 0 and needs_refinement:
            refined_nodes += 1
            for child_kind, J1, J2, J3 in refined_children(kind, I1, I2, I3):
                process_cell(child_kind, J1, J2, J3, depth - 1)
            return

        leaf_cells += 1
        if theta is not None:
            branch_counts[label or "unknown"] = branch_counts.get(label or "unknown", 0) + 1
        else:
            ambiguity_counts[reason or "unknown"] = ambiguity_counts.get(reason or "unknown", 0) + 1
        weight = positive_weight(kind, I1, I2, I3)

        if shi <= 2:
            add(kind, "exact_f_zero", weight)
            return
        if kind == "off" and theta is not None and slo >= 2 and shi <= 3:
            tay = exact_f_second_order(theta, I1, I2, I3, egamma)
            delay_tay = delay_f_second_order(theta, I1, I2, I3, egamma, delay, shapes)
            flo, fhi = table.f_range(slo, shi)
            direct = iv_mul((Q(scale - fhi, scale), Q(scale - flo, scale)), weight)
            clipped = max(tay[0], delay_tay[0], direct[0]), min(tay[1], delay_tay[1], direct[1])
            assert clipped[0] <= clipped[1]
            add(kind, "fixed_branch_second_order_2_to_3", clipped)
            return
        if kind == "off" and theta is not None and slo >= 2:
            tay = delay_f_second_order(theta, I1, I2, I3, egamma, delay, shapes)
            flo, fhi = table.f_range(slo, shi)
            direct = iv_mul((Q(scale - fhi, scale), Q(scale - flo, scale)), weight)
            clipped = max(tay[0], direct[0]), min(tay[1], direct[1])
            assert clipped[0] <= clipped[1]
            add(kind, "fixed_branch_second_order_delay_intersected", clipped)
            return
        flo, fhi = table.f_range(max(Q(0), slo), shi)
        delta = (Q(scale - fhi, scale), Q(scale - flo, scale))
        mode = "fixed_branch_range" if theta is not None else f"ambiguous_range:{reason}"
        add(kind, mode, iv_mul(delta, weight))

    for i1, I1 in enumerate(intervals):
        for i2 in range(i1 + 1):
            I2 = intervals[i2]
            for i3 in range(i2 + 1):
                I3 = intervals[i3]
                cells += 1
                if i1 > i2 > i3:
                    kind = "off"
                elif i1 == i2 and i2 > i3:
                    kind = "eq12"
                elif i1 > i2 and i2 == i3:
                    kind = "eq23"
                else:
                    kind = "eq123"
                process_cell(kind, I1, I2, I3, refine_depth)

    v2_path = HERE / "g1-taylor-certificate-v2.json"
    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    fixed_lo = Q(128, 25)
    fixed_hi = Q(128, 25)
    for key in ("zero_dimensional_500_F_minus_1", "one_dimensional", "two_dimensional"):
        record = v2["corrections"][key]
        fixed_lo += parse_q(record["lower_exact"])
        fixed_hi += parse_q(record["upper_exact"])
    g1_lo, g1_hi = fixed_lo + total_lo, fixed_hi + total_hi
    paper = Q(606932, 100000)
    return {
        "boxes_per_doubling": boxes_per_doubling,
        "adaptive_refine_depth": refine_depth,
        "axis_intervals": len(intervals),
        "ordered_cells": cells,
        "evaluated_leaf_cells": leaf_cells,
        "refined_internal_nodes": refined_nodes,
        "triple_interval": BASE.interval_record(total_lo, total_hi, 15),
        "G1_interval_using_R031_nontriple_terms": BASE.interval_record(g1_lo, g1_hi, 15),
        "strictly_below_6_06932": g1_hi < paper,
        "upper_deficit": BASE.decimal_ceil(max(Q(0), g1_hi - paper), 15),
        "mode_counts": counts,
        "mode_widths": {key: BASE.decimal_ceil(value, 15) for key, value in sorted(widths.items())},
        "kind_mode_widths": {
            key: BASE.decimal_ceil(value, 15) for key, value in sorted(kind_widths.items())
        },
        "certified_branch_counts": dict(sorted(branch_counts.items())),
        "ambiguity_counts": dict(sorted(ambiguity_counts.items())),
        "R031_dependency": {
            "file": "artifacts/g1-taylor-certificate-v2.json",
            "sha256": hashlib.sha256(v2_path.read_bytes()).hexdigest(),
            "use": "Only the already-certified zero-, one-, and two-dimensional correction endpoints are reused.",
        },
    }


def build(args: argparse.Namespace) -> dict[str, object]:
    inventory = lattice_inventory(args.parts)
    cubature = branch_cubature(args.boxes, args.refine_depth)
    return {
        "schema": "li-g1-branch-cubature-prototype-v1",
        "verdict": "SHARP_BOUND_CERTIFIED" if cubature["strictly_below_6_06932"] else "PARTIAL_STRICT_CERTIFICATE",
        "proved_global_reductions": {
            "p2_dominated": (
                "For a<=z<=y<=x<=c and phi increasing on [a,c], "
                "phi(y)<=phi(x), so the p2 candidate never uniquely maximizes."
            ),
            "w_inner_reduction": (
                "A(r)=(66-34r)/107 exceeds B(r)=153/256-3r/8; "
                "1-2y exceeds B(z) on the full ordered domain. Hence "
                "w(x,y,z)=B(z) when x<=c-3z/4, and is zero otherwise."
            ),
            "w2_dominated": (
                "Whenever w(x,z,y)=B(y) is active, w(x,y,z)=B(z) is active; "
                "B(z)>=B(y), hence w2 is dominated globally."
            ),
            "w_gate_eliminated_in_outer_max": (
                "The w1 activation condition x+3z/4<=c is equivalent to "
                "B(z)>=phi(x); therefore max(phi(x), gated B(z))="
                "max(phi(x), B(z))."
            ),
            "psi_gates_eliminated_in_outer_max": (
                "For phi(x+z) and phi(y+z), failure of the corresponding psi "
                "gate implies that candidate is no larger than phi(x); whenever "
                "it can improve the outer maximum, the gate is automatic."
            ),
        },
        "remaining_exact_point_candidates": [
            "phi_t",
            "phi_tu",
            "phi_tuv",
            "beta_v",
            "phi_tv",
            "phi_uv",
        ],
        "lattice_inventory": inventory,
        "branch_cubature": cubature,
        "limitations": [
            "The lattice inventory is exploratory and is not used to certify a branch partition.",
            "Second-order weighted Taylor cubature is used only on certified off-diagonal affine-branch cells wholly inside 2<=s<=3; all other cells retain directed range bounds.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--parts", type=int, default=48)
    parser.add_argument("--boxes", type=int, default=12, help="rational boxes per doubling band")
    parser.add_argument(
        "--refine-depth",
        type=int,
        default=1,
        help="recursive ordered-domain bisection depth for ambiguous, diagonal, and s=2 crossing cells",
    )
    args = parser.parse_args()
    result = build(args)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "branch_cubature": result["branch_cubature"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
