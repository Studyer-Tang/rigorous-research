from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "scripts" / "statistics_backend.py"
SPEC = importlib.util.spec_from_file_location("statistics_backend", MODULE)
assert SPEC and SPEC.loader
stats = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stats)


class StatisticsBackendTests(unittest.TestCase):
    def test_iid_and_hac_agree_at_zero_lags(self):
        values = [1.0, 2.0, 4.0, 8.0, 16.0]
        expected = math.sqrt(sum((x - stats.mean(values)) ** 2 for x in values) / len(values) ** 2)
        self.assertAlmostEqual(stats.hac_standard_error(values, 0), expected)

    def test_positive_serial_correlation_inflates_hac_se(self):
        values = [float(index // 8) for index in range(160)]
        self.assertGreater(stats.hac_standard_error(values, 8), stats.hac_standard_error(values, 0))

    def test_holm_and_bh_preserve_original_order(self):
        p_values = [0.04, 0.001, 0.02, 0.9]
        holm = stats.holm(p_values)
        bh = stats.benjamini_hochberg(p_values)
        self.assertEqual([item["p_value"] for item in holm], p_values)
        self.assertEqual([item["p_value"] for item in bh], p_values)
        self.assertTrue(holm[1]["reject"])
        self.assertFalse(holm[0]["reject"])

    def test_block_bootstrap_is_seed_reproducible(self):
        values = [float(index) for index in range(30)]
        first = stats.circular_block_bootstrap_ci(values, 5, 300, 17)
        second = stats.circular_block_bootstrap_ci(values, 5, 300, 17)
        self.assertEqual(first, second)

    def test_ar1_stress_test_exposes_iid_undercoverage(self):
        result = stats.coverage_simulation(120, 0.8, 400, 8, "gaussian", 2026)
        iid = result["methods"]["iid_normal"]["coverage"]
        hac = result["methods"]["newey_west_normal"]["coverage"]
        self.assertLess(iid, 0.75)
        self.assertGreater(hac, iid + 0.1)


if __name__ == "__main__":
    unittest.main()
