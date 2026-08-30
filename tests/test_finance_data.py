from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "finance_data.py"
sys.path.insert(0, str(MODULE.parent))
SPEC = importlib.util.spec_from_file_location("finance_data", MODULE)
assert SPEC and SPEC.loader
finance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(finance)


class FinanceDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self, raw: bytes, as_of: str):
        return finance.create_snapshot(
            raw,
            self.root,
            provider="Test Exchange",
            dataset="daily prices",
            url="https://data.test/prices",
            query={"symbol": "ABC"},
            as_of=as_of,
            revision_policy="append-only fixture",
            schema="date,close",
            units="USD",
            timezone="UTC",
            calendar="weekdays",
            identifier_system="fixture symbol",
            adjustment_policy="unadjusted",
            license_text="test only",
            extension="csv",
            retrieved_at="2026-01-01T00:00:00+00:00",
        )

    def test_snapshot_verifies_and_replays_offline(self):
        raw, manifest, _ = self.snapshot(b"date,close\n2025-01-01,10\n", "2025-01-01")
        self.assertEqual(finance.verify(manifest)[0], [])
        self.assertEqual(raw.read_bytes(), b"date,close\n2025-01-01,10\n")

    def test_tampering_is_detected(self):
        raw, manifest, _ = self.snapshot(b"date,close\n2025-01-01,10\n", "2025-01-01")
        raw.write_bytes(b"revised silently")
        self.assertIn("raw snapshot checksum mismatch", finance.verify(manifest)[0])

    def test_vintage_diff_preserves_both_snapshots(self):
        old_raw, old_manifest, _ = self.snapshot(b"date,close\n2025-01-01,10\n", "2025-01-01")
        new_raw, new_manifest, _ = self.snapshot(b"date,close\n2025-01-01,11\n", "2025-01-02")
        result = finance.compare(old_manifest, new_manifest)
        self.assertTrue(result["raw_changed"])
        self.assertTrue(old_raw.is_file() and new_raw.is_file())

    def test_fred_adapter_discloses_latest_revised_semantics(self):
        request = finance.provider_request("fred-csv", "DGS10")
        self.assertIn("not point-in-time", request["revision_policy"])
        self.assertIn("DGS10", request["url"])


if __name__ == "__main__":
    unittest.main()
