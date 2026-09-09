"""Rational log bounds and adversarial certificates for finite coupling optimizers."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from certificate_verifier import verify
from coupling_research import coupling_entropy
from rational_log import entropy_bounds, log_bounds, outward
from research_agent.core import Study


def uniform_certificate():
    return {
        "schema_version": 1,
        "backend": "balanced-coupling",
        "claim": dict(
            kernel=[["1", "1"], ["1", "1"]],
            labels=[[0, 0], [1, 1]],
            bound="2/3",
            relation=">=",
            units="nats",
            marginals="uniform-rows-and-columns",
            objective="minimize-sum-p-log-p-over-k",
        ),
        "approximation": dict(
            counts=[[1, 1], [1, 1]], row_factors=["1/2", "1/2"], column_factors=["1/2", "1/2"], delta="0"
        ),
        "diagnostic": {},
    }


class RationalLogTests(unittest.TestCase):
    def test_log_one_and_outward_negative_rounding(self):
        self.assertEqual(log_bounds(1), (0, 0))
        x = Fraction(-1, 3)
        lower, upper = outward(x, x)
        self.assertLessEqual(lower, x)
        self.assertGreaterEqual(upper, x)
        self.assertLess(upper - lower, Fraction(1, 10**23))

    def test_log_reciprocals_powers_and_known_bracket(self):
        a, b = log_bounds(2)
        self.assertGreater(a, Fraction(69314718055994, 10**14))
        self.assertLess(b, Fraction(69314718055996, 10**14))
        for value in [Fraction(3, 7), Fraction(17, 11), Fraction(2**30), Fraction(1, 2**30)]:
            lo, hi = log_bounds(value)
            rlo, rhi = log_bounds(1 / value)
            self.assertLessEqual(lo + rlo, 0)
            self.assertGreaterEqual(hi + rhi, 0)
            self.assertLess(hi - lo, Fraction(1, 10**12))

    def test_refinement_and_probability_contract(self):
        lo, hi = log_bounds(Fraction(7, 4), 4)
        a, b = log_bounds(Fraction(7, 4), 16)
        self.assertLessEqual(lo, a)
        self.assertGreaterEqual(hi, b)
        self.assertEqual(entropy_bounds([Fraction(0), Fraction(1)]), (0, 0))
        for p in [[Fraction(1, 3)], [Fraction(-1), Fraction(2)]]:
            with self.assertRaises(ValueError):
                entropy_bounds(p)
        for value in [0, -1, 2**1025]:
            with self.assertRaises(ValueError):
                log_bounds(value)


class CouplingTests(unittest.TestCase):
    def test_known_optimizer_and_both_bound_directions(self):
        certificate = uniform_certificate()
        self.assertEqual(verify(certificate)["status"], "ESTABLISHED")
        certificate["claim"]["bound"] = "7/10"
        self.assertEqual(verify(certificate)["status"], "REFUTED")
        certificate["claim"]["relation"] = "<="
        self.assertEqual(verify(certificate)["status"], "ESTABLISHED")
        certificate["claim"]["bound"] = "2/3"
        self.assertEqual(verify(certificate)["status"], "REFUTED")

    def test_scope_kernel_and_event_changes(self):
        base = uniform_certificate()
        for key, value in [
            ("units", "bits"),
            ("marginals", "arbitrary"),
            ("objective", "maximize-entropy"),
            ("kernel", [["0", "1"], ["1", "1"]]),
            ("labels", [[True, 0], [1, 1]]),
        ]:
            bad = copy.deepcopy(base)
            bad["claim"][key] = value
            self.assertEqual(verify(bad)["status"], "INVALID")
        base["claim"]["labels"] = [[0, 0], [0, 0]]
        self.assertEqual(verify(base)["status"], "REFUTED")

    def test_approximate_feasibility_and_optimality_are_separate(self):
        for counts in [[[1, 1], [1, 2]], [[2, 1], [2, 1]], [[0, 2], [2, 0]], [[2, 1], [1, 2]]]:
            bad = uniform_certificate()
            bad["approximation"]["counts"] = counts
            bad["approximation"]["delta"] = "1/1000"
            self.assertEqual(verify(bad)["status"], "INVALID")
        bad = uniform_certificate()
        bad["approximation"]["row_factors"] = ["1", "1"]
        self.assertEqual(verify(bad)["status"], "INVALID")

    def test_continuity_budget_and_missing_approximation(self):
        certificate = uniform_certificate()
        certificate["approximation"]["delta"] = "1/2"
        self.assertEqual(verify(certificate)["status"], "INCONCLUSIVE")
        certificate["approximation"]["delta"] = "3/4"
        self.assertEqual(verify(certificate)["status"], "INVALID")
        certificate["approximation"] = None
        certificate["diagnostic"] = {"claimed_entropy": 100, "converged": True}
        self.assertEqual(verify(certificate)["status"], "INCONCLUSIVE")

    def test_solver_proposal_and_iteration_exhaustion(self):
        args = dict(
            kernel=[["1", "1/3"], ["1/3", "1/3"]],
            labels=[[0, 1], [1, 1]],
            bound="3/5",
            relation=">=",
            digits=12,
            max_iterations=1000,
            delta="1/1000",
        )
        self.assertEqual(verify(coupling_entropy(**args))["status"], "ESTABLISHED")
        args["max_iterations"] = 1
        self.assertEqual(verify(coupling_entropy(**args))["status"], "INCONCLUSIVE")

    def test_checker_without_numeric_libraries(self):
        code = "import sys,json; sys.path.insert(0,sys.argv[1]); from coupling_verifier import verify; print(verify(json.load(sys.stdin))['status'])"
        result = subprocess.run(
            [sys.executable, "-S", "-c", code, str(ROOT / "scripts")],
            input=json.dumps(uniform_certificate()),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "ESTABLISHED")

    def test_native_worker_does_not_promote_original_goal(self):
        args = dict(
            kernel=[["1", "1/3"], ["1/3", "1/3"]],
            labels=[[0, 1], [1, 1]],
            bound="3/5",
            relation=">=",
            digits=12,
            max_iterations=1000,
            delta="1/1000",
        )
        with tempfile.TemporaryDirectory() as root:
            study = Study.create(
                root,
                "coupling",
                "Resolve a universal conjecture",
                machine_contract={"tool": "coupling_entropy", "arguments": args, "status": "ESTABLISHED"},
            )
            record = study.submit(
                dict(
                    action=dict(tool="coupling_entropy", arguments=args),
                    rationale="Certify a finite optimizer entropy.",
                    falsifier="A failed interval bound.",
                    evidence=[],
                ),
                0,
            )
            self.assertEqual(record["execution"], "SUCCEEDED", record)
            self.assertEqual(study.state()["machine_contract_status"], "MET")
            self.assertEqual(study.state()["objective_status"], "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
