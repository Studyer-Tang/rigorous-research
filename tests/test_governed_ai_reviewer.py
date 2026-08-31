from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "governed_ai_reviewer.py"
SPEC = importlib.util.spec_from_file_location("governed_ai_reviewer", MODULE)
assert SPEC and SPEC.loader
reviewer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reviewer
SPEC.loader.exec_module(reviewer)


class FakeResponse:
    def __init__(self, value: dict):
        self.payload = json.dumps(value).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.payload


class GovernedAiReviewerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.report = self.root / "report.md"
        self.report.write_text(
            "# Report\n\n## Claims\n\n- [C001] The survey proves that all developers always trust AI tools. [@survey]\n",
            encoding="utf-8",
        )
        self.manifest = self.root / "evidence.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "id": "survey",
                            "title": "Developer survey about trust in AI tools",
                            "version_notes": "A sample of respondents may trust AI tools.",
                        }
                    ],
                    "evidence": [
                        {
                            "claim_id": "C001",
                            "source_id": "survey",
                            "quote": "Some respondents distrust AI tools.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_local_draft_recommends_but_never_decides(self):
        draft = reviewer.heuristic_draft(self.report, self.manifest)
        self.assertEqual(draft["governance"]["state"], "AI_DRAFT")
        self.assertFalse(draft["governance"]["formal_judgments_created"])
        claim = draft["candidates"][0]
        self.assertEqual(claim["status"], "AI_DRAFT_REQUIRES_HUMAN_REVIEW")
        self.assertEqual(claim["evidence_recommendations"][0]["status"], "SUGGESTION_NOT_A_VERDICT")
        issue_types = {item["type"] for item in claim["scope_issues"]}
        self.assertIn("possible_overgeneralization", issue_types)

    def test_openai_compatible_key_is_used_but_not_persisted(self):
        draft = reviewer.heuristic_draft(self.report, self.manifest)
        captured = {}

        def request(request, timeout):
            captured["authorization"] = request.headers.get("Authorization")
            captured["timeout"] = timeout
            content = json.dumps(
                {
                    "candidates": [
                        {
                            "id": "C001",
                            "rationale": "Check population scope.",
                            "additional_scope_issues": ["Survey population differs."],
                            "search_suggestions": ["Find the sampling frame."],
                            "verdict": "SUPPORTED",
                        }
                    ]
                }
            )
            return FakeResponse({"choices": [{"message": {"content": content}}]})

        with patch.dict(os.environ, {"TEST_REVIEW_KEY": "secret-value"}):
            enriched = reviewer.request_model(
                draft,
                "openai-compatible",
                "https://model.example.test/v1",
                "review-model",
                "TEST_REVIEW_KEY",
                requester=request,
            )
        self.assertEqual(captured["authorization"], "Bearer secret-value")
        self.assertNotIn("secret-value", json.dumps(enriched))
        self.assertNotIn("verdict", enriched["candidates"][0]["model_analysis"])
        self.assertFalse(enriched["governance"]["formal_judgments_created"])

    def test_confirmation_requires_human_quote_and_locator(self):
        draft_path = self.root / "draft.json"
        reviewer.write_json(draft_path, reviewer.heuristic_draft(self.report, self.manifest))
        with self.assertRaises(ValueError):
            reviewer.confirm_draft(draft_path, "C001", "survey", "SUPPORTED", "", "", "human-1", "")
        with self.assertRaises(ValueError):
            reviewer.confirm_draft(draft_path, "C001", "survey", "SUPPORTED", "Exact quote", "p. 2", "ai-assistant", "")
        confirmation = reviewer.confirm_draft(
            draft_path,
            "C001",
            "survey",
            "CONTRADICTED",
            "Some respondents distrust AI tools.",
            "Trust section, paragraph 2",
            "reviewer-42",
            "The universal claim reverses the evidence scope.",
            "2026-08-31T00:00:00+00:00",
        )
        self.assertEqual(confirmation["status"], "HUMAN_CONFIRMED")
        self.assertEqual(confirmation["evidence"]["review_method"], "human")
        self.assertTrue(confirmation["governance"]["ai_draft_was_non_decisive"])

    def test_cli_creates_draft_and_confirmation_receipt(self):
        draft = self.root / "draft.json"
        self.assertEqual(
            reviewer.main(["draft", str(self.report), "--manifest", str(self.manifest), "--output", str(draft)]),
            0,
        )
        confirmation = self.root / "confirmation.json"
        self.assertEqual(
            reviewer.main(
                [
                    "confirm",
                    str(draft),
                    "--claim-id",
                    "C001",
                    "--source-id",
                    "survey",
                    "--verdict",
                    "UNVERIFIABLE",
                    "--reviewer-id",
                    "reviewer-42",
                    "--output",
                    str(confirmation),
                ]
            ),
            0,
        )
        self.assertEqual(json.loads(confirmation.read_text())["status"], "HUMAN_CONFIRMED")


if __name__ == "__main__":
    unittest.main()
