#!/usr/bin/env python3
"""Independent exact-rational elimination checks for the Toeplitz determinant identity."""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path


def determinant(matrix: list[list[Fraction]]) -> Fraction:
    work = [row[:] for row in matrix]
    sign = 1
    value = Fraction(1)
    for column in range(len(work)):
        pivot = next((row for row in range(column, len(work)) if work[row][column]), None)
        if pivot is None:
            return Fraction(0)
        if pivot != column:
            work[column], work[pivot] = work[pivot], work[column]
            sign *= -1
        pivot_value = work[column][column]
        value *= pivot_value
        for row in range(column + 1, len(work)):
            factor = work[row][column] / pivot_value
            for index in range(column, len(work)):
                work[row][index] -= factor * work[column][index]
    return sign * value


def encode(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-n", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parameters = [Fraction(-2), Fraction(-1), Fraction(-1, 2), Fraction(0), Fraction(1, 3), Fraction(1), Fraction(2)]
    cases = []
    for n in range(1, args.max_n + 1):
        for rho in parameters:
            matrix = [[rho ** abs(i - j) for j in range(n)] for i in range(n)]
            observed = determinant(matrix)
            expected = (1 - rho * rho) ** (n - 1)
            cases.append(
                {
                    "n": n,
                    "rho": encode(rho),
                    "observed": encode(observed),
                    "expected": encode(expected),
                    "match": observed == expected,
                }
            )
    result = {
        "method": "Gaussian elimination over fractions.Fraction",
        "coverage": f"n=1..{args.max_n}; rho in {', '.join(encode(value) for value in parameters)}",
        "all_match": all(case["match"] for case in cases),
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"verified={result['all_match']} cases={len(cases)}")
    return 0 if result["all_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
