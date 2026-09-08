"""Strict Li-(14) fiber certificate after exact cancellation of ``D``.

For one affine winner and one vertical fiber ``L(x,y) <= z <= U(x,y)``,

    s_L = e + D/L,       s_U = e + D/U,
    delta_s = D(U-L)/(LU).

Writing ``g=q-Fbar=P'`` gives the exact identity

    (P(s_L)-P(s_U))/(xyD)
      = (U-L)/(xyLU) * integral_0^1 g(s_U+t*delta_s) dt.

Thus the poorly correlated product of a primitive difference with ``1/D``
is absent.  The remaining positive rational weight and the complete range of
``g`` are enclosed with directed exact-rational interval arithmetic.  Exact
doubling cuts in x, y, L, and U keep every positive factor on a relative
scale.  The inherited widest-first midpoint refinement supplies convergence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction as Q
from pathlib import Path

import certify_li_equation14_fiber_primitive as F
import certify_li_equation14_fiber_taylor as T
import certify_li_equation14_fiber_taylor_v2 as V2

B = F.B
G = F.G
HERE = Path(__file__).resolve().parent
Interval = B.Interval
Triangle = F.Triangle
T_PANELS = 16


def affine_range(affine: B.BR.Affine, polygon: list[F.Point2]) -> Interval:
    values = [affine.at(x, y, Q(0)) for x, y in polygon]
    return min(values), max(values)


def split_on_doubling_bands(
    polygon: list[F.Point2], affine: B.BR.Affine
) -> list[list[F.Point2]]:
    """Partition a positive-affine polygon at the global doubling cuts."""
    lo, hi = affine_range(affine, polygon)
    assert lo > 0
    pieces = []
    for band_lo, band_hi in V2.dyadic_bands():
        if hi < band_lo or lo > band_hi:
            continue
        clipped = V2.clip_polygon(polygon, affine - B.BR.Affine(band_lo))
        clipped = V2.clip_polygon(clipped, B.BR.Affine(band_hi) - affine)
        if len(clipped) >= 3:
            area = sum((F.triangle_area(t) for t in F.polygon_triangles(clipped)), Q(0))
            if area > 0:
                pieces.append(clipped)
    return pieces


def relative_fiber_cells(
    piece: B.BranchPiece,
) -> list[tuple[list[F.Point2], B.BR.Affine, B.BR.Affine]]:
    """Apply exact x/y/L/U relative-scale cuts to every fiber cell."""
    answer = []
    for polygon, lower, upper in FIBER_CELLS(piece):
        polygons = [polygon]
        for affine in (B.BR.X, B.BR.Y, lower, upper):
            next_polygons = []
            for current in polygons:
                next_polygons.extend(split_on_doubling_bands(current, affine))
            polygons = next_polygons
        answer.extend((current, lower, upper) for current in polygons)
    return answer


FIBER_CELLS = F.fiber_cells


def union_ranges(items: list[Interval]) -> Interval:
    return min(item[0] for item in items), max(item[1] for item in items)


def g_second_range(evaluator: B.ARatioDerivatives, lo: Q, hi: Q) -> Interval:
    """Directed range of g''=-2(a/s)'' with the s=3 formula cut."""
    cuts = sorted({lo, hi, *[pivot for pivot in (Q(3),) if lo < pivot < hi]})
    pieces = []
    if lo == hi:
        if lo <= 3:
            pieces.append((2 / lo**3, 2 / lo**3))
        else:
            scale = evaluator.scale
            alo, ahi = evaluator.delay.shape_point("a", lo)
            b1lo, b1hi = evaluator.delay.shape_point("b", lo - 1)
            am2lo, am2hi = evaluator.delay.shape_point("a", lo - 2)
            a = Q(alo, scale), Q(ahi, scale)
            b1 = Q(b1lo, scale), Q(b1hi, scale)
            am2 = Q(am2lo, scale), Q(am2hi, scale)
            ap = B.iv_scale(b1, 1 / (lo - 1))
            app = B.iv_sub(
                B.iv_scale(am2, 1 / ((lo - 2) * (lo - 1))),
                B.iv_scale(b1, 1 / (lo - 1) ** 2),
            )
            rpp = B.iv_add(
                B.iv_sub(B.iv_scale(app, 1 / lo), B.iv_scale(ap, 2 / lo**2)),
                B.iv_scale(a, 2 / lo**3),
            )
            pieces.append(rpp)
    else:
        for left, right in zip(cuts, cuts[1:]):
            pieces.append(evaluator.ranges(left, right)[2])
    return B.iv_scale(union_ranges(pieces), -2)


def average_g_interval(
    primitive: F.Primitive,
    d_range: Interval,
    lr: Interval,
    ur: Interval,
    width_range: Interval,
    su_range: Interval,
    sl_range: Interval,
) -> Interval:
    """Certified composite-midpoint enclosure of the t-average of g."""
    coarse = T.g_derivative_ranges(
        primitive.ratio, su_range[0], sl_range[1]
    )[0]
    if T_PANELS == 0:
        return coarse
    assert T_PANELS > 0
    inv_l = B.reciprocal_power(*lr, 1)
    inv_u = B.reciprocal_power(*ur, 1)
    delta = B.iv_mul(
        B.iv_mul(d_range, width_range), B.iv_mul(inv_l, inv_u)
    )
    delta2 = B.iv_mul(delta, delta)
    total = (Q(0), Q(0))
    h = Q(1, T_PANELS)
    for panel in range(T_PANELS):
        left = Q(panel, T_PANELS)
        right = Q(panel + 1, T_PANELS)
        center = (left + right) / 2

        s_center = B.iv_add(
            B.iv_scale(su_range, 1 - center), B.iv_scale(sl_range, center)
        )
        g_center = T.g_derivative_ranges(primitive.ratio, *s_center)[0]

        s_left = B.iv_add(
            B.iv_scale(su_range, 1 - left), B.iv_scale(sl_range, left)
        )
        s_right = B.iv_add(
            B.iv_scale(su_range, 1 - right), B.iv_scale(sl_range, right)
        )
        s_panel = (
            min(s_left[0], s_right[0]),
            max(s_left[1], s_right[1]),
        )
        gpp = g_second_range(primitive.ratio, *s_panel)
        midpoint_error = B.iv_scale(B.iv_mul(gpp, delta2), h**3 / 24)
        total = B.iv_add(total, B.iv_add(B.iv_scale(g_center, h), midpoint_error))

    # The coarse enclosure is mathematically independent of the midpoint
    # remainder and catches implementation errors in either route.
    clipped = max(total[0], coarse[0]), min(total[1], coarse[1])
    assert clipped[0] <= clipped[1]
    return clipped


def triangle_interval(
    triangle: Triangle,
    lower: B.BR.Affine,
    upper: B.BR.Affine,
    theta: B.BR.Affine,
    primitive: F.Primitive,
) -> Interval:
    """Enclose the D-free fiber integrand on one exact triangle."""
    d_affine = B.BR.Affine(theta.c, theta.x - 1, theta.y - 1)
    thickness = upper - lower
    e = theta.z - 1
    rows = []
    for x, y in triangle:
        d = d_affine.at(x, y, Q(0))
        zl = lower.at(x, y, Q(0))
        zu = upper.at(x, y, Q(0))
        width = thickness.at(x, y, Q(0))
        assert x > 0 and y > 0 and d > 0 and 0 < zl <= zu and width >= 0
        rows.append((x, y, zl, zu, width, e + d / zu, e + d / zl))

    xr = min(row[0] for row in rows), max(row[0] for row in rows)
    yr = min(row[1] for row in rows), max(row[1] for row in rows)
    lr = min(row[2] for row in rows), max(row[2] for row in rows)
    ur = min(row[3] for row in rows), max(row[3] for row in rows)
    width_range = min(row[4] for row in rows), max(row[4] for row in rows)
    su_range = min(row[5] for row in rows), max(row[5] for row in rows)
    sl_range = min(row[6] for row in rows), max(row[6] for row in rows)
    assert 0 < su_range[0] <= sl_range[1] < primitive.delay.max_s
    d_range = affine_range(d_affine, list(triangle))
    average_g = average_g_interval(
        primitive, d_range, lr, ur, width_range, su_range, sl_range
    )
    ix, iy = B.reciprocal_power(*xr, 1), B.reciprocal_power(*yr, 1)
    il, iu = B.reciprocal_power(*lr, 1), B.reciprocal_power(*ur, 1)
    delta_difference = B.iv_sub(il, iu)
    delta_positive = B.iv_mul(width_range, B.iv_mul(il, iu))
    delta = max(Q(0), delta_difference[0], delta_positive[0]), min(
        delta_difference[1], delta_positive[1]
    )
    assert delta[0] <= delta[1]
    positive_weight = B.iv_mul(B.iv_mul(ix, iy), delta)
    raw = B.iv_mul(positive_weight, average_g)
    area = F.triangle_area(triangle)
    return area * raw[0], area * raw[1]


def certify(args: argparse.Namespace) -> dict[str, object]:
    global T_PANELS
    old_triangle, old_fibers, old_primitive = F.triangle_interval, F.fiber_cells, F.Primitive
    old_t_panels = T_PANELS
    T_PANELS = args.t_panels
    F.triangle_interval = triangle_interval
    F.fiber_cells = relative_fiber_cells
    F.Primitive = T.AnchoredPrimitive
    try:
        result = F.certify(args)
    finally:
        F.triangle_interval, F.fiber_cells, F.Primitive = old_triangle, old_fibers, old_primitive
        T_PANELS = old_t_panels

    parent_paths = (
        HERE / "certify_li_equation14_fiber_primitive.py",
        HERE / "certify_li_equation14_fiber_taylor.py",
        HERE / "certify_li_equation14_fiber_taylor_v2.py",
    )
    result["schema"] = "li-equation14-fiber-cancel-d-range-v1"
    result["dependencies"]["parent_program_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in parent_paths
    }
    result["method"]["substitution"] = (
        "s=e+D/z followed by P(sL)-P(sU)=delta_s*integral_0^1 g(sU+t*delta_s)dt"
    )
    result["method"]["reduced_integrand"] = (
        "(U-L)/(x*y*L*U) * integral_0^1 (q-Fbar)(sU+t*(sL-sU)) dt"
    )
    result["method"]["quadrature"] = (
        "Exact x/y/L/U doubling cuts; "
        + (
            f"{args.t_panels}-panel certified composite-midpoint enclosure of the t-average with directed g'' remainder; "
            if args.t_panels
            else "complete pointwise g-range enclosure of the t-average; "
        )
        + "directed positive-weight range; "
        "widest-first exact midpoint refinement in x/y."
    )
    result["geometry"]["relative_precut"] = (
        "Exact doubling bands from 1/500 to 50/309 applied independently to x, y, L, and U."
    )
    result["limitations"][0] = (
        "Strict D-cancellation range certificate; equation (14) closes only if its directed lower endpoint reaches the paper threshold."
    )
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
    parser.add_argument("--t-panels", type=int, default=16)
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
