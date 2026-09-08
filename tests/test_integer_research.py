"""Adversarial and independent checks for the research-driven integer tools."""

import copy
import json
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from integer_certificate_verifier import verify
from integer_research import family, scan, window
from research_agent import Study


class IntegerResearchTests(unittest.TestCase):
    def test_live_research_counterexamples_do_not_refute_original_existence(self):
        for n, rejected_width, first_success in [(1129, 2, 285), (1201, 5, 306), (246241, 9, 61570)]:
            first = n // 4 + 1
            self.assertEqual(
                verify(window(4, n, first, first + rejected_width - 1, True, 1000000))["status"], "REFUTED"
            )
            self.assertEqual(verify(window(4, n, first_success, first_success, True, 1000000))["status"], "ESTABLISHED")

    def test_scan_partial_budget_and_changed_domain(self):
        good = scan(4, 25, 97, 24, 1, True, 100000)
        self.assertEqual(verify(good)["status"], "REFUTED")
        self.assertEqual(len(good["windows"]), 2)
        self.assertEqual(verify(scan(4, 25, 97, 24, 1, True, 1))["status"], "INCONCLUSIVE")
        self.assertEqual(verify(scan(4, 25, 97, 24, 2, True, 100000))["status"], "ESTABLISHED")
        bad = copy.deepcopy(good)
        bad["windows"][1]["claim"]["denominator"] = 73
        self.assertEqual(verify(bad)["status"], "INVALID")
        bad = copy.deepcopy(good)
        bad["windows"].pop(0)
        self.assertEqual(verify(bad)["status"], "INVALID")
        good["windows"].pop()
        self.assertEqual(verify(good)["status"], "INCONCLUSIVE")

    def test_windows_agree_with_independent_denominator_enumeration(self):
        for n in range(3, 100):
            first = n // 4 + 1
            expected = False
            for x in range(first, first + 3):
                r = Fraction(4, n) - Fraction(1, x)
                if r <= 0:
                    continue
                for y in range(x + 1, (2 * r.denominator) // r.numerator + 1):
                    s = r - Fraction(1, y)
                    if s > 0 and s.numerator == 1 and s.denominator > y:
                        expected = True
            result = verify(window(4, n, first, first + 2, True, 100000))
            self.assertEqual(result["status"], "ESTABLISHED" if expected else "REFUTED", (n, result))

    def test_exhaustion_does_not_become_a_refutation(self):
        certificate = window(4, 49, 13, 14, True, 1)
        self.assertEqual(verify(certificate)["status"], "INCONCLUSIVE")
        self.assertEqual(verify(window(4, 49, 13, 13, True, 10000))["status"], "REFUTED")
        self.assertEqual(verify(window(4, 49, 14, 14, True, 10000))["status"], "ESTABLISHED")

    def test_window_tampering_and_invalid_factorizations(self):
        good = window(4, 49, 13, 13, True, 10000)
        for mutate in (
            lambda c: c["entries"].clear(),
            lambda c: c["claim"].update(stop_x=14),
            lambda c: c["claim"].update(denominator=True),
            lambda c: c["entries"][0].update(factorization=[[7, 1]]),
            lambda c: c["entries"][0].update(factorization=[[49, 1], [13, 1]]),
            lambda c: c["entries"][0].update(outcome="nonpositive-residual"),
        ):
            bad = copy.deepcopy(good)
            mutate(bad)
            self.assertEqual(verify(bad)["status"], "INVALID", bad)
        bad = window(4, 49, 14, 14, True, 10000)
        bad["entries"][0]["z"] += 1
        self.assertEqual(verify(bad)["status"], "INVALID")
        # b=98 has a genuine completion; forged complete factors must not certify obstruction.
        bad["entries"][0] = {"x": 14, "outcome": "obstructed", "factorization": [[2, 1], [7, 2]]}
        self.assertEqual(verify(bad)["status"], "INVALID")

    def test_universal_family_and_coefficient_mutations(self):
        good = family(4, [97, 120], [25, 30], [970, 2364, 1440], [4850, 11820, 7200], True)
        self.assertEqual(verify(good)["status"], "ESTABLISHED")
        bad = copy.deepcopy(good)
        bad["claim"]["y"][1] += 1
        self.assertEqual(verify(bad)["status"], "INCONCLUSIVE")
        bad["counterexample_parameter"] = 1
        self.assertEqual(verify(bad)["status"], "REFUTED")
        good["counterexample_parameter"] = 0
        self.assertEqual(verify(good)["status"], "INVALID")

    def test_unsupported_positivity_and_distinctness_are_not_promoted(self):
        # All denominators are positive multiples of (t-1)^2+1, but coefficient positivity cannot prove it.
        c = family(4, [12, -12, 6], [6, -6, 3], [8, -8, 4], [24, -24, 12], True)
        self.assertIsNone(c["counterexample_parameter"])
        c["identity_zero"] = c["nonnegative_coefficients"] = True
        self.assertEqual(verify(c)["status"], "INCONCLUSIVE")
        self.assertEqual(verify(family(4, [2], [1], [2], [2], False))["status"], "ESTABLISHED")
        self.assertEqual(verify(family(4, [2], [1], [2], [2], True))["status"], "REFUTED")

    def test_agent_tools_contract_and_original_goal_separation(self):
        args = dict(numerator=4, denominator=49, start_x=13, stop_x=13, distinct=True, max_work=10000)
        with tempfile.TemporaryDirectory() as directory:
            study = Study.create(
                directory,
                "integer",
                "Original universal conjecture",
                machine_contract={"tool": "egyptian_window", "arguments": args, "status": "REFUTED"},
            )
            result = study.submit(
                {
                    "action": {"tool": "egyptian_window", "arguments": args},
                    "rationale": "Test one restricted route",
                    "falsifier": "An ordered completion",
                    "evidence": [],
                },
                0,
            )
            self.assertEqual(result["result"]["independent_check"]["status"], "REFUTED")
            self.assertIn("integer_research_verifier.py", result["result"]["toolchain_sha256"])
            self.assertEqual(study.state()["machine_contract_status"], "MET")
            self.assertEqual(study.state()["objective_status"], "UNRESOLVED")
            result = study.submit(
                {
                    "action": {
                        "tool": "egyptian",
                        "arguments": dict(numerator=4, start=49, stop=49, distinct=True, max_x=64, max_work=10000),
                    },
                    "rationale": "Try another first denominator",
                    "falsifier": "No valid witness",
                    "evidence": [1],
                },
                1,
            )
            self.assertEqual(result["result"]["status"], "ESTABLISHED")

    def test_context_exposes_changed_obligations_without_accepting_them(self):
        with tempfile.TemporaryDirectory() as directory:
            study = Study.create(directory, "context", "Original goal")
            first = study.context()["research_memory"]["case.json"]
            path = study.directory / "case.json"
            case = json.loads(path.read_text())
            case["proof_obligations"][0]["statement"] = "A new translation obligation remains open."
            path.write_text(json.dumps(case), encoding="utf-8")
            second = study.context()["research_memory"]["case.json"]
            self.assertNotEqual(first["sha256"], second["sha256"])
            self.assertIn("new translation", second["content"]["proof_obligations"][0]["statement"])
            self.assertEqual(study.state()["objective_status"], "UNRESOLVED")
            path.write_text("[]", encoding="utf-8")
            self.assertIn("error", study.context()["research_memory"]["case.json"])


if __name__ == "__main__":
    unittest.main()
