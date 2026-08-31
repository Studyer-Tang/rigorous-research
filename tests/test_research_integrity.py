from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "research_integrity.py"
SPEC = importlib.util.spec_from_file_location("research_integrity", MODULE)
assert SPEC and SPEC.loader
integrity = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = integrity
SPEC.loader.exec_module(integrity)

CROSSREF = {
    "message": {
        "DOI": "10.1000/Study",
        "title": ["A Trial Result"],
        "author": [{"given": "Ada", "family": "Lovelace"}],
        "published-online": {"date-parts": [[2024]]},
        "URL": "https://doi.org/10.1000/study",
        "type": "journal-article",
        "updated-by": [
            {
                "DOI": "10.1000/notice",
                "type": "retraction",
                "label": "Retraction notice",
                "updated": {"date-time": "2026-01-02T00:00:00Z"},
            }
        ],
        "relation": {"has-preprint": [{"id-type": "doi", "id": "10.1000/preprint"}]},
    }
}

OPENALEX = {
    "id": "https://openalex.org/W123",
    "display_name": "A Trial Result",
    "publication_year": 2024,
    "doi": "https://doi.org/10.1000/study",
    "ids": {"doi": "https://doi.org/10.1000/study", "pmid": "https://pubmed.ncbi.nlm.nih.gov/42"},
    "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
    "primary_location": {"landing_page_url": "https://doi.org/10.1000/study"},
    "type": "article",
    "is_retracted": True,
    "updated_date": "2026-01-03T00:00:00Z",
}

PUBMED = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>42</PMID><Article>
<ArticleTitle>A Trial Result</ArticleTitle><Journal><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue></Journal>
<AuthorList><Author><ForeName>Ada</ForeName><LastName>Lovelace</LastName></Author></AuthorList>
<PublicationTypeList><PublicationType>Retracted Publication</PublicationType></PublicationTypeList>
</Article><CommentsCorrectionsList><CommentsCorrections RefType="RetractionIn"><PMID>43</PMID><RefSource>Notice</RefSource></CommentsCorrections></CommentsCorrectionsList>
</MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1000/study</ArticleId></ArticleIdList></PubmedData>
</PubmedArticle></PubmedArticleSet>"""


class ResearchIntegrityTests(unittest.TestCase):
    def test_identifiers_are_normalized_without_guessing_titles(self):
        self.assertEqual(
            integrity.normalize_identifier("https://doi.org/10.1000/Study"), {"kind": "doi", "value": "10.1000/study"}
        )
        self.assertEqual(integrity.normalize_identifier("PMID: 42"), {"kind": "pmid", "value": "42"})
        self.assertEqual(
            integrity.normalize_identifier("https://openalex.org/W123"), {"kind": "openalex", "value": "W123"}
        )
        with self.assertRaises(ValueError):
            integrity.normalize_identifier("a paper title")

    def test_provider_parsers_preserve_events_and_response_hashes(self):
        checked = "2026-08-31T00:00:00+00:00"
        crossref = integrity.parse_crossref(json.dumps(CROSSREF).encode(), checked, "fixture:crossref.json")
        openalex = integrity.parse_openalex(json.dumps(OPENALEX).encode(), checked, "fixture:openalex.json")
        pubmed = integrity.parse_pubmed(PUBMED, checked, "fixture:pubmed.xml")
        self.assertEqual(crossref["events"][0]["type"], "retraction")
        self.assertEqual(crossref["versions"][0]["role"], "preprint")
        self.assertEqual(openalex["events"][0]["type"], "retraction")
        self.assertEqual(pubmed["identity"]["doi"], "10.1000/study")
        self.assertTrue(pubmed["response_sha256"])

    def test_aggregate_reports_crossmark_gap_and_high_risk_status(self):
        checked = "2026-08-31T00:00:00+00:00"
        checks = [
            integrity.parse_crossref(json.dumps(CROSSREF).encode(), checked, "fixture:crossref.json"),
            integrity.parse_openalex(json.dumps(OPENALEX).encode(), checked, "fixture:openalex.json"),
            integrity.parse_pubmed(PUBMED, checked, "fixture:pubmed.xml"),
            integrity.crossmark_manual({"kind": "doi", "value": "10.1000/study"}, checked),
        ]
        network = integrity.aggregate_network(
            {"kind": "doi", "value": "10.1000/study"}, checks, checked, list(integrity.PROVIDERS)
        )
        self.assertEqual(network["status"], "REVIEW_REQUIRED")
        self.assertEqual(network["high_risk_events"], ["retraction"])
        self.assertEqual(network["coverage_gaps"][0]["provider"], "crossmark")
        self.assertTrue(network["version_graph"]["edges"])
        self.assertIn("absence", network["interpretation"].casefold())

    def test_update_notice_is_not_mislabeled_as_retracted_work(self):
        checked = "2026-08-31T00:00:00+00:00"
        notice = json.loads(json.dumps(CROSSREF))
        notice["message"].pop("updated-by")
        notice["message"]["update-to"] = [
            {"DOI": "10.1000/original", "type": "retraction", "label": "Retracts another work"}
        ]
        check = integrity.parse_crossref(json.dumps(notice).encode(), checked, "fixture:notice.json")
        network = integrity.aggregate_network({"kind": "doi", "value": "10.1000/study"}, [check], checked, ["crossref"])
        self.assertEqual(network["high_risk_events"], [])
        self.assertEqual(network["integrity_events"][0]["direction"], "updates_related")

    def test_fixture_replay_writes_json_markdown_and_html(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures = {}
            for provider, value, suffix in (
                ("crossref", json.dumps(CROSSREF).encode(), ".json"),
                ("openalex", json.dumps(OPENALEX).encode(), ".json"),
                ("pubmed", PUBMED, ".xml"),
            ):
                path = root / f"{provider}{suffix}"
                path.write_bytes(value)
                fixtures[provider] = path
            output = root / "site"
            result = integrity.main(
                [
                    "check",
                    "10.1000/study",
                    "--checked-at",
                    "2026-08-31T00:00:00+00:00",
                    "--fixture",
                    f"crossref={fixtures['crossref']}",
                    "--fixture",
                    f"openalex={fixtures['openalex']}",
                    "--fixture",
                    f"pubmed={fixtures['pubmed']}",
                    "--output-dir",
                    str(output),
                ]
            )
            self.assertEqual(result, 1)
            self.assertEqual(json.loads((output / "integrity.json").read_text())["kind"], "research-integrity-network")
            self.assertIn("```mermaid", (output / "integrity.md").read_text(encoding="utf-8"))
            self.assertIn("Coverage gaps", (output / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
