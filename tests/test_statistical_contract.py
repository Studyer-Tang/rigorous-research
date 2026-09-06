from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import statistical_contract as sc
from research_io import sha256


class StatisticalContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "design.txt"
        self.source.write_text(
            "Recorded theorem/design argument for a test fixture; not a data-derived proof.", encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def justified(self, method):
        contract = sc.template(method, "C001")
        contract["target"] = "population mean or testing family specified by this fixture"
        for row in contract["conditions"].values():
            row.update(
                status="JUSTIFIED",
                basis="theorem",
                statement="Explicit fixture condition",
                evidence_file="design.txt",
                evidence_sha256=sha256(self.source),
            )
        return contract

    def test_asymptotic_theorem_cannot_become_finite_sample_guarantee(self):
        contract = self.justified("newey-west-mean")
        self.assertTrue(sc.audit(contract, self.root)["applicable"])
        contract["guarantee"] = "finite-sample"
        self.assertFalse(sc.audit(contract, self.root)["applicable"])

    def test_simulation_does_not_discharge_theorem_conditions(self):
        contract = self.justified("iid-mean-clt")
        contract["conditions"]["finite_positive_variance"]["basis"] = "simulation"
        self.assertFalse(sc.audit(contract, self.root)["applicable"])

    def test_selection_dependence_and_unknown_conditions_are_exposed(self):
        for method, key in (
            ("iid-mean-clt", "no_outcome_selection"),
            ("bh", "independence_or_prds"),
            ("holm", "prespecified_family"),
        ):
            for status in ("UNTESTED", "CONDITIONAL", "VIOLATED"):
                with self.subTest(method=method, status=status):
                    contract = self.justified(method)
                    contract["conditions"][key]["status"] = status
                    report = sc.audit(contract, self.root)
                    self.assertFalse(report["applicable"])
                    self.assertIn(key, report["unresolved_conditions"] + report["violated_conditions"])
                    self.assertNotEqual(report["status"], "REFUTED")

    def test_unchanged_hash_is_required(self):
        contract = self.justified("student-t-mean")
        self.source.write_text("revised after review", encoding="utf-8")
        self.assertFalse(sc.audit(contract, self.root)["applicable"])

    def test_missing_condition_is_not_assumed_true(self):
        contract = self.justified("newey-west-mean")
        del contract["conditions"]["bandwidth_sequence"]
        self.assertIn("bandwidth_sequence", sc.audit(contract, self.root)["unresolved_conditions"])


if __name__ == "__main__":
    unittest.main()
