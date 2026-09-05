#!/usr/bin/env python3
"""Create conservative SymPy identity certificates and Lean compilation records."""

from __future__ import annotations

import argparse
import ast
import itertools
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from research_io import sha256, utc_timestamp as timestamp, write_json

FUNCTIONS = ("sin", "cos", "tan", "exp", "log", "sqrt", "Abs")
CONSTANTS = ("pi", "E", "I")


def parse_expression(text: str, symbols: dict[str, Any]) -> tuple[Any, list[Any], bool]:
    """Parse explicit arithmetic without eval, retaining original denominator guards."""
    sympy = load_sympy()
    if not isinstance(text, str) or not text.strip() or len(text) > 10000:
        raise ValueError("expression must be non-empty text of at most 10000 characters")
    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("invalid arithmetic expression") from exc
    if sum(1 for _ in ast.walk(tree)) > 1000:
        raise ValueError("expression exceeds the 1000-node limit")
    guards: list[Any] = []
    rational = True

    def read(node: ast.AST, depth: int = 0) -> Any:
        nonlocal rational
        if depth > 100:
            raise ValueError("expression nesting exceeds 100 levels")
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return sympy.Integer(node.value)
        if isinstance(node, ast.Name):
            if node.id in symbols:
                return symbols[node.id]
            if node.id in CONSTANTS:
                rational = False
                return getattr(sympy, node.id)
            raise ValueError(f"undeclared symbol: {node.id}")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = read(node.operand, depth + 1)
            return value if isinstance(node.op, ast.UAdd) else sympy.Mul(-1, value, evaluate=False)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            left, right = read(node.left, depth + 1), read(node.right, depth + 1)
            if isinstance(node.op, ast.Add):
                return sympy.Add(left, right, evaluate=False)
            if isinstance(node.op, ast.Sub):
                return sympy.Add(left, sympy.Mul(-1, right, evaluate=False), evaluate=False)
            if isinstance(node.op, ast.Mult):
                return sympy.Mul(left, right, evaluate=False)
            if isinstance(node.op, ast.Div):
                guards.append(right)
                return sympy.Mul(left, sympy.Pow(right, -1, evaluate=False), evaluate=False)
            exponent = sympy.simplify(right)
            if exponent.is_Integer is not True:
                rational = False
            elif abs(exponent) > 1000:
                raise ValueError("integer exponents must be between -1000 and 1000")
            if exponent.is_negative:
                guards.append(left)
            return sympy.Pow(left, exponent, evaluate=False)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in FUNCTIONS
            and len(node.args) == 1
            and not node.keywords
        ):
            rational = False
            return getattr(sympy, node.func.id)(read(node.args[0], depth + 1), evaluate=False)
        raise ValueError(
            "use declared symbols, integers, arithmetic, and supported one-argument functions; use 1/10 for decimals"
        )

    expression = read(tree.body)
    if any(sympy.simplify(guard) == 0 for guard in guards):
        raise ValueError("expression contains an identically zero denominator")
    return expression, guards, rational


def load_sympy() -> Any:
    try:
        import sympy
    except ImportError as exc:
        raise RuntimeError("SymPy is not installed; install requirements-math.txt") from exc
    return sympy


def symbol_table(sympy: Any, names: list[str], real: set[str], positive: set[str], integer: set[str]) -> dict[str, Any]:
    if len(names) != len(set(names)):
        raise ValueError("symbol names must be unique")
    table = {}
    for name in names:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            raise ValueError(f"invalid symbol name: {name}")
        if name in FUNCTIONS or name in CONSTANTS:
            raise ValueError(f"reserved symbol name: {name}")
        assumptions: dict[str, bool] = {}
        if name in real:
            assumptions["real"] = True
        if name in positive:
            assumptions["positive"] = True
        if name in integer:
            assumptions["integer"] = True
        table[name] = sympy.Symbol(name, **assumptions)
    unknown = (real | positive | integer) - set(names)
    if unknown:
        raise ValueError(f"assumptions reference unknown symbols: {', '.join(sorted(unknown))}")
    return table


def identity_certificate(
    lhs_text: str,
    rhs_text: str,
    names: list[str],
    *,
    real: set[str] | None = None,
    positive: set[str] | None = None,
    integer: set[str] | None = None,
) -> dict[str, Any]:
    sympy = load_sympy()
    real = real or set()
    positive = positive or set()
    integer = integer or set()
    symbols = symbol_table(sympy, names, real, positive, integer)
    lhs, lhs_guards, lhs_rational = parse_expression(lhs_text, symbols)
    rhs, rhs_guards, rhs_rational = parse_expression(rhs_text, symbols)
    guards = lhs_guards + rhs_guards
    difference = sympy.together(lhs - rhs)
    numerator, denominator = sympy.fraction(difference)
    polynomial = False
    coefficients: list[str] | None = None
    try:
        poly = sympy.Poly(numerator, *[symbols[name] for name in names], domain="QQ")
        polynomial = True
        coefficients = (
            [str(value) for value in poly.all_coeffs()] if len(names) == 1 else [str(value) for value in poly.coeffs()]
        )
        exact_zero = poly.is_zero
    except (sympy.PolynomialError, sympy.polys.polyerrors.CoercionFailed, ValueError):
        exact_zero = bool(sympy.simplify(difference) == 0)
    if exact_zero and polynomial and lhs_rational and rhs_rational:
        classification = "exact-rational-on-domain" if guards else "exact-polynomial"
        evidence_role = "decisive"
    elif exact_zero:
        classification = "symbolically-simplified"
        evidence_role = "diagnostic"
    else:
        classification = "not-established"
        evidence_role = "diagnostic"
    denominator_text = str(sympy.factor(denominator))
    restrictions = sorted({str(sympy.factor(guard)) for guard in guards if guard.free_symbols})
    exceptional = " or ".join(f"{guard} = 0" for guard in restrictions) or "none"
    return {
        "schema_version": 1,
        "backend": "sympy",
        "backend_version": sympy.__version__,
        "created_at": timestamp(),
        "claim": {"lhs": lhs_text, "rhs": rhs_text, "symbols": names},
        "assumptions": {
            "real": sorted(real),
            "positive": sorted(positive),
            "integer": sorted(integer),
        },
        "normalized": {
            "lhs": str(lhs),
            "rhs": str(rhs),
            "difference": str(difference),
            "numerator": str(sympy.factor(numerator)),
            "denominator": denominator_text,
        },
        "polynomial_numerator": polynomial,
        "numerator_coefficients": coefficients,
        "exceptional_set": exceptional,
        "domain_restrictions": [f"{guard} != 0" for guard in restrictions],
        "domain_analysis_complete": lhs_rational and rhs_rational,
        "identity_established": bool(exact_zero),
        "classification": classification,
        "recommended_evidence_role": evidence_role,
        "warning": (
            "A general SymPy simplification is diagnostic unless reduced to an exact polynomial or rational identity with its denominator domain recorded."
            if evidence_role != "decisive"
            else "The certificate establishes the normalized algebraic identity; it does not validate that the expression models the user's intended object."
        ),
    }


def matrix_certificate(matrix_file: Path, expected: str, names: list[str], **assumptions: Any) -> dict[str, Any]:
    sympy = load_sympy()
    data = json.loads(matrix_file.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data or any(not isinstance(row, list) for row in data):
        raise ValueError("matrix file must contain a non-empty JSON array of rows")
    width = len(data[0])
    if width != len(data) or any(len(row) != width for row in data):
        raise ValueError("determinant requires a square matrix")
    table = symbol_table(
        sympy,
        names,
        assumptions.get("real", set()),
        assumptions.get("positive", set()),
        assumptions.get("integer", set()),
    )
    parsed = [[parse_expression(str(value), table) for value in row] for row in data]
    matrix = sympy.Matrix([[entry[0] for entry in row] for row in parsed])
    determinant = sympy.factor(matrix.det(method="domain-ge"))
    certificate = identity_certificate(str(determinant), expected, names, **assumptions)
    guards = sorted(
        {
            str(sympy.factor(guard))
            for row in parsed
            for _, conditions, _ in row
            for guard in conditions
            if guard.free_symbols
        }
    )
    restrictions = sorted(set(certificate["domain_restrictions"]) | {f"{guard} != 0" for guard in guards})
    certificate["domain_restrictions"] = restrictions
    certificate["exceptional_set"] = " or ".join(value.replace(" != 0", " = 0") for value in restrictions) or "none"
    certificate["domain_analysis_complete"] &= all(entry[2] for row in parsed for entry in row)
    if not certificate["domain_analysis_complete"] and certificate["identity_established"]:
        certificate["classification"] = "symbolically-simplified"
        certificate["recommended_evidence_role"] = "diagnostic"
        certificate["warning"] = (
            "Matrix entries contain non-rational expressions; determinant simplification does not close their domain or branch obligations."
        )
    elif restrictions and certificate["classification"] == "exact-polynomial":
        certificate["classification"] = "exact-rational-on-domain"
    certificate["operation"] = "matrix-determinant"
    certificate["matrix_sha256"] = sha256(matrix_file)
    certificate["matrix_shape"] = [len(data), width]
    certificate["computed_determinant"] = str(determinant)
    return certificate


def counterexample_search(
    lhs_text: str,
    rhs_text: str,
    names: list[str],
    values: list[str],
    max_points: int = 1000,
    **assumptions: Any,
) -> dict[str, Any]:
    """Search a bounded exact rational grid; exhaustion never establishes an identity."""
    sympy = load_sympy()
    if not names or not values or not 1 <= max_points <= 100000:
        raise ValueError("provide symbols and grid values, with max-points between 1 and 100000")
    table = symbol_table(
        sympy,
        names,
        assumptions.get("real", set()),
        assumptions.get("positive", set()),
        assumptions.get("integer", set()),
    )
    lhs, left_guards, left_rational = parse_expression(lhs_text, table)
    rhs, right_guards, right_rational = parse_expression(rhs_text, table)
    if not left_rational or not right_rational:
        raise ValueError("counterexample search currently requires rational arithmetic with integer powers")
    grid = []
    for value in values:
        if not re.fullmatch(r"[+-]?\d+(?:/[1-9]\d*)?", value):
            raise ValueError(f"grid values must be exact integers or fractions: {value}")
        number = sympy.Rational(value)
        if number not in grid:
            grid.append(number)
    visited = tested = excluded = 0
    witness = None
    for point in itertools.islice(itertools.product(grid, repeat=len(names)), max_points):
        visited += 1
        substitution = dict(zip(table.values(), point))
        if any(
            (symbol.is_positive and number <= 0) or (symbol.is_integer and number.q != 1)
            for symbol, number in substitution.items()
        ) or any(sympy.simplify(guard.subs(substitution)) == 0 for guard in left_guards + right_guards):
            excluded += 1
            continue
        left_value, right_value = sympy.cancel(lhs.subs(substitution)), sympy.cancel(rhs.subs(substitution))
        if left_value.is_Rational is not True or right_value.is_Rational is not True:
            raise ValueError("evaluation did not produce finite exact rational values")
        tested += 1
        if left_value != right_value:
            witness = {
                "assignment": dict(zip(names, map(str, point))),
                "lhs": str(left_value),
                "rhs": str(right_value),
                "difference": str(left_value - right_value),
            }
            break
    return {
        "schema_version": 1,
        "backend": "sympy",
        "backend_version": sympy.__version__,
        "created_at": timestamp(),
        "operation": "rational-counterexample-search",
        "claim": {"lhs": lhs_text, "rhs": rhs_text, "symbols": names},
        "assumptions": {key: sorted(assumptions.get(key, set())) for key in ("real", "positive", "integer")},
        "grid": list(map(str, grid)),
        "max_points": max_points,
        "total_grid_points": len(grid) ** len(names),
        "visited_points": visited,
        "tested_points": tested,
        "excluded_points": excluded,
        "grid_exhausted": visited == len(grid) ** len(names),
        "counterexample_found": witness is not None,
        "witness": witness,
        "status": "COUNTEREXAMPLE_FOUND" if witness else "INCONCLUSIVE",
        "recommended_evidence_role": "decisive" if witness else "diagnostic",
        "warning": "A witness refutes only the stated identity under the recorded assumptions. Finite search cannot prove a universal identity; case verdict and release review remain separate.",
    }


def lean_trust_scan(source: str) -> dict[str, list[str] | bool]:
    findings = {
        "sorry": re.findall(r"\bsorry\b", source),
        "admit": re.findall(r"\badmit\b", source),
        "axiom": re.findall(r"(?m)^\s*axiom\s+([A-Za-z0-9_']+)", source),
    }
    findings["trust_clean"] = not any(findings[key] for key in ("sorry", "admit", "axiom"))
    return findings


def lean_certificate(file: Path, executable: str, project: Path | None, timeout: int) -> tuple[dict[str, Any], int]:
    if not file.is_file():
        raise ValueError(f"Lean file not found: {file}")
    source = file.read_text(encoding="utf-8")
    scan = lean_trust_scan(source)
    if project:
        command = (
            [executable, "env", "lean", str(file.resolve())]
            if Path(executable).name.startswith("lake")
            else [executable, str(file.resolve())]
        )
        cwd = project.resolve()
    else:
        command = [executable, str(file.resolve())]
        cwd = file.parent.resolve()
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    version = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    compiled = completed.returncode == 0
    trusted = compiled and bool(scan["trust_clean"])
    certificate = {
        "schema_version": 1,
        "backend": "lean",
        "created_at": timestamp(),
        "file": str(file.resolve()),
        "file_sha256": sha256(file),
        "command": command,
        "backend_version": (version.stdout or version.stderr).strip(),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "trust_scan": scan,
        "compiled": compiled,
        "trusted_certificate": trusted,
        "recommended_evidence_role": "decisive" if trusted else "diagnostic",
        "warning": "Compilation with sorry, admit, or declared axioms is not a closed proof certificate.",
    }
    return certificate, 0 if compiled else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    identity = commands.add_parser("sympy-identity")
    identity.add_argument("--lhs", required=True)
    identity.add_argument("--rhs", required=True)
    identity.add_argument("--symbols", nargs="+", required=True)
    identity.add_argument("--real", nargs="*", default=[])
    identity.add_argument("--positive", nargs="*", default=[])
    identity.add_argument("--integer", nargs="*", default=[])
    identity.add_argument("--output", type=Path, required=True)
    matrix = commands.add_parser("sympy-matrix-det")
    matrix.add_argument("--matrix", type=Path, required=True)
    matrix.add_argument("--expected", required=True)
    matrix.add_argument("--symbols", nargs="+", required=True)
    matrix.add_argument("--real", nargs="*", default=[])
    matrix.add_argument("--positive", nargs="*", default=[])
    matrix.add_argument("--integer", nargs="*", default=[])
    matrix.add_argument("--output", type=Path, required=True)
    search = commands.add_parser(
        "sympy-counterexample", help="search an exact rational grid for an identity counterexample"
    )
    search.add_argument("--lhs", required=True)
    search.add_argument("--rhs", required=True)
    search.add_argument("--symbols", nargs="+", required=True)
    search.add_argument("--values", nargs="+", default=["-2", "-1", "0", "1", "2"])
    search.add_argument("--max-points", type=int, default=1000)
    search.add_argument("--real", nargs="*", default=[])
    search.add_argument("--positive", nargs="*", default=[])
    search.add_argument("--integer", nargs="*", default=[])
    search.add_argument("--output", type=Path, required=True)
    lean = commands.add_parser("lean-check")
    lean.add_argument("--file", type=Path, required=True)
    lean.add_argument("--lean", default="")
    lean.add_argument("--project", type=Path)
    lean.add_argument("--timeout", type=int, default=120)
    lean.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in {"sympy-identity", "sympy-matrix-det", "sympy-counterexample"}:
            assumption_args = {
                "real": set(args.real),
                "positive": set(args.positive),
                "integer": set(args.integer),
            }
            if args.command == "sympy-counterexample":
                result = counterexample_search(
                    args.lhs, args.rhs, args.symbols, args.values, args.max_points, **assumption_args
                )
                write_json(args.output, result)
                print(f"status={result['status']} tested={result['tested_points']}")
                return 0 if result["counterexample_found"] else 1
            if args.command == "sympy-identity":
                result = identity_certificate(args.lhs, args.rhs, args.symbols, **assumption_args)
            else:
                result = matrix_certificate(args.matrix, args.expected, args.symbols, **assumption_args)
            write_json(args.output, result)
            print(f"established={result['identity_established']} classification={result['classification']}")
            return 0 if result["identity_established"] else 1
        executable = args.lean or shutil.which("lake") or shutil.which("lean")
        if not executable:
            raise RuntimeError("Lean was not found; install Lean 4/elan or pass --lean")
        result, returncode = lean_certificate(args.file, executable, args.project, args.timeout)
        write_json(args.output, result)
        print(f"compiled={result['compiled']} trusted={result['trusted_certificate']}")
        return returncode
    except (
        RuntimeError,
        ValueError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
    ) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
