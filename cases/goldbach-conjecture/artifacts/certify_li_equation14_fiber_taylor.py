"""Second-order Taylor sharpening of the equation (14) fiber primitive smoke.

The exact branch and vertical-fiber decomposition, primitive, adaptive heap,
and volume assertions are inherited from ``certify_li_equation14_fiber_primitive``.
Only its triangle evaluator is replaced.  The reduced integrand is

    H(x,y) = W(x,y) R(x,y),
    W = 1/(x*y*D),
    R = P(s_L)-P(s_U).

Its Hessian is enclosed from the exact affine data D,L,U and directed delay
ranges for g=P'=q-Fbar and g'=P''.  The triangle-centroid Taylor interval uses
exact signed covariance plus a radius/Young remainder and is intersected with
the original direct range interval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction as Q
from pathlib import Path

import certify_li_equation14_fiber_primitive as F

B = F.B
G = F.G
HERE = Path(__file__).resolve().parent
Interval = B.Interval
Triangle = F.Triangle
DIRECT_TRIANGLE_INTERVAL = F.triangle_interval
DIRECT_PRIMITIVE = F.Primitive


class AnchoredPrimitive(F.Primitive):
    """Range P on delay cells from fixed, reusable half-mesh anchors."""

    def range(self, lo: Q, hi: Q) -> Interval:
        assert 0 < lo <= hi
        if lo == hi:
            return self.point(lo)
        first_boundary = G.floor_q(lo, self.delay.mesh) + 1
        last_boundary = G.ceil_q(hi, self.delay.mesh) - 1
        boundaries = [
            Q(j, self.delay.mesh)
            for j in range(first_boundary, last_boundary + 1)
            if lo < Q(j, self.delay.mesh) < hi
        ]
        cut_values = [lo, hi, *boundaries]
        cut_values.extend(pivot for pivot in (Q(1), Q(3)) if lo < pivot < hi)
        cuts = sorted(set(cut_values))
        ranges: list[Interval] = []
        for left, right in zip(cuts, cuts[1:]):
            cell = G.floor_q((left + right) / 2, self.delay.mesh)
            anchor = Q(2 * cell + 1, 2 * self.delay.mesh)
            derivative = self.derivative_range(min(left, anchor), max(right, anchor))
            displacement = left - anchor, right - anchor
            ranges.append(B.iv_add(self.point(anchor), B.iv_mul(derivative, displacement)))
        return union_ranges(ranges)


def union_ranges(items: list[Interval]) -> Interval:
    return min(item[0] for item in items), max(item[1] for item in items)


def g_derivative_ranges(
    evaluator: B.ARatioDerivatives, lo: Q, hi: Q
) -> tuple[Interval, Interval]:
    cuts = sorted({lo, hi, *[value for value in (Q(3),) if lo < value < hi]})
    ratios = []
    derivatives = []
    if lo == hi:
        point = evaluator.point(lo)
        ratios.append(point)
        if lo <= 3:
            derivatives.append((-1 / lo**2, -1 / lo**2))
        else:
            alo, ahi = evaluator.delay.shape_point("a", lo)
            b1lo, b1hi = evaluator.delay.shape_point("b", lo - 1)
            a = Q(alo, evaluator.scale), Q(ahi, evaluator.scale)
            ap = Q(b1lo, evaluator.scale) / (lo - 1), Q(b1hi, evaluator.scale) / (lo - 1)
            derivatives.append(
                B.iv_sub(B.iv_scale(ap, 1 / lo), B.iv_scale(a, 1 / lo**2))
            )
    else:
        for left, right in zip(cuts, cuts[1:]):
            r, rp, _ = evaluator.ranges(left, right)
            ratios.append(r)
            derivatives.append(rp)
    r = union_ranges(ratios)
    rp = union_ranges(derivatives)
    return (B.QSTAR - 2 * r[1], B.QSTAR - 2 * r[0]), B.iv_scale(rp, -2)


def endpoint_ranges(
    z_affine: B.BR.Affine,
    theta: B.BR.Affine,
    triangle: Triangle,
    evaluator: B.ARatioDerivatives,
) -> dict[str, object]:
    d_affine = B.BR.Affine(theta.c, theta.x - 1, theta.y - 1)
    e = theta.z - 1
    values = []
    for x, y in triangle:
        d = d_affine.at(x, y, Q(0))
        z = z_affine.at(x, y, Q(0))
        assert d > 0 and z > 0
        values.append((d, z, e + d / z))
    d_range = min(item[0] for item in values), max(item[0] for item in values)
    z_range = min(item[1] for item in values), max(item[1] for item in values)
    s_range = min(item[2] for item in values), max(item[2] for item in values)
    iz = B.reciprocal_power(*z_range, 1)
    iz2 = B.reciprocal_power(*z_range, 2)
    iz3 = B.reciprocal_power(*z_range, 3)
    derivatives = []
    second = {}
    for di, zi in (
        (theta.x - 1, z_affine.x),
        (theta.y - 1, z_affine.y),
    ):
        derivatives.append(
            B.iv_sub(B.iv_scale(iz, di), B.iv_scale(B.iv_mul(d_range, iz2), zi))
        )
    for i, (di, zi) in enumerate(
        ((theta.x - 1, z_affine.x), (theta.y - 1, z_affine.y))
    ):
        for j, (dj, zj) in enumerate(
            ((theta.x - 1, z_affine.x), (theta.y - 1, z_affine.y))
        ):
            if j < i:
                continue
            first = B.iv_scale(iz2, -(di * zj + dj * zi))
            trailing = B.iv_scale(B.iv_mul(d_range, iz3), 2 * zi * zj)
            second[i, j] = B.iv_add(first, trailing)
    g, gp = g_derivative_ranges(evaluator, *s_range)
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


def reduced_weight_ranges(
    triangle: Triangle, theta: B.BR.Affine
) -> tuple[Interval, Interval, Interval, Interval, Interval, Interval]:
    xs = [point[0] for point in triangle]
    ys = [point[1] for point in triangle]
    d_affine = B.BR.Affine(theta.c, theta.x - 1, theta.y - 1)
    ds = [d_affine.at(x, y, Q(0)) for x, y in triangle]
    xr, yr, dr = (min(xs), max(xs)), (min(ys), max(ys)), (min(ds), max(ds))
    assert xr[0] > 0 and yr[0] > 0 and dr[0] > 0
    ix, iy, id_ = (
        B.reciprocal_power(*xr, 1),
        B.reciprocal_power(*yr, 1),
        B.reciprocal_power(*dr, 1),
    )
    ix2, iy2, id2 = (
        B.reciprocal_power(*xr, 2),
        B.reciprocal_power(*yr, 2),
        B.reciprocal_power(*dr, 2),
    )
    p, q = theta.x - 1, theta.y - 1
    w = B.iv_mul(B.iv_mul(ix, iy), id_)
    lx = B.iv_scale(B.iv_add(ix, B.iv_scale(id_, p)), -1)
    ly = B.iv_scale(B.iv_add(iy, B.iv_scale(id_, q)), -1)
    wx, wy = B.iv_mul(w, lx), B.iv_mul(w, ly)
    factor_xx = B.iv_add(
        B.iv_add(B.iv_scale(ix2, 2), B.iv_scale(B.iv_mul(ix, id_), 2 * p)),
        B.iv_scale(id2, 2 * p * p),
    )
    factor_yy = B.iv_add(
        B.iv_add(B.iv_scale(iy2, 2), B.iv_scale(B.iv_mul(iy, id_), 2 * q)),
        B.iv_scale(id2, 2 * q * q),
    )
    factor_xy = B.iv_add(
        B.iv_add(
            B.iv_add(B.iv_mul(ix, iy), B.iv_scale(B.iv_mul(ix, id_), q)),
            B.iv_scale(B.iv_mul(iy, id_), p),
        ),
        B.iv_scale(id2, 2 * p * q),
    )
    return w, wx, wy, B.iv_mul(w, factor_xx), B.iv_mul(w, factor_xy), B.iv_mul(w, factor_yy)


def endpoint_r_derivatives(endpoint: dict[str, object]) -> tuple[Interval, Interval, Interval, Interval, Interval]:
    g = endpoint["g"]
    gp = endpoint["gp"]
    sx, sy = endpoint["sx"], endpoint["sy"]
    sxx, sxy, syy = endpoint["sxx"], endpoint["sxy"], endpoint["syy"]
    assert isinstance(g, tuple) and isinstance(gp, tuple)
    assert isinstance(sx, tuple) and isinstance(sy, tuple)
    assert isinstance(sxx, tuple) and isinstance(sxy, tuple) and isinstance(syy, tuple)
    rx = B.iv_mul(g, sx)
    ry = B.iv_mul(g, sy)
    rxx = B.iv_add(B.iv_mul(gp, B.iv_mul(sx, sx)), B.iv_mul(g, sxx))
    rxy = B.iv_add(B.iv_mul(gp, B.iv_mul(sx, sy)), B.iv_mul(g, sxy))
    ryy = B.iv_add(B.iv_mul(gp, B.iv_mul(sy, sy)), B.iv_mul(g, syy))
    return rx, ry, rxx, rxy, ryy


def taylor_triangle_interval(
    triangle: Triangle,
    lower: B.BR.Affine,
    upper: B.BR.Affine,
    theta: B.BR.Affine,
    primitive: F.Primitive,
) -> Interval:
    direct = DIRECT_TRIANGLE_INTERVAL(triangle, lower, upper, theta, primitive)
    area = F.triangle_area(triangle)
    center = tuple(sum((point[i] for point in triangle), Q(0)) / 3 for i in range(2))
    d_center = theta.c + (theta.x - 1) * center[0] + (theta.y - 1) * center[1]
    zl = lower.at(center[0], center[1], Q(0))
    zu = upper.at(center[0], center[1], Q(0))
    e = theta.z - 1
    sl, su = e + d_center / zl, e + d_center / zu
    assert d_center > 0 and 0 < zl <= zu and sl >= su > 0
    r_center = B.iv_sub(primitive.point(sl), primitive.point(su))
    w_center = 1 / (center[0] * center[1] * d_center)
    h_center = B.iv_scale(r_center, w_center)

    low_endpoint = endpoint_ranges(lower, theta, triangle, primitive.ratio)
    high_endpoint = endpoint_ranges(upper, theta, triangle, primitive.ratio)
    r_range = B.iv_sub(
        primitive.range(*low_endpoint["s"]), primitive.range(*high_endpoint["s"])
    )
    low_derivatives = endpoint_r_derivatives(low_endpoint)
    high_derivatives = endpoint_r_derivatives(high_endpoint)
    rx, ry, rxx, rxy, ryy = (
        B.iv_sub(low_derivatives[index], high_derivatives[index]) for index in range(5)
    )
    w, wx, wy, wxx, wxy, wyy = reduced_weight_ranges(triangle, theta)
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
    covariance = (
        sum(
            (
                (point[0] - center[0]) * (point[1] - center[1])
                for point in triangle
            ),
            Q(0),
        )
        / 12
    )
    mixed_mid = (hxy[0] + hxy[1]) / 2
    mixed_radius = (hxy[1] - hxy[0]) / 2
    mixed_signed = mixed_mid * covariance
    mixed_error = mixed_radius * (variances[0] + variances[1]) / 2
    remainder_lo = (
        hxx[0] * variances[0] / 2
        + hyy[0] * variances[1] / 2
        + mixed_signed
        - mixed_error
    )
    remainder_hi = (
        hxx[1] * variances[0] / 2
        + hyy[1] * variances[1] / 2
        + mixed_signed
        + mixed_error
    )
    taylor = (
        area * (h_center[0] + remainder_lo),
        area * (h_center[1] + remainder_hi),
    )
    clipped = max(direct[0], taylor[0]), min(direct[1], taylor[1])
    assert clipped[0] <= clipped[1]
    return clipped


def certify(args: argparse.Namespace) -> dict[str, object]:
    original_triangle = F.triangle_interval
    original_primitive = F.Primitive
    F.triangle_interval = taylor_triangle_interval
    F.Primitive = AnchoredPrimitive
    try:
        result = F.certify(args)
    finally:
        F.triangle_interval = original_triangle
        F.Primitive = original_primitive
    direct_path = HERE / "certify_li_equation14_fiber_primitive.py"
    result["schema"] = "li-equation14-fiber-second-order-taylor-smoke-v1"
    result["dependencies"]["fiber_direct_program_sha256"] = hashlib.sha256(
        direct_path.read_bytes()
    ).hexdigest()
    result["method"]["quadrature"] = (
        "Triangle-centroid second-order Taylor using exact signed covariance and radius/Young mixed error; "
        "intersected with the direct reduced-integrand range."
    )
    result["limitations"][0] = (
        "Strict second-order convergence smoke only; W050 remains IN_PROGRESS pending independent audit."
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
