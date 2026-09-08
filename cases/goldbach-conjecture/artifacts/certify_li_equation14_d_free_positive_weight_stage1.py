"""D-free positive-weight stage-1 producer for Li equation (14).

This program is deliberately independent of the older equation-(14) JSON
certificates.  It constructs a fresh strict enclosure of the triple term

    T3 = integral W(x,y) A(x,y) dx dy,
    W = (1/L - 1/U)/(x*y) >= 0,
    A = integral_0^1 g((1-t)s_U + t*s_L) dt,

on the existing exact x/y/L/U relative-scale precut.  The value A(c) at a
triangle centroid is obtained from a new directed delay-cell prefix table,
not from a difference of two independently evaluated global primitives.
First derivatives of A are integrated as interval ranges in t.  A first-order
Taylor polynomial is integrated against strict signed W-weighted moments; an
essential Hessian bound is paired with absolute W-weighted second moments.

The output verdict is fixed to INCONCLUSIVE.  This is a finite stage-1
producer and audit checkpoint, not a proof of Li equation (14), any upstream
sieve interface, or strong Goldbach.  It is intended to be run directly for
local smoke testing and later adopted through the workspace runner only after
independent audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    # Exact Fraction accumulation across hundreds of independently bounded
    # moment cells legitimately produces integers longer than Python's I/O
    # safety default.  No decimal approximation replaces these integers.
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import certify_g1_taylor as G  # noqa: E402
import certify_li_equation14_fiber_cancel_d as C  # noqa: E402
import certify_li_equation14_fiber_cancel_d_taylor as D2  # noqa: E402
import certify_li_equation14_fiber_primitive as F  # noqa: E402
import certify_li_equation14_fiber_taylor as T  # noqa: E402
import certify_li_equation14_g_cell_model as GC  # noqa: E402
import certify_li_equation14_positive_weight_moments as PM  # noqa: E402

B = F.B
Interval = B.Interval
Affine = B.BR.Affine
Point2 = F.Point2
Triangle = F.Triangle
ZERO: Interval = (Q(0), Q(0))

REQUIRED_T3_FROM_PLAN = -Q(
    8302212373127748196068333548850242080780676647178395391298313681330450936750372749,
    40925498111187964337502690567744729161035465845660167929455443968000000000000000000,
)


def iv_add(first: Interval, second: Interval) -> Interval:
    return first[0] + second[0], first[1] + second[1]


def iv_sub(first: Interval, second: Interval) -> Interval:
    return first[0] - second[1], first[1] - second[0]


def iv_scale(interval: Interval, scalar: Q) -> Interval:
    if scalar >= 0:
        return interval[0] * scalar, interval[1] * scalar
    return interval[1] * scalar, interval[0] * scalar


def iv_intersection(first: Interval, second: Interval) -> Interval:
    answer = max(first[0], second[0]), min(first[1], second[1])
    assert answer[0] <= answer[1], (first, second)
    return answer


def iv_subset(inner: Interval, outer: Interval) -> bool:
    return outer[0] <= inner[0] <= inner[1] <= outer[1]


def iv_mid_radius(interval: Interval) -> tuple[Q, Q]:
    assert interval[0] <= interval[1]
    return (interval[0] + interval[1]) / 2, (interval[1] - interval[0]) / 2


def abs_upper(interval: Interval) -> Q:
    return max(abs(interval[0]), abs(interval[1]))


def q_record(value: Q, places: int = 18) -> dict[str, str]:
    return {
        "exact": G.frac(value),
        "decimal_upper": G.decimal_ceil(value, places),
    }


def parse_q(text: str) -> Q:
    numerator, denominator = text.split("/")
    return Q(int(numerator), int(denominator))


def affine_record(value: Affine) -> dict[str, str]:
    return {
        "constant": G.frac(value.c),
        "x": G.frac(value.x),
        "y": G.frac(value.y),
        "z": G.frac(value.z),
    }


@dataclass(frozen=True)
class PrefixQuery:
    alpha: Q
    beta: Q
    anchored_difference: Interval
    local_cell_sum: Interval
    enclosure: Interval
    uniform_remainder_radius: Q
    cells_touched: int

    def __post_init__(self) -> None:
        assert 0 < self.alpha <= self.beta
        assert self.uniform_remainder_radius >= 0
        assert iv_subset(self.local_cell_sum, self.anchored_difference)
        assert self.enclosure == iv_intersection(
            self.local_cell_sum, self.anchored_difference
        )


class StrictGPrefix:
    """Directed prefix integrals of the local polynomial models for g.

    Two enclosures are retained.  ``anchored_difference`` performs literal
    directed interval subtraction P(beta)-P(alpha).  ``local_cell_sum`` sums
    only the intersected cells and is tighter because the common anchored
    prefix cancels algebraically.  Their asserted intersection is returned.
    """

    def __init__(self, delay: G.FixedDelayTaylor, origin: Q):
        if origin <= 0 or origin * delay.mesh != int(origin * delay.mesh):
            raise ValueError("prefix origin must be a positive mesh boundary")
        self.delay = delay
        self.mesh = delay.mesh
        self.origin = origin
        self.minimum_index = int(origin * self.mesh)
        self.maximum_index = delay.max_s * self.mesh - 1
        self.models: dict[int, GC.GCellModel] = {}
        self.cell_integrals: dict[int, Interval] = {}
        self.cell_remainder_radii: dict[int, Q] = {}
        self.prefix_lower = [Q(0)]
        self.prefix_upper = [Q(0)]
        self.prefix_remainder_radius = [Q(0)]
        for index in range(self.minimum_index, self.maximum_index + 1):
            model = GC.g_cell_model(delay, index)
            integral = model.integral()
            remainder_radius = (model.remainder[1] - model.remainder[0]) * model.width / 2
            assert remainder_radius >= 0
            self.models[index] = model
            self.cell_integrals[index] = integral
            self.cell_remainder_radii[index] = remainder_radius
            self.prefix_lower.append(self.prefix_lower[-1] + integral[0])
            self.prefix_upper.append(self.prefix_upper[-1] + integral[1])
            self.prefix_remainder_radius.append(
                self.prefix_remainder_radius[-1] + remainder_radius
            )

    @property
    def end(self) -> Q:
        return Q(self.maximum_index + 1, self.mesh)

    def _offset(self, cell_boundary_index: int) -> int:
        offset = cell_boundary_index - self.minimum_index
        assert 0 <= offset < len(self.prefix_lower)
        return offset

    def _sum_complete_cells(self, left: int, right: int) -> Interval:
        """Sum complete cells with left <= j <= right, or return zero."""

        if left > right:
            return ZERO
        assert self.minimum_index <= left <= right <= self.maximum_index
        lo = self.prefix_lower[self._offset(right + 1)] - self.prefix_lower[
            self._offset(left)
        ]
        hi = self.prefix_upper[self._offset(right + 1)] - self.prefix_upper[
            self._offset(left)
        ]
        return lo, hi

    def _sum_complete_remainders(self, left: int, right: int) -> Q:
        if left > right:
            return Q(0)
        return self.prefix_remainder_radius[self._offset(right + 1)] - self.prefix_remainder_radius[
            self._offset(left)
        ]

    def prefix_at(self, s: Q) -> Interval:
        """Enclose integral_origin^s g by an anchored directed prefix."""

        assert self.origin <= s <= self.end
        scaled = s * self.mesh
        if scaled.denominator == 1:
            boundary = int(scaled)
            offset = self._offset(boundary)
            return self.prefix_lower[offset], self.prefix_upper[offset]
        cell = G.floor_q(s, self.mesh)
        assert self.minimum_index <= cell <= self.maximum_index
        offset = self._offset(cell)
        partial = self.models[cell].integral(Q(0), s - Q(cell, self.mesh))
        return (
            self.prefix_lower[offset] + partial[0],
            self.prefix_upper[offset] + partial[1],
        )

    def _local_sum(self, alpha: Q, beta: Q) -> tuple[Interval, Q, int]:
        if alpha == beta:
            return ZERO, Q(0), 0
        left = G.floor_q(alpha, self.mesh)
        right = G.ceil_q(beta, self.mesh) - 1
        assert self.minimum_index <= left <= right <= self.maximum_index
        if left == right:
            model = self.models[left]
            u0 = alpha - model.origin
            u1 = beta - model.origin
            interval = model.integral(u0, u1)
            radius = (model.remainder[1] - model.remainder[0]) * (u1 - u0) / 2
            return interval, radius, 1

        left_model = self.models[left]
        left_interval = left_model.integral(alpha - left_model.origin, left_model.width)
        left_radius = (
            (left_model.remainder[1] - left_model.remainder[0])
            * (left_model.end - alpha)
            / 2
        )
        right_model = self.models[right]
        right_width = beta - right_model.origin
        right_interval = right_model.integral(Q(0), right_width)
        right_radius = (
            (right_model.remainder[1] - right_model.remainder[0])
            * right_width
            / 2
        )
        middle = self._sum_complete_cells(left + 1, right - 1)
        middle_radius = self._sum_complete_remainders(left + 1, right - 1)
        return (
            iv_add(iv_add(left_interval, middle), right_interval),
            left_radius + middle_radius + right_radius,
            right - left + 1,
        )

    def query(self, alpha: Q, beta: Q) -> PrefixQuery:
        assert self.origin <= alpha <= beta <= self.end
        at_alpha = self.prefix_at(alpha)
        at_beta = self.prefix_at(beta)
        # This is deliberately generic directed interval subtraction.  It is
        # kept and checked even though the same-cell sum below is tighter.
        anchored = iv_sub(at_beta, at_alpha)
        local, remainder_radius, touched = self._local_sum(alpha, beta)
        assert iv_subset(local, anchored), (alpha, beta, local, anchored)
        return PrefixQuery(
            alpha,
            beta,
            anchored,
            local,
            iv_intersection(local, anchored),
            remainder_radius,
            touched,
        )


def exact_low_s_integral(alpha: Q, beta: Q, bits: int = 224) -> Interval:
    assert 0 < alpha <= beta <= 3
    log_ratio = G.log_interval(beta / alpha, bits)
    return iv_add(
        (B.QSTAR * (beta - alpha),) * 2,
        iv_scale(log_ratio, Q(-2)),
    )


def prefix_self_tests(prefix: StrictGPrefix) -> list[dict[str, object]]:
    tests: list[dict[str, object]] = []
    h = Q(1, prefix.mesh)
    probes = (
        (Q(59, 100), Q(79, 100), "below_one_cross_cell"),
        (Q(7, 8), Q(9, 8), "cross_s_equals_one"),
        (Q(23, 8), Q(3), "touch_s_equals_three_from_left"),
        (Q(3, 4), Q(3), "long_explicit_identity"),
    )
    for alpha, beta, name in probes:
        query = prefix.query(alpha, beta)
        exact = exact_low_s_integral(alpha, beta)
        assert iv_subset(exact, query.enclosure), (name, exact, query.enclosure)
        assert query.cells_touched == G.ceil_q(beta, prefix.mesh) - G.floor_q(alpha, prefix.mesh)
        tests.append(
            {
                "name": name,
                "status": "PASS",
                "query": G.interval_record(*query.enclosure, places=24),
                "independent_exact_log_enclosure": G.interval_record(*exact, places=24),
            }
        )

    ordinary = prefix.query(Q(401, 100), Q(507, 100))
    split = Q(9, 2)
    left = prefix.query(ordinary.alpha, split)
    right = prefix.query(split, ordinary.beta)
    additive = iv_add(left.local_cell_sum, right.local_cell_sum)
    assert additive == ordinary.local_cell_sum
    tests.append(
        {
            "name": "ordinary_delay_query_local_additivity",
            "status": "PASS",
            "query_cells": ordinary.cells_touched,
            "anchored_directed_contains_local": True,
        }
    )

    zero = prefix.query(Q(3), Q(3))
    assert zero.enclosure == ZERO and zero.cells_touched == 0
    tests.append({"name": "zero_width_query", "status": "PASS"})

    # Both adjacent cell models must contain the exact boundary value.  This
    # independently exercises point evaluation in addition to prefix sums.
    exact_three = (B.QSTAR - Q(2, 3),) * 2
    left_model = prefix.models[3 * prefix.mesh - 1]
    right_model = prefix.models[3 * prefix.mesh]
    assert iv_subset(exact_three, left_model.point(h))
    assert iv_subset(exact_three, right_model.point(Q(0)))
    tests.append({"name": "s_equals_three_two_sided_point_models", "status": "PASS"})
    return tests


def g_second_essential_range(
    evaluator: B.ARatioDerivatives, lo: Q, hi: Q
) -> Interval:
    assert 0 < lo <= hi <= evaluator.delay.max_s
    if lo == hi == 3:
        # g'' has a finite jump here.  Its two one-sided values are retained;
        # an essential Hessian bound is all the first-order Taylor remainder
        # needs.
        return -Q(13, 27), -Q(4, 27)
    return C.g_second_range(evaluator, lo, hi)


def endpoint_range_hull(
    first: Interval, second: Interval
) -> Interval:
    return min(first[0], second[0]), max(first[1], second[1])


def interpolate_interval(first: Interval, second: Interval, t: Q) -> Interval:
    return iv_add(iv_scale(first, 1 - t), iv_scale(second, t))


def averaged_a_derivatives(
    triangle: Triangle,
    lower: Affine,
    upper: Affine,
    theta: Affine,
    evaluator: B.ARatioDerivatives,
    t_panels: int,
) -> tuple[Interval, Interval, Interval, Interval, Interval]:
    """Ranges of Ax, Ay, Axx, Axy, Ayy without a divided difference."""

    assert t_panels > 0
    endpoint_l = D2.endpoint_s_ranges(lower, theta, triangle)
    endpoint_u = D2.endpoint_s_ranges(upper, theta, triangle)
    ax = ay = axx = axy = ayy = ZERO
    keys = ("sx", "sy", "sxx", "sxy", "syy")
    for panel in range(t_panels):
        left = Q(panel, t_panels)
        right = Q(panel + 1, t_panels)
        width = right - left
        s_left = interpolate_interval(endpoint_u["s"], endpoint_l["s"], left)
        s_right = interpolate_interval(endpoint_u["s"], endpoint_l["s"], right)
        s_range = endpoint_range_hull(s_left, s_right)
        _, gp = T.g_derivative_ranges(evaluator, *s_range)
        gpp = g_second_essential_range(evaluator, *s_range)

        derivatives: list[Interval] = []
        for key in keys:
            at_left = interpolate_interval(endpoint_u[key], endpoint_l[key], left)
            at_right = interpolate_interval(endpoint_u[key], endpoint_l[key], right)
            derivatives.append(endpoint_range_hull(at_left, at_right))
        sx, sy, sxx, sxy, syy = derivatives
        ax = iv_add(ax, iv_scale(B.iv_mul(gp, sx), width))
        ay = iv_add(ay, iv_scale(B.iv_mul(gp, sy), width))
        axx = iv_add(
            axx,
            iv_scale(iv_add(B.iv_mul(gpp, B.iv_mul(sx, sx)), B.iv_mul(gp, sxx)), width),
        )
        axy = iv_add(
            axy,
            iv_scale(iv_add(B.iv_mul(gpp, B.iv_mul(sx, sy)), B.iv_mul(gp, sxy)), width),
        )
        ayy = iv_add(
            ayy,
            iv_scale(iv_add(B.iv_mul(gpp, B.iv_mul(sy, sy)), B.iv_mul(gp, syy)), width),
        )
    return ax, ay, axx, axy, ayy


def midpoint_average_check(
    su: Q,
    sl: Q,
    evaluator: B.ARatioDerivatives,
    t_panels: int,
) -> Interval:
    """Independent directed midpoint enclosure of the centroid t-average."""

    assert 0 < su <= sl and t_panels > 0
    delta = sl - su
    h = Q(1, t_panels)
    total = ZERO
    for panel in range(t_panels):
        left = Q(panel, t_panels)
        right = Q(panel + 1, t_panels)
        center = (left + right) / 2
        s_center = su + center * delta
        g_center = T.g_derivative_ranges(evaluator, s_center, s_center)[0]
        panel_range = su + left * delta, su + right * delta
        gpp = g_second_essential_range(evaluator, *panel_range)
        remainder = iv_scale(gpp, delta**2 * h**3 / 24)
        total = iv_add(total, iv_add(iv_scale(g_center, h), remainder))
    coarse = T.g_derivative_ranges(evaluator, su, sl)[0]
    return iv_intersection(total, coarse)


def final_moments(
    triangle: Triangle, lower: Affine, upper: Affine, depth: int
) -> tuple[PM.MomentBundle, int]:
    weight = PM.PositiveFiberWeight(lower, upper)
    checkpoints, moments = PM.moment_sequence(triangle, weight.range, depth)
    return moments, int(checkpoints[-1]["sign_fixed_leaf_triangles"])


@dataclass(frozen=True)
class TaylorContribution:
    nominal: Q
    budgets: dict[str, Q]
    interval: Interval
    uniform_remainder_subbudget: Q

    def __post_init__(self) -> None:
        assert all(value >= 0 for value in self.budgets.values())
        radius = sum(self.budgets.values(), Q(0))
        assert self.interval == (self.nominal - radius, self.nominal + radius)
        assert 0 <= self.uniform_remainder_subbudget <= self.budgets[
            "g_prefix_model_radius"
        ] + self.budgets["coefficient_moment_interaction_radius"]


def weighted_first_order_taylor(
    a0: Interval,
    ax: Interval,
    ay: Interval,
    axx: Interval,
    axy: Interval,
    ayy: Interval,
    moments: PM.MomentBundle,
    a0_uniform_radius: Q,
) -> TaylorContribution:
    budgets = {
        "g_prefix_model_radius": Q(0),
        "center_derivative_panel_radius": Q(0),
        "weighted_moment_radius": Q(0),
        "coefficient_moment_interaction_radius": Q(0),
        "taylor_hessian_remainder_radius": Q(0),
    }
    nominal = Q(0)
    uniform_subbudget = Q(0)
    for name, coefficient, index in (
        ("a0", a0, (0, 0)),
        ("ax", ax, (1, 0)),
        ("ay", ay, (0, 1)),
    ):
        cmid, cradius = iv_mid_radius(coefficient)
        mmid, mradius = iv_mid_radius(moments.signed[index])
        nominal += cmid * mmid
        coefficient_key = (
            "g_prefix_model_radius"
            if name == "a0"
            else "center_derivative_panel_radius"
        )
        budgets[coefficient_key] += cradius * abs(mmid)
        budgets["weighted_moment_radius"] += abs(cmid) * mradius
        budgets["coefficient_moment_interaction_radius"] += cradius * mradius
        if name == "a0":
            assert 0 <= a0_uniform_radius <= cradius
            uniform_subbudget = a0_uniform_radius * (abs(mmid) + mradius)

    hessian = (
        Q(1, 2) * abs_upper(axx) * moments.absolute[2, 0][1]
        + abs_upper(axy) * moments.absolute[1, 1][1]
        + Q(1, 2) * abs_upper(ayy) * moments.absolute[0, 2][1]
    )
    budgets["taylor_hessian_remainder_radius"] = hessian
    radius = sum(budgets.values(), Q(0))
    return TaylorContribution(
        nominal,
        budgets,
        (nominal - radius, nominal + radius),
        uniform_subbudget,
    )


def manufactured_weighted_taylor_test() -> dict[str, object]:
    triangle: Triangle = (
        (Q(0), Q(0)),
        (Q(1), Q(0)),
        (Q(0), Q(1)),
    )
    weight = Q(7, 5)

    def constant_weight(_: Triangle) -> Interval:
        return weight, weight

    _, moments = PM.moment_sequence(triangle, constant_weight, 0)
    a0, ax, ay = Q(5, 7), Q(-3, 5), Q(4, 9)
    axx, axy, ayy = Q(7, 4), Q(-5, 6), Q(11, 10)
    result = weighted_first_order_taylor(
        (a0, a0),
        (ax, ax),
        (ay, ay),
        (axx, axx),
        (axy, axy),
        (ayy, ayy),
        moments,
        Q(0),
    )
    signed, _ = PM.exact_reference_moments()
    exact = weight * (
        a0 * signed[0, 0]
        + ax * signed[1, 0]
        + ay * signed[0, 1]
        + Q(1, 2) * axx * signed[2, 0]
        + axy * signed[1, 1]
        + Q(1, 2) * ayy * signed[0, 2]
    )
    assert result.interval[0] <= exact <= result.interval[1]
    return {
        "name": "manufactured_constant_weight_quadratic_A",
        "status": "PASS",
        "exact_integral": G.frac(exact),
        "enclosure": G.interval_record(*result.interval, places=18),
    }


def geometry_identity(
    label: str,
    theta: Affine,
    lower: Affine,
    upper: Affine,
    triangle: Triangle,
) -> tuple[str, dict[str, object]]:
    payload: dict[str, object] = {
        "winner": label,
        "theta": affine_record(theta),
        "lower": affine_record(lower),
        "upper": affine_record(upper),
        "triangle": [[G.frac(x), G.frac(y)] for x, y in triangle],
    }
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest(), payload


def triangle_stage1(
    triangle: Triangle,
    lower: Affine,
    upper: Affine,
    theta: Affine,
    prefix: StrictGPrefix,
    evaluator: B.ARatioDerivatives,
    t_panels: int,
    moment_depth: int,
) -> tuple[TaylorContribution, dict[str, object]]:
    center = PM.centroid(triangle)
    center_triangle: Triangle = (center, center, center)
    d_affine = Affine(theta.c, theta.x - 1, theta.y - 1)
    d = d_affine.at(center[0], center[1], Q(0))
    zl = lower.at(center[0], center[1], Q(0))
    zu = upper.at(center[0], center[1], Q(0))
    e = theta.z - 1
    assert center[0] > 0 and center[1] > 0 and d > 0 and 0 < zl < zu
    su, sl = e + d / zu, e + d / zl
    assert prefix.origin <= su < sl <= prefix.end

    query = prefix.query(su, sl)
    delta_s = sl - su
    a0 = iv_scale(query.enclosure, 1 / delta_s)
    a0_uniform_radius = query.uniform_remainder_radius / delta_s
    independent_a0 = midpoint_average_check(su, sl, evaluator, t_panels)
    overlap = iv_intersection(a0, independent_a0)
    assert overlap[0] <= overlap[1]

    ax, ay, _, _, _ = averaged_a_derivatives(
        center_triangle, lower, upper, theta, evaluator, t_panels
    )
    _, _, axx, axy, ayy = averaged_a_derivatives(
        triangle, lower, upper, theta, evaluator, t_panels
    )
    moments, moment_leaves = final_moments(
        triangle, lower, upper, moment_depth
    )
    contribution = weighted_first_order_taylor(
        a0,
        ax,
        ay,
        axx,
        axy,
        ayy,
        moments,
        a0_uniform_radius,
    )
    detail = {
        "centroid": [G.frac(value) for value in center],
        "s_U_exact": G.frac(su),
        "s_L_exact": G.frac(sl),
        "delta_s_exact": G.frac(delta_s),
        "g_prefix_query": {
            "cells_touched": query.cells_touched,
            "anchored_directed": G.interval_record(
                *query.anchored_difference, places=24
            ),
            "local_cell_sum": G.interval_record(*query.local_cell_sum, places=24),
            "returned_intersection": G.interval_record(*query.enclosure, places=24),
            "uniform_remainder_radius_exact": G.frac(
                query.uniform_remainder_radius
            ),
        },
        "A_coefficients": {
            "A0_prefix": G.interval_record(*a0, places=24),
            "A0_independent_midpoint_check": G.interval_record(
                *independent_a0, places=24
            ),
            "Ax": G.interval_record(*ax, places=18),
            "Ay": G.interval_record(*ay, places=18),
            "Axx_full_triangle": G.interval_record(*axx, places=18),
            "Axy_full_triangle": G.interval_record(*axy, places=18),
            "Ayy_full_triangle": G.interval_record(*ayy, places=18),
        },
        "moment_leaf_triangles": moment_leaves,
        "moments": moments.record(places=18),
    }
    return contribution, detail


def certify(args: argparse.Namespace) -> dict[str, object]:
    if not __debug__:
        raise RuntimeError("assertions are part of this stage-1 producer")
    if args.mesh != 8:
        raise ValueError("the inherited relative precut is currently audited at mesh=8")

    source_path = HERE / "li-equation14-certificate.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    fixed_names = (
        "zero_dimensional_500_fbar_minus_q",
        "one_dimensional_500_integral_q_minus_Fbar",
        "two_dimensional_500_integral_fbar_minus_q",
    )
    fixed = [
        (
            parse_q(source["components"][name]["lower_exact"]),
            parse_q(source["components"][name]["upper_exact"]),
        )
        for name in fixed_names
    ]
    skeleton_record = source["stable_identity"]["constant_skeleton"]
    skeleton = (
        parse_q(skeleton_record["lower_exact"]),
        parse_q(skeleton_record["upper_exact"]),
    )
    assert skeleton[0] == skeleton[1]
    required_t3 = B.TARGET_K14 / 2 - skeleton[0] - sum(
        (item[0] for item in fixed), Q(0)
    )
    assert required_t3 == REQUIRED_T3_FROM_PLAN

    delay = G.FixedDelayTaylor(
        args.mesh, args.degree, args.max_s, args.dyadic_bits
    )
    evaluator = D2.FastARatioDerivatives(delay)
    prefix = StrictGPrefix(delay, args.prefix_origin)
    prefix_tests = prefix_self_tests(prefix)
    manufactured_test = manufactured_weighted_taylor_test()

    pieces = B.theta_branch_polytopes()
    expected_volume = (B.C14 - B.A0) ** 3 / 6
    assert len(pieces) == 12
    base_cell_count = relative_cell_count = triangle_count = 0
    base_volume = relative_volume = Q(0)
    min_positive = {
        "x": None,
        "y": None,
        "D": None,
        "L": None,
        "U": None,
    }
    min_thickness = None
    min_s = None
    max_s = None
    winner_records: list[dict[str, object]] = []
    cell_records: list[dict[str, object]] = []
    detail_records: list[tuple[Q, dict[str, object]]] = []
    all_identity_hashes: list[str] = []
    global_nominal = Q(0)
    global_budgets = {
        "g_prefix_model_radius": Q(0),
        "center_derivative_panel_radius": Q(0),
        "weighted_moment_radius": Q(0),
        "coefficient_moment_interaction_radius": Q(0),
        "taylor_hessian_remainder_radius": Q(0),
    }
    global_uniform_subbudget = Q(0)

    for piece_index, piece in enumerate(pieces):
        base_cells = F.fiber_cells(piece)
        relative_cells = C.relative_fiber_cells(piece)
        piece_base_volume = Q(0)
        piece_relative_volume = Q(0)
        piece_triangles = 0
        base_cell_count += len(base_cells)
        relative_cell_count += len(relative_cells)
        for polygon, lower, upper in base_cells:
            for triangle in F.polygon_triangles(polygon):
                volume = F.affine_integral_triangle(upper - lower, triangle)
                assert volume > 0
                piece_base_volume += volume
        assert piece_base_volume == piece.volume

        for relative_index, (polygon, lower, upper) in enumerate(relative_cells):
            triangles = F.polygon_triangles(polygon)
            assert triangles
            for local_triangle_index, triangle in enumerate(triangles):
                area = F.triangle_area(triangle)
                thickness_affine = upper - lower
                volume = F.affine_integral_triangle(thickness_affine, triangle)
                assert area > 0 and volume > 0
                piece_relative_volume += volume
                piece_triangles += 1
                triangle_count += 1
                d_affine = Affine(piece.theta.c, piece.theta.x - 1, piece.theta.y - 1)
                e = piece.theta.z - 1
                for x, y in triangle:
                    values = {
                        "x": x,
                        "y": y,
                        "D": d_affine.at(x, y, Q(0)),
                        "L": lower.at(x, y, Q(0)),
                        "U": upper.at(x, y, Q(0)),
                    }
                    assert values["x"] > 0 and values["y"] > 0
                    assert values["D"] > 0 and values["L"] > 0
                    assert values["U"] >= values["L"]
                    thickness = values["U"] - values["L"]
                    min_thickness = (
                        thickness
                        if min_thickness is None
                        else min(min_thickness, thickness)
                    )
                    for name in min_positive:
                        value = values[name]
                        min_positive[name] = (
                            value
                            if min_positive[name] is None
                            else min(min_positive[name], value)
                        )
                    su = e + values["D"] / values["U"]
                    sl = e + values["D"] / values["L"]
                    assert 0 < su <= sl <= delay.max_s
                    min_s = su if min_s is None else min(min_s, su)
                    max_s = sl if max_s is None else max(max_s, sl)

                contribution, detail = triangle_stage1(
                    triangle,
                    lower,
                    upper,
                    piece.theta,
                    prefix,
                    evaluator,
                    args.t_panels,
                    args.moment_depth,
                )
                identity_hash, identity = geometry_identity(
                    piece.label, piece.theta, lower, upper, triangle
                )
                all_identity_hashes.append(identity_hash)
                global_nominal += contribution.nominal
                for name, value in contribution.budgets.items():
                    global_budgets[name] += value
                global_uniform_subbudget += contribution.uniform_remainder_subbudget
                radius = sum(contribution.budgets.values(), Q(0))
                record = {
                    "piece_index": piece_index,
                    "relative_cell_index": relative_index,
                    "local_triangle_index": local_triangle_index,
                    "identity_sha256": identity_hash,
                    "nominal_exact": G.frac(contribution.nominal),
                    "radius_exact": G.frac(radius),
                    "interval": G.interval_record(*contribution.interval, places=18),
                    "budgets_exact": {
                        name: G.frac(value)
                        for name, value in contribution.budgets.items()
                    },
                    "g_uniform_remainder_propagated_subbudget_exact": G.frac(
                        contribution.uniform_remainder_subbudget
                    ),
                }
                cell_records.append(record)
                detail_records.append(
                    (
                        radius,
                        {
                            **record,
                            "geometry_identity": identity,
                            "calculation_detail": detail,
                        },
                    )
                )

        assert piece_relative_volume == piece.volume
        base_volume += piece_base_volume
        relative_volume += piece_relative_volume
        winner_records.append(
            {
                "piece_index": piece_index,
                "winner": piece.label,
                "base_fiber_cells": len(base_cells),
                "relative_fiber_cells": len(relative_cells),
                "relative_triangles": piece_triangles,
                "declared_volume_exact": G.frac(piece.volume),
                "base_fiber_volume_exact": G.frac(piece_base_volume),
                "relative_precut_volume_exact": G.frac(piece_relative_volume),
                "both_volume_equalities_verified": True,
            }
        )

    assert base_cell_count == 28
    assert base_volume == expected_volume
    assert relative_volume == expected_volume
    assert min_positive["D"] == Q(53, 206)
    assert min_s is not None and prefix.origin <= min_s
    assert max_s is not None and max_s <= prefix.end
    assert all(value is not None and value > 0 for value in min_positive.values())
    assert min_thickness is not None and min_thickness >= 0

    exact_radius = sum(global_budgets.values(), Q(0))
    exact_interval = global_nominal - exact_radius, global_nominal + exact_radius
    rounded_interval = (
        B.lower_dyadic(exact_interval[0], args.accum_bits),
        B.upper_dyadic(exact_interval[1], args.accum_bits),
    )
    rounding_slack = (
        exact_interval[0] - rounded_interval[0],
        rounded_interval[1] - exact_interval[1],
    )
    assert rounding_slack[0] >= 0 and rounding_slack[1] >= 0
    coefficient = (
        2
        * (
            skeleton[0]
            + sum((item[0] for item in fixed), Q(0))
            + rounded_interval[0]
        ),
        2
        * (
            skeleton[1]
            + sum((item[1] for item in fixed), Q(0))
            + rounded_interval[1]
        ),
    )

    top_details = [
        item
        for _, item in sorted(
            detail_records, key=lambda pair: pair[0], reverse=True
        )[: args.record_top]
    ]
    identity_digest = hashlib.sha256(
        "\n".join(all_identity_hashes).encode("ascii")
    ).hexdigest()
    dependencies = (
        HERE / "certify_g1_taylor.py",
        HERE / "certify_li_equation14_polytope_taylor.py",
        HERE / "certify_li_equation14_fiber_primitive.py",
        HERE / "certify_li_equation14_fiber_cancel_d.py",
        HERE / "certify_li_equation14_fiber_cancel_d_taylor.py",
        HERE / "certify_li_equation14_g_cell_model.py",
        HERE / "certify_li_equation14_positive_weight_moments.py",
        source_path,
    )
    return {
        "schema": "li-equation14-d-free-positive-weight-stage1-v1",
        "verdict": "D_FREE_POSITIVE_WEIGHT_STAGE1_INCONCLUSIVE",
        "formal_status": "LOCAL_NON_WORKSPACE_SMOKE_UNTIL_RUNNER_ADOPTION_AND_INDEPENDENT_AUDIT",
        "scope": {
            "computed": (
                "A full-domain strict interval for Li equation (14)'s T3 term "
                "on the current relative x/y/L/U precut, using a D-free "
                "positive-weight first-order Taylor/moment formula."
            ),
            "does_not_certify": [
                "Li equation (14)",
                "the printed S2/M lower bound",
                "any upstream or downstream sieve interface",
                "the strong Goldbach conjecture",
            ],
        },
        "parameters": {
            "delay_mesh": args.mesh,
            "delay_degree": args.degree,
            "delay_max_s": args.max_s,
            "dyadic_bits": args.dyadic_bits,
            "prefix_origin_exact": G.frac(args.prefix_origin),
            "t_panels": args.t_panels,
            "moment_midpoint_depth": args.moment_depth,
            "accumulation_bits": args.accum_bits,
            "detailed_widest_cells_recorded": args.record_top,
        },
        "mathematical_contract": {
            "d_free_identity": (
                "int_L^U g(e+D/z)/(x*y*z^2) dz = "
                "((1/L-1/U)/(x*y))*int_0^1 g((1-t)s_U+t*s_L) dt"
            ),
            "prefix_query": (
                "Every g integral retains directed anchored subtraction "
                "[P_beta_lo-P_alpha_hi,P_beta_hi-P_alpha_lo], intersects it "
                "with a tighter sum of only the touched certified delay-cell "
                "models, and never subtracts midpoints."
            ),
            "weighted_taylor": (
                "int W*A = A(c)mu00+Ax(c)mu10+Ay(c)mu01+R, with "
                "|R| <= |Axx|mu20_abs/2+|Axy|mu11_abs+|Ayy|mu02_abs/2."
            ),
            "positivity": (
                "W=(U-L)/(x*y*L*U)>=0 is range-enclosed only after exact "
                "vertex checks x,y,L,U>0 and U-L>=0."
            ),
            "division_by_D": False,
            "global_primitive_point_difference": False,
        },
        "self_tests": {
            "g_prefix": prefix_tests,
            "weighted_taylor": manufactured_test,
        },
        "geometry": {
            "theta_branch_polytopes": len(pieces),
            "base_vertical_fiber_cells": base_cell_count,
            "relative_precut_fiber_cells": relative_cell_count,
            "relative_precut_triangles": triangle_count,
            "minimum_positive_exact": {
                name: G.frac(value) for name, value in min_positive.items()
            },
            "minimum_U_minus_L_at_vertices_exact": G.frac(min_thickness),
            "endpoint_s_range_exact": [G.frac(min_s), G.frac(max_s)],
            "ordered_domain_volume_exact": G.frac(expected_volume),
            "base_fiber_volume_exact": G.frac(base_volume),
            "relative_precut_volume_exact": G.frac(relative_volume),
            "all_three_volumes_equal": True,
            "ordered_triangle_identity_digest_sha256": identity_digest,
            "per_winner": winner_records,
        },
        "T3": {
            "nominal_exact": G.frac(global_nominal),
            "exact_symmetric_radius": q_record(exact_radius, 18),
            "exact_interval_before_accumulation_rounding": G.interval_record(
                *exact_interval, places=18
            ),
            "directed_accumulation_interval": G.interval_record(
                *rounded_interval, places=18
            ),
            "required_lower_exact": G.frac(required_t3),
            "lower_slack_or_deficit": (
                G.decimal_floor(rounded_interval[0] - required_t3, 18)
                if rounded_interval[0] > required_t3
                else G.decimal_ceil(required_t3 - rounded_interval[0], 18)
            ),
            "strictly_above_required_lower": rounded_interval[0] > required_t3,
        },
        "error_decomposition": {
            "additive_symmetric_radius_components": {
                name: q_record(value, 18)
                for name, value in global_budgets.items()
            },
            "g_uniform_remainder_propagated_subbudget_not_added_twice": q_record(
                global_uniform_subbudget, 24
            ),
            "directed_accumulation_rounding_slack": {
                "lower": q_record(rounding_slack[0], 24),
                "upper": q_record(rounding_slack[1], 24),
            },
            "budget_sum_equals_exact_symmetric_radius": True,
        },
        "S2_over_M_diagnostic_only": {
            "interval": G.interval_record(*coefficient, places=18),
            "target_exact": G.frac(B.TARGET_K14),
            "numeric_gate_before_audit": coefficient[0] >= B.TARGET_K14,
        },
        "all_triangle_contributions": cell_records,
        "widest_triangle_details": top_details,
        "dependencies_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in dependencies
        },
        "limitations": [
            "This file was designed as a local stage-1 producer; a direct run is not a ledgered workspace run.",
            "The W-moment enclosures use positive-factor range subdivision, not the proposed analytic-y/strict-1D-x moment integrator.",
            "The first-order Taylor remainder can remain too wide on coarse triangles; performance is not a theorem.",
            "The imported delay Taylor and geometry engines are pinned by hashes but still require independent proof audit for formal adoption.",
            "The verdict remains inconclusive regardless of the diagnostic numeric gate.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-check-only", action="store_true")
    parser.add_argument("--mesh", type=int, default=8)
    parser.add_argument("--degree", type=int, default=16)
    parser.add_argument("--max-s", type=int, default=300)
    parser.add_argument("--dyadic-bits", type=int, default=96)
    parser.add_argument("--prefix-origin", type=parse_q, default=Q(1, 2))
    parser.add_argument("--t-panels", type=int, default=16)
    parser.add_argument("--moment-depth", type=int, default=0)
    parser.add_argument("--accum-bits", type=int, default=160)
    parser.add_argument("--record-top", type=int, default=24)
    args = parser.parse_args()
    if args.t_panels <= 0:
        parser.error("require t-panels > 0")
    if not 0 <= args.moment_depth <= 5:
        parser.error("require 0 <= moment-depth <= 5")
    if args.record_top < 0:
        parser.error("require record-top >= 0")

    if args.self_check_only:
        delay = G.FixedDelayTaylor(
            args.mesh, args.degree, args.max_s, args.dyadic_bits
        )
        prefix = StrictGPrefix(delay, args.prefix_origin)
        result: dict[str, object] = {
            "schema": "li-equation14-d-free-positive-weight-stage1-selfcheck-v1",
            "verdict": "LOCAL_SELFCHECK_PASS",
            "g_prefix": prefix_self_tests(prefix),
            "weighted_taylor": manufactured_weighted_taylor_test(),
        }
    else:
        if args.output is None:
            parser.error("--output is required unless --self-check-only is used")
        result = certify(args)

    result["program_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    if args.self_check_only:
        print(rendered, end="")
    else:
        print(
            json.dumps(
                {
                    "verdict": result["verdict"],
                    "formal_status": result["formal_status"],
                    "geometry": {
                        key: result["geometry"][key]
                        for key in (
                            "theta_branch_polytopes",
                            "base_vertical_fiber_cells",
                            "relative_precut_fiber_cells",
                            "relative_precut_triangles",
                            "ordered_domain_volume_exact",
                            "all_three_volumes_equal",
                        )
                    },
                    "T3": result["T3"],
                    "error_decomposition": result["error_decomposition"],
                    "program_sha256": result["program_sha256"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
