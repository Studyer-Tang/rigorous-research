"""Adversarial finite entropy comparisons and retrieval failure semantics."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from certificate_verifier import verify
from entropy_research import entropy_inequality
from research_agent.core import Study
from research_agent.worker import produce


def difference(counts, first, second, budget=500000):
    return entropy_inequality(
        counts, [{"coefficient": "1", "labels": first}, {"coefficient": "-1", "labels": second}], "0", budget
    )


class EntropyTests(unittest.TestCase):
    def test_independent_bernoulli_union_loses_entropy_at_two_fifths(self):
        certificate = difference([9, 6, 6, 4], [0, 1, 1, 1], [0, 0, 1, 1])
        result = verify(certificate)
        self.assertEqual(result["status"], "REFUTED")
        self.assertEqual(result["computation"]["sign"], -1)
        certificate["diagnostic"]["approximate_difference_bits"] = 1000
        self.assertEqual(verify(certificate)["status"], "REFUTED")

    def test_same_marginals_different_coupling_can_gain_entropy(self):
        certificate = difference([5, 1, 1, 3], [0, 1, 1, 1], [0, 0, 1, 1])
        self.assertEqual(verify(certificate)["status"], "ESTABLISHED")
        # Equal input entropies are checked exactly; equality alone does not prove equal marginals.
        certificate = difference([5, 1, 1, 3], [0, 1, 0, 1], [0, 0, 1, 1])
        self.assertEqual(verify(certificate)["computation"]["sign"], 0)

    def test_zero_mass_singleton_and_rational_weights(self):
        for counts, constant in [([0, 7], "0"), ([3, 3], "1/3")]:
            certificate = entropy_inequality(counts, [{"coefficient": "1/3", "labels": [0, 1]}], constant, 500000)
            self.assertEqual(verify(certificate)["computation"]["sign"], 0)

    def test_subadditivity_keeps_joint_atom_mapping(self):
        certificate = entropy_inequality(
            [1, 2, 3, 4],
            [
                {"coefficient": "1", "labels": [0, 0, 1, 1]},
                {"coefficient": "1", "labels": [0, 1, 0, 1]},
                {"coefficient": "-1", "labels": [0, 1, 2, 3]},
            ],
            "0",
            500000,
        )
        self.assertEqual(verify(certificate)["status"], "ESTABLISHED")
        certificate["claim"]["terms"][0]["labels"] = [0, 0, 0, 0]
        self.assertEqual(verify(certificate)["status"], "REFUTED")

    def test_changed_scope_malformed_counts_and_partitions_are_invalid(self):
        base = difference([9, 6, 6, 4], [0, 1, 1, 1], [0, 0, 1, 1])
        for key, value in [
            ("domain", "all-distributions"),
            ("units", "nats"),
            ("relation", ">"),
            ("counts", [0, 0, 0, 0]),
            ("counts", [True, 1, 2, 3]),
        ]:
            bad = copy.deepcopy(base)
            bad["claim"][key] = value
            self.assertEqual(verify(bad)["status"], "INVALID")
        for labels in [[0], [0, 1, 2, True], [0, 1, 2, -1]]:
            bad = copy.deepcopy(base)
            bad["claim"]["terms"][0]["labels"] = labels
            self.assertEqual(verify(bad)["status"], "INVALID")
        base["claim"]["constant"] = "0.1"
        self.assertEqual(verify(base)["status"], "INVALID")

    def test_budget_exhaustion_and_zero_constant_identity(self):
        certificate = difference([999983, 17], [0, 1], [0, 0], 1000)
        self.assertEqual(verify(certificate)["status"], "INCONCLUSIVE")
        certificate = entropy_inequality([1], [{"coefficient": "0", "labels": [0]}], "-1/7", 1000)
        self.assertEqual(verify(certificate)["status"], "ESTABLISHED")
        certificate["claim"]["constant"] = "1/7"
        self.assertEqual(verify(certificate)["status"], "REFUTED")

    def test_checker_runs_without_site_packages(self):
        certificate = difference([9, 6, 6, 4], [0, 1, 1, 1], [0, 0, 1, 1])
        code = "import sys,json; sys.path.insert(0,sys.argv[1]); from entropy_verifier import verify; print(verify(json.load(sys.stdin))['status'])"
        result = subprocess.run(
            [sys.executable, "-S", "-c", code, str(ROOT / "scripts")],
            input=json.dumps(certificate),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "REFUTED")

    def test_real_worker_and_contract_do_not_claim_universal_proof(self):
        args = dict(
            counts=[5, 1, 1, 3],
            terms=[{"coefficient": "1", "labels": [0, 1, 1, 1]}, {"coefficient": "-1", "labels": [0, 0, 1, 1]}],
            constant="0",
            max_bits=500000,
        )
        with tempfile.TemporaryDirectory() as root:
            study = Study.create(
                root,
                "entropy",
                "Investigate a universal entropy claim",
                machine_contract={"tool": "entropy_inequality", "arguments": args, "status": "ESTABLISHED"},
            )
            result = study.submit(
                dict(
                    action=dict(tool="entropy_inequality", arguments=args),
                    rationale="Check a scoped entropy comparison.",
                    falsifier="Exact negative difference.",
                    evidence=[],
                ),
                0,
            )
            self.assertEqual(result["execution"], "SUCCEEDED", result)
            self.assertEqual(result["result"]["status"], "ESTABLISHED")
            self.assertEqual(study.state()["machine_contract_status"], "MET")
            self.assertEqual(study.state()["objective_status"], "UNRESOLVED")

    def test_literature_transport_failure_is_not_empty_success(self):
        action = dict(tool="literature", arguments=dict(query="union-closed", limit=2, provider="arxiv"))
        with patch("literature_search.request_bytes", side_effect=OSError("test transport failure")):
            result = produce(action)
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertFalse(result["retrieval_complete"])
        self.assertEqual(len(result["sources"]["request_errors"]), 1)

    def test_failed_retrieval_can_retry_same_query_but_empty_success_is_distinct(self):
        proposal = dict(
            action=dict(tool="literature", arguments=dict(query="union-closed", limit=2, provider="arxiv")),
            rationale="Read primary metadata.",
            falsifier="Failure cannot establish absence.",
            evidence=[],
        )
        failed = dict(
            status="INCONCLUSIVE",
            sources=dict(requests=[], request_errors=[{"error": "transport"}]),
            retrieval_complete=False,
        )
        empty = dict(
            status="CANDIDATE_SOURCES",
            sources=dict(requests=[{"status": "OK"}], request_errors=[], records=[]),
            retrieval_complete=True,
        )
        with tempfile.TemporaryDirectory() as root:
            study = Study.create(root, "retrieval", "Check literature", network=True)
            with patch("research_agent.core.run_worker", side_effect=[failed, empty]):
                self.assertEqual(study.submit(proposal, 0)["execution"], "FAILED")
                self.assertEqual(study.submit(proposal, 1)["execution"], "SUCCEEDED")


if __name__ == "__main__":
    unittest.main()
