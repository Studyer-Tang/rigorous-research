from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "inference_case.py"
SPEC = importlib.util.spec_from_file_location("inference_case", MODULE_PATH)
assert SPEC and SPEC.loader
ic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ic)


class InferenceCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def case(self, domain: str = "mathematics"):
        path = ic.initialize(self.root, f"case-{domain}", domain, "What is supported?", "The scoped claim holds.")
        _, data = ic.load_case(path)
        return path, data

    @staticmethod
    def fill_contract(data):
        for field in ic.CONTRACT_FIELDS[data["domain"]]:
            data["contract"][field] = f"specified {field}"

    @staticmethod
    def evidence(data, *, independent=False, kind="derivation"):
        item_id = ic.next_id(data["evidence"], "E")
        data["evidence"].append(
            {
                "id": item_id,
                "kind": kind,
                "summary": f"evidence for {item_id}",
                "locator": f"memory://{item_id}",
                "sha256": None,
                "independent": independent,
            }
        )
        return item_id

    def support_case(self, domain: str):
        path, data = self.case(domain)
        self.fill_contract(data)
        assumption_evidence = self.evidence(data, kind="source")
        data["assumptions"].append(
            {
                "id": "A001",
                "statement": "The stated regularity condition holds.",
                "role": "scope",
                "status": "JUSTIFIED",
                "evidence_ids": [assumption_evidence],
            }
        )
        data["claims"][0]["assumption_ids"] = ["A001"]
        decisive = self.evidence(data, independent=True)
        for index, kind in enumerate(ic.REQUIRED_CHECKS[domain], start=1):
            check_evidence = decisive if index == 1 else self.evidence(data, kind="diagnostic")
            data["checks"].append(
                {
                    "id": f"K{index:03d}",
                    "target_claim": "C001",
                    "kind": kind,
                    "target": f"required property {kind}",
                    "falsifier": f"a documented failure of {kind}",
                    "outcome": "CLEARED",
                    "evidence_ids": [check_evidence],
                }
            )
        data["claims"][0]["status"] = "SUPPORTED"
        data["claims"][0]["evidence_ids"] = [decisive]
        data["decision"] = {
            "verdict": "SUPPORTED",
            "claim_id": "C001",
            "reason": "Every required domain check is cleared.",
            "evidence_ids": [decisive],
            "limitations": "The conclusion is conditional on A001.",
        }
        return path, data

    def test_init_builds_domain_specific_contract(self):
        path, data = self.case("finance")
        self.assertTrue(path.is_file())
        self.assertEqual(tuple(data["contract"]), ic.CONTRACT_FIELDS["finance"])
        self.assertEqual(data["claims"][0]["id"], "C001")

    def test_nonrelease_validation_allows_open_work(self):
        path, data = self.case()
        errors, _ = ic.validate_case(data, path)
        self.assertEqual(errors, [])

    def test_release_rejects_blank_contract(self):
        path, data = self.case()
        data["decision"]["verdict"] = "INCONCLUSIVE"
        data["decision"]["reason"] = "Initial evidence only."
        data["decision"]["limitations"] = "No proof yet."
        evidence = self.evidence(data)
        data["decision"]["evidence_ids"] = [evidence]
        data["claims"][0]["status"] = "INCONCLUSIVE"
        errors, _ = ic.validate_case(data, path, release=True)
        self.assertTrue(any("contract fields" in error for error in errors))

    def test_supported_mathematics_passes_release_gate(self):
        path, data = self.support_case("mathematics")
        errors, _ = ic.validate_case(data, path, release=True)
        self.assertEqual(errors, [])

    def test_supported_statistics_passes_release_gate(self):
        path, data = self.support_case("statistics")
        errors, _ = ic.validate_case(data, path, release=True)
        self.assertEqual(errors, [])

    def test_supported_finance_passes_release_gate(self):
        path, data = self.support_case("finance")
        errors, _ = ic.validate_case(data, path, release=True)
        self.assertEqual(errors, [])

    def test_statistics_gate_names_missing_sensitivity(self):
        path, data = self.support_case("statistics")
        data["checks"] = [item for item in data["checks"] if item["kind"] != "sensitivity"]
        errors, _ = ic.validate_case(data, path, release=True)
        self.assertTrue(any("sensitivity" in error for error in errors))

    def test_finance_gate_rejects_unmodeled_costs(self):
        path, data = self.support_case("finance")
        data["contract"]["cost_model"] = ""
        data["checks"] = [item for item in data["checks"] if item["kind"] != "cost"]
        errors, _ = ic.validate_case(data, path, release=True)
        joined = "\n".join(errors)
        self.assertIn("cost_model", joined)
        self.assertIn("cost", joined)

    def test_refutation_requires_triggered_falsifier(self):
        path, data = self.case()
        self.fill_contract(data)
        evidence = self.evidence(data, kind="counterexample")
        data["claims"][0]["status"] = "REFUTED"
        data["decision"] = {
            "verdict": "REFUTED",
            "claim_id": "C001",
            "reason": "A witness defeats the universal statement.",
            "evidence_ids": [evidence],
            "limitations": "Restricted variants remain open.",
        }
        errors, _ = ic.validate_case(data, path, release=True)
        self.assertTrue(any("triggered falsifier" in error for error in errors))
        data["checks"].append(
            {
                "id": "K001",
                "target_claim": "C001",
                "kind": "counterexample",
                "target": "universal quantifier",
                "falsifier": "one valid witness",
                "outcome": "TRIGGERED",
                "evidence_ids": [evidence],
            }
        )
        errors, _ = ic.validate_case(data, path, release=True)
        self.assertEqual(errors, [])

    def test_supported_claim_rejects_violated_assumption(self):
        path, data = self.support_case("mathematics")
        data["assumptions"][0]["status"] = "VIOLATED"
        errors, _ = ic.validate_case(data, path, release=True)
        self.assertTrue(any("violated assumptions" in error for error in errors))

    def test_checksum_tampering_is_detected(self):
        path, data = self.case()
        artifact = path.parent / "artifacts" / "result.txt"
        artifact.write_text("first", encoding="utf-8")
        data["evidence"].append(
            {
                "id": "E001",
                "kind": "exact-computation",
                "summary": "an exact result",
                "locator": "artifacts/result.txt",
                "sha256": ic.sha256(artifact),
                "independent": False,
            }
        )
        artifact.write_text("changed", encoding="utf-8")
        errors, _ = ic.validate_case(data, path)
        self.assertTrue(any("checksum mismatch" in error for error in errors))

    def test_wrong_domain_check_is_rejected(self):
        path, data = self.case("statistics")
        data["checks"].append(
            {
                "id": "K001",
                "target_claim": "C001",
                "kind": "cost",
                "target": "fees",
                "falsifier": "large costs",
                "outcome": "OPEN",
                "evidence_ids": [],
            }
        )
        errors, _ = ic.validate_case(data, path)
        self.assertTrue(any("invalid for statistics" in error for error in errors))

    def test_report_exposes_contract_and_falsifiers(self):
        _, data = self.support_case("finance")
        report = ic.render(data)
        self.assertIn("## Domain contract", report)
        self.assertIn("## Assumption surface", report)
        self.assertIn("## Falsification checks", report)
        self.assertIn("walk-forward", report)

    def test_cli_init_and_contract_mutation(self):
        result = ic.main(
            [
                "init",
                str(self.root),
                "cli-case",
                "--domain",
                "mathematics",
                "--question",
                "Does it vanish?",
                "--claim",
                "It does not vanish.",
            ]
        )
        self.assertEqual(result, 0)
        case_path = self.root / "cli-case" / "case.json"
        result = ic.main(["set-contract", str(case_path), "--field", "ambient_object", "--value", "A quotient algebra"])
        self.assertEqual(result, 0)
        _, data = ic.load_case(case_path)
        self.assertEqual(data["contract"]["ambient_object"], "A quotient algebra")

    def test_assumptions_bind_to_an_explicit_claim(self):
        path, data = self.case()
        data["claims"].append(
            {
                "id": "C002",
                "statement": "A restricted claim holds.",
                "scope": "finite level",
                "status": "OPEN",
                "assumption_ids": [],
                "evidence_ids": [],
            }
        )
        data["assumptions"].append(
            {
                "id": "A001",
                "statement": "The transition map is injective.",
                "role": "persistence",
                "status": "CONDITIONAL",
                "evidence_ids": [],
            }
        )
        ic.atomic_json(path, data)
        result = ic.main(["use-assumption", str(path), "--claim", "C002", "--assumption", "A001"])
        self.assertEqual(result, 0)
        _, updated = ic.load_case(path)
        self.assertEqual(updated["claims"][1]["assumption_ids"], ["A001"])
        self.assertEqual(updated["claims"][0]["assumption_ids"], [])


if __name__ == "__main__":
    unittest.main()
