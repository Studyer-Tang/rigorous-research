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
            demo_audit = json.loads((output / "demo" / "audit.json").read_text(encoding="utf-8"))
            self.assertTrue((output / "demo" / "index.html").is_file())
            self.assertTrue((output / "demo" / "audit.json").is_file())
            self.assertTrue((output / ".nojekyll").is_file())
        self.assertIn("Private by design", app)
        self.assertIn("Audit locally", app)
        self.assertIn("Add source from Crossref", app)
        self.assertIn("Draft claim candidates", app)
        self.assertIn("Evidence graph", app)
        self.assertIn("Claims on the left connected to cited sources on the right", app)
        self.assertIn('id="language-select"', app)
        self.assertIn("简体中文", app)
        self.assertIn("追溯每一个结论背后的证据", app)
        self.assertIn("papertrail-language", app)
        self.assertIn("checklistLabels[language]", app)
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
