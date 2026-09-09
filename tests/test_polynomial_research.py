"""Exact inequalities, forged proofs, scope boundaries and durable research routes."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from certificate_verifier import verify
from polynomial_research import inequality_search, polynomial_amgm, polynomial_sos
from polynomial_verifier import parse
from research_agent.core import Study


def proposal(tool, args, evidence=None):
    return {
        "action": {"tool": tool, "arguments": args},
        "rationale": "Compare precise proof routes using exact evidence.",
        "falsifier": "A feasible negative value or a nonzero residual defeats this route.",
        "evidence": evidence or [],
    }


def route(name="quadratic", status="exploring"):
    return dict(
        route_id=name,
        status=status,
        claim="x**2+y**2>=2*x*y for real x,y",
        approach="Complete rational squares.",
        blocker="",
        next_test="Independently check the decomposition.",
    )


class PolynomialTests(unittest.TestCase):
    def test_amgm_certifies_motzkin_and_rejects_wrong_product_or_sum(self):
        certificate = polynomial_amgm(
            "x**4*y**2+x**2*y**4+1",
            "3*x**2*y**2",
            ["x", "y"],
            [],
            [{"weight": "1", "square": square, "factors": []} for square in ["x**2*y", "x*y**2", "1"]],
            "x**2*y**2",
        )
        self.assertEqual(verify(certificate)["status"], "ESTABLISHED")
        for field, value in [("base", "x*y"), ("rule", "trust-me"), ("addends", [])]:
            forged = copy.deepcopy(certificate)
            forged["proof"][field] = value
            self.assertEqual(verify(forged)["status"], "INVALID")
        certificate["claim"]["rhs"] = "4*x**2*y**2"
        self.assertEqual(verify(certificate)["status"], "INVALID")

    def test_amgm_even_power_does_not_require_positive_base(self):
        certificate = polynomial_amgm(
            "x**2+1", "2*x", ["x"], [], [{"weight": "1", "square": s, "factors": []} for s in ["x", "1"]], "x"
        )
        self.assertEqual(verify(certificate)["status"], "ESTABLISHED")

    def test_amgm_constraints_are_checked_before_using_product(self):
        certificate = polynomial_amgm(
            "x+y",
            "2*z",
            ["x", "y", "z"],
            ["x", "y"],
            [{"weight": "1", "square": "1", "factors": [i]} for i in [0, 1]],
            "z",
        )
        # x*y=z*z is not a declared identity: AM-GM alone cannot establish this claim.
        self.assertEqual(verify(certificate)["status"], "INVALID")

    def test_quadratic_discovery_including_singular_constant_and_affine(self):
        for expr in ["x**2+y**2-2*x*y", "(x+y-1)**2+3*(y+2)**2", "0", "1/7", "y**2"]:
            with self.subTest(expr=expr):
                certificate = polynomial_sos(expr, "0", ["x", "y"], [], [])
                self.assertEqual(verify(certificate)["status"], "ESTABLISHED", certificate)

    def test_unsupported_or_indefinite_is_not_a_disproof(self):
        for expr in ["x**4+y**4", "x*y", "x**2-y**2", "x", "-1"]:
            with self.subTest(expr=expr):
                self.assertEqual(verify(polynomial_sos(expr, "0", ["x", "y"], [], []))["status"], "INCONCLUSIVE")

    def test_three_term_unevaluated_parser_sums_are_normalized(self):
        certificate = polynomial_sos("x**2+y**2+z**2", "(x+y+z)**2/3", ["x", "y", "z"], [], [])
        self.assertEqual(verify(certificate)["status"], "ESTABLISHED")

    def test_lagrange_identity_supplied_quartic_proof(self):
        certificate = polynomial_sos(
            "(a**2+b**2)*(c**2+d**2)",
            "(a*c+b*d)**2",
            ["a", "b", "c", "d"],
            [],
            [{"weight": "1", "square": "a*d-b*c", "factors": []}],
        )
        self.assertEqual(verify(certificate)["status"], "ESTABLISHED")
        certificate["proof"][0]["square"] = "a*d+b*c"
        self.assertEqual(verify(certificate)["status"], "INVALID")

    def test_constraints_and_products_are_explicit(self):
        certificate = polynomial_sos(
            "x*(1-x)", "0", ["x"], ["x", "1-x"], [{"weight": "1", "square": "1", "factors": [0, 1]}]
        )
        self.assertEqual(verify(certificate)["status"], "ESTABLISHED")
        for change in [[], ["x"], ["x", "1+x"]]:
            forged = copy.deepcopy(certificate)
            forged["claim"]["assumptions"] = change
            self.assertEqual(verify(forged)["status"], "INVALID")

    def test_forged_semantics_weights_factors_and_witness(self):
        original = polynomial_sos("x**2", "0", ["x"], [], [{"weight": "1", "square": "x", "factors": []}])
        for field, value in [("domain", "integer"), ("relation", ">"), ("symbols", ["x", "x"])]:
            forged = copy.deepcopy(original)
            forged["claim"][field] = value
            self.assertEqual(verify(forged)["status"], "INVALID")
        for field, value in [("weight", "-1"), ("factors", [True]), ("weight", "0.1"), ("square", "x/x")]:
            forged = copy.deepcopy(original)
            forged["proof"][0][field] = value
            self.assertEqual(verify(forged)["status"], "INVALID")
        original["witness"] = {"x": "1"}
        self.assertEqual(verify(original)["status"], "INVALID")

    def test_exact_grid_refutation_checks_feasibility_and_rational_witness(self):
        certificate = inequality_search("x", "0", ["x"], [], ["-1/3"], 1)
        self.assertEqual(verify(certificate)["status"], "REFUTED")
        certificate["claim"]["assumptions"] = ["x"]
        self.assertEqual(verify(certificate)["status"], "INVALID")
        certificate["claim"]["assumptions"] = []
        certificate["witness"]["x"] = "0"
        self.assertEqual(verify(certificate)["status"], "INVALID")

    def test_no_witness_and_budget_exhaustion_never_prove(self):
        certificate = inequality_search("x*y", "0", ["x", "y"], [], ["-1", "1"], 1)
        self.assertFalse(certificate["search"]["grid_complete"])
        self.assertEqual(verify(certificate)["status"], "INCONCLUSIVE")
        certificate = inequality_search("x*y", "0", ["x", "y"], ["x", "y"], ["-1", "1"], 4)
        self.assertTrue(certificate["search"]["grid_complete"])
        self.assertEqual(verify(certificate)["status"], "INCONCLUSIVE")

    def test_checker_is_standard_library_only(self):
        certificate = polynomial_sos("(x-2)**2", "0", ["x"], [], [])
        code = "import sys,json; sys.path.insert(0,sys.argv[1]); from polynomial_verifier import verify; print(verify(json.load(sys.stdin))['status'])"
        result = subprocess.run(
            [sys.executable, "-S", "-c", code, str(ROOT / "scripts")],
            input=json.dumps(certificate),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "ESTABLISHED")

    def test_parser_rejects_hidden_poles_code_and_excessive_expansion(self):
        for expr in [
            "x/(x-x+1)",
            "x**-1",
            "__import__('os')",
            "x**1000",
            "0.1*x",
            "True",
            "x/0",
            "(x+1)**16*(x+2)**16*x",
        ]:
            with self.subTest(expr=expr), self.assertRaises((ValueError, SyntaxError)):
                parse(expr, ["x"])


class ResearchRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.study = Study.create(self.temp.name, "inequalities", "Study polynomial inequalities")

    def test_routes_survive_history_window_reopen_and_revisions(self):
        self.study.submit(proposal("route", route()), 0)
        for i in range(22):
            self.study.submit(proposal("note", {"text": f"Draft calculation {i}"}), i + 1)
        reopened = Study(self.study.directory)
        context = reopened.context()
        self.assertNotIn(1, [a["id"] for a in context["recent_actions"]])
        self.assertEqual(context["research_routes"]["items"][0]["action_id"], 1)
        reopened.submit(proposal("route", route(status="supported"), [1]), 23)
        self.assertEqual(reopened.routes()["items"][0]["arguments"]["status"], "supported")
        self.assertEqual(reopened.inspect(1)["proposal"]["action"]["arguments"]["status"], "exploring")
        self.assertEqual(reopened.state()["objective_status"], "UNRESOLVED")
        self.assertEqual(reopened.export()["research_routes"], reopened.routes())

    def test_route_capacity_and_legacy_database_migration(self):
        with self.study.connect() as db:
            db.execute("DROP TABLE research_routes")
        study = Study(self.study.directory)
        for i in range(32):
            study.submit(proposal("route", route(f"r-{i}")), i)
        with self.assertRaisesRegex(ValueError, "32"):
            study.submit(proposal("route", route("extra")), 32)
        study.submit(proposal("route", route("r-0", "blocked")), 32)
        self.assertEqual(len(study.routes()["items"]), 32)

    def test_route_cannot_promote_or_forge_evidence(self):
        for args, evidence in [(route(status="PROVED"), []), (route(), [99])]:
            with self.assertRaises(ValueError):
                self.study.submit(proposal("route", args, evidence), 0)
        self.study.submit(proposal("route", route()), 0)
        with self.study.connect() as db:
            db.execute("UPDATE actions SET result='{}' WHERE id=1")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.study.routes()

    def test_hosted_worker_and_machine_contract_keep_original_goal_open(self):
        args = dict(lhs="x**2+y**2", rhs="2*x*y", symbols=["x", "y"], assumptions=[], terms=[])
        study = Study.create(
            self.temp.name,
            "contract",
            "Research inequality",
            machine_contract={"tool": "polynomial_sos", "arguments": args, "status": "ESTABLISHED"},
        )
        record = study.submit(proposal("polynomial_sos", args), 0)
        self.assertEqual(record["execution"], "SUCCEEDED", record)
        self.assertEqual(record["result"]["status"], "ESTABLISHED")
        self.assertIn("polynomial_verifier.py", record["result"]["toolchain_sha256"])
        self.assertEqual(study.state()["machine_contract_status"], "MET")
        self.assertEqual(study.state()["objective_status"], "UNRESOLVED")
        search_args = dict(lhs="x", rhs="0", symbols=["x"], assumptions=[], values=["-1/3"], max_points=1)
        self.assertEqual(study.submit(proposal("inequality_search", search_args), 1)["result"]["status"], "REFUTED")


if __name__ == "__main__":
    unittest.main()
