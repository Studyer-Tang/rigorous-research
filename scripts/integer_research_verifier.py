"""Independent integer-only checking of bounded windows and universal polynomial families.

Does not import the producer or SymPy. Nonnegative polynomial coefficients are a
sufficient positivity proof, not a complete decision procedure for positivity.
"""

from math import gcd, isqrt


def number(value, low=0, high=10**30):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("invalid bounded integer")
    return value


def denominators(claim):
    a = number(claim["numerator"], 1, 100)
    n = number(claim["denominator"], 1, 10**6)
    first = number(claim["start_x"], 1, 10**6)
    last = number(claim["stop_x"], first, min(10**6, first + 63))
    if type(claim["distinct"]) is not bool:
        raise ValueError("distinct must be boolean")
    return a, n, first, last


def divisors_of_square(factors, b):
    if not isinstance(factors, list) or len(factors) > 40:
        raise ValueError("invalid factorization")
    result, product, previous = [1], 1, 1
    for item in factors:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError("invalid prime power")
        p, exponent = number(item[0], previous + 1, b), number(item[1], 1, 40)
        if p < 2 or any(p % d == 0 for d in range(2, isqrt(p) + 1)):
            raise ValueError("composite factor base")
        product *= p**exponent
        if product > b or len(result) * (2 * exponent + 1) > 100000:
            raise ValueError("factorization exceeds product or divisor limit")
        result = [d * p**k for d in result for k in range(2 * exponent + 1)]
        previous = p
    if product != b:
        raise ValueError("incomplete factorization")
    return result


def check_window(certificate):
    claim = certificate["claim"]
    if set(claim) != {"numerator", "denominator", "start_x", "stop_x", "distinct"}:
        raise ValueError("window claim must retain its exact bounds and ordering")
    a0, n, first, last = denominators(claim)
    entries = certificate["entries"]
    if not isinstance(entries, list) or len(entries) != last - first + 1:
        raise ValueError("window coverage gap")
    witness, unresolved = False, False
    for x, row in zip(range(first, last + 1), entries):
        if number(row["x"], first, last) != x:
            raise ValueError("window entries must cover every x exactly once in order")
        outcome = row["outcome"]
        keys = {"x", "outcome"}
        if outcome == "witness":
            keys |= {"y", "z"}
            y, z = number(row["y"], 1), number(row["z"], 1)
            if not (x < y < z if claim["distinct"] else x <= y <= z):
                raise ValueError("invalid witness order")
            if a0 * x * y * z != n * (x * y + x * z + y * z):
                raise ValueError("false witness")
            witness = True
        elif outcome == "unresolved":
            unresolved = True
        elif outcome == "nonpositive-residual":
            if a0 * x > n:
                raise ValueError("residual is positive")
        elif outcome == "obstructed":
            keys.add("factorization")
            a, b = a0 * x - n, n * x
            if a <= 0:
                raise ValueError("use nonpositive-residual for this case")
            g = gcd(a, b)
            a, b = a // g, b // g
            for d in divisors_of_square(row["factorization"], b):
                if d > b:
                    continue
                e = b * b // d
                if (b + d) % a == 0 and (b + e) % a == 0:
                    y, z = (b + d) // a, (b + e) // a
                    if (x < y < z) if claim["distinct"] else (x <= y <= z):
                        raise ValueError("claimed obstruction has an ordered completion")
        else:
            raise ValueError("unknown window outcome")
        if set(row) != keys:
            raise ValueError("unexpected window entry fields")
    return "ESTABLISHED" if witness else "INCONCLUSIVE" if unresolved else "REFUTED"


def add(*polynomials):
    return [sum(p[i] if i < len(p) else 0 for p in polynomials) for i in range(max(map(len, polynomials)))]


def multiply(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def evaluate(polynomial, t):
    value = 0
    for coefficient in reversed(polynomial):
        value = value * t + coefficient
    return value


def check_family(certificate):
    claim = certificate["claim"]
    if set(claim) != {"numerator", "n", "x", "y", "z", "distinct", "parameter"}:
        raise ValueError("family claim must retain all polynomial coefficients and parameter domain")
    a = number(claim["numerator"], 1, 100)
    if claim["parameter"] != "nonnegative-integer" or type(claim["distinct"]) is not bool:
        raise ValueError("unsupported parameter domain or ordering")
    arrays = []
    for key in ("n", "x", "y", "z"):
        p = claim[key]
        if not isinstance(p, list) or not 1 <= len(p) <= 13:
            raise ValueError("polynomial degree limit is 12")
        arrays.append([number(c, -(10**18), 10**18) for c in p])
    n, x, y, z = arrays
    lhs = [a * c for c in multiply(multiply(x, y), z)]
    rhs = multiply(n, add(multiply(x, y), multiply(x, z), multiply(y, z)))
    difference = add(lhs, [-c for c in rhs])
    step = int(claim["distinct"])
    conditions = [add(n, [-1]), add(x, [-1]), add(y, [-c for c in x], [-step]), add(z, [-c for c in y], [-step])]
    t = certificate.get("counterexample_parameter")
    if t is not None:
        t = number(t, 0, 1000)
        if evaluate(difference, t) == 0 and all(evaluate(p, t) >= 0 for p in conditions):
            raise ValueError("purported family counterexample is valid")
        return "REFUTED"
    # Ignore producer booleans: recompute identity and side conditions independently.
    if any(difference) or any(c < 0 for p in conditions for c in p):
        return "INCONCLUSIVE"
    return "ESTABLISHED"


def check_scan(certificate):
    claim = certificate["claim"]
    if set(claim) != {"numerator", "start", "stop", "step", "width", "distinct"}:
        raise ValueError("scan claim must retain its finite progression and window width")
    a = number(claim["numerator"], 1, 100)
    start = number(claim["start"], 1, 10**6)
    stop = number(claim["stop"], start, 10**6)
    step = number(claim["step"], 1, 10**6)
    width = number(claim["width"], 1, 16)
    if type(claim["distinct"]) is not bool or (stop - start) // step >= 256:
        raise ValueError("scan exceeds input limit or has invalid ordering")
    ns = range(start, stop + 1, step)
    windows = certificate["windows"]
    if not isinstance(windows, list) or len(windows) > len(ns):
        raise ValueError("invalid scan windows")
    statuses = []
    for n, window in zip(ns, windows):
        if window.get("assumptions", {}) != {}:
            raise ValueError("scan windows cannot introduce assumptions")
        expected = dict(
            numerator=a, denominator=n, start_x=n // a + 1, stop_x=n // a + width, distinct=claim["distinct"]
        )
        if window["claim"] != expected:
            raise ValueError("scan window has changed domain or a coverage gap")
        statuses.append(check_window(window))
    if "REFUTED" in statuses:
        return "REFUTED"
    return "ESTABLISHED" if len(windows) == len(ns) and all(s == "ESTABLISHED" for s in statuses) else "INCONCLUSIVE"
