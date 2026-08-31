from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "papertrail_audit.py"
SPEC = importlib.util.spec_from_file_location("papertrail_audit", MODULE)
assert SPEC and SPEC.loader
papertrail = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = papertrail
SPEC.loader.exec_module(papertrail)


class PaperTrailAuditTests(unittest.TestCase):
    def write_fixture(self, directory: Path) -> tuple[Path, Path]:
        report = directory / "report.md"
        report.write_text(
            "# Example audit\n\n## Claims\n\n"
            "- [C001] The measured value increased by 18%. [@study]\n"
            "- [C002] The method is universally accurate. [@study]\n",
            encoding="utf-8",
        )
        manifest = directory / "evidence.json"
        manifest.write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "id": "study",
                            "title": "Controlled study",
                            "authors": ["A. Researcher"],
                            "year": 2026,
                            "url": "https://example.org/study",
                            "publication_status": "active",
                            "integrity_checked_at": "2026-08-31",
                            "version": "version of record",
                            "version_conflict": False,
                            "data_availability": "available",
                            "data_url": "https://example.org/data",
                            "code_availability": "not_applicable",
                        }
                    ],
                    "evidence": [
                        {
                            "claim_id": "C001",
                            "source_id": "study",
                            "verdict": "SUPPORTED",
                            "quote": "The measured value increased by 18%.",
                            "locator": "Results, paragraph 2",
                            "reviewer_id": "reviewer-a",
                            "reviewed_at": "2026-08-31",
                            "review_method": "human",
                        },
                        {
                            "claim_id": "C002",
                            "source_id": "study",
                            "verdict": "CONTRADICTED",
                            "quote": "Accuracy declined outside the evaluated sample.",
                            "locator": "Limitations",
                            "reviewer_id": "reviewer-a",
                            "reviewed_at": "2026-08-31",
                            "review_method": "human",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        return report, manifest

    def test_extracts_explicit_claims_and_citations(self):
        with tempfile.TemporaryDirectory() as directory:
            report, _ = self.write_fixture(Path(directory))
            parsed = papertrail.parse_markdown_report(report)
        self.assertEqual(parsed["title"], "Example audit")
        self.assertEqual([claim["id"] for claim in parsed["claims"]], ["C001", "C002"])
        self.assertEqual(parsed["claims"][0]["citations"], ["study"])
        self.assertNotIn("[@study]", parsed["claims"][0]["statement"])

    def test_builds_supported_and_contradicted_verdicts(self):
        with tempfile.TemporaryDirectory() as directory:
            report, manifest = self.write_fixture(Path(directory))
            audit = papertrail.build_audit(report, manifest)
        self.assertEqual([claim["verdict"] for claim in audit["claims"]], ["SUPPORTED", "CONTRADICTED"])
        self.assertEqual(audit["reproducibility_checklist"]["sources_resolved"]["status"], "PASS")
        self.assertEqual(audit["reproducibility_checklist"]["data_availability"]["status"], "PASS")
        self.assertEqual(audit["reproducibility_checklist"]["version_conflicts"]["status"], "PASS")
        self.assertEqual(audit["reproducibility_checklist"]["review_provenance"]["status"], "PASS")

    def test_missing_source_is_unverifiable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.md"
            report.write_text("# Missing\n\n## Claims\n- A claim. [@missing]\n", encoding="utf-8")
            manifest = root / "evidence.json"
            manifest.write_text('{"sources": [], "evidence": []}', encoding="utf-8")
            audit = papertrail.build_audit(report, manifest)
        self.assertEqual(audit["claims"][0]["verdict"], "UNVERIFIABLE")
        self.assertEqual(audit["unresolved_source_ids"], ["missing"])

    def test_decisive_verdict_requires_quote_and_locator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.write_fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["evidence"][0]["quote"] = ""
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires quote and locator"):
                papertrail.build_audit(report, manifest)

    def test_retraction_and_version_conflict_fail_checklist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.write_fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["sources"][0]["publication_status"] = "retracted"
            data["sources"][0]["version_conflict"] = True
            manifest.write_text(json.dumps(data), encoding="utf-8")
            audit = papertrail.build_audit(report, manifest)
        checklist = audit["reproducibility_checklist"]
        self.assertEqual(checklist["publication_status"]["status"], "FAIL")
        self.assertEqual(checklist["version_conflicts"]["status"], "FAIL")

    def test_ai_assisted_draft_cannot_assign_decisive_verdict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.write_fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["evidence"][0]["review_method"] = "ai_assisted"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must remain UNREVIEWED"):
                papertrail.build_audit(report, manifest)

    def test_decisive_verdict_requires_a_real_human_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.write_fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["evidence"][0]["reviewer_id"] = "ai-reviewer"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "accountable human reviewer"):
                papertrail.build_audit(report, manifest)

    def test_review_history_is_validated_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.write_fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["evidence"][0]["id"] = "E001"
            data["review_history"] = [
                {
                    "event_id": "H001",
                    "action": "created",
                    "evidence_id": "E001",
                    "performed_at": "2026-08-31T00:00:00Z",
                    "reviewer_id": "reviewer-a",
                    "before": None,
                    "after": data["evidence"][0],
                    "ai_recommendation": {"relation": "potential_support", "score": 0.8},
                }
            ]
            manifest.write_text(json.dumps(data), encoding="utf-8")
            audit = papertrail.build_audit(report, manifest)
        self.assertEqual(audit["claims"][0]["evidence"][0]["id"], "E001")
        self.assertEqual(audit["review_history"][0]["action"], "created")
        self.assertEqual(audit["review_history"][0]["ai_recommendation"]["relation"], "potential_support")

    def test_conflicting_human_reviews_fail_consensus(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.write_fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            conflict = dict(data["evidence"][0])
            conflict.update(
                {
                    "verdict": "CONTRADICTED",
                    "quote": "A second reviewer found the opposite result.",
                    "reviewer_id": "reviewer-b",
                }
            )
            data["evidence"].append(conflict)
            manifest.write_text(json.dumps(data), encoding="utf-8")
            audit = papertrail.build_audit(report, manifest)
        self.assertEqual(audit["reproducibility_checklist"]["review_consensus"]["status"], "FAIL")

    def test_pdf_anchor_is_validated_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.write_fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["evidence"][0]["anchor"] = {
                "kind": "pdf_text",
                "file_sha256": "a" * 64,
                "page": 3,
                "start": 12,
                "end": 30,
                "rects": [{"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.04}],
            }
            manifest.write_text(json.dumps(data), encoding="utf-8")
            audit = papertrail.build_audit(report, manifest)
            rendered = papertrail.render_html(audit)
        self.assertEqual(audit["claims"][0]["evidence"][0]["anchor"]["page"], 3)
        self.assertIn("PDF page 3", rendered)
        self.assertIn("SHA-256 aaaaaaaaaaaa…", rendered)

    def test_pdf_anchor_rejects_invalid_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.write_fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["evidence"][0]["anchor"] = {
                "kind": "pdf_text",
                "file_sha256": "not-a-digest",
                "page": 1,
                "start": 0,
                "end": 4,
            }
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be a SHA-256 digest"):
                papertrail.build_audit(report, manifest)

    def test_html_escapes_report_content(self):
        with tempfile.TemporaryDirectory() as directory:
            report, manifest = self.write_fixture(Path(directory))
            audit = papertrail.build_audit(report, manifest)
            audit["claims"][0]["statement"] = "<script>alert(1)</script>"
            rendered = papertrail.render_html(audit)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertIn('class="graph-wrap"', rendered)
        self.assertIn('role="img" aria-labelledby="graph-title graph-desc"', rendered)
        self.assertIn("Claim-to-source evidence graph", rendered)

    def test_cli_writes_pages_ready_site(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.write_fixture(root)
            output = root / "site"
            self.assertEqual(
                papertrail.main([str(report), "--manifest", str(manifest), "--output-dir", str(output)]),
                0,
            )
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "audit.json").is_file())


if __name__ == "__main__":
    unittest.main()
