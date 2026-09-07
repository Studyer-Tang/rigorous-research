#!/usr/bin/env python3
"""Budgeted exact searches for three positive unit fractions; gaps remain inconclusive."""

from __future__ import annotations

import argparse
import json
from math import gcd
from pathlib import Path
from typing import Any

from research_io import write_json


class BudgetExhausted(Exception):
    pass


class Budget:
    def __init__(self, limit: int):
        self.limit = limit
        self.used = 0

    def spend(self) -> None:
        if self.used >= self.limit:
            raise BudgetExhausted
        self.used += 1


def square_divisors(value: int, budget: Budget) -> list[int]:
    """Factor b, then enumerate divisors of b squared; no floating-point arithmetic."""
    factors, candidate = [], 2
    while candidate * candidate <= value:
        budget.spend()
        exponent = 0
        while value % candidate == 0:
            budget.spend()
            value //= candidate
            exponent += 1
        if exponent:
            factors.append((candidate, exponent * 2))
        candidate = 3 if candidate == 2 else candidate + 2
    if value > 1:
        factors.append((value, 2))
    divisors = [1]
    for prime, exponent in factors:
        previous, power = divisors[:], 1
        for _ in range(exponent):
            power *= prime
            for divisor in previous:
                budget.spend()
                divisors.append(divisor * power)
    return sorted(divisors)


def completion(a: int, n: int, x: int, distinct: bool, budget: Budget) -> tuple[int, int, int] | None:
    residual, denominator = a * x - n, n * x
    if residual <= 0:
        return None
    common = gcd(residual, denominator)
    residual, denominator = residual // common, denominator // common
    for divisor in square_divisors(denominator, budget):
        budget.spend()
        if divisor > denominator:
            break
        other = denominator * denominator // divisor
        if (divisor + denominator) % residual or (other + denominator) % residual:
            continue
        y, z = (divisor + denominator) // residual, (other + denominator) // residual
        if (distinct and x < y < z) or (not distinct and x <= y <= z):
            return x, y, z
    return None


def construction(n: int) -> tuple[int, int, int] | None:
    """Elementary known residue families; these are not a new universal proof."""
    if n >= 4 and n % 2 == 0:
        m = n // 2
        return m, m + 1, m * (m + 1)
    if n % 4 == 3:
        x = (n + 1) // 4
        m = n * x
        return x, m + 1, m * (m + 1)
    if n >= 5 and n % 3 == 2:
        x = (n + 1) // 3
        return x, n, n * x
    if n % 8 == 5:
        x = (n + 3) // 4
        return x, n * x // 2, n * x
    return None


def search(
    numerator: int, start: int, stop: int, distinct: bool, max_x: int = 64, max_work: int = 1_000_000
) -> dict[str, Any]:
    if any(type(value) is not int for value in (numerator, start, stop, max_x, max_work)):
        raise ValueError("search limits must be integers")
    if not (1 <= numerator <= 100 and 1 <= start <= stop <= 10**6 and stop - start < 10000):
        raise ValueError("require numerator 1..100, denominator 1..1000000, and at most 10000 inputs")
    if type(distinct) is not bool or not 1 <= max_x <= 10000 or not 1 <= max_work <= 10_000_000:
        raise ValueError("require boolean distinct, max_x 1..10000, and max_work 1..10000000")
    budget, rows, unresolved = Budget(max_work), [], []
    strategies = {"construction": 0, "divisor_search": 0}
    for n in range(start, stop + 1):
        witness = None
        try:
            budget.spend()
            witness = construction(n) if numerator == 4 else None
            if witness:
                strategies["construction"] += 1
            else:
                first = n // numerator + 1
                last = min(3 * n // numerator, first + max_x - 1)
                for x in range(first, last + 1):
                    budget.spend()
                    witness = completion(numerator, n, x, distinct, budget)
                    if witness:
                        strategies["divisor_search"] += 1
                        break
        except BudgetExhausted:
            unresolved.extend(range(n, stop + 1))
            break
        if witness:
            rows.append(dict(zip(("n", "x", "y", "z"), (n, *witness))))
        else:
            unresolved.append(n)
    return {
        "schema_version": 1,
        "backend": "exact-integer",
        "backend_version": "1",
        "operation": "three-unit-fractions-finite",
        "claim": {"numerator": numerator, "start": start, "stop": stop, "distinct": distinct},
        "witnesses": rows,
        "unresolved": unresolved,
        "budget": {"max_x_per_n": max_x, "max_work": max_work, "used_work": budget.used},
        "strategies": strategies,
        "recommended_evidence_role": "diagnostic" if unresolved else "decisive",
        "warning": "Evidence covers only the finite declared domain. Missing witnesses are not counterexamples. Construction formulas are elementary known partial results, not a claim of novelty.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numerator", type=int, default=4)
    parser.add_argument("--start", type=int, default=3)
    parser.add_argument("--stop", type=int, required=True)
    parser.add_argument("--distinct", action="store_true")
    parser.add_argument("--max-x", type=int, default=64)
    parser.add_argument("--max-work", type=int, default=1_000_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        from integer_certificate_verifier import verify

        certificate = search(args.numerator, args.start, args.stop, args.distinct, args.max_x, args.max_work)
        checked = verify(certificate)
        write_json(args.output, certificate)
        print(json.dumps({"status": checked["status"], "errors": checked["errors"], "output": str(args.output)}))
        return 0 if checked["status"] == "ESTABLISHED" else 1
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
