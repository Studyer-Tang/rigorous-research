#!/usr/bin/env python3
"""Exact permutation expansion for det(rho^|i-j|), n <= 7."""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path


def permutation_sign(values: tuple[int, ...]) -> int:
    inversions = sum(values[i] > values[j] for i in range(len(values)) for j in range(i + 1, len(values)))
    return -1 if inversions % 2 else 1


def determinant_coefficients(n: int) -> list[int]:
    coefficients = [0] * (n * n + 1)
    for permutation in itertools.permutations(range(n)):
        degree = sum(abs(i - permutation[i]) for i in range(n))
        coefficients[degree] += permutation_sign(permutation)
    while len(coefficients) > 1 and coefficients[-1] == 0:
        coefficients.pop()
    return coefficients


def expected_coefficients(n: int) -> list[int]:
    coefficients = [0] * (2 * (n - 1) + 1)
    for k in range(n):
        coefficients[2 * k] = (-1) ** k * math.comb(n - 1, k)
    return coefficients


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-n", type=int, default=7)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.max_n <= 9:
        parser.error("max-n must be between 1 and 9")
    cases = []
    for n in range(1, args.max_n + 1):
        observed = determinant_coefficients(n)
        expected = expected_coefficients(n)
        cases.append(
            {
                "n": n,
                "permutations": math.factorial(n),
                "observed_coefficients_low_to_high": observed,
                "expected_coefficients_low_to_high": expected,
                "match": observed == expected,
            }
        )
    result = {
        "method": "Leibniz determinant expansion with exact integer coefficient collection",
        "coverage": f"all n from 1 through {args.max_n}",
        "all_match": all(case["match"] for case in cases),
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"verified={result['all_match']} cases={len(cases)}")
    return 0 if result["all_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
