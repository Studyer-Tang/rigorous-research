#!/usr/bin/env python3
"""Recheck mathematical content without calling certificate-producing routines."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from math_backend import load_sympy, parse_expression, symbol_table
from research_io import canonical_hash, load_json_object, sha256, write_json


def rational(value: Any) -> Any:
    if not isinstance(value, str) or len(value) > 1000 or not re.fullmatch(r"[+-]?\d+(?:/[1-9]\d*)?", value):
        raise ValueError("certificate numbers must be exact rational strings")
    return load_sympy().Rational(value)


def expressions(certificate: dict[str, Any]) -> tuple[Any, Any, dict[str, Any], list[Any]]:
    claim = certificate["claim"]
    expected_fields = (
        {"lhs", "rhs", "symbol", "relation", "lower", "upper"}
        if certificate.get("operation") == "polynomial-interval-bound"
        else {"lhs", "rhs", "symbols"}
    )
    if not isinstance(claim, dict) or set(claim) != expected_fields:
        raise ValueError(
            "claim fields must exactly match the supported operation; unrecognized semantics cannot be ignored"
        )
    names = claim.get("symbols", [claim.get("symbol")])
    if not isinstance(names, list) or not names or len(names) > 20 or any(not isinstance(name, str) for name in names):
        raise ValueError("certificate requires declared symbols")
    assumptions = certificate.get("assumptions", {})
    if not isinstance(assumptions, dict) or set(assumptions) - {"real", "positive", "integer"}:
        raise ValueError("unsupported certificate assumptions")
    flags = {}
    for key in ("real", "positive", "integer"):
        values = assumptions.get(key, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError("assumptions must be arrays of declared symbols")
        flags[key] = set(values)
    table = symbol_table(load_sympy(), names, **flags)
    lhs, left_guards, left_rational = parse_expression(claim["lhs"], table)
    rhs, right_guards, right_rational = parse_expression(claim["rhs"], table)
    if not left_rational or not right_rational:
        raise ValueError("independent exact checking requires rational arithmetic")
    return lhs, rhs, table, left_guards + right_guards


def check_witness(certificate: dict[str, Any], lhs: Any, rhs: Any, table: dict[str, Any], guards: list[Any]) -> str:
    sympy = load_sympy()
    witness = certificate["witness"]
    if set(witness["assignment"]) != set(table):
        raise ValueError("witness assignment must cover exactly the declared symbols")
    substitution = {symbol: rational(witness["assignment"][name]) for name, symbol in table.items()}
    if any(
        (symbol.is_positive and value <= 0) or (symbol.is_integer and value.q != 1)
        for symbol, value in substitution.items()
    ):
        raise ValueError("witness violates a declared assumption")
    if any(sympy.cancel(guard.subs(substitution)) == 0 for guard in guards):
        raise ValueError("witness lies outside the original expression domain")
    difference = sympy.cancel((lhs - rhs).subs(substitution))
    if difference.is_Rational is not True or difference == 0 or difference != rational(witness["difference"]):
        raise ValueError("witness does not reproduce the claimed exact difference")
    if certificate.get("operation") == "polynomial-interval-bound":
        claim = certificate["claim"]
        point = next(iter(substitution.values()))
        if not rational(claim["lower"]) <= point <= rational(claim["upper"]) or difference >= 0:
            raise ValueError("bound witness must be negative inside the claimed interval")
    else:
        for key, expression in (("lhs", lhs), ("rhs", rhs)):
            if sympy.cancel(expression.subs(substitution)) != rational(witness[key]):
                raise ValueError(f"witness {key} value is incorrect")
    return "REFUTED"


def check_bound(certificate: dict[str, Any], lhs: Any, rhs: Any, table: dict[str, Any], guards: list[Any]) -> str:
    sympy = load_sympy()
    claim = certificate["claim"]
    if len(table) != 1 or claim["relation"] != ">=" or any(guard.free_symbols for guard in guards):
        raise ValueError("bound requires a univariate polynomial with no variable denominators")
    a, b = rational(claim["lower"]), rational(claim["upper"])
    if a >= b:
        raise ValueError("invalid bound interval")
    x = next(iter(table.values()))
    polynomial = sympy.Poly(lhs - rhs, x, domain="QQ")
    if polynomial.degree() > 40:
        raise ValueError("polynomial degree exceeds verifier limit")
    if certificate.get("witness"):
        return check_witness(certificate, lhs, rhs, table, guards)
    if certificate.get("bound_established") is not True:
        return "INCONCLUSIVE"
    intervals = certificate["certified_intervals"]
    if not isinstance(intervals, list) or not 1 <= len(intervals) <= 2048:
        raise ValueError("invalid certificate interval count")
    position = a
    for interval in intervals:
        start, end = rational(interval["lower"]), rational(interval["upper"])
        if start != position or not start < end <= b:
            raise ValueError("certificate intervals have a gap, overlap, or exceed the claim")
        coefficients = [rational(value) for value in interval["bernstein_coefficients"]]
        if not 1 <= len(coefficients) <= 41 or any(value < 0 for value in coefficients):
            raise ValueError("Bernstein coefficients must be nonnegative and degree-bounded")
        degree = len(coefficients) - 1
        reconstructed = sum(
            value * sympy.binomial(degree, k) * x**k * (1 - x) ** (degree - k) for k, value in enumerate(coefficients)
        )
        expected = polynomial.as_expr().subs(x, start + (end - start) * x)
        if not sympy.Poly(reconstructed - expected, x, domain="QQ").is_zero:
            raise ValueError("Bernstein coefficients do not reconstruct the original polynomial")
        position = end
    if position != b or certificate.get("unresolved_intervals"):
        raise ValueError("certificate does not cover the entire claimed interval")
    return "ESTABLISHED"


def check_identity(
    certificate: dict[str, Any], lhs: Any, rhs: Any, table: dict[str, Any], guards: list[Any], inputs: list[Path]
) -> str:
    sympy = load_sympy()
    if certificate.get("operation") == "matrix-determinant":
        matrix_path = next(
            (path for path in inputs if path.is_file() and sha256(path) == certificate.get("matrix_sha256")), None
        )
        if matrix_path is None:
            raise ValueError("matrix certificate requires its original checksum-bound matrix input")
        rows = json.loads(matrix_path.read_text(encoding="utf-8"))
        if (
            not isinstance(rows, list)
            or not 1 <= len(rows) <= 30
            or any(not isinstance(row, list) or len(row) != len(rows) for row in rows)
        ):
            raise ValueError("matrix input must be square and at most 30 by 30")
        parsed = [[parse_expression(str(value), table) for value in row] for row in rows]
        if not all(entry[2] for row in parsed for entry in row):
            raise ValueError("matrix entries must use rational arithmetic")
        guards += [guard for row in parsed for _, conditions, _ in row for guard in conditions]
        # Recompute from entries using a different determinant algorithm than the producer.
        determinant = sympy.Matrix([[entry[0] for entry in row] for row in parsed]).det(method="berkowitz")
        if sympy.cancel(determinant - lhs) != 0:
            raise ValueError("certificate does not match the original matrix determinant")
    restrictions = sorted({f"{sympy.factor(guard)} != 0" for guard in guards if guard.free_symbols})
    if restrictions and certificate.get("domain_restrictions") != restrictions:
        raise ValueError("certificate omits or changes original denominator restrictions")
    difference = sympy.cancel(lhs - rhs)
    if certificate.get("identity_established") is not True:
        return "INCONCLUSIVE"
    if difference != 0:
        raise ValueError("claimed identity is false under exact recomputation")
    return "ESTABLISHED"


def verify(certificate: dict[str, Any], inputs: list[Path] | None = None) -> dict[str, Any]:
    if certificate.get("backend") == "rational-polynomial":
        from polynomial_verifier import verify as verify_polynomial

        return verify_polynomial(certificate)
    if certificate.get("backend") == "exact-integer":
        from integer_certificate_verifier import verify as verify_integer

        return verify_integer(certificate)
    sympy = load_sympy()
    try:
        if certificate.get("backend") != "sympy" or certificate.get("schema_version") != 1:
            raise ValueError("unsupported exact certificate")
        lhs, rhs, table, guards = expressions(certificate)
        operation = certificate.get("operation", "identity")
        if operation == "polynomial-interval-bound":
            status = check_bound(certificate, lhs, rhs, table, guards)
        elif operation == "rational-counterexample-search":
            status = (
                check_witness(certificate, lhs, rhs, table, guards)
                if certificate.get("counterexample_found") is True
                else "INCONCLUSIVE"
            )
        elif operation in ("identity", "matrix-determinant"):
            status = check_identity(certificate, lhs, rhs, table, guards, inputs or [])
        else:
            raise ValueError("unknown certificate operation")
        errors = []
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OSError,
        sympy.polys.polyerrors.BasePolynomialError,
    ) as exc:
        status, errors = "INVALID", [str(exc)]
    return {
        "schema_version": 1,
        "kind": "independent-certificate-check",
        "status": status,
        "errors": errors,
        "certificate_hash": canonical_hash(certificate),
        "scope": "Recorded mathematical claim and assumptions only; no prose-translation guarantee.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--input", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, help="save the independently derived result")
    args = parser.parse_args(argv)
    try:
        result = verify(load_json_object(args.certificate), args.input)
        if args.output:
            write_json(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in ("ESTABLISHED", "REFUTED") else 1
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
