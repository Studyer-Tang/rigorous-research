from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import research_io as rio


class ResearchIOTests(unittest.TestCase):
    def test_json_hashes_and_portable_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_path = root / "nested" / "record.json"
            rio.write_json(data_path, {"b": 2, "a": 1})
            self.assertEqual(rio.load_json_object(data_path), {"a": 1, "b": 2})
            self.assertEqual(rio.portable_locator(data_path, root), "nested/record.json")
            self.assertEqual(rio.contained_locator(data_path, root), "nested/record.json")
            self.assertEqual(rio.resolve_locator("nested/record.json", root), data_path)
            self.assertEqual(rio.sha256(data_path), rio.sha256_bytes(data_path.read_bytes()))
            self.assertEqual(
                rio.canonical_hash({"a": 1, "b": 2}),
                rio.canonical_hash({"b": 2, "a": 1}),
            )

    def test_json_loader_rejects_non_object_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "list.json"
            path.write_text(json.dumps([1, 2]), encoding="utf-8")
            with self.assertRaises(ValueError):
                rio.load_json_object(path)

    def test_atomic_write_replaces_complete_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            rio.atomic_write_json(path, {"version": 1})
            rio.atomic_write_json(path, {"version": 2})
            self.assertEqual(rio.load_json_object(path), {"version": 2})


if __name__ == "__main__":
    unittest.main()
