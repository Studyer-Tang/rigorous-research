"""Small rational-polynomial checker, independent of SymPy and the proof producer."""

import ast
import re
from fractions import Fraction

from research_io import canonical_hash


def bounded(poly):
    poly = {powers: value for powers, value in poly.items() if value}
    if len(poly) > 2048 or any(
        sum(powers) > 32 or max(value.numerator.bit_length(), value.denominator.bit_length()) > 4096
        for powers, value in poly.items()
    ):
        raise ValueError("polynomial exceeds term, degree or coefficient limit")
    return poly


def add(left, right):
    result = left.copy()
    for powers, value in right.items():
        result[powers] = result.get(powers, Fraction(0)) + value
    return bounded(result)


def multiply(left, right):
    if len(left) * len(right) > 100000:
        raise ValueError("polynomial product exceeds work limit")
    result = {}
    for a, x in left.items():
        for b, y in right.items():
            powers = tuple(i + j for i, j in zip(a, b))
            result[powers] = result.get(powers, Fraction(0)) + x * y
    return bounded(result)


def parse(text, names):
    """Parse polynomial arithmetic; even canceling variable denominators are rejected."""
    if not isinstance(text, str) or not 1 <= len(text) <= 500:
        raise ValueError("expression must contain 1–500 characters")
    tree = ast.parse(text.strip(), mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 256:
        raise ValueError("expression exceeds node limit")
    zero = (0,) * len(names)

    def read(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return bounded({zero: Fraction(node.value)})
        if isinstance(node, ast.Name) and node.id in names:
            return {tuple(int(name == node.id) for name in names): Fraction(1)}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return {p: (-v if isinstance(node.op, ast.USub) else v) for p, v in read(node.operand).items()}
        if not isinstance(node, ast.BinOp):
            raise ValueError("use declared symbols, integers and polynomial arithmetic")
        left = read(node.left)
        if isinstance(node.op, ast.Pow):
            if (
                not isinstance(node.right, ast.Constant)
                or type(node.right.value) is not int
                or not 0 <= node.right.value <= 16
            ):
                raise ValueError("powers must be integer literals in 0..16")
            result = {zero: Fraction(1)}
            for _ in range(node.right.value):
                result = multiply(result, left)
            return result
        right = read(node.right)
        if isinstance(node.op, ast.Add):
            return add(left, right)
        if isinstance(node.op, ast.Sub):
            return add(left, {p: -v for p, v in right.items()})
        if isinstance(node.op, ast.Mult):
            return multiply(left, right)
        if isinstance(node.op, ast.Div):
            if any(isinstance(n, ast.Name) for n in ast.walk(node.right)) or set(right) - {zero}:
                raise ValueError("variable denominators are outside this polynomial fragment")
            value = right.get(zero, 0)
            if not value:
                raise ValueError("zero denominator")
            return bounded({p: v / value for p, v in left.items()})
        raise ValueError("unsupported arithmetic operator")

    return read(tree.body)


def scalar(text):
    return parse(text, []).get((), Fraction(0))


def evaluate(poly, values):
    result = Fraction(0)
    for powers, coefficient in poly.items():
        for value, exponent in zip(values, powers):
            coefficient *= value**exponent
        result += coefficient
    return result


def nonnegative_term(term, names, assumptions):
    if set(term) != {"weight", "square", "factors"}:
        raise ValueError("unsupported square term")
    weight, square = scalar(term["weight"]), parse(term["square"], names)
    if weight < 0:
        raise ValueError("square weights must be nonnegative")
    factors = term["factors"]
    if (
        not isinstance(factors, list)
        or len(factors) > 8
        or any(type(i) is not int or not 0 <= i < len(assumptions) for i in factors)
    ):
        raise ValueError("factors must index declared nonnegative assumptions")
    product = {p: weight * v for p, v in multiply(square, square).items()}
    for i in factors:
        product = multiply(product, assumptions[i])
    return bounded(product)


def amgm(proof, names, assumptions):
    if set(proof) != {"rule", "addends", "base"} or proof["rule"] != "amgm":
        raise ValueError("unsupported polynomial proof rule")
    addends = proof["addends"]
    if not isinstance(addends, list) or not 2 <= len(addends) <= 8:
        raise ValueError("AM-GM requires 2–8 nonnegative addends")
    base = parse(proof["base"], names)
    product = power = {(0,) * len(names): Fraction(1)}
    total = {}
    for term in addends:
        polynomial = nonnegative_term(term, names, assumptions)
        product, power = multiply(product, polynomial), multiply(power, base)
        total = add(total, polynomial)
    if product != power:
        raise ValueError("AM-GM product does not equal base**m")
    # AM-GM gives sum >= m * the nonnegative m-th root. If base < 0,
    # sum >= 0 >= m*base already suffices; no root-sign assumption is hidden.
    return add(total, {p: -len(addends) * v for p, v in base.items()})


def check(certificate):
    if (
        set(certificate) != {"schema_version", "backend", "operation", "claim", "proof", "witness", "search", "method"}
        or type(certificate["schema_version"]) is not int
        or certificate["schema_version"] != 1
        or certificate["backend"] != "rational-polynomial"
        or certificate["operation"] != "nonnegative"
    ):
        raise ValueError("unsupported polynomial certificate")
    claim = certificate["claim"]
    if set(claim) != {"lhs", "rhs", "symbols", "assumptions", "domain", "relation"}:
        raise ValueError("claim must retain its exact domain and assumptions")
    if claim["domain"] != "real" or claim["relation"] != ">=":
        raise ValueError("only non-strict real polynomial inequalities are supported")
    names = claim["symbols"]
    if (
        not isinstance(names, list)
        or not 1 <= len(names) <= 6
        or any(not isinstance(n, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,19}", n) for n in names)
        or len(set(names)) != len(names)
    ):
        raise ValueError("declare 1–6 unique symbols")
    assumptions = claim["assumptions"]
    if not isinstance(assumptions, list) or len(assumptions) > 8:
        raise ValueError("at most 8 nonnegative polynomial assumptions")
    assumptions = [parse(expr, names) for expr in assumptions]
    target = add(parse(claim["lhs"], names), {p: -v for p, v in parse(claim["rhs"], names).items()})
    witness, proof = certificate["witness"], certificate["proof"]
    if witness is not None:
        if proof is not None or not isinstance(witness, dict) or set(witness) != set(names):
            raise ValueError("witness must give exactly the declared symbols and no simultaneous proof")
        values = [scalar(witness[name]) for name in names]
        if any(evaluate(p, values) < 0 for p in assumptions) or evaluate(target, values) >= 0:
            raise ValueError("witness is infeasible or does not violate the inequality")
        return "REFUTED"
    if proof is None:
        return "INCONCLUSIVE"
    if isinstance(proof, dict):
        if amgm(proof, names, assumptions) != target:
            raise ValueError("AM-GM sum does not reconstruct lhs-rhs")
        return "ESTABLISHED"
    if not isinstance(proof, list) or len(proof) > 32:
        raise ValueError("at most 32 square terms")
    reconstructed = {}
    for term in proof:
        reconstructed = add(reconstructed, nonnegative_term(term, names, assumptions))
    if reconstructed != target:
        raise ValueError("square decomposition does not reconstruct lhs-rhs")
    return "ESTABLISHED"


def verify(certificate):
    try:
        status, errors = check(certificate), []
    except (ValueError, TypeError, KeyError, AttributeError, SyntaxError, RecursionError, ZeroDivisionError) as exc:
        status, errors = "INVALID", [str(exc)]
    return {
        "schema_version": 1,
        "kind": "independent-certificate-check",
        "status": status,
        "errors": errors,
        "certificate_hash": canonical_hash(certificate),
        "scope": "Only the recorded real polynomial inequality under its listed nonnegative assumptions; no application or novelty guarantee.",
    }
