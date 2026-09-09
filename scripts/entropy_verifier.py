"""Exact finite Shannon-entropy comparisons through integer products, without logarithms."""

import math
import re
from collections import Counter, defaultdict
from fractions import Fraction

from research_io import canonical_hash


def rational(value):
    if not isinstance(value, str) or not re.fullmatch(r"-?\d{1,8}(?:/[1-9]\d{0,7})?", value):
        raise ValueError("use a bounded exact rational string")
    return Fraction(value)


def check(certificate):
    if (
        set(certificate) != {"schema_version", "backend", "claim", "max_bits", "diagnostic"}
        or type(certificate["schema_version"]) is not int
        or certificate["schema_version"] != 1
        or certificate["backend"] != "exact-entropy"
    ):
        raise ValueError("unsupported entropy certificate")
    claim = certificate["claim"]
    if set(claim) != {"counts", "terms", "constant", "relation", "units", "domain"}:
        raise ValueError("entropy claim must retain its full finite distribution and partitions")
    if claim["relation"] != ">=" or claim["units"] != "bits" or claim["domain"] != "recorded-finite-distribution":
        raise ValueError("only the recorded finite Shannon entropy inequality in bits is supported")
    counts = claim["counts"]
    if (
        not isinstance(counts, list)
        or not 1 <= len(counts) <= 1024
        or any(type(c) is not int or not 0 <= c <= 10**6 for c in counts)
        or not sum(counts)
    ):
        raise ValueError("counts must be 1–1024 nonnegative integers with positive total")
    terms = claim["terms"]
    if not isinstance(terms, list) or not 1 <= len(terms) <= 32:
        raise ValueError("specify 1–32 entropy terms")
    limit = certificate["max_bits"]
    if type(limit) is not int or not 1000 <= limit <= 500000:
        raise ValueError("integer product bit budget must be in 1000..500000")
    total = sum(counts)
    coefficients = defaultdict(Fraction)
    coefficients[2] -= rational(claim["constant"])
    for term in terms:
        if set(term) != {"coefficient", "labels"}:
            raise ValueError("each entropy term needs exactly its coefficient and partition labels")
        weight = rational(term["coefficient"])
        labels = term["labels"]
        if (
            not isinstance(labels, list)
            or len(labels) != len(counts)
            or any(type(label) is not int or not 0 <= label <= 1023 for label in labels)
        ):
            raise ValueError("partition labels must cover exactly the recorded atoms")
        marginal = Counter()
        for label, count in zip(labels, counts):
            marginal[label] += count
        # H = log2(total) - sum_c (c/total)*log2(c); zero bins contribute zero.
        coefficients[total] += weight
        for count in marginal.values():
            if count:
                coefficients[count] -= weight * Fraction(count, total)
    coefficients = {base: value for base, value in coefficients.items() if base > 1 and value}
    scale = math.lcm(*(c.denominator for c in coefficients.values())) if coefficients else 1
    exponents = {base: int(scale * coefficient) for base, coefficient in coefficients.items()}
    required_bits = sum(abs(power) * base.bit_length() for base, power in exponents.items())
    if required_bits > limit:
        return "INCONCLUSIVE", {"reason": "integer product budget exceeded", "required_bits_upper_bound": required_bits}
    numerator = denominator = 1
    for base, exponent in exponents.items():
        if exponent > 0:
            numerator *= pow(base, exponent)
        else:
            denominator *= pow(base, -exponent)
    sign = (numerator > denominator) - (numerator < denominator)
    return ("ESTABLISHED" if sign >= 0 else "REFUTED"), {
        "sign": sign,
        "integer_scale": scale,
        "numerator_bits": numerator.bit_length(),
        "denominator_bits": denominator.bit_length(),
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
        "scope": "Only this recorded finite distribution and its partitions; no universal entropy inequality, coupling applicability or conjecture verdict.",
    }
