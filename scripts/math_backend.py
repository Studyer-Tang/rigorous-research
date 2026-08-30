#!/usr/bin/env python3
"""Create conservative SymPy identity certificates and Lean compilation records."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from research_io import sha256, utc_timestamp as timestamp, write_json


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
    allowed = {
        **symbols,
        "sin": sympy.sin,
        "cos": sympy.cos,
        "tan": sympy.tan,
        "exp": sympy.exp,
        "log": sympy.log,
        "sqrt": sympy.sqrt,
        "Abs": sympy.Abs,
        "pi": sympy.pi,
        "E": sympy.E,
        "I": sympy.I,
    }
    lhs = sympy.sympify(lhs_text, locals=allowed)
    rhs = sympy.sympify(rhs_text, locals=allowed)
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
    except (sympy.PolynomialError, ValueError):
        exact_zero = bool(sympy.simplify(difference) == 0)
    if exact_zero and polynomial:
        classification = "exact-polynomial" if sympy.simplify(denominator - 1) == 0 else "exact-rational-on-domain"
        evidence_role = "decisive"
    elif exact_zero:
        classification = "symbolically-simplified"
        evidence_role = "diagnostic"
    else:
        classification = "not-established"
        evidence_role = "diagnostic"
    denominator_text = str(sympy.factor(denominator))
    exceptional = "none" if sympy.simplify(denominator - 1) == 0 else f"{denominator_text} = 0"
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
    matrix = sympy.Matrix([[sympy.sympify(value, locals=table) for value in row] for row in data])
    determinant = sympy.factor(matrix.det(method="domain-ge"))
    certificate = identity_certificate(str(determinant), expected, names, **assumptions)
    certificate["operation"] = "matrix-determinant"
    certificate["matrix_sha256"] = sha256(matrix_file)
    certificate["matrix_shape"] = [len(data), width]
    certificate["computed_determinant"] = str(determinant)
    return certificate


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
    lean = commands.add_parser("lean-check")
    lean.add_argument("--file", type=Path, required=True)
    lean.add_argument("--lean", default="")
    lean.add_argument("--project", type=Path)
    lean.add_argument("--timeout", type=int, default=120)
    lean.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command in {"sympy-identity", "sympy-matrix-det"}:
            assumption_args = {
                "real": set(args.real),
                "positive": set(args.positive),
                "integer": set(args.integer),
            }
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
