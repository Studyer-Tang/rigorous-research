"""Polytope/Taylor smoke certificate for Li (2024), equation (14).

Only the three-dimensional term left wide by R044 is recomputed here.  On
the exact ordered domain

    1/500 <= t3 <= t2 <= t1 <= 1/6.18,

the flattened six-candidate representation of ``theta_1`` is partitioned by
all phi fold planes and winner comparison planes.  Every resulting convex
polytope is then cut by the delay planes ``s=j/8``, where

    s = (theta_1(t1,t2,t3)-t1-t2-t3)/t3.

The delay pieces are tetrahedralized over exact rational vertices.  On each
tetrahedron a second-order Taylor enclosure of

    (q - Fbar(s))/(t1*t2*t3**2),  Fbar(s)=2*a(s)/s,

is integrated about the centroid.  Diagonal second moments are exact;
mixed terms use ``|uv| <= (u^2+v^2)/2``.  This is deliberately a smoke
implementation: it favors a short, easily audited error argument over the
tighter orthant moments that may be needed for the final certificate.

All decisive geometry and arithmetic uses ``fractions.Fraction``.  R044's
already rigorous zero-, one-, and two-dimensional component intervals are
reused by hash, and W050 must remain IN_PROGRESS until an independent audit.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path

import certify_g1_branch_cubature as BR

G = BR.BASE
HERE = Path(__file__).resolve().parent
A0 = Q(1, 500)
C14 = Q(50, 309)
THETA_FOLD = Q(25, 128)
QSTAR = Q(5614594835668851, 10**16)
TARGET_K14 = Q(1_633_479, 250_000)

Point3 = tuple[Q, Q, Q]
Tetra = tuple[Point3, Point3, Point3, Point3]
Interval = tuple[Q, Q]


def iv_add(a: Interval, b: Interval) -> Interval:
    return a[0] + b[0], a[1] + b[1]


def iv_sub(a: Interval, b: Interval) -> Interval:
    return a[0] - b[1], a[1] - b[0]


def iv_mul(a: Interval, b: Interval) -> Interval:
    values = (a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1])
    return min(values), max(values)


def iv_scale(a: Interval, q: Q) -> Interval:
    return (a[0] * q, a[1] * q) if q >= 0 else (a[1] * q, a[0] * q)


def reciprocal_power(lo: Q, hi: Q, power: int) -> Interval:
    assert 0 < lo <= hi and power > 0
    return 1 / hi**power, 1 / lo**power


def lower_dyadic(value: Q, bits: int) -> Q:
    scale = 1 << bits
    return Q(G.floor_q(value, scale), scale)


def upper_dyadic(value: Q, bits: int) -> Q:
    scale = 1 << bits
    return Q(G.ceil_q(value, scale), scale)


def determinant3(rows: tuple[Point3, Point3, Point3]) -> Q:
    (a, b, c), (d, e, f), (g, h, i) = rows
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def tetra_volume(tetra: Tetra) -> Q:
    a, b, c, d = tetra
    rows = (
        (b[0] - a[0], b[1] - a[1], b[2] - a[2]),
        (c[0] - a[0], c[1] - a[1], c[2] - a[2]),
        (d[0] - a[0], d[1] - a[1], d[2] - a[2]),
    )
    return abs(determinant3(rows)) / 6


def solve_planes(a: BR.Affine, b: BR.Affine, c: BR.Affine) -> Point3 | None:
    rows = ((a.x, a.y, a.z), (b.x, b.y, b.z), (c.x, c.y, c.z))
    det = determinant3(rows)
    if det == 0:
        return None
    rhs = (-a.c, -b.c, -c.c)
    x = determinant3(((rhs[0], a.y, a.z), (rhs[1], b.y, b.z), (rhs[2], c.y, c.z))) / det
    y = determinant3(((a.x, rhs[0], a.z), (b.x, rhs[1], b.z), (c.x, rhs[2], c.z))) / det
    z = determinant3(((a.x, a.y, rhs[0]), (b.x, b.y, rhs[1]), (c.x, c.y, rhs[2]))) / det
    return x, y, z


def plane_key(a: BR.Affine) -> tuple[int, int, int, int] | None:
    values = (a.c, a.x, a.y, a.z)
    if not any(values):
        return None
    denominator = math.lcm(*(value.denominator for value in values))
    integers = [value.numerator * (denominator // value.denominator) for value in values]
    divisor = 0
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    integers = [value // divisor for value in integers]
    first = next(value for value in integers if value)
    if first < 0:
        integers = [-value for value in integers]
    return tuple(integers)  # type: ignore[return-value]


def unique_planes(constraints: list[BR.Affine]) -> list[BR.Affine]:
    answer: dict[tuple[int, int, int, int], BR.Affine] = {}
    for affine in constraints:
        key = plane_key(affine)
        if key is not None:
            answer.setdefault(key, affine)
    return list(answer.values())


def poly_vertices(constraints: list[BR.Affine]) -> list[Point3]:
    vertices: set[Point3] = set()
    for planes in itertools.combinations(unique_planes(constraints), 3):
        point = solve_planes(*planes)
        if point is not None and all(affine.at(*point) >= 0 for affine in constraints):
            vertices.add(point)
    return sorted(vertices)


def cross2(o: tuple[Q, Q], a: tuple[Q, Q], b: tuple[Q, Q]) -> Q:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def face_hull(points: list[Point3], plane: BR.Affine) -> list[Point3]:
    normal = (plane.x, plane.y, plane.z)
    drop = next(index for index, value in enumerate(normal) if value != 0)
    keep = tuple(index for index in range(3) if index != drop)
    projected = sorted({(point[keep[0]], point[keep[1]], point) for point in points})
    if len(projected) < 3:
        return []

    def build(items):
        hull = []
        for item in items:
            p = item[:2]
            while len(hull) >= 2 and cross2(hull[-2][:2], hull[-1][:2], p) <= 0:
                hull.pop()
            hull.append(item)
        return hull

    lower = build(projected)
    upper = build(reversed(projected))
    hull = lower[:-1] + upper[:-1]
    return [item[2] for item in hull]


def poly_tetrahedra(constraints: list[BR.Affine], vertices: list[Point3] | None = None) -> list[Tetra]:
    vertices = poly_vertices(constraints) if vertices is None else vertices
    if len(vertices) < 4:
        return []
    center = tuple(sum((point[i] for point in vertices), Q(0)) / len(vertices) for i in range(3))
    tetrahedra: list[Tetra] = []
    for plane in unique_planes(constraints):
        face = [point for point in vertices if plane.at(*point) == 0]
        hull = face_hull(face, plane)
        for index in range(1, len(hull) - 1):
            tetra = (center, hull[0], hull[index], hull[index + 1])
            if tetra_volume(tetra) > 0:
                tetrahedra.append(tetra)
    return tetrahedra


def midpoint(a: Point3, b: Point3) -> Point3:
    return tuple((a[i] + b[i]) / 2 for i in range(3))  # type: ignore[return-value]


def subdivide_tetra(tetra: Tetra) -> tuple[Tetra, ...]:
    a, b, c, d = tetra
    ab, ac, ad = midpoint(a, b), midpoint(a, c), midpoint(a, d)
    bc, bd, cd = midpoint(b, c), midpoint(b, d), midpoint(c, d)
    children = (
        (a, ab, ac, ad),
        (b, ab, bc, bd),
        (c, ac, bc, cd),
        (d, ad, bd, cd),
        (ab, ac, ad, cd),
        (ab, ac, bc, cd),
        (ab, ad, bd, cd),
        (ab, bc, bd, cd),
    )
    assert sum((tetra_volume(child) for child in children), Q(0)) == tetra_volume(tetra)
    return children


def refined_tetrahedra(tetra: Tetra, depth: int):
    if depth == 0:
        yield tetra
        return
    for child in subdivide_tetra(tetra):
        yield from refined_tetrahedra(child, depth - 1)


class ARatioDerivatives:
    """Directed ranges for r=a(s)/s and its first two derivatives."""

    def __init__(self, delay: G.FixedDelayTaylor):
        self.delay = delay
        self.scale = delay.scale

    @staticmethod
    def _mul_integer_interval(x: tuple[int, int], q: Interval) -> tuple[int, int]:
        values = (Q(x[0]) * q[0], Q(x[0]) * q[1], Q(x[1]) * q[0], Q(x[1]) * q[1])
        return G.floor_q(min(values), 1), G.ceil_q(max(values), 1)

    def shape_range(self, which: str, lo: Q, hi: Q) -> Interval:
        assert which in ("a", "b") and 1 <= lo <= hi <= self.delay.max_s
        left = G.floor_q(lo, self.delay.mesh)
        right = G.ceil_q(hi, self.delay.mesh) - 1
        ranges: list[tuple[int, int]] = []
        for j in range(left, right + 1):
            x0 = Q(j, self.delay.mesh)
            clip_lo = max(lo, x0)
            clip_hi = min(hi, x0 + Q(1, self.delay.mesh))
            if clip_lo > clip_hi:
                continue
            model = self.delay.a[j] if which == "a" else self.delay.b[j]
            u = clip_lo - x0, clip_hi - x0
            value = (0, 0)
            for coefficient in reversed(model.coeff):
                value = self._mul_integer_interval(value, u)
                value = value[0] + coefficient[0], value[1] + coefficient[1]
            ranges.append((value[0] - model.error, value[1] + model.error))
        assert ranges
        return Q(min(item[0] for item in ranges), self.scale), Q(max(item[1] for item in ranges), self.scale)

    def point(self, s: Q) -> Interval:
        if s <= 3:
            return 1 / s, 1 / s
        lo, hi = self.delay.shape_point("a", s)
        return Q(lo, self.scale) / s, Q(hi, self.scale) / s

    def ranges(self, slo: Q, shi: Q) -> tuple[Interval, Interval, Interval]:
        assert 0 < slo <= shi <= self.delay.max_s
        if shi <= 3:
            return (
                reciprocal_power(slo, shi, 1),
                (-1 / slo**2, -1 / shi**2),
                (2 / shi**3, 2 / slo**3),
            )
        assert slo >= 3
        inv1 = reciprocal_power(slo, shi, 1)
        inv2 = reciprocal_power(slo, shi, 2)
        inv3 = reciprocal_power(slo, shi, 3)
        a = self.shape_range("a", slo, shi)
        b1 = self.shape_range("b", slo - 1, shi - 1)
        am2 = self.shape_range("a", slo - 2, shi - 2)
        sm1 = reciprocal_power(slo - 1, shi - 1, 1)
        sm1_2 = reciprocal_power(slo - 1, shi - 1, 2)
        sm2 = reciprocal_power(slo - 2, shi - 2, 1)
        ap = iv_mul(b1, sm1)
        app = iv_sub(iv_mul(am2, iv_mul(sm2, sm1)), iv_mul(b1, sm1_2))
        r = iv_mul(a, inv1)
        rp = iv_sub(iv_mul(ap, inv1), iv_mul(a, inv2))
        rpp = iv_add(
            iv_sub(iv_mul(app, inv1), iv_scale(iv_mul(ap, inv2), 2)),
            iv_scale(iv_mul(a, inv3), 2),
        )
        return r, rp, rpp


@dataclass
class GeometryStats:
    branch_polytopes: int = 0
    delay_polytopes: int = 0
    base_tetrahedra: int = 0
    evaluated_tetrahedra: int = 0
    max_vertices: int = 0


def base_constraints() -> list[BR.Affine]:
    return [
        BR.X - BR.Affine(A0),
        BR.Affine(C14) - BR.X,
        BR.Y - BR.Affine(A0),
        BR.X - BR.Y,
        BR.Z - BR.Affine(A0),
        BR.Y - BR.Z,
    ]


def phi_affine(argument: BR.Affine, rising: bool) -> BR.Affine:
    if rising:
        return BR.Affine(Q(1, 2)) + argument.scale(Q(1, 2))
    return BR.Affine(Q(57, 64)) - argument.scale(Q(3, 2))


@dataclass
class BranchPiece:
    label: str
    theta: BR.Affine
    constraints: list[BR.Affine]
    vertices: list[Point3]
    volume: Q


def theta_branch_polytopes() -> list[BranchPiece]:
    arguments = [
        ("phi_t", BR.X),
        ("phi_tu", BR.X + BR.Y),
        ("phi_tuv", BR.X + BR.Y + BR.Z),
        ("phi_tv", BR.X + BR.Z),
        ("phi_uv", BR.Y + BR.Z),
    ]
    pieces: list[BranchPiece] = []
    for folds in itertools.product((True, False), repeat=len(arguments)):
        constraints = base_constraints()
        candidates: list[tuple[str, BR.Affine]] = []
        for (label, argument), rising in zip(arguments, folds, strict=True):
            constraints.append(
                BR.Affine(THETA_FOLD) - argument if rising else argument - BR.Affine(THETA_FOLD)
            )
            candidates.append((label, phi_affine(argument, rising)))
        candidates.append(("beta_v", BR.Affine(Q(153, 256), z=Q(-3, 8))))
        for label, winner in candidates:
            winner_constraints = constraints + [winner - other for _, other in candidates]
            vertices = poly_vertices(winner_constraints)
            tetrahedra = poly_tetrahedra(winner_constraints, vertices)
            volume = sum((tetra_volume(tetra) for tetra in tetrahedra), Q(0))
            if volume > 0:
                pieces.append(BranchPiece(label, winner, winner_constraints, vertices, volume))
    expected = (C14 - A0) ** 3 / 6
    assert sum((piece.volume for piece in pieces), Q(0)) == expected
    return pieces


def s_at(theta: BR.Affine, point: Point3) -> Q:
    x, y, z = point
    return (theta.at(x, y, z) - x - y - z) / z


def hessian_ranges(
    theta: BR.Affine,
    bounds: tuple[Interval, Interval, Interval],
    slo: Q,
    shi: Q,
    evaluator: ARatioDerivatives,
) -> tuple[Interval, Interval, Interval, Interval, Interval, Interval]:
    x, y, z = bounds
    ix, iy, iz = reciprocal_power(*x, 1), reciprocal_power(*y, 1), reciprocal_power(*z, 1)
    ix2, iy2, iz2 = reciprocal_power(*x, 2), reciprocal_power(*y, 2), reciprocal_power(*z, 2)
    w = iv_mul(iv_mul(ix, iy), iz2)
    wx, wy, wz = iv_mul(w, (-1 / x[0], -1 / x[1])), iv_mul(w, (-1 / y[0], -1 / y[1])), iv_mul(w, (-2 / z[0], -2 / z[1]))
    wxx = iv_scale(iv_mul(w, ix2), 2)
    wyy = iv_scale(iv_mul(w, iy2), 2)
    wzz = iv_scale(iv_mul(w, iz2), 6)
    wxy = iv_mul(w, iv_mul(ix, iy))
    wxz = iv_scale(iv_mul(w, iv_mul(ix, iz)), 2)
    wyz = iv_scale(iv_mul(w, iv_mul(iy, iz)), 2)

    p, q, d = theta.x - 1, theta.y - 1, theta.z - 1
    sx, sy = iv_scale(iz, p), iv_scale(iz, q)
    sz = iv_mul((d - shi, d - slo), iz)
    zero = (Q(0), Q(0))
    sxz, syz = iv_scale(iz2, -p), iv_scale(iz2, -q)
    szz = iv_scale(iv_mul((slo - d, shi - d), iz2), 2)

    r, rp, rpp = evaluator.ranges(slo, shi)
    g = QSTAR - 2 * r[1], QSTAR - 2 * r[0]
    gp, gpp = iv_scale(rp, -2), iv_scale(rpp, -2)

    def entry(wij: Interval, wi: Interval, wj: Interval, si: Interval, sj: Interval, sij: Interval):
        linear = iv_add(iv_add(iv_mul(wi, sj), iv_mul(wj, si)), iv_mul(w, sij))
        return iv_add(iv_add(iv_mul(wij, g), iv_mul(gp, linear)), iv_mul(iv_mul(w, gpp), iv_mul(si, sj)))

    return (
        entry(wxx, wx, wx, sx, sx, zero),
        entry(wxy, wx, wy, sx, sy, zero),
        entry(wxz, wx, wz, sx, sz, sxz),
        entry(wyy, wy, wy, sy, sy, zero),
        entry(wyz, wy, wz, sy, sz, syz),
        entry(wzz, wz, wz, sz, sz, szz),
    )


def tetra_taylor_interval(tetra: Tetra, theta: BR.Affine, evaluator: ARatioDerivatives) -> Interval:
    volume = tetra_volume(tetra)
    center = tuple(sum((point[i] for point in tetra), Q(0)) / 4 for i in range(3))
    bounds = tuple((min(point[i] for point in tetra), max(point[i] for point in tetra)) for i in range(3))
    s_values = [s_at(theta, point) for point in tetra]
    slo, shi = min(s_values), max(s_values)
    s_center = s_at(theta, center)  # linear-fractional, evaluated exactly
    r_center = evaluator.point(s_center)
    g_center = QSTAR - 2 * r_center[1], QSTAR - 2 * r_center[0]
    weight_center = 1 / (center[0] * center[1] * center[2] ** 2)
    center_value = iv_scale(g_center, weight_center)
    hxx, hxy, hxz, hyy, hyz, hzz = hessian_ranges(theta, bounds, slo, shi, evaluator)
    variances = [
        sum(((point[i] - center[i]) ** 2 for point in tetra), Q(0)) / 20 for i in range(3)
    ]
    diagonal_lo = (hxx[0] * variances[0] + hyy[0] * variances[1] + hzz[0] * variances[2]) / 2
    diagonal_hi = (hxx[1] * variances[0] + hyy[1] * variances[1] + hzz[1] * variances[2]) / 2
    mixed_error = Q(0)
    for hij, i, j in ((hxy, 0, 1), (hxz, 0, 2), (hyz, 1, 2)):
        magnitude = max(abs(hij[0]), abs(hij[1]))
        mixed_error += magnitude * (variances[i] + variances[j]) / 2
    return (
        volume * (center_value[0] + diagonal_lo - mixed_error),
        volume * (center_value[1] + diagonal_hi + mixed_error),
    )


def triple_interval(args: argparse.Namespace) -> tuple[Interval, dict[str, object]]:
    delay = G.FixedDelayTaylor(args.mesh, args.degree, args.max_s, args.dyadic_bits)
    evaluator = ARatioDerivatives(delay)
    pieces = theta_branch_polytopes()
    stats = GeometryStats(branch_polytopes=len(pieces))
    branch_counts: dict[str, int] = {}
    total_lo = total_hi = Q(0)
    branch_volume = sum((piece.volume for piece in pieces), Q(0))
    delay_volume = Q(0)
    argument_lo, argument_hi = Q(10**9), Q(0)

    for piece in pieces:
        branch_counts[piece.label] = branch_counts.get(piece.label, 0) + 1
        values = [s_at(piece.theta, point) for point in piece.vertices]
        first = G.floor_q(min(values), args.mesh)
        last = G.ceil_q(max(values), args.mesh) - 1
        numerator = piece.theta - BR.X - BR.Y - BR.Z
        local_volume = Q(0)
        for j in range(first, last + 1):
            lower = numerator - BR.Z.scale(Q(j, args.mesh))
            upper = BR.Z.scale(Q(j + 1, args.mesh)) - numerator
            constraints = piece.constraints + [lower, upper]
            vertices = poly_vertices(constraints)
            tetrahedra = poly_tetrahedra(constraints, vertices)
            volume = sum((tetra_volume(tetra) for tetra in tetrahedra), Q(0))
            if volume == 0:
                continue
            stats.delay_polytopes += 1
            stats.max_vertices = max(stats.max_vertices, len(vertices))
            stats.base_tetrahedra += len(tetrahedra)
            local_volume += volume
            delay_volume += volume
            argument_lo = min(argument_lo, *(s_at(piece.theta, point) for point in vertices))
            argument_hi = max(argument_hi, *(s_at(piece.theta, point) for point in vertices))
            value_lo = value_hi = Q(0)
            for tetra in tetrahedra:
                for leaf in refined_tetrahedra(tetra, args.taylor_depth):
                    lo, hi = tetra_taylor_interval(leaf, piece.theta, evaluator)
                    value_lo += lo
                    value_hi += hi
                    stats.evaluated_tetrahedra += 1
            total_lo += lower_dyadic(value_lo, args.accum_bits)
            total_hi += upper_dyadic(value_hi, args.accum_bits)
        assert local_volume == piece.volume
    assert delay_volume == branch_volume == (C14 - A0) ** 3 / 6
    return (total_lo, total_hi), {
        "branch_polytopes": stats.branch_polytopes,
        "delay_polytopes": stats.delay_polytopes,
        "base_tetrahedra": stats.base_tetrahedra,
        "evaluated_tetrahedra": stats.evaluated_tetrahedra,
        "max_vertices_per_delay_polytope": stats.max_vertices,
        "branch_counts": dict(sorted(branch_counts.items())),
        "ordered_domain_volume_exact": G.frac(branch_volume),
        "delay_partition_volume_exact": G.frac(delay_volume),
        "argument_range_exact": [G.frac(argument_lo), G.frac(argument_hi)],
        "coverage": (
            "Exact rational half-space vertices; phi folds and all winner comparisons partition the ordered "
            "domain, delay planes partition every branch polytope, and both volume identities are asserted."
        ),
    }


def parse_q(text: str) -> Q:
    numerator, denominator = text.split("/")
    return Q(int(numerator), int(denominator))


def certify(args: argparse.Namespace) -> dict[str, object]:
    source_path = HERE / "li-equation14-certificate.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    triple, geometry = triple_interval(args)
    component_names = (
        "zero_dimensional_500_fbar_minus_q",
        "one_dimensional_500_integral_q_minus_Fbar",
        "two_dimensional_500_integral_fbar_minus_q",
    )
    fixed = []
    for name in component_names:
        record = source["components"][name]
        fixed.append((parse_q(record["lower_exact"]), parse_q(record["upper_exact"])))
    skeleton_record = source["stable_identity"]["constant_skeleton"]
    skeleton = parse_q(skeleton_record["lower_exact"])
    hlo = skeleton + sum((item[0] for item in fixed), Q(0)) + triple[0]
    hhi = skeleton + sum((item[1] for item in fixed), Q(0)) + triple[1]
    klo, khi = 2 * hlo, 2 * hhi
    meets = klo >= TARGET_K14
    return {
        "schema": "li-equation14-polytope-taylor-smoke-v1",
        "verdict": "EQUATION_14_LOWER_BOUND_CERTIFIED" if meets else "PARTIAL_STRICT_CERTIFICATE",
        "paper_claim": "S2/M(N) >= 6.533916",
        "parameters": {
            "delay_mesh": args.mesh,
            "delay_degree": args.degree,
            "delay_max_s": args.max_s,
            "dyadic_bits": args.dyadic_bits,
            "accumulation_bits": args.accum_bits,
            "tetrahedron_taylor_depth": args.taylor_depth,
        },
        "dependencies": {
            "R044_nontriple_file": "artifacts/li-equation14-certificate.json",
            "R044_nontriple_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "use": "Only R044's exact zero-, one-, two-dimensional intervals and constant skeleton are reused.",
        },
        "three_dimensional_integral_q_minus_Fbar": G.interval_record(*triple, 18),
        "S2_over_M_coefficient_interval": G.interval_record(klo, khi, 18),
        "strictly_meets_paper_lower": meets,
        "lower_slack_or_deficit": (
            G.decimal_floor(klo - TARGET_K14, 18)
            if meets
            else G.decimal_ceil(TARGET_K14 - klo, 18)
        ),
        "geometry": geometry,
        "method": {
            "theta": "Flattened six-candidate maximum; exact phi-fold and affine-winner half spaces.",
            "delay": "Exact planes s=j/mesh after fixing an affine theta winner.",
            "cubature": (
                "Exact rational tetrahedralization; centroid Taylor with exact diagonal simplex moments and "
                "|du_i du_j| <= (du_i^2+du_j^2)/2 for mixed Hessian terms."
            ),
        },
        "limitations": [
            "This is a convergence smoke for Li equation (14), not an independently audited final certificate.",
            "The zero-, one-, and two-dimensional components are inherited by hash from R044.",
            "It does not prove the upstream variable-level sieve hypotheses or strong Goldbach.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh", type=int, default=8)
    parser.add_argument("--degree", type=int, default=16)
    parser.add_argument("--max-s", type=int, default=300)
    parser.add_argument("--dyadic-bits", type=int, default=96)
    parser.add_argument("--accum-bits", type=int, default=160)
    parser.add_argument("--taylor-depth", type=int, default=0)
    args = parser.parse_args()
    result = certify(args)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "three_dimensional_integral_q_minus_Fbar": result[
                    "three_dimensional_integral_q_minus_Fbar"
                ],
                "S2_over_M_coefficient_interval": result["S2_over_M_coefficient_interval"],
                "strictly_meets_paper_lower": result["strictly_meets_paper_lower"],
                "lower_slack_or_deficit": result["lower_slack_or_deficit"],
                "geometry": result["geometry"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
