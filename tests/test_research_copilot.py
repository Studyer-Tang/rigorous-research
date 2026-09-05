from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research_copilot as rc
import research_workspace as rw


class Response:
    def __init__(self, value):
        self.data = json.dumps(value).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, limit):
        return self.data[:limit]


class ResearchCopilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = rw.initialize(
            self.root, "copilot", "mathematics", "Does the bound hold?", "x*(1-x) >= 0 on [0,1]"
        )
        self.packet = rc.prepare(self.workspace)
        self.proposed = {
            "actions": [
                {
                    "task_id": "",
                    "claim_id": "C001",
                    "objective": "Check the polynomial bound",
                    "rationale": "Keep the stated interval",
                    "falsifier": "An admissible negative value",
                    "search_queries": [],
                    "tests": [
                        {
                            "operation": "bound",
                            "lhs": "x*(1-x)",
                            "rhs": "0",
                            "symbols": ["x"],
                            "lower": "0",
                            "upper": "1",
                            "values": [],
                        }
                    ],
                }
            ]
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_prepare_preserves_case_and_does_not_embed_artifacts(self):
        case = self.workspace.parent / "case.json"
        before = case.read_bytes()
        (case.parent / "artifacts" / "private.txt").write_text("raw-unshared-data", encoding="utf-8")
        packet = rc.prepare(self.workspace)
        self.assertNotIn("raw-unshared-data", json.dumps(packet))
        self.assertEqual(case.read_bytes(), before)
        packet["context"]["question"] = "changed"
        with self.assertRaisesRegex(ValueError, "changed"):
            rc.check_packet(packet)

    def test_replay_discards_commands_and_verdicts_and_rejects_unknown_claims(self):
        self.proposed["verdict"] = "SUPPORTED"
        self.proposed["actions"][0]["command"] = "arbitrary code"
        advice = rc.normalize_advice(self.packet, self.proposed)
        self.assertNotIn("command", advice["actions"][0])
        self.assertNotIn("verdict", advice)
        self.proposed["actions"][0]["claim_id"] = "C999"
        with self.assertRaisesRegex(ValueError, "unknown"):
            rc.normalize_advice(self.packet, self.proposed)

    def test_check_runs_real_backend_without_changing_workspace(self):
        before = self.workspace.read_bytes()
        case_before = (self.workspace.parent / "case.json").read_bytes()
        result = rc.verify(self.workspace, self.packet, rc.normalize_advice(self.packet, self.proposed))
        self.assertEqual(result["results"][0]["execution_status"], "CHECKED")
        self.assertTrue(result["results"][0]["certificate"]["bound_established"])
        self.assertFalse(result["governance"]["formal_verdicts_created"])
        self.assertEqual(self.workspace.read_bytes(), before)
        self.assertEqual((self.workspace.parent / "case.json").read_bytes(), case_before)

    def test_stale_workspace_prevents_execution(self):
        advice = rc.normalize_advice(self.packet, self.proposed)
        path, data = rw.load(self.workspace)
        data["stage"] = "ANALYSIS"
        rw.atomic_json(path, data)
        with patch.object(rc.subprocess, "run") as run, self.assertRaisesRegex(ValueError, "stale"):
            rc.verify(self.workspace, self.packet, advice)
        run.assert_not_called()

    def test_rehashed_but_fabricated_context_is_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["context"]["claims"][0]["statement"] = "A different claim"
        packet["packet_hash"] = rc.canonical_hash({key: value for key, value in packet.items() if key != "packet_hash"})
        advice = rc.normalize_advice(packet, self.proposed)
        with self.assertRaisesRegex(ValueError, "stale"):
            rc.verify(self.workspace, packet, advice)

    def test_timeout_is_recorded_without_a_certificate(self):
        with patch.object(rc.subprocess, "run", side_effect=subprocess.TimeoutExpired("math", 1)):
            result = rc.verify(self.workspace, self.packet, rc.normalize_advice(self.packet, self.proposed), timeout=1)
        self.assertEqual(result["results"][0]["execution_status"], "TIMEOUT")
        self.assertIsNone(result["results"][0]["certificate"])

    def test_grid_cannot_inject_command_options(self):
        test = self.proposed["actions"][0]["tests"][0]
        test.update({"operation": "counterexample", "values": ["--output=unwanted.json"]})
        with self.assertRaisesRegex(ValueError, "grid values"):
            rc.normalize_advice(self.packet, self.proposed)

    def test_negative_fraction_grid_reaches_the_backend_exactly(self):
        test = self.proposed["actions"][0]["tests"][0]
        test.update({"operation": "counterexample", "lhs": "x**2", "rhs": "x", "values": ["-1/2", "-2/3"]})
        result = rc.verify(self.workspace, self.packet, rc.normalize_advice(self.packet, self.proposed))
        self.assertEqual(result["results"][0]["execution_status"], "CHECKED")
        self.assertEqual(result["results"][0]["certificate"]["witness"]["assignment"], {"x": "-1/2"})

    def test_responses_protocol_and_secret_handling(self):
        captured = {}

        def request(req, timeout):
            captured.update({"body": json.loads(req.data), "auth": req.headers["Authorization"], "url": req.full_url})
            return Response(
                {
                    "status": "completed",
                    "output": [
                        {"type": "reasoning", "summary": []},
                        {"type": "message", "content": [{"type": "output_text", "text": json.dumps(self.proposed)}]},
                    ],
                }
            )

        with patch.dict(os.environ, {"TEST_RESEARCH_KEY": "example-secret"}):
            advice = rc.request_advice(
                self.packet,
                "openai-responses",
                "https://api.openai.com/v1",
                "user-selected-model",
                "TEST_RESEARCH_KEY",
                request,
            )
        self.assertEqual(captured["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(captured["auth"], "Bearer example-secret")
        self.assertFalse(captured["body"]["store"])
        self.assertTrue(captured["body"]["text"]["format"]["strict"])
        self.assertNotIn("example-secret", json.dumps(advice))

    def test_refused_or_incomplete_responses_do_not_become_advice(self):
        for envelope in (
            {"status": "incomplete"},
            {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal"}]}]},
        ):
            with (
                self.subTest(envelope=envelope),
                patch.dict(os.environ, {"TEST_RESEARCH_KEY": "example-secret"}),
                self.assertRaises(ValueError),
            ):
                rc.request_advice(
                    self.packet,
                    "openai-responses",
                    "https://api.openai.com/v1",
                    "user-selected-model",
                    "TEST_RESEARCH_KEY",
                    lambda *args, **kwargs: Response(envelope),
                )

    def test_ollama_and_compatible_replay(self):
        for provider in ("ollama", "openai-compatible"):

            def request(req, timeout):
                content = json.dumps(self.proposed)
                return Response(
                    {"message": {"content": content}}
                    if provider == "ollama"
                    else {"choices": [{"message": {"content": content}}]}
                )

            with self.subTest(provider=provider), patch.dict(os.environ, {"TEST_RESEARCH_KEY": "example-secret"}):
                result = rc.request_advice(
                    self.packet, provider, "http://127.0.0.1:11434", "user-selected-model", "TEST_RESEARCH_KEY", request
                )
                self.assertEqual(len(result["actions"]), 1)

    def test_empty_checks_are_not_reported_as_verified(self):
        proposed = copy.deepcopy(self.proposed)
        proposed["actions"][0]["tests"] = []
        result = rc.verify(self.workspace, self.packet, rc.normalize_advice(self.packet, proposed))
        self.assertEqual(result["governance"]["state"], "NO_CHECKS")


if __name__ == "__main__":
    unittest.main()
