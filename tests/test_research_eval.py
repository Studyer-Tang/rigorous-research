from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "research_eval.py"
SPEC = importlib.util.spec_from_file_location("research_eval", MODULE)
assert SPEC and SPEC.loader
evaluation = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evaluation
SPEC.loader.exec_module(evaluation)


class ResearchEvaluationTests(unittest.TestCase):
    def test_release_and_mutation_benchmark_passes(self):
        result = evaluation.run_benchmark(ROOT, ROOT / "evals" / "benchmark.json")
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["passed"], result["total"])
        self.assertGreaterEqual(result["total"], 8)

    def test_json_pointer_updates_nested_array(self):
        document = {"items": [{"status": "DONE"}]}
        evaluation.set_pointer(document, "/items/0/status", "PLANNED")
        self.assertEqual(document["items"][0]["status"], "PLANNED")


if __name__ == "__main__":
    unittest.main()
