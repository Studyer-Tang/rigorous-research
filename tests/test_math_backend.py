from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "math_backend.py"
sys.path.insert(0, str(MODULE_PATH.parent))
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

    def test_cancelled_denominators_remain_domain_obligations(self):
        for lhs, rhs in (("x/x", "1"), ("0/x", "0"), ("1/x - 1/x", "0"), ("x**(-1)*x", "1")):
            with self.subTest(lhs=lhs):
                result = mb.identity_certificate(lhs, rhs, ["x"])
                self.assertTrue(result["identity_established"])
                self.assertEqual(result["classification"], "exact-rational-on-domain")
                self.assertIn("x != 0", result["domain_restrictions"])
        result = mb.identity_certificate("x/x", "y/y", ["x", "y"])
        self.assertEqual(result["domain_restrictions"], ["x != 0", "y != 0"])

    def test_cancelled_transcendental_expressions_remain_diagnostic(self):
        for lhs in ("log(x) - log(x)", "sqrt(x)**2 - x", "sin(x) - sin(x)"):
            with self.subTest(lhs=lhs):
                result = mb.identity_certificate(lhs, "0", ["x"])
                self.assertEqual(result["recommended_evidence_role"], "diagnostic")
                self.assertFalse(result["domain_analysis_complete"])
        result = mb.identity_certificate("pi*x", "0", ["x"])
        self.assertEqual(result["classification"], "not-established")

    def test_expression_parser_rejects_code_unknown_symbols_and_inexact_inputs(self):
        for lhs in ("__import__('os').getcwd()", "x.__class__", "[x]", "y + 1", "0.1*x", "x/0", "x/(x-x)", "x**1001"):
            with self.subTest(lhs=lhs), self.assertRaises(ValueError):
                mb.identity_certificate(lhs, "0", ["x"])
        with self.assertRaises(ValueError):
            mb.identity_certificate("sin", "sin", ["sin"])

    def test_matrix_retains_entry_domains_after_determinant_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matrix.json"
            path.write_text(json.dumps([["x/x", "0"], ["0", "1"]]), encoding="utf-8")
            result = mb.matrix_certificate(path, "1", ["x"])
            self.assertEqual(result["classification"], "exact-rational-on-domain")
            self.assertEqual(result["domain_restrictions"], ["x != 0"])
            path.write_text(json.dumps([["sin(x)", "sin(x)"], ["1", "1"]]), encoding="utf-8")
            result = mb.matrix_certificate(path, "0", ["x"])
            self.assertEqual(result["recommended_evidence_role"], "diagnostic")

    def test_counterexample_returns_reproducible_exact_witness(self):
        result = mb.counterexample_search("x**2", "x", ["x"], ["0", "1", "1/2"])
        self.assertEqual(result["status"], "COUNTEREXAMPLE_FOUND")
        self.assertEqual(
            result["witness"], {"assignment": {"x": "1/2"}, "lhs": "1/4", "rhs": "1/2", "difference": "-1/4"}
        )
        self.assertEqual(result["tested_points"], 3)

    def test_counterexample_respects_domain_and_assumptions(self):
        result = mb.counterexample_search("x/x", "1", ["x"], ["0", "1"])
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertEqual(result["excluded_points"], 1)
        self.assertEqual(result["tested_points"], 1)
        result = mb.counterexample_search("x**2", "x", ["x"], ["-1", "1/2", "1"], positive={"x"}, integer={"x"})
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertEqual(result["excluded_points"], 2)

    def test_counterexample_search_budget_and_empty_admissible_grid_are_inconclusive(self):
        result = mb.counterexample_search("x**2", "x", ["x"], ["0", "1", "2"], max_points=2)
        self.assertFalse(result["grid_exhausted"])
        self.assertEqual(result["status"], "INCONCLUSIVE")
        result = mb.counterexample_search("1/x", "0", ["x"], ["0"])
        self.assertEqual(result["tested_points"], 0)
        self.assertEqual(result["status"], "INCONCLUSIVE")
        with self.assertRaises(ValueError):
            mb.counterexample_search("sin(x)", "x", ["x"], ["1"])

    def test_counterexample_cli_writes_witness(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "witness.json"
            self.assertEqual(
                mb.main(
                    [
                        "sympy-counterexample",
                        "--lhs",
                        "x**2",
                        "--rhs",
                        "x",
                        "--symbols",
                        "x",
                        "--values",
                        "2",
                        "--output",
                        str(path),
                    ]
                ),
                0,
            )
            self.assertTrue(json.loads(path.read_text(encoding="utf-8"))["counterexample_found"])


if __name__ == "__main__":
    unittest.main()
