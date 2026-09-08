"""Strict local polynomial models for g(s)=q-2*a(s)/s on one delay cell.

This is an isolated building block for a future Li-equation-(14) certificate.
It does not construct the equation-(14) geometry and does not integrate its
triple term.  For a mesh cell

    s = c + u,  c = j/mesh,  0 <= u <= 1/mesh,

``g_cell_model`` returns directed polynomial coefficients and one uniform
remainder interval.  For c>=1 it reuses ``FixedDelayTaylor._quotient_model``.
For c<1, where the delay table is intentionally absent and a(s)=1, it uses
the exact finite geometric identity for 1/(c+u).

Running the file performs only local, non-workspace self-tests and prints a
JSON report.  No proof status is changed by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import certify_g1_taylor as G
import certify_li_equation14_polytope_taylor as B


Interval = tuple[Q, Q]
ZERO: Interval = (Q(0), Q(0))


def iv_add(first: Interval, second: Interval) -> Interval:
    return first[0] + second[0], first[1] + second[1]


def iv_mul(first: Interval, second: Interval) -> Interval:
    values = (
        first[0] * second[0],
        first[0] * second[1],
        first[1] * second[0],
        first[1] * second[1],
    )
    return min(values), max(values)


def iv_scale(interval: Interval, scalar: Q) -> Interval:
    """Scale an interval, reversing directed endpoints for a negative scalar."""

    if scalar >= 0:
        return interval[0] * scalar, interval[1] * scalar
    return interval[1] * scalar, interval[0] * scalar


def assert_contains(outer: Interval, inner: Interval) -> None:
    assert outer[0] <= inner[0] <= inner[1] <= outer[1], (outer, inner)


@dataclass(frozen=True)
class GCellModel:
    """Directed polynomial plus a single pointwise-uniform remainder."""

    cell_index: int
    mesh: int
    degree: int
    origin: Q
    width: Q
    coefficients: tuple[Interval, ...]
    remainder: Interval
    source: str
    ratio_remainder_units: int | None = None
    scale: int | None = None

    def __post_init__(self) -> None:
        assert self.cell_index > 0
        assert self.mesh >= 2 and self.degree >= 0
        assert self.origin > 0 and self.width > 0
        assert len(self.coefficients) == self.degree + 1
        assert self.remainder[0] <= self.remainder[1]

    @property
    def end(self) -> Q:
        return self.origin + self.width

    def polynomial_point(self, u: Q) -> Interval:
        assert 0 <= u <= self.width
        value = ZERO
        for coefficient in reversed(self.coefficients):
            value = iv_add(iv_scale(value, u), coefficient)
        return value

    def point(self, u: Q) -> Interval:
        return iv_add(self.polynomial_point(u), self.remainder)

    def point_at_s(self, s: Q) -> Interval:
        assert self.origin <= s <= self.end
        return self.point(s - self.origin)

    def remainder_budget(self, u0: Q, u1: Q) -> Interval:
        assert 0 <= u0 <= u1 <= self.width
        return iv_scale(self.remainder, u1 - u0)

    def integral(self, u0: Q = Q(0), u1: Q | None = None) -> Interval:
        """Enclose integral_{u0}^{u1} g(origin+u) du coefficientwise."""

        right = self.width if u1 is None else u1
        assert 0 <= u0 <= right <= self.width
        total = ZERO
        for power, coefficient in enumerate(self.coefficients):
            moment = (right ** (power + 1) - u0 ** (power + 1)) / (power + 1)
            assert moment >= 0
            total = iv_add(total, iv_scale(coefficient, moment))
        return iv_add(total, self.remainder_budget(u0, right))

    def record(self) -> dict[str, object]:
        return {
            "cell_index": self.cell_index,
            "origin_exact": G.frac(self.origin),
            "end_exact": G.frac(self.end),
            "degree": self.degree,
            "source": self.source,
            "coefficient_count": len(self.coefficients),
            "uniform_remainder": G.interval_record(*self.remainder, 24),
            "ratio_remainder_units": self.ratio_remainder_units,
            "fixed_scale": self.scale,
        }


def _ratio_to_g_coefficients(ratio_coefficients: tuple[Interval, ...]) -> tuple[Interval, ...]:
    coefficients = []
    for power, ratio in enumerate(ratio_coefficients):
        coefficient = iv_scale(ratio, Q(-2))
        if power == 0:
            coefficient = iv_add((B.QSTAR, B.QSTAR), coefficient)
        coefficients.append(coefficient)
    return tuple(coefficients)


def _explicit_reciprocal_model(delay: G.FixedDelayTaylor, j: int) -> GCellModel:
    """Exact finite geometric model for cells below s=1."""

    c = Q(j, delay.mesh)
    h = Q(1, delay.mesh)
    assert 0 < c < 1 and c + h <= 1
    ratio_coefficients = tuple(
        ((Q((-1) ** power, 1) / c ** (power + 1)),) * 2
        for power in range(delay.degree + 1)
    )
    # Exact identity:
    # 1/(c+u)-sum_{k=0}^n (-1)^k u^k/c^(k+1)
    #   = (-1)^(n+1) u^(n+1)/(c^(n+1)*(c+u)).
    # Its magnitude is increasing on 0<=u<=h.
    magnitude = h ** (delay.degree + 1) / (
        c ** (delay.degree + 1) * (c + h)
    )
    ratio_remainder = (
        (Q(0), magnitude)
        if (delay.degree + 1) % 2 == 0
        else (-magnitude, Q(0))
    )
    return GCellModel(
        cell_index=j,
        mesh=delay.mesh,
        degree=delay.degree,
        origin=c,
        width=h,
        coefficients=_ratio_to_g_coefficients(ratio_coefficients),
        remainder=iv_scale(ratio_remainder, Q(-2)),
        source="explicit-geometric-a-over-s",
    )


def g_cell_model(delay: G.FixedDelayTaylor, j: int) -> GCellModel:
    """Return a rigorous model for g on [j/mesh,(j+1)/mesh]."""

    if j <= 0:
        raise ValueError("the cell must stay strictly to the right of s=0")
    c = Q(j, delay.mesh)
    h = Q(1, delay.mesh)
    if c + h > delay.max_s:
        raise ValueError("cell exceeds the constructed delay table")
    if c < 1:
        return _explicit_reciprocal_model(delay, j)

    source = delay.a[j]
    ratio = delay._quotient_model(source, c)
    ratio_coefficients = tuple(
        (Q(lo, delay.scale), Q(hi, delay.scale)) for lo, hi in ratio.coeff
    )
    error = Q(ratio.error, delay.scale)
    return GCellModel(
        cell_index=j,
        mesh=delay.mesh,
        degree=delay.degree,
        origin=c,
        width=h,
        coefficients=_ratio_to_g_coefficients(ratio_coefficients),
        remainder=(-2 * error, 2 * error),
        source="FixedDelayTaylor._quotient_model(a[j],j/mesh)",
        ratio_remainder_units=ratio.error,
        scale=delay.scale,
    )


def reference_g(delay: G.FixedDelayTaylor, s: Q) -> Interval:
    """Independent point enclosure from the explicit branch or shape_point."""

    assert 0 < s <= delay.max_s
    if s <= 3:
        value = B.QSTAR - 2 / s
        return value, value
    alo, ahi = delay.shape_point("a", s)
    ratio = Q(alo, delay.scale) / s, Q(ahi, delay.scale) / s
    return B.QSTAR - 2 * ratio[1], B.QSTAR - 2 * ratio[0]


def exact_explicit_integral(c: Q, h: Q) -> Interval:
    """Independent enclosure of integral_c^(c+h) (q-2/s) ds."""

    log_ratio = G.log_interval((c + h) / c, 192)
    return iv_add((B.QSTAR * h, B.QSTAR * h), iv_scale(log_ratio, Q(-2)))


def run_self_tests(delay: G.FixedDelayTaylor) -> tuple[list[dict[str, object]], list[GCellModel]]:
    if delay.max_s <= 5:
        raise ValueError("self-tests require max_s>5")
    tests: list[dict[str, object]] = []
    selected: list[GCellModel] = []
    h = Q(1, delay.mesh)

    # Explicit s<1 branch, including its one-sided geometric remainder.
    low_j = max(1, G.floor_q(Q(59, 100), delay.mesh))
    if low_j >= delay.mesh:
        low_j = delay.mesh - 1
    low = g_cell_model(delay, low_j)
    selected.append(low)
    for u in (Q(0), h / 3, 2 * h / 3, h):
        assert_contains(low.point(u), reference_g(delay, low.origin + u))
        exact_delta = reference_g(delay, low.origin + u)[0] - low.polynomial_point(u)[0]
        assert low.remainder[0] <= exact_delta <= low.remainder[1]
    assert_contains(low.integral(), exact_explicit_integral(low.origin, h))
    tests.append({"name": "s_below_1_explicit_model_and_integral", "status": "PASS"})

    # Both closed-cell models must contain the exact value at s=1.
    left_one = g_cell_model(delay, delay.mesh - 1)
    right_one = g_cell_model(delay, delay.mesh)
    exact_one = (B.QSTAR - 2, B.QSTAR - 2)
    assert_contains(left_one.point(h), exact_one)
    assert_contains(right_one.point(Q(0)), exact_one)
    tests.append({"name": "s_equals_1_two_sided_boundary", "status": "PASS"})

    # The explicit a=1 identity remains valid at s=3 from both adjacent cells.
    left_three = g_cell_model(delay, 3 * delay.mesh - 1)
    right_three = g_cell_model(delay, 3 * delay.mesh)
    exact_three = (B.QSTAR - Q(2, 3), B.QSTAR - Q(2, 3))
    assert_contains(left_three.point(h), exact_three)
    assert_contains(right_three.point(Q(0)), exact_three)
    tests.append({"name": "s_equals_3_two_sided_boundary", "status": "PASS"})

    # A non-special mesh boundary above 3 checks adjacent delay models.
    boundary_index = 4 * delay.mesh + 1
    boundary_s = Q(boundary_index, delay.mesh)
    left_regular = g_cell_model(delay, boundary_index - 1)
    right_regular = g_cell_model(delay, boundary_index)
    reference = reference_g(delay, boundary_s)
    assert_contains(left_regular.point(h), reference)
    assert_contains(right_regular.point(Q(0)), reference)
    selected.append(right_regular)
    tests.append({"name": "ordinary_mesh_boundary_two_sided", "status": "PASS"})

    # Explicitly guard the endpoint reversal used in g=q-2(a/s).
    assert iv_scale((Q(2), Q(5)), Q(-2)) == (Q(-10), Q(-4))
    ratio = delay._quotient_model(delay.a[boundary_index], boundary_s)
    expected = tuple(
        iv_scale((Q(lo, delay.scale), Q(hi, delay.scale)), Q(-2))
        for lo, hi in ratio.coeff
    )
    for power in range(1, delay.degree + 1):
        assert right_regular.coefficients[power] == expected[power]
    tests.append({"name": "negative_coefficient_endpoint_reversal", "status": "PASS"})

    # The quotient error is one pointwise-uniform remainder.  Its integral
    # budget is therefore remainder*length, and splitting a cell is additive.
    expected_error = Q(2 * ratio.error, delay.scale)
    assert right_regular.remainder == (-expected_error, expected_error)
    assert right_regular.integral() == iv_add(
        right_regular.integral(Q(0), h / 2),
        right_regular.integral(h / 2, h),
    )
    assert low.integral() == iv_add(low.integral(Q(0), h / 2), low.integral(h / 2, h))
    tests.append({"name": "uniform_remainder_integral_budget", "status": "PASS"})

    # Point probes inside an ordinary delay cell validate the transformed
    # quotient model against shape_point without using a primitive difference.
    for u in (Q(0), h / 4, h / 2, 3 * h / 4, h):
        assert_contains(right_regular.point(u), reference_g(delay, right_regular.origin + u))
    tests.append({"name": "ordinary_cell_point_enclosures", "status": "PASS"})

    return tests, selected


def certify_local_models(args: argparse.Namespace) -> dict[str, object]:
    if not __debug__:
        raise RuntimeError("self-tests require assertions; optimized Python is unsupported")
    delay = G.FixedDelayTaylor(args.mesh, args.degree, args.max_s, args.dyadic_bits)
    tests, selected = run_self_tests(delay)
    dependencies = [
        HERE / "certify_g1_taylor.py",
        HERE / "certify_li_equation14_polytope_taylor.py",
    ]
    return {
        "schema": "li-equation14-g-cell-model-selftest-v1",
        "verdict": "LOCAL_G_CELL_MODEL_SELFTEST_PASS",
        "scope": "Local delay-cell polynomial enclosures only; equation (14) is not evaluated.",
        "parameters": {
            "mesh": args.mesh,
            "degree": args.degree,
            "max_s": args.max_s,
            "dyadic_bits": args.dyadic_bits,
        },
        "selected_models": [model.record() for model in selected],
        "self_tests": tests,
        "dependencies_sha256": {
            dependency.name: hashlib.sha256(dependency.read_bytes()).hexdigest()
            for dependency in dependencies
        },
        "limitations": [
            "No equation-(14) winner geometry, positive moments, or triple integral is computed.",
            "Ordinary-cell probes reuse the inherited FixedDelayTaylor value enclosures; they test integration and transformation wiring but do not independently re-prove its uniform quotient remainder.",
            "A passing local self-test does not change W050 or the Goldbach dossier verdict.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mesh", type=int, default=8)
    parser.add_argument("--degree", type=int, default=16)
    parser.add_argument("--max-s", type=int, default=300)
    parser.add_argument("--dyadic-bits", type=int, default=96)
    args = parser.parse_args()
    result = certify_local_models(args)
    result["program_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
