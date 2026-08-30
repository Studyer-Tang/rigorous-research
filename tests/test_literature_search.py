from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "literature_search.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("literature_search", MODULE_PATH)
assert SPEC and SPEC.loader
ls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ls)


class LiteratureSearchTests(unittest.TestCase):
    def test_crossref_and_arxiv_duplicate_by_doi(self):
        crossref = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1000/ABC",
                        "title": ["A Precise Mathematical Result"],
                        "author": [{"given": "Ada", "family": "Lovelace"}],
                        "published-online": {"date-parts": [[2024]]},
                        "URL": "https://doi.org/10.1000/abc",
                        "container-title": ["Journal"],
                        "type": "journal-article",
                    }
                ]
            }
        }
        atom = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
          <entry><id>https://arxiv.org/abs/2401.00001v2</id><published>2024-01-01T00:00:00Z</published>
          <title>A precise mathematical result</title><summary>Proof.</summary>
          <author><name>Ada Lovelace</name></author><arxiv:doi>https://doi.org/10.1000/abc</arxiv:doi></entry>
        </feed>"""
        left = ls.parse_crossref(json.dumps(crossref).encode())
        right = ls.parse_arxiv(atom.encode())
        records, decisions = ls.merge_records(left + right)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["providers"], ["arxiv", "crossref"])
        self.assertEqual(decisions[0]["reason"], "same-doi")

    def test_fuzzy_merge_requires_author_and_year_compatibility(self):
        base = {
            "title": "Inference for dependent financial time series",
            "authors": ["Qingjun Tang"],
            "year": 2025,
            "doi": "",
            "arxiv_id": "",
            "url": "a",
            "venue": "",
            "abstract": "",
            "record_type": "article",
            "providers": ["crossref"],
        }
        variant = dict(
            base,
            title="Inference in dependent financial time-series",
            url="b",
            providers=["arxiv"],
        )
        records, decisions = ls.merge_records([base, variant], threshold=0.85)
        self.assertEqual(len(records), 2)
        self.assertTrue(decisions[0]["reason"].startswith("fuzzy-title"))
        self.assertEqual(decisions[0]["disposition"], "REVIEW_REQUIRED")
        different_author = dict(variant, authors=["Another Author"])
        records, _ = ls.merge_records([base, different_author], threshold=0.85)
        self.assertEqual(len(records), 2)

    def test_same_title_different_authors_and_years_is_not_merged(self):
        first = {
            "title": "Editorial",
            "authors": ["First Author"],
            "year": 1999,
            "doi": "",
            "arxiv_id": "",
            "url": "a",
            "venue": "",
            "abstract": "",
            "record_type": "editorial",
            "providers": ["crossref"],
        }
        second = dict(first, authors=["Second Author"], year=2024, url="b")
        records, decisions = ls.merge_records([first, second])
        self.assertEqual(len(records), 2)
        self.assertEqual(decisions[0]["disposition"], "REVIEW_REQUIRED")

    def test_unicode_titles_remain_distinguishable(self):
        self.assertEqual(ls.normalize_title("六维球面：复结构"), "六维球面 复结构")

    def test_bibtex_keys_are_unique(self):
        record = {
            "title": "A result about matrices",
            "authors": ["Ada Lovelace"],
            "year": 2024,
            "doi": "10.1/a",
            "arxiv_id": "",
            "url": "https://example.test",
            "venue": "Journal",
        }
        rendered = ls.render_bibtex([record, dict(record, doi="10.1/b")])
        self.assertIn("lovelace2024result", rendered)
        self.assertIn("lovelace2024result2", rendered)


if __name__ == "__main__":
    unittest.main()
