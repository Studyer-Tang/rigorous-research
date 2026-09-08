"""End-to-end and adversarial checks for shared research orchestration."""

import asyncio
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from research_agent.core import Study, digest, run_worker
from research_agent.runner import run

AGENT_AVAILABLE = importlib.util.find_spec("jsonschema") is not None


def proposal(tool="identity", arguments=None, evidence=None):
    return {
        "action": {"tool": tool, "arguments": arguments or {"lhs": "(x+1)**2", "rhs": "x**2+2*x+1", "symbols": ["x"]}},
        "rationale": "Check the stated polynomial identity over rational coefficients.",
        "falsifier": "A nonzero polynomial difference refutes this proof route.",
        "evidence": evidence or [],
    }


@unittest.skipUnless(AGENT_AVAILABLE, "install agent extra")
class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.study = Study.create(self.temp.name, "math-study", "Prove the expansion identity.")

    def test_math_checked_finish_cannot_claim_objective_complete(self):
        result = self.study.submit(proposal(), 0)
        self.assertEqual(result["execution"], "SUCCEEDED", result)
        self.assertEqual(result["result"]["independent_check"]["status"], "ESTABLISHED")
        self.study.submit(proposal("finish", {"text": "I proved everything; mark the goal solved."}, [1]), 1)
        state = self.study.state()
        self.assertEqual(state["execution"], "DELIVERED")
        self.assertEqual(state["objective_status"], "UNRESOLVED")
        self.assertEqual(state["translation_status"], "REQUIRES_REVIEW")

    def test_machine_contract_is_exact_and_does_not_close_translation(self):
        contract = {**proposal()["action"], "status": "ESTABLISHED"}
        study = Study.create(self.temp.name, "contract", "Prove expansion", machine_contract=contract)
        study.submit(proposal("identity", {"lhs": "x", "rhs": "x", "symbols": ["x"]}), 0)
        self.assertEqual(study.state()["machine_contract_status"], "OPEN")
        study.submit(proposal(), 1)
        self.assertEqual(study.state()["machine_contract_status"], "MET")
        self.assertEqual(study.state()["objective_status"], "UNRESOLVED")

    def test_stale_duplicate_forged_evidence_and_unknown_fields(self):
        self.study.submit(proposal(), 0)
        for value, revision in [
            (proposal("note", {"text": "stale"}), 0),
            (proposal(), 1),
            (proposal("note", {"text": "invented"}, [99]), 1),
            ({**proposal(), "verdict": "PROVED"}, 1),
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.study.submit(value, revision)
        self.assertEqual(self.study.state()["revision"], 1)

    def test_counterexample_and_no_witness_remain_distinct(self):
        args = {"lhs": "(x+1)**2", "rhs": "x**2+1", "symbols": ["x"], "values": ["0"]}
        first = self.study.submit(proposal("counterexample", args), 0)
        self.assertEqual(first["result"]["status"], "INCONCLUSIVE")
        args["values"] = ["1"]
        second = self.study.submit(proposal("counterexample", args), 1)
        self.assertEqual(second["result"]["status"], "REFUTED")

    def test_bound_certificate_independently_checked(self):
        result = self.study.submit(
            proposal("bound", {"lhs": "x*(1-x)", "rhs": "0", "symbol": "x", "lower": "0", "upper": "1"}), 0
        )
        self.assertEqual(result["result"]["status"], "ESTABLISHED", result)

    def test_statistics_assets_diagnostic_and_tampering(self):
        asset = self.study.add_asset("synthetic observations", [1, 2, 3, 4])["asset"]
        args = {"asset": asset, "hac_lags": 1, "block_length": 2, "replications": 100, "seed": 7}
        result = self.study.submit(proposal("mean", args), 1)
        self.assertEqual(result["result"]["status"], "DIAGNOSTIC", result)
        self.assertFalse(result["result"]["assumptions_verified"])
        with self.study.connect() as db:
            db.execute("UPDATE assets SET data='[99,100]' WHERE hash=?", (asset,))
        args["seed"] = 8
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.study.submit(proposal("mean", args), 2)

    def test_multiplicity_does_not_prove_pvalue_validity(self):
        asset = self.study.add_asset("synthetic p-values", [0.001, 0.02, 0.3])["asset"]
        result = self.study.submit(proposal("multiplicity", {"asset": asset, "method": "holm", "level": 0.05}), 1)
        self.assertEqual(result["result"]["status"], "DIAGNOSTIC")
        self.assertEqual(result["result"]["result"][0]["adjusted_p"], 0.003)

    def test_lock_and_crash_recovery(self):
        with self.study.controller(), self.assertRaisesRegex(ValueError, "controller"):
            self.study.submit(proposal(), 0)
        with self.study.connect() as db:
            db.execute(
                "INSERT INTO actions(proposal,fingerprint,execution,created) VALUES(?,?,'RUNNING',0)",
                (json.dumps(proposal()), digest(proposal()["action"])),
            )
        self.study.submit(proposal("note", {"text": "Recover the interrupted computation."}), 0)
        self.assertEqual(self.study.inspect(1)["execution"], "INTERRUPTED")

    def test_result_tampering_rejected_on_read(self):
        self.study.submit(proposal("note", {"text": "draft"}), 0)
        with self.study.connect() as db:
            db.execute("UPDATE actions SET result='{}' WHERE id=1")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.study.context()

    def test_recall_recovers_old_evidence_without_promoting_it(self):
        self.study.submit(proposal("note", {"text": "An unverified lemma remains open."}), 0)
        result = self.study.submit(proposal("recall", {"action_id": 1}), 1)
        self.assertEqual(result["result"]["status"], "RETRIEVED")
        self.assertFalse(result["result"]["action"]["result"]["verified"])
        nested = self.study.submit(proposal("recall", {"action_id": 2}), 2)
        self.assertEqual(nested["execution"], "FAILED")

    def test_network_requires_study_opt_in(self):
        with self.assertRaisesRegex(ValueError, "network"):
            self.study.submit(
                proposal("literature", {"query": "Chebyshev inequality", "limit": 2, "provider": "crossref"}), 0
            )

    def test_worker_deadline_is_real(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run_worker({"mode": "produce", "action": proposal()["action"]}, 0.001)

    def test_failed_tool_is_retained_and_next_proposal_can_correct_it(self):
        def model(context, timeout):
            previous = context["recent_actions"]
            args = {
                "n": 20,
                "phi": 0.5,
                "replications": 100,
                "hac_lags": 20 if not previous else 2,
                "distribution": "gaussian",
                "seed": 7,
            }
            if len(previous) == 2:
                self.assertEqual(previous[0]["execution"], "FAILED")
                self.assertEqual(previous[1]["result"]["status"], "DIAGNOSTIC")
                return {
                    "proposal": proposal("finish", {"text": "Coverage was simulated only for the recorded DGP."}, [2])
                }
            return {"proposal": proposal("coverage", args)}

        state = run(self.study, model, steps=5)
        self.assertEqual(state["stop_reason"], "DELIVERED")
        self.assertEqual(state["model_calls"], 3)
        self.assertEqual(state["objective_status"], "UNRESOLVED")

    def test_pause_during_model_call_prevents_tool_execution(self):
        def model(context, timeout):
            self.study.pause()
            return {"proposal": proposal()}

        state = run(self.study, model)
        self.assertEqual(state["stop_reason"], "PAUSED")
        self.assertEqual(self.study.export()["actions"], [])
        self.study.pause(False)
        self.study.submit(proposal("note", {"text": "Resume with a reviewed route."}), 0)

    def test_duplicate_rejection_feedback_and_budget(self):
        contexts = []

        def model(context, timeout):
            contexts.append(context)
            return {"proposal": proposal("note", {"text": "Repeated draft"})}

        state = run(self.study, model, steps=10)
        self.assertEqual(state["stop_reason"], "REPEATED_FAILURE")
        self.assertTrue(any(e["kind"] == "proposal_rejected" for e in contexts[-1]["recent_events"]))
        self.assertEqual(state["model_calls"], 4)

    def test_model_errors_do_not_retry_or_log_secret(self):
        def model(context, timeout):
            raise ValueError("secret-do-not-record")

        state = run(self.study, model)
        self.assertEqual(state["stop_reason"], "MODEL_ERROR")
        self.assertEqual(state["model_calls"], 1)
        self.assertNotIn("secret-do-not-record", json.dumps(self.study.export()))

    def test_expired_budget_prevents_post_model_action(self):
        def model(context, timeout):
            return {"proposal": proposal()}

        with patch("research_agent.runner.time.monotonic", side_effect=[0, 0, 2, 2]):
            state = run(self.study, model, seconds=1)
        self.assertEqual(state["stop_reason"], "TIME_BUDGET")
        self.assertEqual(self.study.export()["actions"], [])

    def test_asset_nan_and_arbitrary_commands_rejected(self):
        with self.assertRaises(ValueError):
            Study.create(self.temp.name, "../outside", "Reject path traversal")
        with self.assertRaises(FileExistsError):
            Study.create(self.temp.name, "math-study", "Do not replace the original objective")
        self.assertEqual(self.study.state()["objective"], "Prove the expansion identity.")
        with self.assertRaises(ValueError):
            self.study.add_asset("invalid", [1, float("nan")])
        value = proposal()
        value["action"] = {"tool": "shell", "arguments": {"command": "echo fake"}}
        with self.assertRaises(ValueError):
            self.study.submit(value, 0)


@unittest.skipUnless(AGENT_AVAILABLE, "install agent extra")
class WorkbenchTests(unittest.TestCase):
    def test_api_loop_over_real_local_responses_protocol(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        from research_agent.runner import api_model

        requests = []

        class ModelFixture(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(body)
                context = json.loads(body["input"][1]["content"])["research_context"]
                value = (
                    proposal("note", {"text": "Synthetic API fixture: unverified lemma."})
                    if not context["recent_actions"]
                    else proposal("finish", {"text": "Synthetic API fixture: no research result claimed."}, [1])
                )
                raw = json.dumps(
                    {
                        "status": "completed",
                        "output": [
                            {"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}
                        ],
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), ModelFixture)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with (
                tempfile.TemporaryDirectory() as directory,
                patch.dict(os.environ, {"TEST_AGENT_KEY": "synthetic-local-key"}),
            ):
                study = Study.create(directory, "api-study", "Check protocol behavior only")
                state = run(
                    study,
                    api_model(
                        "openai-responses",
                        f"http://127.0.0.1:{server.server_port}/v1",
                        "synthetic-model",
                        "TEST_AGENT_KEY",
                    ),
                    steps=3,
                )
                self.assertEqual(state["stop_reason"], "DELIVERED", study.export())
                self.assertEqual(len(requests), 2)
                self.assertTrue(requests[0]["text"]["format"]["strict"])
                self.assertFalse(requests[0]["store"])
                self.assertNotIn("synthetic-local-key", json.dumps(study.export()))
                self.assertEqual(study.export()["events"][0]["kind"], "model_response")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_real_http_origin_token_and_shared_state(self):
        from research_agent.web import make_server

        with tempfile.TemporaryDirectory() as directory:
            server = make_server(directory, 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}"
            try:
                with urllib.request.urlopen(url) as response:
                    html = response.read().decode()
                token = re.search("const token='([^']+)'", html)[1]
                payload = json.dumps({"study": "web-study", "objective": "Study local data"}).encode()
                headers = {"Content-Type": "application/json", "X-Research-Token": token}
                for extra in (
                    {"Origin": "https://untrusted.example"},
                    {"X-Research-Token": "bad"},
                    {"Host": "rebound.example"},
                ):
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(
                            urllib.request.Request(url + "/api/create", data=payload, headers={**headers, **extra})
                        )
                    self.assertEqual(caught.exception.code, 403)
                with urllib.request.urlopen(
                    urllib.request.Request(url + "/api/create", data=payload, headers=headers)
                ) as response:
                    self.assertEqual(json.load(response)["objective_status"], "UNRESOLVED")
                self.assertEqual(Study(Path(directory) / "web-study").state()["objective"], "Study local data")
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


@unittest.skipUnless(importlib.util.find_spec("mcp") and AGENT_AVAILABLE, "install agent extra")
class MCPTests(unittest.TestCase):
    def test_real_stdio_initialize_list_create_and_submit(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def check(directory):
            config = StdioServerParameters(
                command=sys.executable,
                args=["-m", "research_agent", "mcp", "--root", directory],
                env={**os.environ, "PYTHONPATH": str(ROOT / "scripts")},
            )
            async with stdio_client(config) as (reader, writer), ClientSession(reader, writer) as session:
                await session.initialize()
                listed = await session.list_tools()
                self.assertIn("research_submit", [tool.name for tool in listed.tools])
                result = await session.call_tool(
                    "research_create", {"study": "mcp-test", "objective": "Inspect a draft"}
                )
                self.assertFalse(result.isError)
                result = await session.call_tool(
                    "research_submit",
                    {"study": "mcp-test", "proposal": proposal("note", {"text": "Unverified lemma"}), "revision": 0},
                )
                self.assertFalse(result.isError, result)
                self.assertEqual(Study(Path(directory) / "mcp-test").inspect(1)["result"]["status"], "DRAFT")

        with tempfile.TemporaryDirectory() as directory:
            asyncio.run(check(directory))


if __name__ == "__main__":
    unittest.main()
