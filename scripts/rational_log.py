"""Outward rational enclosures for natural logarithms; no floating arithmetic."""

from fractions import Fraction

SCALE = 10**24


def outward(lower, upper):
    a, b = lower * SCALE, upper * SCALE
    return Fraction(a.numerator // a.denominator, SCALE), Fraction(-((-b.numerator) // b.denominator), SCALE)


def _series(value, terms):
    z = (value - 1) / (value + 1)
    square, power, total = z * z, z, Fraction(0)
    for index in range(terms):
        total += power / (2 * index + 1)
        power *= square
    lower = 2 * total
    tail = 2 * power / ((2 * terms + 1) * (1 - square))
    return outward(lower, lower + tail)


def log_bounds(value, terms=16):
    value = Fraction(value)
    if value <= 0 or type(terms) is not int or not 1 <= terms <= 24:
        raise ValueError("positive rational and 1–24 series terms required")
    if max(value.numerator.bit_length(), value.denominator.bit_length()) > 1024:
        raise ValueError("log input exceeds bit limit")
    k = value.numerator.bit_length() - value.denominator.bit_length()
    power = Fraction(2**k) if k >= 0 else Fraction(1, 2 ** (-k))
    if value < power:
        k, power = k - 1, power / 2
    reduced = value / power
    low, high = _series(reduced, terms)
    a, b = _series(Fraction(2), terms)
    return outward(low + k * (a if k >= 0 else b), high + k * (b if k >= 0 else a))


def entropy_bounds(probabilities):
    low = high = Fraction(0)
    if any(p < 0 for p in probabilities) or sum(probabilities) != 1:
        raise ValueError("entropy probabilities must be nonnegative and sum exactly to one")
    for p in probabilities:
        if p:
            a, b = log_bounds(p)
            low, high = outward(low - p * b, high - p * a)
    return low, high
