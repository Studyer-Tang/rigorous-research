from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "math_backend.py"
SPEC = importlib.util.spec_from_file_location("math_backend", MODULE_PATH)
assert SPEC and SPEC.loader
mb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mb)


class MathBackendTests(unittest.TestCase):
    def test_exact_polynomial_identity_is_decisive(self):
        result = mb.identity_certificate("(x + 1)**3", "x**3 + 3*x**2 + 3*x + 1", ["x"])
        self.assertTrue(result["identity_established"])
        self.assertEqual(result["classification"], "exact-polynomial")
        self.assertEqual(result["recommended_evidence_role"], "decisive")

    def test_rational_identity_records_exceptional_set(self):
        result = mb.identity_certificate("(x**2 - 1)/(x - 1)", "x + 1", ["x"])
        self.assertTrue(result["identity_established"])
        self.assertEqual(result["classification"], "exact-rational-on-domain")
        self.assertIn("x - 1", result["exceptional_set"])

    def test_false_identity_is_not_established(self):
        result = mb.identity_certificate("x**2", "x", ["x"])
        self.assertFalse(result["identity_established"])
        self.assertEqual(result["classification"], "not-established")

    def test_transcendental_simplification_is_only_diagnostic(self):
        result = mb.identity_certificate("sin(x)**2 + cos(x)**2", "1", ["x"], real={"x"})
        self.assertTrue(result["identity_established"])
        self.assertEqual(result["recommended_evidence_role"], "diagnostic")

    def test_lean_scan_rejects_proof_holes_and_axioms(self):
        clean = mb.lean_trust_scan("theorem add_zero (n : Nat) : n + 0 = n := by simp")
        dirty = mb.lean_trust_scan("axiom magic : False\ntheorem bad : False := by sorry")
        self.assertTrue(clean["trust_clean"])
        self.assertFalse(dirty["trust_clean"])
        self.assertEqual(dirty["axiom"], ["magic"])


if __name__ == "__main__":
    unittest.main()
