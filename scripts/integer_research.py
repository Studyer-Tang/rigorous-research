"""Bounded integer research producers; verification lives in a separate module."""

from math import gcd

from egyptian_fractions import Budget, BudgetExhausted


def factor(value, budget):
    result, p = [], 2
    while p * p <= value:
        budget.spend()
        exponent = 0
        while value % p == 0:
            budget.spend()
            value //= p
            exponent += 1
        if exponent:
            result.append([p, exponent])
        p = 3 if p == 2 else p + 2
    if value > 1:
        result.append([value, 1])
    return result


def window(numerator, denominator, start_x, stop_x, distinct, max_work):
    """Existence in an explicit first-denominator window, never the unbounded conjecture."""
    if any(type(v) is not int for v in (numerator, denominator, start_x, stop_x, max_work)):
        raise ValueError("integer parameters required")
    if not (1 <= numerator <= 100 and 1 <= denominator <= 10**6 and 1 <= start_x <= stop_x <= 10**6):
        raise ValueError("parameters exceed integer research limits")
    if stop_x - start_x >= 64 or type(distinct) is not bool or not 1 <= max_work <= 10**7:
        raise ValueError("require at most 64 first denominators, boolean distinct and work budget 1..10000000")
    claim = dict(numerator=numerator, denominator=denominator, start_x=start_x, stop_x=stop_x, distinct=distinct)
    budget, entries, finished = Budget(max_work), [], False
    for x in range(start_x, stop_x + 1):
        row = {"x": x, "outcome": "unresolved"}
        if not finished:
            try:
                budget.spend()
                a, b = numerator * x - denominator, denominator * x
                if a <= 0:
                    row = {"x": x, "outcome": "nonpositive-residual"}
                else:
                    g = gcd(a, b)
                    a, b = a // g, b // g
                    factors = factor(b, budget)
                    divisors = [1]
                    for prime, power in factors:
                        old = divisors[:]
                        for exponent in range(1, 2 * power + 1):
                            for value in old:
                                budget.spend()
                                divisors.append(value * prime**exponent)
                    row = {"x": x, "outcome": "obstructed", "factorization": factors}
                    for d in sorted(divisors):
                        budget.spend()
                        if d > b:
                            break
                        e = b * b // d
                        if (d + b) % a or (e + b) % a:
                            continue
                        y, z = (d + b) // a, (e + b) // a
                        if (x < y < z) if distinct else (x <= y <= z):
                            row = {"x": x, "outcome": "witness", "y": y, "z": z}
                            finished = True
                            break
            except BudgetExhausted:
                row = {"x": x, "outcome": "unresolved"}
                finished = True
        entries.append(row)
    return {
        "schema_version": 1,
        "backend": "exact-integer",
        "backend_version": "2",
        "operation": "three-unit-fractions-window",
        "claim": claim,
        "entries": entries,
        "budget": {"max_work": max_work, "used_work": budget.used},
        "warning": "REFUTED means no ordered completion inside this explicit window only. Unresolved entries are not obstructions.",
    }


def family(numerator, n, x, y, z, distinct):
    """Use SymPy to propose a coefficient proof, independently rechecked with integer arithmetic."""
    import sympy as sp

    t = sp.Symbol("t")
    arrays = dict(n=n, x=x, y=y, z=z)
    polynomials = {key: sum(c * t**i for i, c in enumerate(value)) for key, value in arrays.items()}
    nn, xx, yy, zz = (polynomials[key] for key in ("n", "x", "y", "z"))
    difference = sp.Poly(numerator * xx * yy * zz - nn * (xx * yy + xx * zz + yy * zz), t)
    step = 1 if distinct else 0
    conditions = [nn - 1, xx - 1, yy - xx - step, zz - yy - step]
    witness = None
    for value in range(3 * max(map(len, arrays.values())) + 1):
        if difference.eval(value) != 0 or any(p.subs(t, value) < 0 for p in conditions):
            witness = value
            break
    return {
        "schema_version": 1,
        "backend": "exact-integer",
        "backend_version": "2",
        "operation": "unit-fraction-polynomial-family",
        "claim": {"numerator": numerator, **arrays, "distinct": distinct, "parameter": "nonnegative-integer"},
        "identity_zero": difference.is_zero,
        "nonnegative_coefficients": all(all(c >= 0 for c in sp.Poly(p, t).all_coeffs()) for p in conditions),
        "counterexample_parameter": witness,
        "warning": "Proves only this explicit polynomial family for integer t>=0. Coverage of other integers and novelty are separate.",
    }


def scan(numerator, start, stop, step, width, distinct, max_work):
    """Search a finite progression for a failed short-window hypothesis, with one shared budget."""
    values = (numerator, start, stop, step, width, max_work)
    if any(type(v) is not int for v in values) or not (1 <= numerator <= 100 and 1 <= start <= stop <= 10**6):
        raise ValueError("invalid scan parameters")
    if not 1 <= step <= 10**6 or not 1 <= width <= 16 or (stop - start) // step >= 256:
        raise ValueError("scan supports at most 256 inputs and 16 first denominators per input")
    if type(distinct) is not bool or not 1 <= max_work <= 10**7:
        raise ValueError("invalid scan distinctness or budget")
    windows, used = [], 0
    for n in range(start, stop + 1, step):
        if used == max_work:
            break
        first = n // numerator + 1
        result = window(numerator, n, first, first + width - 1, distinct, max_work - used)
        windows.append(result)
        used += result["budget"]["used_work"]
        if not any(row["outcome"] == "witness" for row in result["entries"]):
            break
    return {
        "schema_version": 1,
        "backend": "exact-integer",
        "backend_version": "2",
        "operation": "three-unit-fractions-window-scan",
        "claim": dict(numerator=numerator, start=start, stop=stop, step=step, width=width, distinct=distinct),
        "windows": windows,
        "budget": dict(max_work=max_work, used_work=used),
        "warning": "Tests the short-window hypothesis on this finite progression. A refuted window is not an Erdos-Straus counterexample.",
    }
