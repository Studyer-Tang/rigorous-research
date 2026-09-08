"""Strict dimension-reduced smoke for Li equation (14)'s triple term.

For a fixed affine theta winner write

    s = e + D(x,y)/z,
    e = theta.z-1,
    D = theta.c + (theta.x-1)*x + (theta.y-1)*y.

Every winner polytope is decomposed into exact vertical-fiber cells on which
the lower and upper z envelopes are fixed affine functions L(x,y), U(x,y).
Since ds = -D dz/z**2,

    int_L^U (q-Fbar(s))/(x*y*z**2) dz
      = (P(s(L))-P(s(U)))/(x*y*D),

where P'=q-Fbar.  The delay equation gives the particularly sharp primitive

    P(s)=q*s-2*b(s+1)        (s>=1),
    P(s)=q*s-2*log(s)        (0<s<=1).

The remaining two-dimensional integral is enclosed by exact rational
triangle range sums and widest-first four-child refinement.  This is a smoke
certificate; W050 remains IN_PROGRESS pending a sharper Taylor stage and
independent audit.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from fractions import Fraction as Q
from pathlib import Path

import certify_li_equation14_polytope_taylor as B

G = B.G
HERE = Path(__file__).resolve().parent
Point2 = tuple[Q, Q]
Triangle = tuple[Point2, Point2, Point2]
Interval = B.Interval


def solve_lines(a: B.BR.Affine, b: B.BR.Affine) -> Point2 | None:
    det = a.x * b.y - a.y * b.x
    if det == 0:
        return None
    return (a.y * b.c - a.c * b.y) / det, (a.c * b.x - a.x * b.c) / det


def polygon_vertices(constraints: list[B.BR.Affine]) -> list[Point2]:
    lines = B.unique_planes(constraints)
    points: set[Point2] = set()
    for index, first in enumerate(lines):
        for second in lines[index + 1 :]:
            point = solve_lines(first, second)
            if point is not None and all(item.at(point[0], point[1], Q(0)) >= 0 for item in constraints):
                points.add(point)
    projected = sorted(points)
    if len(projected) < 3:
        return []

    def build(items):
        hull = []
        for point in items:
            while len(hull) >= 2 and B.cross2(hull[-2], hull[-1], point) <= 0:
                hull.pop()
            hull.append(point)
        return hull

    lower = build(projected)
    upper = build(reversed(projected))
    return lower[:-1] + upper[:-1]


def triangle_area(triangle: Triangle) -> Q:
    a, b, c = triangle
    return abs(B.cross2(a, b, c)) / 2


def polygon_triangles(polygon: list[Point2]) -> list[Triangle]:
    return [
        (polygon[0], polygon[index], polygon[index + 1])
        for index in range(1, len(polygon) - 1)
        if triangle_area((polygon[0], polygon[index], polygon[index + 1])) > 0
    ]


def affine_integral_triangle(affine: B.BR.Affine, triangle: Triangle) -> Q:
    area = triangle_area(triangle)
    center = tuple(sum((point[i] for point in triangle), Q(0)) / 3 for i in range(2))
    return area * affine.at(center[0], center[1], Q(0))


def midpoint(a: Point2, b: Point2) -> Point2:
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


def split_triangle(triangle: Triangle) -> tuple[Triangle, Triangle, Triangle, Triangle]:
    a, b, c = triangle
    ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
    children = ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))
    assert sum((triangle_area(child) for child in children), Q(0)) == triangle_area(triangle)
    return children


def z_bound(constraint: B.BR.Affine) -> B.BR.Affine:
    assert constraint.z != 0
    return B.BR.Affine(
        -constraint.c / constraint.z,
        -constraint.x / constraint.z,
        -constraint.y / constraint.z,
    )


class Primitive:
    def __init__(self, delay: G.FixedDelayTaylor, bits: int):
        self.delay = delay
        self.scale = delay.scale
        self.bits = bits
        self.ratio = B.ARatioDerivatives(delay)
        self.point_cache: dict[Q, Interval] = {}

    def point(self, s: Q) -> Interval:
        assert s > 0 and s + 1 <= self.delay.max_s
        cached = self.point_cache.get(s)
        if cached is not None:
            return cached
        if s <= 1:
            log_interval = G.outward_dyadic(*G.log_interval(s, 160), self.bits)
            result = B.QSTAR * s - 2 * log_interval[1], B.QSTAR * s - 2 * log_interval[0]
        else:
            blo, bhi = self.delay.shape_point("b", s + 1)
            result = (
                B.QSTAR * s - 2 * Q(bhi, self.scale),
                B.QSTAR * s - 2 * Q(blo, self.scale),
            )
        result = G.outward_dyadic(*result, self.bits)
        self.point_cache[s] = result
        return result

    def derivative_range(self, lo: Q, hi: Q) -> Interval:
        r = self.ratio.ranges(lo, hi)[0]
        return B.QSTAR - 2 * r[1], B.QSTAR - 2 * r[0]

    def range(self, lo: Q, hi: Q) -> Interval:
        assert 0 < lo <= hi
        if lo == hi:
            return self.point(lo)
        cuts = sorted({lo, hi, *[value for value in (Q(1), Q(3)) if lo < value < hi]})
        ranges: list[Interval] = []
        for left, right in zip(cuts, cuts[1:]):
            center = (left + right) / 2
            base = self.point(center)
            derivative = self.derivative_range(left, right)
            displacement = left - center, right - center
            ranges.append(B.iv_add(base, B.iv_mul(derivative, displacement)))
        return min(item[0] for item in ranges), max(item[1] for item in ranges)


def fiber_cells(piece: B.BranchPiece) -> list[tuple[list[Point2], B.BR.Affine, B.BR.Affine]]:
    planar: list[B.BR.Affine] = []
    lowers: list[B.BR.Affine] = []
    uppers: list[B.BR.Affine] = []
    for constraint in piece.constraints:
        if constraint.z > 0:
            lowers.append(z_bound(constraint))
        elif constraint.z < 0:
            uppers.append(z_bound(constraint))
        else:
            planar.append(constraint)
    # Different half-space constraints can induce the same vertical bound.
    # They are harmless as constraints but must not be enumerated twice as
    # candidate active envelopes, or their positive-area projection cell is
    # double counted.
    def deduplicate(items: list[B.BR.Affine]) -> list[B.BR.Affine]:
        unique: dict[tuple[Q, Q, Q, Q], B.BR.Affine] = {}
        for item in items:
            unique.setdefault((item.c, item.x, item.y, item.z), item)
        return list(unique.values())

    planar = deduplicate(planar)
    lowers = deduplicate(lowers)
    uppers = deduplicate(uppers)
    assert lowers and uppers
    cells = []
    for lower in lowers:
        for upper in uppers:
            constraints = [
                *planar,
                *(lower - other for other in lowers),
                *(other - upper for other in uppers),
                upper - lower,
            ]
            polygon = polygon_vertices(constraints)
            if polygon and sum((triangle_area(t) for t in polygon_triangles(polygon)), Q(0)) > 0:
                cells.append((polygon, lower, upper))
    return cells


def triangle_interval(
    triangle: Triangle,
    lower: B.BR.Affine,
    upper: B.BR.Affine,
    theta: B.BR.Affine,
    primitive: Primitive,
) -> Interval:
    d_affine = B.BR.Affine(theta.c, theta.x - 1, theta.y - 1)
    e = theta.z - 1
    data = []
    for x, y in triangle:
        d = d_affine.at(x, y, Q(0))
        zl = lower.at(x, y, Q(0))
        zu = upper.at(x, y, Q(0))
        assert d > 0 and 0 < zl <= zu
        data.append((x, y, d, e + d / zl, e + d / zu))
    shi = min(item[3] for item in data), max(item[3] for item in data)
    slo = min(item[4] for item in data), max(item[4] for item in data)
    assert 0 < slo[0] <= slo[1] <= shi[1] < primitive.delay.max_s
    p_hi = primitive.range(*shi)
    p_lo = primitive.range(*slo)
    numerator = B.iv_sub(p_hi, p_lo)
    x_range = min(item[0] for item in data), max(item[0] for item in data)
    y_range = min(item[1] for item in data), max(item[1] for item in data)
    d_range = min(item[2] for item in data), max(item[2] for item in data)
    weight = B.iv_mul(
        B.iv_mul(B.reciprocal_power(*x_range, 1), B.reciprocal_power(*y_range, 1)),
        B.reciprocal_power(*d_range, 1),
    )
    raw = B.iv_mul(numerator, weight)
    area = triangle_area(triangle)
    return area * raw[0], area * raw[1]


def parse_q(text: str) -> Q:
    numerator, denominator = text.split("/")
    return Q(int(numerator), int(denominator))


def coefficient_record(
    split: int, triple: Interval, skeleton: Q, fixed: list[Interval]
) -> dict[str, object]:
    hlo = skeleton + sum((item[0] for item in fixed), Q(0)) + triple[0]
    hhi = skeleton + sum((item[1] for item in fixed), Q(0)) + triple[1]
    coefficient = 2 * hlo, 2 * hhi
    meets = coefficient[0] >= B.TARGET_K14
    return {
        "adaptive_splits": split,
        "triple_interval": G.interval_record(*triple, 18),
        "S2_over_M_coefficient_interval": G.interval_record(*coefficient, 18),
        "strictly_meets_paper_lower": meets,
        "lower_slack_or_deficit": (
            G.decimal_floor(coefficient[0] - B.TARGET_K14, 18)
            if meets
            else G.decimal_ceil(B.TARGET_K14 - coefficient[0], 18)
        ),
    }


def certify(args: argparse.Namespace) -> dict[str, object]:
    source_path = HERE / "li-equation14-certificate.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    names = (
        "zero_dimensional_500_fbar_minus_q",
        "one_dimensional_500_integral_q_minus_Fbar",
        "two_dimensional_500_integral_fbar_minus_q",
    )
    fixed = [
        (
            parse_q(source["components"][name]["lower_exact"]),
            parse_q(source["components"][name]["upper_exact"]),
        )
        for name in names
    ]
    skeleton = parse_q(source["stable_identity"]["constant_skeleton"]["lower_exact"])
    delay = G.FixedDelayTaylor(args.mesh, args.degree, args.max_s, args.dyadic_bits)
    primitive = Primitive(delay, args.primitive_bits)
    pieces = B.theta_branch_polytopes()
    expected_volume = (B.C14 - B.A0) ** 3 / 6
    total_fiber_volume = Q(0)
    min_d = Q(10**9)
    base_triangles = 0
    fiber_count = 0
    total_lo = total_hi = Q(0)
    heap = []
    serial = 0

    def push(theta, lower, upper, triangle, interval):
        nonlocal serial
        lo = B.lower_dyadic(interval[0], args.accum_bits)
        hi = B.upper_dyadic(interval[1], args.accum_bits)
        heapq.heappush(heap, (-(hi - lo), serial, theta, lower, upper, triangle, lo, hi))
        serial += 1
        return lo, hi

    for piece in pieces:
        cells = fiber_cells(piece)
        piece_volume = Q(0)
        for polygon, lower, upper in cells:
            fiber_count += 1
            for triangle in polygon_triangles(polygon):
                thickness = upper - lower
                volume = affine_integral_triangle(thickness, triangle)
                assert volume > 0
                piece_volume += volume
                total_fiber_volume += volume
                d_affine = B.BR.Affine(piece.theta.c, piece.theta.x - 1, piece.theta.y - 1)
                min_d = min(min_d, *(d_affine.at(x, y, Q(0)) for x, y in triangle))
                interval = triangle_interval(triangle, lower, upper, piece.theta, primitive)
                lo, hi = push(piece.theta, lower, upper, triangle, interval)
                total_lo += lo
                total_hi += hi
                base_triangles += 1
        assert piece_volume == piece.volume
    assert total_fiber_volume == expected_volume
    assert min_d > 0

    checkpoints = sorted(set([0, *args.checkpoints, args.adaptive_splits]))
    records = [coefficient_record(0, (total_lo, total_hi), skeleton, fixed)]
    for split in range(1, args.adaptive_splits + 1):
        _, _, theta, lower, upper, triangle, oldlo, oldhi = heapq.heappop(heap)
        total_lo -= oldlo
        total_hi -= oldhi
        child_lo = child_hi = Q(0)
        for child in split_triangle(triangle):
            interval = triangle_interval(child, lower, upper, theta, primitive)
            lo, hi = push(theta, lower, upper, child, interval)
            child_lo += lo
            child_hi += hi
        total_lo += child_lo
        total_hi += child_hi
        if split in checkpoints:
            records.append(coefficient_record(split, (total_lo, total_hi), skeleton, fixed))
    final = records[-1]
    base_path = HERE / "certify_li_equation14_polytope_taylor.py"
    return {
        "schema": "li-equation14-fiber-primitive-smoke-v1",
        "verdict": (
            "EQUATION_14_LOWER_BOUND_CERTIFIED"
            if final["strictly_meets_paper_lower"]
            else "PARTIAL_STRICT_CERTIFICATE"
        ),
        "paper_claim": "S2/M(N) >= 6.533916",
        "parameters": {
            "delay_mesh": args.mesh,
            "delay_degree": args.degree,
            "delay_max_s": args.max_s,
            "dyadic_bits": args.dyadic_bits,
            "primitive_bits": args.primitive_bits,
            "accumulation_bits": args.accum_bits,
            "adaptive_splits": args.adaptive_splits,
            "checkpoints": checkpoints,
        },
        "dependencies": {
            "R044_nontriple_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "R049_geometry_program_sha256": hashlib.sha256(base_path.read_bytes()).hexdigest(),
        },
        "checkpoints": records,
        "three_dimensional_integral_q_minus_Fbar": final["triple_interval"],
        "S2_over_M_coefficient_interval": final["S2_over_M_coefficient_interval"],
        "strictly_meets_paper_lower": final["strictly_meets_paper_lower"],
        "lower_slack_or_deficit": final["lower_slack_or_deficit"],
        "geometry": {
            "theta_branch_polytopes": len(pieces),
            "vertical_fiber_cells": fiber_count,
            "base_triangles": base_triangles,
            "final_leaf_triangles": len(heap),
            "minimum_D_exact": G.frac(min_d),
            "ordered_domain_volume_exact": G.frac(expected_volume),
            "vertical_fiber_volume_exact": G.frac(total_fiber_volume),
            "coverage": (
                "Each theta branch H-polytope is partitioned by its active affine lower/upper z envelopes; "
                "the exact integrated fiber thickness equals every branch volume and the ordered-domain volume."
            ),
        },
        "method": {
            "substitution": "s=e+D/z, ds=-D*dz/z^2",
            "primitive": "P=q*s-2*b(s+1) for s>=1; P=q*s-2*log(s) for 0<s<=1",
            "reduced_integrand": "(P(s(z_lower))-P(s(z_upper)))/(x*y*D)",
            "quadrature": "Directed triangle range sums with widest-first exact midpoint refinement.",
        },
        "limitations": [
            "Strict convergence smoke only; W050 remains IN_PROGRESS pending Taylor sharpening and audit.",
            "R044 supplies the rigorous nontriple endpoints by hash.",
            "This does not prove the upstream sieve hypotheses or strong Goldbach.",
        ],
    }


def parse_checkpoints(text: str) -> list[int]:
    values = [int(value) for value in text.split(",") if value.strip()]
    assert all(value >= 0 for value in values)
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh", type=int, default=8)
    parser.add_argument("--degree", type=int, default=16)
    parser.add_argument("--max-s", type=int, default=300)
    parser.add_argument("--dyadic-bits", type=int, default=96)
    parser.add_argument("--primitive-bits", type=int, default=160)
    parser.add_argument("--accum-bits", type=int, default=160)
    parser.add_argument("--adaptive-splits", type=int, default=2000)
    parser.add_argument("--checkpoints", type=parse_checkpoints, default=[0, 500, 2000])
    args = parser.parse_args()
    result = certify(args)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"verdict": result["verdict"], "checkpoints": result["checkpoints"], "geometry": result["geometry"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
