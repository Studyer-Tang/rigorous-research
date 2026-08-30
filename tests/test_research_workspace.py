from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "research_workspace.py"
SPEC = importlib.util.spec_from_file_location("research_workspace", MODULE_PATH)
assert SPEC and SPEC.loader
rw = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rw)


class ResearchWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def workspace(self) -> Path:
        return rw.initialize(
            self.root,
            "research-case",
            "mathematics",
            "Does the parameterized identity hold?",
            "The identity holds for every admissible parameter.",
        )

    def add_task(self, workspace: Path, *, depends_on=None, deliverable="") -> str:
        argv = [
            "task",
            str(workspace),
            "--title",
            "Run an exact calculation",
            "--kind",
            "computation",
            "--acceptance",
            "An exact artifact is generated and checked.",
        ]
        if depends_on:
            argv.extend(["--depends-on", *depends_on])
        if deliverable:
            argv.extend(["--deliverable", deliverable])
        self.assertEqual(rw.main(argv), 0)
        _, data = rw.load(workspace)
        return data["tasks"][-1]["id"]

    def test_init_creates_workspace_and_case(self):
        workspace = self.workspace()
        self.assertTrue(workspace.is_file())
        self.assertTrue((workspace.parent / "case.json").is_file())
        _, data = rw.load(workspace)
        self.assertEqual(data["stage"], "SCOPING")
        self.assertEqual(data["domain"], "mathematics")
        self.assertTrue(data["release_policy"]["independent_review_required"])

    def test_dependency_blocks_premature_execution(self):
        workspace = self.workspace()
        first = self.add_task(workspace)
        second = self.add_task(workspace, depends_on=[first])
        result = rw.main(
            [
                "run",
                str(workspace),
                "--task",
                second,
                "--label",
                "premature run",
                "--",
                sys.executable,
                "-c",
                "print('should not run')",
            ]
        )
        self.assertEqual(result, 2)
        _, data = rw.load(workspace)
        self.assertEqual(data["runs"], [])

    def test_run_captures_command_output_and_hash(self):
        workspace = self.workspace()
        task = self.add_task(workspace, deliverable="result.txt")
        result = rw.main(
            [
                "run",
                str(workspace),
                "--task",
                task,
                "--label",
                "exact fixture",
                "--output",
                "result.txt",
                "--complete",
                "--",
                sys.executable,
                "-c",
                "from pathlib import Path; Path('result.txt').write_text('exact=17', encoding='utf-8')",
            ]
        )
        self.assertEqual(result, 0)
        _, data = rw.load(workspace)
        self.assertEqual(data["tasks"][0]["status"], "DONE")
        self.assertEqual(data["runs"][0]["returncode"], 0)
        self.assertEqual(data["runs"][0]["outputs"][0]["file"], "result.txt")
        errors, _ = rw.validate_workspace(data, workspace)
        self.assertEqual(errors, [])

    def test_output_tampering_is_detected(self):
        workspace = self.workspace()
        task = self.add_task(workspace, deliverable="result.txt")
        result = rw.main(
            [
                "run",
                str(workspace),
                "--task",
                task,
                "--label",
                "exact fixture",
                "--output",
                "result.txt",
                "--complete",
                "--",
                sys.executable,
                "-c",
                "from pathlib import Path; Path('result.txt').write_text('first', encoding='utf-8')",
            ]
        )
        self.assertEqual(result, 0)
        (workspace.parent / "result.txt").write_text("changed", encoding="utf-8")
        _, data = rw.load(workspace)
        errors, _ = rw.validate_workspace(data, workspace)
        self.assertTrue(any("checksum mismatch" in error for error in errors))
        self.assertEqual(rw.main(["rehash-run", str(workspace), "--id", "R001"]), 0)
        _, accepted = rw.load(workspace)
        errors, _ = rw.validate_workspace(accepted, workspace)
        self.assertEqual(errors, [])

    def test_dependency_cycle_is_rejected(self):
        workspace = self.workspace()
        _, data = rw.load(workspace)
        data["tasks"] = [
            {
                "id": "W001",
                "title": "first",
                "kind": "proof",
                "acceptance": "closed proof",
                "depends_on": ["W002"],
                "deliverable": "",
                "status": "PLANNED",
                "note": "",
            },
            {
                "id": "W002",
                "title": "second",
                "kind": "replication",
                "acceptance": "independent check",
                "depends_on": ["W001"],
                "deliverable": "",
                "status": "PLANNED",
                "note": "",
            },
        ]
        errors, _ = rw.validate_workspace(data, workspace)
        self.assertTrue(any("dependency cycle" in error for error in errors))

    def test_source_links_to_existing_claim(self):
        workspace = self.workspace()
        result = rw.main(
            [
                "source",
                str(workspace),
                "--citation",
                "A primary source",
                "--role",
                "primary",
                "--url",
                "https://example.test/paper",
                "--supports",
                "C001",
            ]
        )
        self.assertEqual(result, 0)
        _, data = rw.load(workspace)
        self.assertEqual(data["sources"][0]["supports"], ["C001"])
        errors, _ = rw.validate_workspace(data, workspace)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
