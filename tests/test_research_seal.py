from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "scripts" / "research_seal.py"
SPEC = importlib.util.spec_from_file_location("research_seal", MODULE)
assert SPEC and SPEC.loader
seal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seal)


class ResearchSealTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def plan(self) -> Path:
        path = self.root / "plan.json"
        path.write_text(json.dumps({field: f"fixed {field}" for field in seal.PLAN_FIELDS}), encoding="utf-8")
        return path

    def test_plan_mutation_invalidates_seal(self):
        plan = self.plan()
        seal_path = self.root / "seal.json"
        seal.write_json(seal_path, seal.seal_plan(plan, "confirmatory-v1", seal_path.parent))
        self.assertEqual(seal.verify_plan(seal_path)[0], [])
        value = json.loads(plan.read_text(encoding="utf-8"))
        value["sample_window"] = "changed after results"
        plan.write_text(json.dumps(value), encoding="utf-8")
        self.assertTrue(any("changed" in error for error in seal.verify_plan(seal_path)[0]))

    def test_input_or_lock_mutation_invalidates_receipt(self):
        source = self.root / "claim.txt"
        output = self.root / "certificate.json"
        lock = self.root / "requirements.txt"
        source.write_text("x*(x+1)=x^2+x", encoding="utf-8")
        output.write_text(
            '{"backend":"sympy","backend_version":"1.14.0","identity_established":true,"recommended_evidence_role":"decisive"}',
            encoding="utf-8",
        )
        lock.write_text("sympy==1.14.0", encoding="utf-8")
        receipt_path = self.root / "receipt.json"
        receipt = seal.make_receipt(
            [source], [output], [lock], command="verify claim", backend="sympy", backend_version="1.14.0",
            semantic_domain="Q[x]", returncode=0, result="ESTABLISHED", base_dir=receipt_path.parent
        )
        seal.write_json(receipt_path, receipt)
        self.assertEqual(seal.verify_receipt(receipt_path, True)[0], [])
        lock.write_text("sympy==1.15.0", encoding="utf-8")
        self.assertTrue(any("changed" in error for error in seal.verify_receipt(receipt_path, True)[0]))

    def test_false_or_failed_result_is_not_established(self):
        source = self.root / "claim.txt"
        output = self.root / "certificate.json"
        source.write_text("1=0 in Z", encoding="utf-8")
        output.write_text(
            '{"backend":"sympy","backend_version":"1.14.0","identity_established":false,"recommended_evidence_role":"diagnostic"}',
            encoding="utf-8",
        )
        receipt_path = self.root / "receipt.json"
        receipt = seal.make_receipt(
            [source], [output], [], command="verify false claim", backend="sympy", backend_version="1.14.0",
            semantic_domain="Z", returncode=1, result="NOT_ESTABLISHED", base_dir=receipt_path.parent
        )
        seal.write_json(receipt_path, receipt)
        self.assertTrue(any("does not establish" in error for error in seal.verify_receipt(receipt_path, True)[0]))


if __name__ == "__main__":
    unittest.main()
