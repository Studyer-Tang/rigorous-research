from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import inference_case as ic
import math_backend as mb
import proof_contracts as pc
from research_io import write_json


class ProofContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = ic.initialize(self.root, "proof", "mathematics", "A question", "A scoped claim")
        _, self.case = ic.load_case(self.path)
        artifact = self.path.parent / "review.txt"
        artifact.write_text("Human-reviewed argument fixture", encoding="utf-8")
        self.evidence = {
            "id": "E001",
            "locator": "review.txt",
            "sha256": ic.sha256(artifact),
            "kind": "derivation",
            "role": "decisive",
        }
        self.case["evidence"] = [self.evidence]

    def tearDown(self):
        self.temp.cleanup()

    def review(self, node):
        node["resolution"] = {
            "method": "review",
            "reviewer_id": "fixture-reviewer",
            "note": "Reviewed the full stated argument.",
            "evidence_id": "E001",
            "binding": pc.review_binding(self.case, node, self.evidence),
        }

    def test_dependence_on_an_open_step_blocks_a_reviewed_conclusion(self):
        self.review(self.case["proof_obligations"][1])
        result = pc.evaluate(self.case, self.path.parent)
        self.assertEqual(result["states"], {"P001": "OPEN", "P002": "BLOCKED"})

    def test_review_invalidates_when_the_claim_or_scope_changes(self):
        node = self.case["proof_obligations"][0]
        self.review(node)
        self.assertEqual(pc.evaluate(self.case, self.path.parent)["states"]["P001"], "REVIEWED")
        self.case["claims"][0]["scope"] = "now for all real values"
        self.assertEqual(pc.evaluate(self.case, self.path.parent)["states"]["P001"], "INVALID")

    def test_circular_proof_is_rejected(self):
        self.case["proof_obligations"][0]["depends_on"] = ["P002"]
        self.assertIn("cycle", " ".join(pc.evaluate(self.case, self.path.parent)["errors"]))

    def test_changed_dependency_invalidates_existing_reviews(self):
        for node in self.case["proof_obligations"]:
            self.review(node)
        self.case["proof_obligations"][0]["statement"] = "Changed translation and domain"
        self.assertEqual(pc.evaluate(self.case, self.path.parent)["states"]["P002"], "INVALID")

    def test_machine_resolution_checks_formula_and_assumptions(self):
        certificate = mb.identity_certificate("x/x", "1", ["x"])
        artifact = self.path.parent / "certificate.json"
        write_json(artifact, certificate)
        evidence = {"id": "E002", "locator": "certificate.json", "sha256": ic.sha256(artifact)}
        self.case["evidence"].append(evidence)
        node = self.case["proof_obligations"][1]
        node.update(
            certificate_claim=deepcopy(certificate["claim"]),
            certificate_assumptions=deepcopy(certificate["assumptions"]),
        )
        self.review(self.case["proof_obligations"][0])
        node["resolution"] = {
            "method": "certificate",
            "evidence_id": "E002",
            "binding": pc.review_binding(self.case, node, evidence),
        }
        self.assertEqual(pc.evaluate(self.case, self.path.parent)["states"]["P002"], "MACHINE_VERIFIED")
        certificate["assumptions"]["positive"] = ["x"]
        write_json(artifact, certificate)
        evidence["sha256"] = ic.sha256(artifact)
        node["resolution"]["binding"] = pc.review_binding(self.case, node, evidence)
        self.assertEqual(pc.evaluate(self.case, self.path.parent)["states"]["P002"], "INVALID")

    def test_hidden_division_opens_nonzero_obligation_and_attack(self):
        node = self.case["proof_obligations"][1]
        node["operation"] = "division"
        result = pc.evaluate(self.case, self.path.parent)
        self.assertTrue(any("nonzero" in error for error in result["errors"]))
        self.assertEqual(result["falsification_tasks"][0]["check"], "nonzero")

    def test_finite_checks_cannot_close_a_general_proof(self):
        node = self.case["proof_obligations"][0]
        node["kind"] = "finite-check"
        self.review(node)
        self.assertEqual(pc.evaluate(self.case, self.path.parent)["states"]["P001"], "PARTIAL")

    def test_case_release_requires_translation_and_goal_obligations(self):
        self.case["proof_obligations"] = []
        self.case["decision"].update(verdict="SUPPORTED", claim_id="C001")
        errors = pc.release_errors(self.case, pc.evaluate(self.case, self.path.parent))
        self.assertTrue(any("translation" in error for error in errors))
        self.assertTrue(any("proof obligation" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
