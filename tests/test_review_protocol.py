from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "scripts" / "review_protocol.py"
SPEC = importlib.util.spec_from_file_location("review_protocol", MODULE)
assert SPEC and SPEC.loader
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class ReviewProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.case = self.root / "case.json"
        self.artifact = self.root / "proof.md"
        self.artifact.write_text("proof attempt", encoding="utf-8")
        self.case.write_text(json.dumps({
            "domain": "mathematics", "question": "Q", "contract": {"ambient_object": "Z"},
            "claims": [{"id": "C001", "statement": "P", "status": "SUPPORTED", "scope": "all"}],
            "assumptions": [], "checks": [{"id": "K001", "outcome": "CLEARED", "result": "yes"}],
            "evidence": [{"id": "E001", "locator": str(self.artifact), "role": "decisive", "summary": "proof"}],
            "decision": {"verdict": "SUPPORTED"}
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def packet(self):
        path = self.root / "packet.json"
        review.write(path, review.prepare(self.case, [self.artifact], path.parent))
        return path

    def test_packet_redacts_author_answer(self):
        packet = review.load(self.packet())
        encoded = json.dumps(packet["blinded_case"])
        self.assertNotIn("SUPPORTED", encoded)
        self.assertNotIn("decisive", encoded)
        self.assertNotIn("CLEARED", encoded)

    def test_author_modification_invalidates_adjudication(self):
        packet = self.packet()
        receipt_path = self.root / "review.json"
        review.write(receipt_path, review.submit(packet, "reviewer-7", "ACCEPT", True, [], [], [], ["author-1"], receipt_path.parent))
        self.assertEqual(review.verify_review(receipt_path)[0], [])
        case_value = json.loads(self.case.read_text(encoding="utf-8"))
        case_value["question"] = "changed after review"
        self.case.write_text(json.dumps(case_value), encoding="utf-8")
        self.assertEqual(review.verify_review(receipt_path)[0], [])
        self.assertEqual(review.adjudicate(self.case, [receipt_path], self.root)["status"], "RECONCILIATION_REQUIRED")

    def test_packet_exposes_no_author_workspace_path(self):
        packet_path = self.packet()
        encoded = packet_path.read_text(encoding="utf-8")
        self.assertNotIn(str(self.case), encoded)
        self.assertNotIn("case_file", encoded)

    def test_conflict_forces_reconciliation(self):
        packet = self.packet()
        receipt_path = self.root / "review.json"
        review.write(receipt_path, review.submit(packet, "same-person", "ACCEPT", True, [], [], [], ["same-person"], receipt_path.parent))
        result = review.adjudicate(self.case, [receipt_path], self.root)
        self.assertEqual(result["status"], "RECONCILIATION_REQUIRED")

    def test_rejection_forces_reconciliation(self):
        packet = self.packet()
        receipt_path = self.root / "review.json"
        review.write(receipt_path, review.submit(packet, "reviewer-2", "REJECT", False, ["counterexample"], [], [], ["author-1"], receipt_path.parent))
        result = review.adjudicate(self.case, [receipt_path], self.root)
        self.assertEqual(result["status"], "RECONCILIATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
