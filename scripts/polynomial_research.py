"""Exact quadratic SOS discovery and polynomial inequality experiments using SymPy."""

import itertools

from math_backend import load_sympy, parse_expression, symbol_table


def setup(lhs, rhs, symbols, assumptions):
    sympy = load_sympy()
    table = symbol_table(sympy, symbols, set(symbols), set(), set())

    def polynomial(text):
        expression, guards, rational = parse_expression(text, table)
        if not rational or any(g.free_symbols for g in guards):
            raise ValueError("requires rational polynomials without variable denominators")
        # Normalize the safe parser's unevaluated sums only after checking domain guards.
        poly = sympy.Poly(sympy.expand(expression).doit(), *table.values(), domain="QQ")
        if poly.total_degree() > 32 or len(poly.terms()) > 2048:
            raise ValueError("polynomial exceeds degree or term limit")
        return poly.as_expr()

    target = polynomial(lhs) - polynomial(rhs)
    constraints = [polynomial(a) for a in assumptions]
    certificate = {
        "schema_version": 1,
        "backend": "rational-polynomial",
        "operation": "nonnegative",
        "claim": dict(lhs=lhs, rhs=rhs, symbols=symbols, assumptions=assumptions, domain="real", relation=">="),
        "proof": None,
        "witness": None,
        "search": None,
        "method": "",
    }
    return sympy, table, target, constraints, certificate


def quadratic_squares(sympy, target, variables):
    """Rational completion of squares on the homogenized quadratic form; no numeric PSD tolerance."""
    poly = sympy.Poly(target, *variables, domain="QQ")
    if poly.total_degree() > 2:
        return None
    basis = [*variables, sympy.Integer(1)]
    size = len(basis)
    matrix = sympy.zeros(size)
    for powers, coefficient in poly.terms():
        indices = [i for i, power in enumerate(powers) for _ in range(power)]
        indices += [size - 1] * (2 - len(indices))
        i, j = indices
        if i == j:
            matrix[i, i] += coefficient
        else:
            matrix[i, j] += coefficient / 2
            matrix[j, i] += coefficient / 2
    terms = []
    for i in range(size):
        pivot = matrix[i, i]
        if pivot < 0 or (pivot == 0 and any(matrix[i, j] != 0 for j in range(i + 1, size))):
            return None
        if pivot == 0:
            continue
        square = basis[i] + sum(matrix[i, j] / pivot * basis[j] for j in range(i + 1, size))
        terms.append({"weight": str(pivot), "square": str(sympy.expand(square)), "factors": []})
        for j in range(i + 1, size):
            for k in range(i + 1, size):
                matrix[j, k] -= matrix[i, j] * matrix[i, k] / pivot
    return terms


def polynomial_sos(lhs, rhs, symbols, assumptions, terms):
    sympy, table, target, _, certificate = setup(lhs, rhs, symbols, assumptions)
    if terms:
        certificate.update(proof=terms, method="supplied-decomposition")
    elif not assumptions:
        certificate.update(proof=quadratic_squares(sympy, target, list(table.values())), method="quadratic-completion")
    else:
        certificate.update(proof=[] if sympy.expand(target) == 0 else None, method="no-constrained-discovery")
    return certificate


def polynomial_amgm(lhs, rhs, symbols, assumptions, addends, base):
    _, _, _, _, certificate = setup(lhs, rhs, symbols, assumptions)
    certificate.update(proof={"rule": "amgm", "addends": addends, "base": base}, method="supplied-amgm")
    return certificate


def inequality_search(lhs, rhs, symbols, assumptions, values, max_points):
    sympy, table, target, constraints, certificate = setup(lhs, rhs, symbols, assumptions)
    grid = []
    for value in values:
        expression, _, rational = parse_expression(value, {})
        number = sympy.cancel(expression)
        if not rational or number.is_Rational is not True:
            raise ValueError("grid values must be exact rational constants")
        grid.append(number)
    grid = list(dict.fromkeys(grid))
    total, checked, feasible = len(grid) ** len(symbols), 0, 0
    for point in itertools.islice(itertools.product(grid, repeat=len(symbols)), max_points):
        checked += 1
        substitution = dict(zip(table.values(), point))
        if any(c.subs(substitution) < 0 for c in constraints):
            continue
        feasible += 1
        if target.subs(substitution) < 0:
            certificate["witness"] = dict(zip(symbols, map(str, point)))
            break
    certificate.update(
        method="exact-rational-grid",
        search={
            "values": list(map(str, grid)),
            "total_points": total,
            "checked_points": checked,
            "feasible_points": feasible,
            "grid_complete": checked == total,
            "max_points": max_points,
        },
    )
    return certificate
