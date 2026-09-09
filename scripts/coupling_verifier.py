"""Certify event entropy of a finite matrix-scaling minimizer via a rational approximate solution."""

import re
from fractions import Fraction

from rational_log import entropy_bounds, log_bounds, outward
from research_io import canonical_hash


def rational(value):
    if not isinstance(value, str) or not re.fullmatch(r"-?\d{1,40}(?:/[1-9]\d{0,39})?", value):
        raise ValueError("use an exact rational string of bounded length")
    return Fraction(value)


def matrix(value, size):
    if (
        not isinstance(value, list)
        or len(value) != size
        or any(not isinstance(row, list) or len(row) != size for row in value)
    ):
        raise ValueError("matrix dimensions disagree")
    return value


def check(certificate):
    if (
        set(certificate) != {"schema_version", "backend", "claim", "approximation", "diagnostic"}
        or type(certificate["schema_version"]) is not int
        or certificate["schema_version"] != 1
        or certificate["backend"] != "balanced-coupling"
    ):
        raise ValueError("unsupported coupling certificate")
    claim = certificate["claim"]
    if set(claim) != {"kernel", "labels", "bound", "relation", "units", "marginals", "objective"}:
        raise ValueError("coupling claim must retain its objective, event and marginals")
    if (
        claim["units"] != "nats"
        or claim["marginals"] != "uniform-rows-and-columns"
        or claim["objective"] != "minimize-sum-p-log-p-over-k"
        or claim["relation"] not in {">=", "<="}
    ):
        raise ValueError("unsupported coupling semantics")
    kernel = claim["kernel"]
    if not isinstance(kernel, list) or not 2 <= len(kernel) <= 16:
        raise ValueError("kernel size must be 2–16")
    n = len(kernel)
    kernel = [[rational(k) for k in row] for row in matrix(kernel, n)]
    if any(k <= 0 for row in kernel for k in row):
        raise ValueError("kernel must be strictly positive")
    labels = matrix(claim["labels"], n)
    if any(type(x) is not int or not 0 <= x < n * n for row in labels for x in row):
        raise ValueError("invalid event labels")
    bound = rational(claim["bound"])
    approx = certificate["approximation"]
    if approx is None:
        return "INCONCLUSIVE", {"reason": "no approximate solution was supplied"}
    if set(approx) != {"counts", "row_factors", "column_factors", "delta"}:
        raise ValueError("invalid approximation fields")
    counts = matrix(approx["counts"], n)
    if any(type(c) is not int or not 1 <= c <= 10**18 for row in counts for c in row):
        raise ValueError("approximation counts must be strictly positive bounded integers")
    total = sum(map(sum, counts))
    if any(n * sum(row) != total for row in counts) or any(
        n * sum(row[j] for row in counts) != total for j in range(n)
    ):
        raise ValueError("approximation must preserve both uniform marginals exactly")
    factors = []
    for key in ("row_factors", "column_factors"):
        values = approx[key]
        if not isinstance(values, list) or len(values) != n:
            raise ValueError("scaling factors have incorrect length")
        values = list(map(rational, values))
        if any(x <= 0 for x in values):
            raise ValueError("scaling factors must be positive")
        factors.append(values)
    delta = rational(approx["delta"])
    if not 0 <= delta <= Fraction(1, 2):
        raise ValueError("continuity radius must be in [0,1/2]")
    bins, epsilon = {}, Fraction(0)
    for i in range(n):
        for j in range(n):
            p = Fraction(counts[i][j], total)
            ratio = p / (factors[0][i] * kernel[i][j] * factors[1][j])
            epsilon = max(epsilon, ratio - 1, 1 / ratio - 1)
            bins[labels[i][j]] = bins.get(labels[i][j], Fraction(0)) + p
    # |log(ratio)| <= max(ratio-1, 1/ratio-1). Uniform marginals cancel the
    # scaling multipliers in the convexity gap, so D(R||P*) <= 2*epsilon.
    # Pinsker then gives TV(R,P*) <= sqrt(epsilon) <= delta.
    if epsilon > delta * delta:
        raise ValueError("stationarity error exceeds the supplied continuity radius")
    low, high = entropy_bounds(list(bins.values()))
    error = Fraction(0)
    if delta and len(bins) > 1:
        error = delta * log_bounds(len(bins) - 1)[1] + entropy_bounds([delta, 1 - delta])[1]
    low, high = outward(low - error, high + error)
    if claim["relation"] == ">=":
        status = "ESTABLISHED" if low >= bound else "REFUTED" if high < bound else "INCONCLUSIVE"
    else:
        status = "ESTABLISHED" if high <= bound else "REFUTED" if low > bound else "INCONCLUSIVE"
    return status, {
        "entropy_lower_nats": str(low),
        "entropy_upper_nats": str(high),
        "continuity_radius": str(delta),
        "stationarity_error_upper": str(outward(epsilon, epsilon)[1]),
    }


def verify(certificate):
    try:
        status, computation = check(certificate)
        errors = []
    except (ValueError, TypeError, KeyError, AttributeError, ZeroDivisionError) as exc:
        status, computation, errors = "INVALID", {}, [str(exc)]
    return {
        "schema_version": 1,
        "kind": "independent-certificate-check",
        "status": status,
        "errors": errors,
        "computation": computation,
        "certificate_hash": canonical_hash(certificate),
        "scope": "Event entropy of the recorded positive-kernel optimization with uniform marginals only; no conjecture or model-translation verdict.",
    }
