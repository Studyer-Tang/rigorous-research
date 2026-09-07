from __future__ import annotations

import copy
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import certificate_verifier as cv
import egyptian_fractions as ef
import integer_certificate_verifier as iv


class EgyptianFractionTests(unittest.TestCase):
    def test_exact_distinct_witnesses_and_independent_checker(self):
        certificate = ef.search(4, 3, 300, True)
        with (
            patch.object(ef, "search", side_effect=AssertionError("producer must not run")),
            patch.object(cv, "load_sympy", side_effect=AssertionError("integer checks need no SymPy")),
        ):
            self.assertEqual(cv.verify(certificate)["status"], "ESTABLISHED")
        for row in certificate["witnesses"]:
            n, x, y, z = (row[key] for key in ("n", "x", "y", "z"))
            self.assertLess(x, y)
            self.assertLess(y, z)
            self.assertEqual(Fraction(4, n), sum(Fraction(1, value) for value in (x, y, z)))

    def test_budget_exhaustion_is_inconclusive_and_preserves_domain(self):
        certificate = ef.search(4, 3, 100, True, max_work=1)
        self.assertEqual(certificate["budget"]["used_work"], 1)
        self.assertEqual(iv.verify(certificate)["status"], "INCONCLUSIVE")
        self.assertEqual(len(certificate["witnesses"]) + len(certificate["unresolved"]), 98)

    def test_distinct_and_repeated_denominators_are_different_claims(self):
        self.assertEqual(iv.verify(ef.search(4, 2, 2, False))["status"], "ESTABLISHED")
        self.assertEqual(iv.verify(ef.search(4, 2, 2, True))["status"], "INCONCLUSIVE")
        altered = ef.search(4, 2, 2, False)
        altered["claim"]["distinct"] = True
        self.assertEqual(iv.verify(altered)["status"], "INVALID")

    def test_forgery_gaps_duplicates_and_quantifier_changes_fail(self):
        certificate = ef.search(4, 3, 8, True)
        mutations = [
            lambda c: c["witnesses"][0].update(x=0),
            lambda c: c["witnesses"][0].update(x=True),
            lambda c: c["witnesses"][0].update(x=1.0),
            lambda c: c["witnesses"][0].update(z=13),
            lambda c: c["witnesses"].pop(),
            lambda c: c["witnesses"].append(c["witnesses"][0]),
            lambda c: c["claim"].update(stop=9),
            lambda c: c["claim"].update(quantifier="all positive integers"),
            lambda c: c.update(assumptions={"ignore_distinctness": True}),
        ]
        for index, mutate in enumerate(mutations):
            broken = copy.deepcopy(certificate)
            mutate(broken)
            with self.subTest(mutation=index):
                self.assertEqual(iv.verify(broken)["status"], "INVALID")

    def test_small_general_fractions_agree_with_exhaustive_search(self):
        # These denominators are bounded enough for an independently written enumeration.
        for a in range(1, 8):
            for n in range(1, 8):
                target = Fraction(a, n)
                found = False
                for x in range(1, 3 * n // a + 1):
                    residual = target - Fraction(1, x)
                    if residual <= 0:
                        continue
                    for y in range(x, 2 * residual.denominator // residual.numerator + 1):
                        last = residual - Fraction(1, y)
                        if last > 0 and last.numerator == 1 and last.denominator >= y:
                            found = True
                with self.subTest(a=a, n=n):
                    self.assertEqual(bool(ef.search(a, n, n, False)["witnesses"]), found)

    def test_greedy_first_denominator_fails_at_49_but_conjecture_does_not(self):
        self.assertIsNone(ef.completion(4, 49, 13, True, ef.Budget(10000)))
        result = ef.search(4, 49, 49, True)
        self.assertEqual(iv.verify(result)["status"], "ESTABLISHED")
        self.assertEqual(result["witnesses"][0]["x"], 14)

    def test_invalid_limits_are_rejected(self):
        for kwargs in ({"max_work": 0}, {"max_x": -1}, {"max_work": True}):
            with self.assertRaises(ValueError):
                ef.search(4, 3, 10, True, **kwargs)
        with self.assertRaises(ValueError):
            ef.search(4, 1, 10001, True)


class ModularObstructionTests(unittest.TestCase):
    def certificate(self):
        return {
            "schema_version": 1,
            "backend": "exact-integer",
            "backend_version": "1",
            "operation": "two-unit-fractions-obstruction",
            "claim": {"numerator": 4, "denominator": 49, "first_denominator": 13},
            "denominator_factorization": [{"prime": 7, "exponent": 2}, {"prime": 13, "exponent": 1}],
        }

    def test_obstruction_is_exact_and_scoped_to_fixed_denominator(self):
        result = iv.verify(self.certificate())
        self.assertEqual(result["status"], "ESTABLISHED")
        self.assertIn("fixed-first-denominator", result["scope"])

    def test_composite_factors_incomplete_products_and_changed_claims_fail(self):
        for mode in ("composite", "incomplete", "changed"):
            certificate = self.certificate()
            if mode == "composite":
                certificate["denominator_factorization"][0] = {"prime": 49, "exponent": 1}
            elif mode == "incomplete":
                certificate["denominator_factorization"].pop()
            else:
                certificate["claim"]["first_denominator"] = 14
            with self.subTest(mode=mode):
                self.assertEqual(iv.verify(certificate)["status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
