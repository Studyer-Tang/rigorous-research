"""Independently check finite unit-fraction witnesses and a narrow modular obstruction."""

from __future__ import annotations

from math import gcd, isqrt
from typing import Any

from research_io import canonical_hash


def integer(value: Any, label: str, lower: int = 1, upper: int = 10**30) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"{label} must be an integer in [{lower}, {upper}]")
    return value


def check_finite(certificate: dict[str, Any]) -> str:
    claim = certificate["claim"]
    if set(claim) != {"numerator", "start", "stop", "distinct"}:
        raise ValueError("finite claim must specify exactly numerator, start, stop, and distinct")
    a = integer(claim["numerator"], "numerator", upper=100)
    start = integer(claim["start"], "start", upper=10**6)
    stop = integer(claim["stop"], "stop", lower=start, upper=min(10**6, start + 9999))
    if type(claim["distinct"]) is not bool:
        raise ValueError("distinct must be a boolean")
    rows, unresolved = certificate["witnesses"], certificate["unresolved"]
    if (
        not isinstance(rows, list)
        or not isinstance(unresolved, list)
        or len(rows) + len(unresolved) != stop - start + 1
    ):
        raise ValueError("witnesses and unresolved entries must cover the entire finite domain")
    covered = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"n", "x", "y", "z"}:
            raise ValueError("each witness must contain exactly n, x, y, z")
        n = integer(row["n"], "n", start, stop)
        x, y, z = (integer(row[key], key) for key in ("x", "y", "z"))
        if n in covered or not x <= y <= z or (claim["distinct"] and not x < y < z):
            raise ValueError("duplicate n or invalid denominator order/distinctness")
        if a * x * y * z != n * (x * y + x * z + y * z):
            raise ValueError(f"n={n}: witness fails exact cross multiplication")
        covered.add(n)
    for value in unresolved:
        n = integer(value, "unresolved n", start, stop)
        if n in covered:
            raise ValueError("duplicate or contradictory finite coverage")
        covered.add(n)
    if covered != set(range(start, stop + 1)):
        raise ValueError("finite coverage has a gap")
    return "INCONCLUSIVE" if unresolved else "ESTABLISHED"


def check_obstruction(certificate: dict[str, Any]) -> str:
    claim = certificate["claim"]
    if set(claim) != {"numerator", "denominator", "first_denominator"}:
        raise ValueError("obstruction is scoped to one rational number and fixed first denominator")
    numerator = integer(claim["numerator"], "numerator", upper=100)
    n = integer(claim["denominator"], "denominator", upper=10**6)
    x = integer(claim["first_denominator"], "first denominator", upper=10**6)
    a, b = numerator * x - n, n * x
    if a <= 0:
        raise ValueError("obstruction requires a positive residual")
    common = gcd(a, b)
    a, b = a // common, b // common
    factors = certificate["denominator_factorization"]
    if not isinstance(factors, list) or not 1 <= len(factors) <= 40:
        raise ValueError("a complete prime factorization is required")
    product, seen = 1, set()
    for factor in factors:
        if not isinstance(factor, dict) or set(factor) != {"prime", "exponent"}:
            raise ValueError("invalid prime-power record")
        p = integer(factor["prime"], "prime", 2, 10**6)
        exponent = integer(factor["exponent"], "exponent", upper=40)
        if p in seen or any(p % divisor == 0 for divisor in range(2, isqrt(p) + 1)):
            raise ValueError("factor bases must be distinct primes")
        if p % a != 1:
            raise ValueError(
                "this narrow obstruction requires every prime factor to equal 1 modulo the residual numerator"
            )
        seen.add(p)
        product *= p**exponent
    if product != b or (-b) % a == 1:
        raise ValueError("factorization or modular contradiction is invalid")
    # If a/b=1/y+1/z, then (ay-b)(az-b)=b^2 and both factors are positive.
    # Every divisor of b^2 is 1 mod a, but ay-b is -b mod a, a contradiction.
    return "ESTABLISHED"


def verify(certificate: dict[str, Any]) -> dict[str, Any]:
    try:
        if certificate.get("schema_version") != 1 or certificate.get("backend") != "exact-integer":
            raise ValueError("unsupported integer certificate")
        if certificate.get("assumptions", {}) != {}:
            raise ValueError("integer operations do not accept extra assumptions")
        operation = certificate.get("operation")
        if operation == "three-unit-fractions-finite":
            status = check_finite(certificate)
        elif operation == "two-unit-fractions-obstruction":
            status = check_obstruction(certificate)
        else:
            raise ValueError("unsupported integer operation")
        errors = []
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        status, errors = "INVALID", [str(exc)]
    return {
        "schema_version": 1,
        "kind": "independent-certificate-check",
        "status": status,
        "errors": errors,
        "certificate_hash": canonical_hash(certificate),
        "scope": "Only the explicit finite domain or fixed-first-denominator obstruction; no universal conjecture or novelty claim.",
    }
