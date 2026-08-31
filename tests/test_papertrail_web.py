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
MODULE = SCRIPTS / "papertrail_web.py"
SPEC = importlib.util.spec_from_file_location("papertrail_web", MODULE)
assert SPEC and SPEC.loader
papertrail_web = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = papertrail_web
SPEC.loader.exec_module(papertrail_web)


class PaperTrailWebTests(unittest.TestCase):
    def fixtures(self, root: Path) -> tuple[Path, Path]:
        report = root / "report.md"
        report.write_text("# Demo\n\n## Claims\n- [C001] A checked claim. [@source]\n", encoding="utf-8")
        manifest = root / "evidence.json"
        manifest.write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "id": "source",
                            "title": "Source title",
                            "authors": ["Researcher"],
                            "year": 2026,
                            "url": "https://example.org/source",
                            "publication_status": "active",
                            "version_conflict": False,
                        }
                    ],
                    "evidence": [
                        {
                            "claim_id": "C001",
                            "source_id": "source",
                            "verdict": "SUPPORTED",
                            "quote": "A checked claim.",
                            "locator": "Results",
                            "reviewer_id": "reviewer-a",
                            "reviewed_at": "2026-08-31",
                            "review_method": "human",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return report, manifest

    def test_embedded_demo_cannot_close_json_script(self):
        rendered = papertrail_web.render_app_html("</script><script>alert(1)</script>", "{}")
        self.assertNotIn("</script><script>alert(1)</script>", rendered)
        self.assertIn("<\\/script>", rendered)

    def test_build_site_writes_playground_and_static_demo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.fixtures(root)
            output = root / "site"
            papertrail_web.build_site(output, report, manifest)
            app = (output / "index.html").read_text(encoding="utf-8")
            app_js = (output / "assets" / "app.js").read_text(encoding="utf-8")
            integrity_js = (output / "assets" / "integrity-network.js").read_text(encoding="utf-8")
            reviewer_js = (output / "assets" / "governed-review.js").read_text(encoding="utf-8")
            i18n_js = (output / "assets" / "i18n.js").read_text(encoding="utf-8")
            app_css = (output / "assets" / "app.css").read_text(encoding="utf-8")
            demo_audit = json.loads((output / "demo" / "audit.json").read_text(encoding="utf-8"))
            self.assertTrue((output / "assets" / "app.js").is_file())
            self.assertTrue((output / "assets" / "i18n.js").is_file())
            self.assertTrue((output / "assets" / "app.css").is_file())
            self.assertTrue((output / "assets" / "integrity-network.js").is_file())
            self.assertTrue((output / "assets" / "governed-review.js").is_file())
            self.assertTrue((output / "demo" / "index.html").is_file())
            self.assertTrue((output / "demo" / "audit.json").is_file())
            self.assertTrue((output / ".nojekyll").is_file())
        self.assertIn("Private by design", app)
        self.assertIn("Audit locally", app)
        self.assertIn("Add source and check integrity", app)
        self.assertIn("Research Integrity Network", app)
        self.assertIn("Governed AI Reviewer", app)
        self.assertIn("Draft governed review", app)
        self.assertIn("Evidence graph", i18n_js)
        self.assertIn("Claims on the left connected to cited sources on the right", app_js)
        self.assertIn('id="language-select"', app)
        self.assertIn("简体中文", app)
        self.assertIn("追溯每一个结论背后的证据", i18n_js)
        self.assertIn("papertrail-language", app_js)
        self.assertIn("SUGGESTION_NOT_A_VERDICT", reviewer_js)
        self.assertIn("manual_required", integrity_js)
        self.assertIn("checklistLabels[language]", app_js)
        self.assertIn('id="pdf-file"', app)
        self.assertIn('id="attach-selection"', app)
        self.assertIn('id="pdf-passages"', app)
        self.assertNotIn("__APP_CSS__", app)
        self.assertIn('id="app-css"', app)
        self.assertIn("pdfjs-dist@4.10.38", app_js)
        self.assertIn("tesseract.js@6.0.1", app_js)
        self.assertIn("file_sha256: pdfFileHash", app_js)
        self.assertIn("kind: pdfExtractionKind", app_js)
        self.assertIn("function passageRanges", app_js)
        self.assertIn("pendingPdfSelection = { ...passage, rects: [] }", app_js)
        self.assertIn("<style>${appCss}</style>", app_js)
        self.assertNotIn('document.querySelector("style")', app_js)
        self.assertIn(".passage-card", app_css)
        self.assertIn("PDF 证据工作区", i18n_js)
        self.assertEqual(demo_audit["reproducibility_checklist"]["review_provenance"]["status"], "PASS")

    def test_cli_builds_pages_ready_site(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, manifest = self.fixtures(root)
            output = root / "site"
            result = papertrail_web.main(
                [
                    "--output-dir",
                    str(output),
                    "--demo-report",
                    str(report),
                    "--demo-manifest",
                    str(manifest),
                ]
            )
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
