"""Prepare finite entropy experiments; floating diagnostics never decide the exact verdict."""

import math
from fractions import Fraction


def entropy_inequality(counts, terms, constant, max_bits):
    total = sum(counts)
    if total == 0:
        raise ValueError("distribution must have positive total count")
    value = -float(Fraction(constant))
    for term in terms:
        if len(term["labels"]) != len(counts):
            raise ValueError("every partition must label every atom")
        bins = {}
        for count, label in zip(counts, term["labels"]):
            bins[label] = bins.get(label, 0) + count
        entropy = -math.fsum((c / total) * math.log2(c / total) for c in bins.values() if c)
        value += float(Fraction(term["coefficient"])) * entropy
    return {
        "schema_version": 1,
        "backend": "exact-entropy",
        "claim": dict(
            counts=counts,
            terms=terms,
            constant=constant,
            relation=">=",
            units="bits",
            domain="recorded-finite-distribution",
        ),
        "max_bits": max_bits,
        "diagnostic": {
            "approximate_difference_bits": value,
            "warning": "Floating diagnostic only; use the independent exact verdict.",
        },
    }
