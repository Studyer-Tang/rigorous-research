"""Correlation-preserving, dyadically pre-cut fiber Taylor smoke for Li (14)."""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction as Q
from pathlib import Path

import certify_li_equation14_fiber_taylor as T

F, B, G = T.F, T.B, T.G
HERE = Path(__file__).resolve().parent
Interval = B.Interval
Triangle = F.Triangle
BASE_FIBER_CELLS = F.fiber_cells


def clip_polygon(polygon: list[F.Point2], affine: B.BR.Affine) -> list[F.Point2]:
    if not polygon:
        return []
    output = []
    previous = polygon[-1]
    previous_value = affine.at(previous[0], previous[1], Q(0))
    for current in polygon:
        current_value = affine.at(current[0], current[1], Q(0))
        previous_inside, current_inside = previous_value >= 0, current_value >= 0
        if current_inside != previous_inside:
            ratio = previous_value / (previous_value - current_value)
            output.append(
                (
                    previous[0] + ratio * (current[0] - previous[0]),
                    previous[1] + ratio * (current[1] - previous[1]),
                )
            )
        if current_inside:
            output.append(current)
        previous, previous_value = current, current_value
    clean = []
    for point in output:
        if not clean or point != clean[-1]:
            clean.append(point)
    if len(clean) > 1 and clean[0] == clean[-1]:
        clean.pop()
    return clean


def dyadic_bands() -> list[tuple[Q, Q]]:
    bands = []
    lo = B.A0
    while lo < B.C14:
        hi = min(2 * lo, B.C14)
        bands.append((lo, hi))
        lo = hi
    return bands


def dyadic_fiber_cells(
    piece: B.BranchPiece,
) -> list[tuple[list[F.Point2], B.BR.Affine, B.BR.Affine]]:
    answer = []
    for polygon, lower, upper in BASE_FIBER_CELLS(piece):
        for xlo, xhi in dyadic_bands():
            for ylo, yhi in dyadic_bands():
                clipped = polygon
                for constraint in (
                    B.BR.X - B.BR.Affine(xlo),
                    B.BR.Affine(xhi) - B.BR.X,
                    B.BR.Y - B.BR.Affine(ylo),
                    B.BR.Affine(yhi) - B.BR.Y,
                ):
                    clipped = clip_polygon(clipped, constraint)
                if len(clipped) >= 3 and sum(
                    (F.triangle_area(triangle) for triangle in F.polygon_triangles(clipped)), Q(0)
                ) > 0:
                    answer.append((clipped, lower, upper))
    return answer


def affine_vertex_range(affine: B.BR.Affine, triangle: Triangle) -> Interval:
    values = [affine.at(x, y, Q(0)) for x, y in triangle]
    return min(values), max(values)


def correlated_endpoint(
    z_affine: B.BR.Affine,
    theta: B.BR.Affine,
    triangle: Triangle,
    evaluator: B.ARatioDerivatives,
) -> dict[str, Interval]:
    d_affine = B.BR.Affine(theta.c, theta.x - 1, theta.y - 1)
    e = theta.z - 1
    z_range = affine_vertex_range(z_affine, triangle)
    d_range = affine_vertex_range(d_affine, triangle)
    assert z_range[0] > 0 and d_range[0] > 0
    s_values = [
        e + d_affine.at(x, y, Q(0)) / z_affine.at(x, y, Q(0)) for x, y in triangle
    ]
    s_range = min(s_values), max(s_values)
    iz2 = B.reciprocal_power(*z_range, 2)
    iz3 = B.reciprocal_power(*z_range, 3)
    derivatives = []
    for di, zi in (
        (theta.x - 1, z_affine.x),
        (theta.y - 1, z_affine.y),
    ):
        numerator = z_affine.scale(di) - d_affine.scale(zi)
        derivatives.append(B.iv_mul(affine_vertex_range(numerator, triangle), iz2))
    second = {}
    coordinate_data = (
        (theta.x - 1, z_affine.x),
        (theta.y - 1, z_affine.y),
    )
    for i, (di, zi) in enumerate(coordinate_data):
        for j, (dj, zj) in enumerate(coordinate_data):
            if j < i:
                continue
            numerator = z_affine.scale(-(di * zj + dj * zi)) + d_affine.scale(2 * zi * zj)
            second[i, j] = B.iv_mul(affine_vertex_range(numerator, triangle), iz3)
    g, gp = T.g_derivative_ranges(evaluator, *s_range)
    return {
        "s": s_range,
        "sx": derivatives[0],
        "sy": derivatives[1],
        "sxx": second[0, 0],
        "sxy": second[0, 1],
        "syy": second[1, 1],
        "g": g,
        "gp": gp,
    }


def endpoint_derivatives(endpoint: dict[str, Interval]) -> tuple[Interval, ...]:
    g, gp = endpoint["g"], endpoint["gp"]
    sx, sy = endpoint["sx"], endpoint["sy"]
    rx, ry = B.iv_mul(g, sx), B.iv_mul(g, sy)
    rxx = B.iv_add(B.iv_mul(gp, B.iv_mul(sx, sx)), B.iv_mul(g, endpoint["sxx"]))
    rxy = B.iv_add(B.iv_mul(gp, B.iv_mul(sx, sy)), B.iv_mul(g, endpoint["sxy"]))
    ryy = B.iv_add(B.iv_mul(gp, B.iv_mul(sy, sy)), B.iv_mul(g, endpoint["syy"]))
    return rx, ry, rxx, rxy, ryy


def correlated_r_range(
    triangle: Triangle,
    lower: B.BR.Affine,
    upper: B.BR.Affine,
    theta: B.BR.Affine,
    low_endpoint: dict[str, Interval],
    high_endpoint: dict[str, Interval],
    evaluator: B.ARatioDerivatives,
) -> Interval:
    d_affine = B.BR.Affine(theta.c, theta.x - 1, theta.y - 1)
    thickness = upper - lower
    d_range = affine_vertex_range(d_affine, triangle)
    thickness_range = affine_vertex_range(thickness, triangle)
    lower_range = affine_vertex_range(lower, triangle)
    upper_range = affine_vertex_range(upper, triangle)
    assert d_range[0] > 0 and thickness_range[0] >= 0 and lower_range[0] > 0
    delta = B.iv_mul(
        B.iv_mul(d_range, thickness_range),
        B.iv_mul(B.reciprocal_power(*lower_range, 1), B.reciprocal_power(*upper_range, 1)),
    )
    combined_s = high_endpoint["s"][0], low_endpoint["s"][1]
    g = T.g_derivative_ranges(evaluator, *combined_s)[0]
    return B.iv_mul(delta, g)


def triangle_interval(
    triangle: Triangle,
    lower: B.BR.Affine,
    upper: B.BR.Affine,
    theta: B.BR.Affine,
    primitive: F.Primitive,
) -> Interval:
    area = F.triangle_area(triangle)
    center = tuple(sum((point[i] for point in triangle), Q(0)) / 3 for i in range(2))
    d_center = theta.c + (theta.x - 1) * center[0] + (theta.y - 1) * center[1]
    zl = lower.at(center[0], center[1], Q(0))
    zu = upper.at(center[0], center[1], Q(0))
    e = theta.z - 1
    sl, su = e + d_center / zl, e + d_center / zu
    assert d_center > 0 and 0 < zl <= zu and sl >= su > 0
    r_center = B.iv_sub(primitive.point(sl), primitive.point(su))
    h_center = B.iv_scale(r_center, 1 / (center[0] * center[1] * d_center))

    low_endpoint = correlated_endpoint(lower, theta, triangle, primitive.ratio)
    high_endpoint = correlated_endpoint(upper, theta, triangle, primitive.ratio)
    r_range = correlated_r_range(
        triangle, lower, upper, theta, low_endpoint, high_endpoint, primitive.ratio
    )
    low_d = endpoint_derivatives(low_endpoint)
    high_d = endpoint_derivatives(high_endpoint)
    rx, ry, rxx, rxy, ryy = (
        B.iv_sub(low_d[index], high_d[index]) for index in range(5)
    )
    w, wx, wy, wxx, wxy, wyy = T.reduced_weight_ranges(triangle, theta)
    hxx = B.iv_add(
        B.iv_add(B.iv_mul(wxx, r_range), B.iv_scale(B.iv_mul(wx, rx), 2)),
        B.iv_mul(w, rxx),
    )
    hxy = B.iv_add(
        B.iv_add(
            B.iv_add(B.iv_mul(wxy, r_range), B.iv_mul(wx, ry)), B.iv_mul(wy, rx)
        ),
        B.iv_mul(w, rxy),
    )
    hyy = B.iv_add(
        B.iv_add(B.iv_mul(wyy, r_range), B.iv_scale(B.iv_mul(wy, ry), 2)),
        B.iv_mul(w, ryy),
    )
    variances = [
        sum(((point[i] - center[i]) ** 2 for point in triangle), Q(0)) / 12
        for i in range(2)
    ]
    covariance = sum(
        ((point[0] - center[0]) * (point[1] - center[1]) for point in triangle), Q(0)
    ) / 12
    midpoint, radius = (hxy[0] + hxy[1]) / 2, (hxy[1] - hxy[0]) / 2
    signed = midpoint * covariance
    error = radius * (variances[0] + variances[1]) / 2
    remainder = (
        hxx[0] * variances[0] / 2 + hyy[0] * variances[1] / 2 + signed - error,
        hxx[1] * variances[0] / 2 + hyy[1] * variances[1] / 2 + signed + error,
    )
    taylor = (
        area * (h_center[0] + remainder[0]),
        area * (h_center[1] + remainder[1]),
    )
    weight = T.reduced_weight_ranges(triangle, theta)[0]
    direct_raw = B.iv_mul(weight, r_range)
    direct = area * direct_raw[0], area * direct_raw[1]
    clipped = max(taylor[0], direct[0]), min(taylor[1], direct[1])
    assert clipped[0] <= clipped[1]
    return clipped


def certify(args: argparse.Namespace) -> dict[str, object]:
    old_triangle, old_fibers, old_primitive = F.triangle_interval, F.fiber_cells, F.Primitive
    F.triangle_interval = triangle_interval
    F.fiber_cells = dyadic_fiber_cells
    F.Primitive = T.AnchoredPrimitive
    try:
        result = F.certify(args)
    finally:
        F.triangle_interval, F.fiber_cells, F.Primitive = old_triangle, old_fibers, old_primitive
    parent_path = HERE / "certify_li_equation14_fiber_taylor.py"
    result["schema"] = "li-equation14-fiber-correlated-taylor-smoke-v2"
    result["dependencies"]["fiber_taylor_v1_sha256"] = hashlib.sha256(
        parent_path.read_bytes()
    ).hexdigest()
    result["method"]["quadrature"] = (
        "Dyadic x/y pre-cut; correlation-preserving s derivatives K/Z^2 and Kij/Z^3; "
        "R=integral(g) bounded as positive delta-s times a g range; centroid second-order Taylor."
    )
    result["geometry"]["xy_precut"] = "Exact doubling bands from 1/500 to 50/309; x and y ratio <=2 per cell."
    return result


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
    parser.add_argument("--checkpoints", type=F.parse_checkpoints, default=[0, 500, 2000])
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
