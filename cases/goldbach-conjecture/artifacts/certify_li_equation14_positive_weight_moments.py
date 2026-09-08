"""Strict order-0--2 centroid moments of Li equation (14)'s positive weight.

For one exact rational triangle and positive affine fiber bounds L<=U,

    W(x,y) = (U-L)/(x*y*L*U) >= 0.

The triangle is cut exactly by x=cx and y=cy, where c is the original
triangle centroid.  Every resulting subtriangle has a fixed sign for each
monomial (x-cx)^i (y-cy)^j.  A directed positive-factor range of W then
multiplies the exact monomial integral.  Subsequent midpoint four-splits
refine those sign-fixed triangles, so the raw enclosures are nested; an
explicit cumulative intersection is retained as an additional guard.

No derivative of W is formed.  This file certifies only a reusable moment
component.  It does not evaluate Li equation (14) or change any dossier
verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import certify_li_equation14_fiber_primitive as F
import certify_li_equation14_fiber_taylor_v2 as V2


B = F.B
G = F.G
Interval = B.Interval
Triangle = F.Triangle
Point2 = F.Point2
Affine = B.BR.Affine
ZERO: Interval = (Q(0), Q(0))
MOMENTS = ((0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2))
MomentKey = tuple[int, int]
WeightRange = Callable[[Triangle], Interval]


def iv_add(first: Interval, second: Interval) -> Interval:
    return first[0] + second[0], first[1] + second[1]


def iv_scale(interval: Interval, scalar: Q) -> Interval:
    if scalar >= 0:
        return interval[0] * scalar, interval[1] * scalar
    return interval[1] * scalar, interval[0] * scalar


def interval_intersection(first: Interval, second: Interval) -> Interval:
    answer = max(first[0], second[0]), min(first[1], second[1])
    assert answer[0] <= answer[1], (first, second)
    return answer


def interval_subset(inner: Interval, outer: Interval) -> bool:
    return outer[0] <= inner[0] <= inner[1] <= outer[1]


def affine_range(affine: Affine, triangle: Triangle) -> Interval:
    values = [affine.at(x, y, Q(0)) for x, y in triangle]
    return min(values), max(values)


def centroid(triangle: Triangle) -> Point2:
    return tuple(
        sum((point[index] for point in triangle), Q(0)) / 3
        for index in range(2)
    )  # type: ignore[return-value]


def monomial_integral(
    triangle: Triangle, center: Point2, x_power: int, y_power: int
) -> Q:
    """Exact integral through total degree two on a rational triangle."""

    assert x_power >= 0 and y_power >= 0 and x_power + y_power <= 2
    area = F.triangle_area(triangle)
    if x_power == y_power == 0:
        return area
    fx = [point[0] - center[0] for point in triangle]
    fy = [point[1] - center[1] for point in triangle]
    if (x_power, y_power) == (1, 0):
        return area * sum(fx, Q(0)) / 3
    if (x_power, y_power) == (0, 1):
        return area * sum(fy, Q(0)) / 3
    first = fx if x_power else fy
    second = fy if y_power else fx
    expectation = (
        sum(first, Q(0)) * sum(second, Q(0))
        + sum((a * b for a, b in zip(first, second, strict=True)), Q(0))
    ) / 12
    return area * expectation


@dataclass(frozen=True)
class SignedTriangle:
    triangle: Triangle
    x_sign: int
    y_sign: int

    def __post_init__(self) -> None:
        assert self.x_sign in (-1, 1) and self.y_sign in (-1, 1)
        assert F.triangle_area(self.triangle) > 0

    def monomial_sign(self, index: MomentKey) -> int:
        i, j = index
        return (self.x_sign if i % 2 else 1) * (
            self.y_sign if j % 2 else 1
        )


def sign_fixed_triangles(triangle: Triangle, center: Point2) -> list[SignedTriangle]:
    """Cut exactly into x/y centroid quadrants and triangulate each polygon."""

    answer: list[SignedTriangle] = []
    total_area = Q(0)
    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            polygon = list(triangle)
            x_halfspace = (
                B.BR.X - Affine(center[0])
                if x_sign > 0
                else Affine(center[0]) - B.BR.X
            )
            y_halfspace = (
                B.BR.Y - Affine(center[1])
                if y_sign > 0
                else Affine(center[1]) - B.BR.Y
            )
            polygon = V2.clip_polygon(polygon, x_halfspace)
            polygon = V2.clip_polygon(polygon, y_halfspace)
            if len(polygon) < 3:
                continue
            for child in F.polygon_triangles(polygon):
                area = F.triangle_area(child)
                if area == 0:
                    continue
                total_area += area
                signed = SignedTriangle(child, x_sign, y_sign)
                for i, j in MOMENTS:
                    integral = monomial_integral(child, center, i, j)
                    assert integral * signed.monomial_sign((i, j)) >= 0
                answer.append(signed)
    assert total_area == F.triangle_area(triangle)
    return answer


def refine_signed_triangles(items: list[SignedTriangle]) -> list[SignedTriangle]:
    answer = []
    for item in items:
        parent_area = F.triangle_area(item.triangle)
        children = F.split_triangle(item.triangle)
        assert sum((F.triangle_area(child) for child in children), Q(0)) == parent_area
        answer.extend(
            SignedTriangle(child, item.x_sign, item.y_sign) for child in children
        )
    return answer


@dataclass(frozen=True)
class PositiveFiberWeight:
    lower: Affine
    upper: Affine

    def range(self, triangle: Triangle) -> Interval:
        xr = min(point[0] for point in triangle), max(point[0] for point in triangle)
        yr = min(point[1] for point in triangle), max(point[1] for point in triangle)
        lr = affine_range(self.lower, triangle)
        ur = affine_range(self.upper, triangle)
        tr = affine_range(self.upper - self.lower, triangle)
        assert xr[0] > 0 and yr[0] > 0
        assert lr[0] > 0 and ur[0] > 0
        assert tr[0] >= 0 and tr[1] >= 0
        if tr[1] == 0:
            return ZERO
        # Every factor in (U-L)*(1/x)*(1/y)*(1/L)*(1/U) is nonnegative.
        lower = tr[0] / (xr[1] * yr[1] * lr[1] * ur[1])
        upper = tr[1] / (xr[0] * yr[0] * lr[0] * ur[0])
        assert 0 <= lower <= upper
        return lower, upper

    def record(self) -> dict[str, object]:
        def affine_record(value: Affine) -> dict[str, str]:
            return {
                "constant": G.frac(value.c),
                "x": G.frac(value.x),
                "y": G.frac(value.y),
            }

        return {"lower": affine_record(self.lower), "upper": affine_record(self.upper)}


@dataclass(frozen=True)
class MomentBundle:
    signed: dict[MomentKey, Interval]
    absolute: dict[MomentKey, Interval]

    def __post_init__(self) -> None:
        assert set(self.signed) == set(MOMENTS)
        assert set(self.absolute) == set(MOMENTS)
        for index in MOMENTS:
            signed = self.signed[index]
            absolute = self.absolute[index]
            assert signed[0] <= signed[1]
            assert 0 <= absolute[0] <= absolute[1]
            assert -absolute[1] <= signed[0] <= signed[1] <= absolute[1]

    def intersect(self, other: "MomentBundle") -> "MomentBundle":
        return MomentBundle(
            signed={
                index: interval_intersection(self.signed[index], other.signed[index])
                for index in MOMENTS
            },
            absolute={
                index: interval_intersection(
                    self.absolute[index], other.absolute[index]
                )
                for index in MOMENTS
            },
        )

    def is_subset_of(self, other: "MomentBundle") -> bool:
        return all(
            interval_subset(self.signed[index], other.signed[index])
            and interval_subset(self.absolute[index], other.absolute[index])
            for index in MOMENTS
        )

    def record(self, places: int = 18) -> dict[str, object]:
        def records(values: dict[MomentKey, Interval]) -> dict[str, object]:
            return {
                f"{i}{j}": G.interval_record(*values[i, j], places=places)
                for i, j in MOMENTS
            }

        return {"signed": records(self.signed), "absolute": records(self.absolute)}


def enclose_on_partition(
    items: list[SignedTriangle], center: Point2, weight_range: WeightRange
) -> MomentBundle:
    signed = {index: ZERO for index in MOMENTS}
    absolute = {index: ZERO for index in MOMENTS}
    for item in items:
        wrange = weight_range(item.triangle)
        assert 0 <= wrange[0] <= wrange[1]
        for index in MOMENTS:
            integral = monomial_integral(item.triangle, center, *index)
            sign = item.monomial_sign(index)
            assert integral * sign >= 0
            signed[index] = iv_add(signed[index], iv_scale(wrange, integral))
            absolute[index] = iv_add(
                absolute[index], iv_scale(wrange, sign * integral)
            )
    return MomentBundle(signed=signed, absolute=absolute)


def moment_sequence(
    triangle: Triangle, weight_range: WeightRange, max_depth: int
) -> tuple[list[dict[str, object]], MomentBundle]:
    assert max_depth >= 0
    center = centroid(triangle)
    pieces = sign_fixed_triangles(triangle, center)
    checkpoints: list[dict[str, object]] = []
    previous_raw: MomentBundle | None = None
    nested: MomentBundle | None = None
    for depth in range(max_depth + 1):
        raw = enclose_on_partition(pieces, center, weight_range)
        if previous_raw is not None:
            assert raw.is_subset_of(previous_raw), (depth, raw, previous_raw)
        nested = raw if nested is None else nested.intersect(raw)
        if previous_raw is not None:
            assert nested.is_subset_of(previous_raw)
        checkpoints.append(
            {
                "midpoint_depth": depth,
                "sign_fixed_leaf_triangles": len(pieces),
                "raw": raw.record(),
                "nested_intersection": nested.record(),
            }
        )
        previous_raw = raw
        if depth < max_depth:
            pieces = refine_signed_triangles(pieces)
    assert nested is not None
    return checkpoints, nested


def exact_reference_moments() -> tuple[dict[MomentKey, Q], dict[MomentKey, Q]]:
    """Hard-coded moments of the standard triangle about (1/3,1/3)."""

    signed = {
        (0, 0): Q(1, 2),
        (1, 0): Q(0),
        (0, 1): Q(0),
        (2, 0): Q(1, 36),
        (1, 1): Q(-1, 72),
        (0, 2): Q(1, 36),
    }
    absolute = {
        (0, 0): Q(1, 2),
        (1, 0): Q(8, 81),
        (0, 1): Q(8, 81),
        (2, 0): Q(1, 36),
        (1, 1): Q(41, 1944),
        (0, 2): Q(1, 36),
    }
    return signed, absolute


def constant_weight_test(max_depth: int) -> dict[str, object]:
    triangle: Triangle = ((Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1)))
    weight = Q(7, 5)

    def constant_range(_: Triangle) -> Interval:
        return weight, weight

    checkpoints, final = moment_sequence(triangle, constant_range, max_depth)
    exact_signed, exact_absolute = exact_reference_moments()
    for index in MOMENTS:
        expected_signed = (weight * exact_signed[index],) * 2
        expected_absolute = (weight * exact_absolute[index],) * 2
        assert final.signed[index] == expected_signed
        assert final.absolute[index] == expected_absolute
        for checkpoint in checkpoints:
            raw = checkpoint["raw"]
            assert isinstance(raw, dict)
    return {
        "status": "PASS",
        "weight_exact": G.frac(weight),
        "triangle": [[G.frac(x), G.frac(y)] for x, y in triangle],
        "hard_coded_exact_moments_verified": True,
        "depths_verified": max_depth + 1,
    }


def first_real_fiber_triangle() -> tuple[B.BranchPiece, Triangle, Affine, Affine]:
    for piece in B.theta_branch_polytopes():
        for polygon, lower, upper in F.fiber_cells(piece):
            for triangle in F.polygon_triangles(polygon):
                center = centroid(triangle)
                if (upper - lower).at(center[0], center[1], Q(0)) <= 0:
                    continue
                return piece, triangle, lower, upper
    raise AssertionError("no positive real fiber triangle found")


def real_fiber_test(max_depth: int) -> dict[str, object]:
    piece, triangle, lower, upper = first_real_fiber_triangle()
    weight = PositiveFiberWeight(lower, upper)
    checkpoints, final = moment_sequence(triangle, weight.range, max_depth)
    # The construction proves |signed moment| <= absolute moment.  These
    # endpoint checks ensure the computed outer intervals retain that fact.
    for index in MOMENTS:
        signed = final.signed[index]
        absolute = final.absolute[index]
        assert absolute[0] >= 0
        assert max(abs(signed[0]), abs(signed[1])) <= absolute[1]
    assert [checkpoint["midpoint_depth"] for checkpoint in checkpoints] == list(
        range(max_depth + 1)
    )
    return {
        "status": "PASS",
        "winner": piece.label,
        "theta": {
            "constant": G.frac(piece.theta.c),
            "x": G.frac(piece.theta.x),
            "y": G.frac(piece.theta.y),
            "z": G.frac(piece.theta.z),
        },
        "triangle": [[G.frac(x), G.frac(y)] for x, y in triangle],
        "centroid": [G.frac(value) for value in centroid(triangle)],
        "fiber_bounds": weight.record(),
        "signed_absolute_dominance_verified": True,
        "raw_refinement_nesting_verified": True,
        "checkpoints": checkpoints,
        "final_nested_moments": final.record(),
    }


def zero_thickness_test() -> dict[str, object]:
    triangle: Triangle = ((Q(1), Q(1)), (Q(2), Q(1)), (Q(1), Q(2)))
    bound = Affine(Q(3), Q(1, 5), Q(1, 7))
    weight = PositiveFiberWeight(bound, bound)
    checkpoints, final = moment_sequence(triangle, weight.range, 1)
    for index in MOMENTS:
        assert final.signed[index] == ZERO
        assert final.absolute[index] == ZERO
    return {
        "status": "PASS",
        "all_signed_and_absolute_moments_exactly_zero": True,
        "depths_verified": len(checkpoints),
    }


def certify_component(args: argparse.Namespace) -> dict[str, object]:
    if not __debug__:
        raise RuntimeError("component self-tests require assertions; optimized Python is unsupported")
    constant = constant_weight_test(args.max_depth)
    real = real_fiber_test(args.max_depth)
    zero_thickness = zero_thickness_test()
    dependencies = (
        HERE / "certify_li_equation14_fiber_primitive.py",
        HERE / "certify_li_equation14_fiber_taylor_v2.py",
    )
    return {
        "schema": "li-equation14-positive-weight-moments-component-v1",
        "verdict": "STRICT_POSITIVE_WEIGHT_MOMENT_COMPONENT_ONLY",
        "scope": {
            "certifies": (
                "Directed signed and absolute centroid moments through total degree two "
                "for W=(U-L)/(x*y*L*U) on one exact rational fiber triangle."
            ),
            "does_not_certify": [
                "Li equation (14)",
                "the equation-(14) triple integral",
                "the S2/M lower bound",
                "the strong Goldbach conjecture",
            ],
        },
        "parameters": {"maximum_midpoint_depth": args.max_depth},
        "method": {
            "sign_partition": "Exact clipping at x=cx and y=cy, followed by rational triangulation.",
            "weight": "Positive-factor directed range of (U-L)*(1/x)*(1/y)*(1/L)*(1/U).",
            "moments": "Exact rational monomial integrals for total degree 0, 1, and 2.",
            "refinement": "Exact midpoint four-splits inside sign-fixed triangles; raw nesting asserted and cumulative intersection retained.",
            "weight_derivatives_used": False,
        },
        "self_tests": {
            "constant_weight_manufactured": constant,
            "real_fiber_triangle_smoke": real,
            "zero_thickness_fiber": zero_thickness,
        },
        "dependencies_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in dependencies
        },
        "limitations": [
            "Only one real fiber triangle is exercised by the smoke test.",
            "The moment intervals have not yet been coupled to a Taylor model for the averaged g factor.",
            "No equation-(14) coefficient or dossier verdict is changed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-depth", type=int, default=2)
    args = parser.parse_args()
    if args.max_depth < 0 or args.max_depth > 5:
        parser.error("require 0 <= max-depth <= 5")
    result = certify_component(args)
    result["program_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
