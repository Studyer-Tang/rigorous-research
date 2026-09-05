from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
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

    def test_malformed_collections_are_reported_without_crashing(self):
        workspace = self.workspace()
        _, original = rw.load(workspace)
        for collection in ("tasks", "sources", "runs"):
            for value in (None, {}, "invalid", [None], ["invalid"], [{"id": []}], [{"id": None}]):
                for release in (False, True):
                    with self.subTest(collection=collection, value=value, release=release):
                        data = copy.deepcopy(original)
                        data[collection] = value
                        errors, _ = rw.validate_workspace(data, workspace, release=release)
                        self.assertTrue(errors)
                        self.assertEqual(data[collection], value)

    def test_malformed_relationships_and_outputs_are_rejected(self):
        workspace = self.workspace()
        _, original = rw.load(workspace)
        cases = (
            ("tasks", "W001", "depends_on", "list of task IDs"),
            ("sources", "S001", "supports", "list of claim IDs"),
            ("runs", "R001", "outputs", "list of objects"),
            ("runs", "R001", "task_id", "must be a string"),
        )
        for collection, item_id, field, message in cases:
            for value in (None, {}, 1, [None], ["invalid"] if field == "outputs" else [{}]):
                with self.subTest(field=field, value=value):
                    data = copy.deepcopy(original)
                    data[collection] = [{"id": item_id, field: value}]
                    errors, _ = rw.validate_workspace(data, workspace)
                    self.assertTrue(any(message in error for error in errors), errors)

    def test_duplicate_ids_return_a_diagnostic(self):
        workspace = self.workspace()
        task = self.add_task(workspace)
        _, data = rw.load(workspace)
        data["tasks"].append(copy.deepcopy(data["tasks"][0]))
        errors, _ = rw.validate_workspace(data, workspace)
        self.assertIn(f"duplicate task IDs: {task}", errors)

    def test_long_dependency_chain_and_cycle(self):
        workspace = self.workspace()
        _, data = rw.load(workspace)
        data["tasks"] = [
            {
                "id": f"W{number:03d}",
                "title": "Check a lemma",
                "kind": "proof",
                "acceptance": "Proof checked",
                "status": "PLANNED",
                "depends_on": [f"W{number + 1:03d}"] if number < 999 else [],
            }
            for number in range(1, 1000)
        ]
        errors, _ = rw.validate_workspace(data, workspace)
        self.assertEqual(errors, [])
        data["tasks"][-1]["depends_on"] = ["W001"]
        errors, _ = rw.validate_workspace(data, workspace)
        self.assertTrue(any("dependency cycle" in error for error in errors))

    def test_validate_cli_reports_malformed_workspace(self):
        workspace = self.workspace()
        _, data = rw.load(workspace)
        data["tasks"] = [None]
        rw.atomic_json(workspace, data)
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            result = rw.main(["validate", str(workspace)])
        self.assertEqual(result, 1)
        self.assertIn("task entries require string IDs", output.getvalue())

    def test_next_actions_respects_dependencies_and_preserves_files(self):
        workspace = self.workspace()
        first = self.add_task(workspace)
        second = self.add_task(workspace, depends_on=[first])
        original = workspace.read_bytes()
        journal = (workspace.parent / "research-journal.jsonl").read_bytes()
        _, data = rw.load(workspace)
        result = rw.next_actions(data, workspace)
        self.assertEqual(
            [(item["task_id"], item["action"]) for item in result["actions"]],
            [(first, "EXECUTE_READY_TASK"), (second, "WAIT_FOR_DEPENDENCIES")],
        )
        self.assertEqual(result["actions"][1]["blocked_by"], [first])
        self.assertFalse(result["release_ready"])
        self.assertTrue(result["release_gaps"])
        self.assertEqual(workspace.read_bytes(), original)
        self.assertEqual((workspace.parent / "research-journal.jsonl").read_bytes(), journal)
        data["tasks"] = [None]
        self.assertEqual(rw.next_actions(data, workspace)["status"], "REPAIR_REQUIRED")

    def test_failed_launch_is_recorded_and_followup_identifies_failure(self):
        workspace = self.workspace()
        task = self.add_task(workspace)
        result = rw.main(
            [
                "run",
                str(workspace),
                "--task",
                task,
                "--label",
                "missing tool",
                "--complete",
                "--",
                str(self.root / "missing-executable"),
            ]
        )
        self.assertEqual(result, 127)
        _, data = rw.load(workspace)
        self.assertEqual(data["tasks"][0]["status"], "PLANNED")
        self.assertTrue(data["runs"][0]["launch_error"])
        self.assertEqual(rw.validate_workspace(data, workspace)[0], [])
        self.assertEqual(rw.next_actions(data, workspace)["actions"][0]["action"], "INVESTIGATE_FAILED_RUN")
        # A later attempt uses a fresh run ID and retains the failure evidence.
        result = rw.main(
            [
                "run",
                str(workspace),
                "--task",
                task,
                "--label",
                "retry",
                "--",
                sys.executable,
                "-c",
                "print('recovered')",
            ]
        )
        self.assertEqual(result, 0)
        _, data = rw.load(workspace)
        self.assertEqual([run["id"] for run in data["runs"]], ["R001", "R002"])
        self.assertEqual(rw.next_actions(data, workspace)["actions"][0]["action"], "RESUME_AND_CHECK_ACCEPTANCE")

    def test_invalid_workspace_does_not_launch_a_command(self):
        workspace = self.workspace()
        task = self.add_task(workspace)
        _, data = rw.load(workspace)
        data["sources"] = [None]
        rw.atomic_json(workspace, data)
        result = rw.main(
            [
                "run",
                str(workspace),
                "--task",
                task,
                "--label",
                "blocked",
                "--",
                sys.executable,
                "-c",
                "raise RuntimeError('must not execute')",
            ]
        )
        self.assertEqual(result, 2)
        self.assertFalse((workspace.parent / "artifacts" / "runs").exists())


if __name__ == "__main__":
    unittest.main()
