from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "papertrail_import.py"
SPEC = importlib.util.spec_from_file_location("papertrail_import", MODULE)
assert SPEC and SPEC.loader
papertrail_import = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = papertrail_import
SPEC.loader.exec_module(papertrail_import)


class PaperTrailImportTests(unittest.TestCase):
    def test_candidate_claims_prefers_empirical_sentences(self):
        text = (
            "# Study title\n\nThis paragraph only introduces the topic. "
            "The experiment showed a 17% increase in accuracy. "
            "Contact the authors for more information."
        )
        self.assertEqual(
            papertrail_import.candidate_claims(text), ["The experiment showed a 17% increase in accuracy."]
        )

    def test_html_parser_excludes_scripts_and_navigation(self):
        parser = papertrail_import.ArticleTextParser()
        parser.feed(
            "<title>Useful study</title><nav>Navigation text should not appear anywhere.</nav>"
            "<article><h1>Result</h1><p>The measured value increased by 18 percent in the study.</p></article>"
            "<script>stealCredentials()</script>"
        )
        title, body = parser.result()
        self.assertEqual(title, "Useful study")
        self.assertIn("increased by 18 percent", body)
        self.assertNotIn("Navigation", body)
        self.assertNotIn("stealCredentials", body)

    def test_pdf_extraction_uses_page_boundaries(self):
        fake_reader = types.SimpleNamespace(
            metadata={"/Title": "PDF study"},
            pages=[
                types.SimpleNamespace(extract_text=lambda: "First page result."),
                types.SimpleNamespace(extract_text=lambda: "Second page result."),
            ],
        )
        fake_module = types.SimpleNamespace(PdfReader=lambda path: fake_reader)
        with patch.dict(sys.modules, {"pypdf": fake_module}):
            title, body = papertrail_import.extract_pdf(Path("study.pdf"))
        self.assertEqual(title, "PDF study")
        self.assertIn("### Page 1", body)
        self.assertIn("### Page 2", body)

    def test_crossref_source_records_retraction(self):
        source = papertrail_import.crossref_source(
            "10.1234/example",
            {
                "message": {
                    "title": ["Retracted work"],
                    "author": [{"given": "A.", "family": "Researcher"}],
                    "issued": {"date-parts": [[2025]]},
                    "URL": "https://doi.org/10.1234/example",
                    "type": "journal-article",
                    "update-to": [{"type": "retraction"}],
                }
            },
        )
        self.assertEqual(source["publication_status"], "retracted")
        self.assertIn("retraction", source["version_notes"])

    def test_private_urls_are_rejected(self):
        with (
            patch.object(papertrail_import.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 0))]),
            self.assertRaisesRegex(ValueError, "non-public"),
        ):
            papertrail_import.validate_public_url("http://example.test/private")

    def test_assist_cli_marks_every_candidate_unreviewed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.md"
            report.write_text("The analysis showed a 12% increase in retention.", encoding="utf-8")
            output = root / "assist.json"
            self.assertEqual(papertrail_import.main(["assist", str(report), "--output", str(output)]), 0)
            packet = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(packet["status"], "DRAFT_REQUIRES_HUMAN_REVIEW")
        self.assertEqual(packet["claims"][0]["status"], "UNREVIEWED")


if __name__ == "__main__":
    unittest.main()
