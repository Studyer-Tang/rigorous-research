"""Stable two-dimensional Taylor certificate for the D-cancelled Li-(14) fiber.

The integrand is written

    H = W A,
    W = (U-L)/(x*y*L*U),
    A = integral_0^1 g(s_U+t*(s_L-s_U)) dt.

Unlike the earlier Taylor certificate, no outer ``1/D`` is multiplied by a
primitive difference proportional to ``D``.  The centroid value is evaluated
from the primitive identity, while the Hessian is bounded directly from the
smooth positive weight W and the averaged chain-rule derivatives of A.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction as Q
from pathlib import Path

import certify_li_equation14_fiber_cancel_d as C
import certify_li_equation14_fiber_primitive as F
import certify_li_equation14_fiber_taylor as T
import certify_li_equation14_fiber_taylor_v2 as V2

B = F.B
G = F.G
HERE = Path(__file__).resolve().parent
Interval = B.Interval
Triangle = F.Triangle


class FastARatioDerivatives(B.ARatioDerivatives):
    """The parent exact ranges with sparse whole-cell min/max lookup."""

    def __init__(self, delay: G.FixedDelayTaylor):
        super().__init__(delay)
        count = delay.max_s * delay.mesh
        self.tables = {}
        for which in ("a", "b"):
            lows = [0] * count
            highs = [0] * count
            for j in range(delay.mesh, count):
                lows[j], highs[j] = self._partial(which, j, Q(0), Q(1, delay.mesh))
            self.tables[which] = G.RangeTable._sparse(lows, highs)
        baseline = B.ARatioDerivatives(delay)
        probes = [
            (Q(193, 64), Q(25, 8)),
            (Q(4), Q(10)),
            (Q(1001, 100), Q(2003, 100)),
            (Q(delay.max_s - 1), Q(delay.max_s)),
        ]
        for which in ("a", "b"):
            for lo, hi in probes:
                if 3 <= lo <= hi <= delay.max_s:
                    assert self.shape_range(which, lo, hi) == baseline.shape_range(which, lo, hi)

    def _partial(self, which: str, j: int, ulo: Q, uhi: Q) -> tuple[int, int]:
        model = self.delay.a[j] if which == "a" else self.delay.b[j]
        value = (0, 0)
        for coefficient in reversed(model.coeff):
            value = self._mul_integer_interval(value, (ulo, uhi))
            value = value[0] + coefficient[0], value[1] + coefficient[1]
        return value[0] - model.error, value[1] + model.error

    def _whole_cells(self, which: str, left: int, right: int) -> tuple[int, int]:
        length = right - left + 1
        level = length.bit_length() - 1
        width = 1 << level
        mins, maxs = self.tables[which]
        return min(mins[level][left], mins[level][right - width + 1]), max(
            maxs[level][left], maxs[level][right - width + 1]
        )

    def shape_range(self, which: str, lo: Q, hi: Q) -> Interval:
        assert which in ("a", "b") and 1 <= lo <= hi <= self.delay.max_s
        if lo == hi:
            point = self.delay.shape_point(which, lo)
            return Q(point[0], self.scale), Q(point[1], self.scale)
        left = G.floor_q(lo, self.delay.mesh)
        right = G.ceil_q(hi, self.delay.mesh) - 1
        assert self.delay.mesh <= left <= right < self.delay.max_s * self.delay.mesh
        ranges = []
        left_origin = Q(left, self.delay.mesh)
        if left == right:
            ranges.append(self._partial(which, left, lo - left_origin, hi - left_origin))
        else:
            ranges.append(
                self._partial(which, left, lo - left_origin, Q(1, self.delay.mesh))
            )
            right_origin = Q(right, self.delay.mesh)
            ranges.append(self._partial(which, right, Q(0), hi - right_origin))
            if left + 1 <= right - 1:
                ranges.append(self._whole_cells(which, left + 1, right - 1))
        return Q(min(r[0] for r in ranges), self.scale), Q(
            max(r[1] for r in ranges), self.scale
        )


class FastAnchoredPrimitive(T.AnchoredPrimitive):
    def __init__(self, delay: G.FixedDelayTaylor, bits: int):
        super().__init__(delay, bits)
        self.ratio = FastARatioDerivatives(delay)


def hull(first: Interval, second: Interval) -> Interval:
    return min(first[0], second[0]), max(first[1], second[1])


def affine_product_integral(
    triangle: Triangle, center: tuple[Q, Q]
) -> Q:
    """Integrate (x-cx)(y-cy) exactly on a triangle."""
    fx = [point[0] - center[0] for point in triangle]
    fy = [point[1] - center[1] for point in triangle]
    expectation = (
        sum(fx, Q(0)) * sum(fy, Q(0))
        + sum((x * y for x, y in zip(fx, fy, strict=True)), Q(0))
    ) / 12
    return F.triangle_area(triangle) * expectation


def absolute_mixed_moment(triangle: Triangle, center: tuple[Q, Q]) -> Q:
    """Return E_T |(x-cx)(y-cy)| by exact quadrant clipping."""
    total = Q(0)
    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            polygon = list(triangle)
            x_halfspace = (
                B.BR.X - B.BR.Affine(center[0])
                if x_sign > 0
                else B.BR.Affine(center[0]) - B.BR.X
            )
            y_halfspace = (
                B.BR.Y - B.BR.Affine(center[1])
                if y_sign > 0
                else B.BR.Affine(center[1]) - B.BR.Y
            )
            polygon = V2.clip_polygon(polygon, x_halfspace)
            polygon = V2.clip_polygon(polygon, y_halfspace)
            for child in F.polygon_triangles(polygon):
                signed = affine_product_integral(child, center)
                assert signed * x_sign * y_sign >= 0
                total += signed * x_sign * y_sign
    return total / F.triangle_area(triangle)


def endpoint_s_ranges(
    z_affine: B.BR.Affine, theta: B.BR.Affine, triangle: Triangle
) -> dict[str, Interval]:
    """Correlation-preserving ranges for s=e+D/Z and its first two derivatives."""
    d_affine = B.BR.Affine(theta.c, theta.x - 1, theta.y - 1)
    e = theta.z - 1
    z_range = C.affine_range(z_affine, list(triangle))
    assert z_range[0] > 0
    s_values = [
        e + d_affine.at(x, y, Q(0)) / z_affine.at(x, y, Q(0)) for x, y in triangle
    ]
    iz2 = B.reciprocal_power(*z_range, 2)
    iz3 = B.reciprocal_power(*z_range, 3)
    coordinate_data = (
        (theta.x - 1, z_affine.x),
        (theta.y - 1, z_affine.y),
    )
    first = []
    for di, zi in coordinate_data:
        numerator = z_affine.scale(di) - d_affine.scale(zi)
        first.append(B.iv_mul(C.affine_range(numerator, list(triangle)), iz2))
    second = {}
    for i, (di, zi) in enumerate(coordinate_data):
        for j, (dj, zj) in enumerate(coordinate_data):
            if j < i:
                continue
            numerator = z_affine.scale(-(di * zj + dj * zi)) + d_affine.scale(2 * zi * zj)
            second[i, j] = B.iv_mul(C.affine_range(numerator, list(triangle)), iz3)
    return {
        "s": (min(s_values), max(s_values)),
        "sx": first[0],
        "sy": first[1],
        "sxx": second[0, 0],
        "sxy": second[0, 1],
        "syy": second[1, 1],
    }


def stable_weight_ranges(
    triangle: Triangle, lower: B.BR.Affine, upper: B.BR.Affine
) -> tuple[Interval, Interval, Interval, Interval, Interval, Interval]:
    """Ranges of W, Wx, Wy, Wxx, Wxy, Wyy from W=(1/L-1/U)/(xy)."""
    xr = min(p[0] for p in triangle), max(p[0] for p in triangle)
    yr = min(p[1] for p in triangle), max(p[1] for p in triangle)
    lr = C.affine_range(lower, list(triangle))
    ur = C.affine_range(upper, list(triangle))
    thickness = upper - lower
    tr = C.affine_range(thickness, list(triangle))
    assert xr[0] > 0 and yr[0] > 0 and lr[0] > 0 and ur[0] > 0 and tr[0] >= 0

    ix = B.reciprocal_power(*xr, 1)
    iy = B.reciprocal_power(*yr, 1)
    il = B.reciprocal_power(*lr, 1)
    iu = B.reciprocal_power(*ur, 1)
    ix2 = B.reciprocal_power(*xr, 2)
    iy2 = B.reciprocal_power(*yr, 2)
    il2 = B.reciprocal_power(*lr, 2)
    iu2 = B.reciprocal_power(*ur, 2)
    il3 = B.reciprocal_power(*lr, 3)
    iu3 = B.reciprocal_power(*ur, 3)

    p = B.iv_mul(ix, iy)
    px, py = B.iv_scale(B.iv_mul(p, ix), -1), B.iv_scale(B.iv_mul(p, iy), -1)
    pxx = B.iv_scale(B.iv_mul(p, ix2), 2)
    pxy = B.iv_mul(p, B.iv_mul(ix, iy))
    pyy = B.iv_scale(B.iv_mul(p, iy2), 2)

    delta_difference = B.iv_sub(il, iu)
    delta_positive = B.iv_mul(tr, B.iv_mul(il, iu))
    delta = max(Q(0), delta_difference[0], delta_positive[0]), min(
        delta_difference[1], delta_positive[1]
    )
    assert delta[0] <= delta[1]

    def reciprocal_derivatives(
        affine: B.BR.Affine, inv2: Interval, inv3: Interval
    ) -> tuple[Interval, Interval, Interval, Interval, Interval]:
        rx = B.iv_scale(inv2, -affine.x)
        ry = B.iv_scale(inv2, -affine.y)
        rxx = B.iv_scale(inv3, 2 * affine.x**2)
        rxy = B.iv_scale(inv3, 2 * affine.x * affine.y)
        ryy = B.iv_scale(inv3, 2 * affine.y**2)
        return rx, ry, rxx, rxy, ryy

    low_derivatives = reciprocal_derivatives(lower, il2, il3)
    high_derivatives = reciprocal_derivatives(upper, iu2, iu3)
    dx, dy, dxx, dxy, dyy = (
        B.iv_sub(low_derivatives[index], high_derivatives[index]) for index in range(5)
    )
    w = B.iv_mul(p, delta)
    wx = B.iv_add(B.iv_mul(px, delta), B.iv_mul(p, dx))
    wy = B.iv_add(B.iv_mul(py, delta), B.iv_mul(p, dy))
    wxx = B.iv_add(
        B.iv_add(B.iv_mul(pxx, delta), B.iv_scale(B.iv_mul(px, dx), 2)),
        B.iv_mul(p, dxx),
    )
    wxy = B.iv_add(
        B.iv_add(
            B.iv_add(B.iv_mul(pxy, delta), B.iv_mul(px, dy)), B.iv_mul(py, dx)
        ),
        B.iv_mul(p, dxy),
    )
    wyy = B.iv_add(
        B.iv_add(B.iv_mul(pyy, delta), B.iv_scale(B.iv_mul(py, dy), 2)),
        B.iv_mul(p, dyy),
    )
    return w, wx, wy, wxx, wxy, wyy


def averaged_chain_ranges(
    triangle: Triangle,
    lower: B.BR.Affine,
    upper: B.BR.Affine,
    theta: B.BR.Affine,
    primitive: F.Primitive,
) -> tuple[Interval, Interval, Interval, Interval, Interval, Interval]:
    """Ranges of A, Ax, Ay, Axx, Axy, Ayy over one triangle."""
    d_affine = B.BR.Affine(theta.c, theta.x - 1, theta.y - 1)
    thickness = upper - lower
    d_range = C.affine_range(d_affine, list(triangle))
    lr = C.affine_range(lower, list(triangle))
    ur = C.affine_range(upper, list(triangle))
    width_range = C.affine_range(thickness, list(triangle))
    endpoint_l = endpoint_s_ranges(lower, theta, triangle)
    endpoint_u = endpoint_s_ranges(upper, theta, triangle)
    su_range = endpoint_u["s"]
    sl_range = endpoint_l["s"]
    a = C.average_g_interval(
        primitive, d_range, lr, ur, width_range, su_range, sl_range
    )

    derivative_panels = max(1, C.T_PANELS)
    ax = ay = axx = axy = ayy = (Q(0), Q(0))
    endpoint_keys = ("sx", "sy", "sxx", "sxy", "syy")
    for panel in range(derivative_panels):
        left = Q(panel, derivative_panels)
        right = Q(panel + 1, derivative_panels)
        h = right - left
        s_panel = (
            (1 - left) * su_range[0] + left * sl_range[0],
            (1 - right) * su_range[1] + right * sl_range[1],
        )
        _, gp = T.g_derivative_ranges(primitive.ratio, *s_panel)
        gpp = C.g_second_range(primitive.ratio, *s_panel)

        derivative_ranges = []
        for key in endpoint_keys:
            at_left = B.iv_add(
                B.iv_scale(endpoint_u[key], 1 - left),
                B.iv_scale(endpoint_l[key], left),
            )
            at_right = B.iv_add(
                B.iv_scale(endpoint_u[key], 1 - right),
                B.iv_scale(endpoint_l[key], right),
            )
            derivative_ranges.append(hull(at_left, at_right))
        sx, sy, sxx, sxy, syy = derivative_ranges
        ax = B.iv_add(ax, B.iv_scale(B.iv_mul(gp, sx), h))
        ay = B.iv_add(ay, B.iv_scale(B.iv_mul(gp, sy), h))
        axx = B.iv_add(
            axx,
            B.iv_scale(
                B.iv_add(B.iv_mul(gpp, B.iv_mul(sx, sx)), B.iv_mul(gp, sxx)), h
            ),
        )
        axy = B.iv_add(
            axy,
            B.iv_scale(
                B.iv_add(B.iv_mul(gpp, B.iv_mul(sx, sy)), B.iv_mul(gp, sxy)), h
            ),
        )
        ayy = B.iv_add(
            ayy,
            B.iv_scale(
                B.iv_add(B.iv_mul(gpp, B.iv_mul(sy, sy)), B.iv_mul(gp, syy)), h
            ),
        )
    return a, ax, ay, axx, axy, ayy


def triangle_interval(
    triangle: Triangle,
    lower: B.BR.Affine,
    upper: B.BR.Affine,
    theta: B.BR.Affine,
    primitive: F.Primitive,
) -> Interval:
    direct = C.triangle_interval(triangle, lower, upper, theta, primitive)
    area = F.triangle_area(triangle)
    center = tuple(sum((point[i] for point in triangle), Q(0)) / 3 for i in range(2))
    d = theta.c + (theta.x - 1) * center[0] + (theta.y - 1) * center[1]
    zl = lower.at(center[0], center[1], Q(0))
    zu = upper.at(center[0], center[1], Q(0))
    e = theta.z - 1
    sl, su = e + d / zl, e + d / zu
    assert d > 0 and 0 < zl < zu and 0 < su <= sl
    primitive_difference = B.iv_sub(primitive.point(sl), primitive.point(su))
    h_center = B.iv_scale(primitive_difference, 1 / (center[0] * center[1] * d))

    w, wx, wy, wxx, wxy, wyy = stable_weight_ranges(triangle, lower, upper)
    a, ax, ay, axx, axy, ayy = averaged_chain_ranges(
        triangle, lower, upper, theta, primitive
    )
    hxx = B.iv_add(
        B.iv_add(B.iv_mul(wxx, a), B.iv_scale(B.iv_mul(wx, ax), 2)),
        B.iv_mul(w, axx),
    )
    hxy = B.iv_add(
        B.iv_add(
            B.iv_add(B.iv_mul(wxy, a), B.iv_mul(wx, ay)), B.iv_mul(wy, ax)
        ),
        B.iv_mul(w, axy),
    )
    hyy = B.iv_add(
        B.iv_add(B.iv_mul(wyy, a), B.iv_scale(B.iv_mul(wy, ay), 2)),
        B.iv_mul(w, ayy),
    )

    variances = [
        sum(((point[i] - center[i]) ** 2 for point in triangle), Q(0)) / 12
        for i in range(2)
    ]
    covariance = sum(
        ((point[0] - center[0]) * (point[1] - center[1]) for point in triangle), Q(0)
    ) / 12
    mixed_mid = (hxy[0] + hxy[1]) / 2
    mixed_radius = (hxy[1] - hxy[0]) / 2
    mixed_signed = mixed_mid * covariance
    mixed_moment = absolute_mixed_moment(triangle, center)
    assert Q(0) <= mixed_moment <= (variances[0] + variances[1]) / 2
    mixed_error = mixed_radius * mixed_moment
    remainder = (
        hxx[0] * variances[0] / 2 + hyy[0] * variances[1] / 2 + mixed_signed - mixed_error,
        hxx[1] * variances[0] / 2 + hyy[1] * variances[1] / 2 + mixed_signed + mixed_error,
    )
    taylor = (
        area * (h_center[0] + remainder[0]),
        area * (h_center[1] + remainder[1]),
    )
    clipped = max(direct[0], taylor[0]), min(direct[1], taylor[1])
    assert clipped[0] <= clipped[1]
    return clipped


def certify(args: argparse.Namespace) -> dict[str, object]:
    old_triangle, old_fibers, old_primitive = F.triangle_interval, F.fiber_cells, F.Primitive
    old_t_panels = C.T_PANELS
    C.T_PANELS = args.t_panels
    F.triangle_interval = triangle_interval
    F.fiber_cells = C.relative_fiber_cells
    F.Primitive = FastAnchoredPrimitive
    try:
        result = F.certify(args)
    finally:
        F.triangle_interval, F.fiber_cells, F.Primitive = old_triangle, old_fibers, old_primitive
        C.T_PANELS = old_t_panels

    parent = HERE / "certify_li_equation14_fiber_cancel_d.py"
    result["schema"] = "li-equation14-fiber-cancel-d-taylor-v1"
    result["dependencies"]["cancel_d_program_sha256"] = hashlib.sha256(parent.read_bytes()).hexdigest()
    result["parameters"]["t_panels"] = args.t_panels
    result["method"]["substitution"] = (
        "r=1/z and r=1/U+t*(1/L-1/U), exactly cancelling the outer D"
    )
    result["method"]["reduced_integrand"] = (
        "(1/L-1/U)/(x*y) * integral_0^1 (q-Fbar)(e+D*((1-t)/U+t/L)) dt"
    )
    result["method"]["quadrature"] = (
        "Exact x/y/L/U doubling cuts; "
        + (
            f"{args.t_panels}-panel directed midpoint enclosure of A; "
            if args.t_panels
            else "complete pointwise g-range enclosure of A for derivative bounds; "
        )
        + "centroid second-order Taylor of the stable product W*A using exact signed covariance; "
        "intersection with the direct D-free range."
    )
    result["limitations"][0] = (
        "Strict stable Taylor certificate; equation (14) closes only if the directed lower endpoint reaches the paper threshold."
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
    parser.add_argument(
        "--t-panels",
        type=int,
        default=0,
        help="Composite-midpoint panels for auxiliary ranges; 0 uses the complete g range.",
    )
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
