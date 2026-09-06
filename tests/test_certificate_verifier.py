from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import certificate_verifier as cv
import math_backend as mb


class CertificateVerifierTests(unittest.TestCase):
    def test_identity_is_recomputed_without_calling_the_producer(self):
        certificate = mb.identity_certificate("(x+1)**2", "x**2+2*x+1", ["x"])
        with patch.object(mb, "identity_certificate", side_effect=AssertionError("producer must not run")):
            self.assertEqual(cv.verify(certificate)["status"], "ESTABLISHED")
        certificate["claim"]["rhs"] = "x**2+2*x+2"
        self.assertEqual(cv.verify(certificate)["status"], "INVALID")

    def test_missing_domain_exclusions_cannot_be_hidden_by_cancellation(self):
        certificate = mb.identity_certificate("x/x", "1", ["x"])
        self.assertEqual(cv.verify(certificate)["status"], "ESTABLISHED")
        certificate["domain_restrictions"] = []
        self.assertEqual(cv.verify(certificate)["status"], "INVALID")

    def test_witness_must_satisfy_assumptions_and_exact_values(self):
        certificate = mb.counterexample_search("x**2", "x", ["x"], ["-1/2"])
        self.assertEqual(cv.verify(certificate)["status"], "REFUTED")
        certificate["assumptions"]["positive"] = ["x"]
        self.assertEqual(cv.verify(certificate)["status"], "INVALID")
        certificate["assumptions"]["positive"] = []
        certificate["witness"]["lhs"] = "3/4"
        self.assertEqual(cv.verify(certificate)["status"], "INVALID")

    def test_out_of_domain_witness_is_rejected(self):
        certificate = mb.counterexample_search("1/x", "0", ["x"], ["1"])
        certificate["witness"]["assignment"]["x"] = "0"
        self.assertEqual(cv.verify(certificate)["status"], "INVALID")

    def test_bernstein_reconstruction_and_partition_are_independent(self):
        certificate = mb.polynomial_bound_certificate("x**2", "0", "x", "-1", "1", 1)
        with patch.object(mb, "polynomial_bound_certificate", side_effect=AssertionError("producer must not run")):
            self.assertEqual(cv.verify(certificate)["status"], "ESTABLISHED")
        for mutation in ("coefficients", "gap", "overlap", "truncated", "claim"):
            broken = copy.deepcopy(certificate)
            if mutation == "coefficients":
                broken["certified_intervals"][0]["bernstein_coefficients"] = ["1", "1", "1"]
            elif mutation == "gap":
                broken["certified_intervals"][1]["lower"] = "1/2"
            elif mutation == "overlap":
                broken["certified_intervals"][1]["lower"] = "-1/2"
            elif mutation == "truncated":
                broken["certified_intervals"].pop()
            else:
                broken["claim"]["lhs"] = "x**2-1"
            with self.subTest(mutation=mutation):
                self.assertEqual(cv.verify(broken)["status"], "INVALID")

    def test_inconclusive_bound_is_never_promoted(self):
        certificate = mb.polynomial_bound_certificate("x**2", "0", "x", "-1", "1", 0)
        self.assertEqual(cv.verify(certificate)["status"], "INCONCLUSIVE")

    def test_bound_witness_is_checked_against_original_interval(self):
        certificate = mb.polynomial_bound_certificate("x*(1-x)", "0", "x", "0", "2")
        self.assertEqual(cv.verify(certificate)["status"], "REFUTED")
        certificate["claim"]["upper"] = "1"
        self.assertEqual(cv.verify(certificate)["status"], "INVALID")

    def test_matrix_claim_requires_original_input_and_recomputation(self):
        with tempfile.TemporaryDirectory() as directory:
            matrix = Path(directory) / "matrix.json"
            matrix.write_text(json.dumps([["x", "1"], ["1", "x"]]), encoding="utf-8")
            certificate = mb.matrix_certificate(matrix, "x**2-1", ["x"])
            self.assertEqual(cv.verify(certificate)["status"], "INVALID")
            self.assertEqual(cv.verify(certificate, [matrix])["status"], "ESTABLISHED")
            certificate["claim"].update(lhs="0", rhs="0")
            self.assertEqual(cv.verify(certificate, [matrix])["status"], "INVALID")

    def test_hand_written_trust_flags_are_not_proof(self):
        certificate = {
            "schema_version": 1,
            "backend": "sympy",
            "identity_established": True,
            "recommended_evidence_role": "decisive",
        }
        self.assertEqual(cv.verify(certificate)["status"], "INVALID")

    def test_unrecognized_claim_semantics_are_not_silently_ignored(self):
        certificate = mb.identity_certificate("x", "x", ["x"])
        certificate["claim"]["relation"] = "<"
        self.assertEqual(cv.verify(certificate)["status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
