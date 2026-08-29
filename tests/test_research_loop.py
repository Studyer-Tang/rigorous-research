from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "research_loop.py"


class ResearchLoopCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        result = self.run_cli(
            "init",
            str(self.root),
            "sample-case",
            "--mode",
            "proof",
            "--objective",
            "Prove the exact frozen target",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.case = self.root / "sample-case" / "case.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )

    def add_complete_verified_record(self) -> Path:
        artifact = self.root / "sample-case" / "artifacts" / "proof.txt"
        artifact.write_text("independent exact verification\n", encoding="utf-8")
        commands = [
            ("obligation", str(self.case), "--statement", "The witness satisfies every defining relation"),
            ("criterion", str(self.case), "--statement", "The exact target is established"),
            (
                "evidence",
                str(self.case),
                "--kind",
                "proof",
                "--summary",
                "Independent derivation checks every defining relation",
                "--file",
                str(artifact),
                "--independent",
            ),
            ("link", str(self.case), "--obligation", "O001", "--evidence", "E001", "--status", "SUPPORTED"),
            ("satisfy", str(self.case), "--criterion", "C001", "--evidence", "E001", "--status", "PASSED"),
            (
                "review",
                str(self.case),
                "--verdict",
                "accept",
                "--reviewer",
                "independent-reviewer",
                "--reason",
                "Raw proof and artifact checked against the frozen target",
                "--evidence",
                "E001",
            ),
            (
                "verdict",
                str(self.case),
                "--status",
                "VERIFIED",
                "--branch-status",
                "VERIFIED",
                "--safe-claim",
                "The exact frozen target is established under its stated assumptions",
                "--unsupported-claim",
                "No broader parameter range or novelty claim is established",
            ),
        ]
        for command in commands:
            result = self.run_cli(*command)
            self.assertEqual(result.returncode, 0, result.stderr)
        return artifact

    def test_init_creates_valid_resumable_case(self) -> None:
        result = self.run_cli("validate", str(self.case))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(self.case.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["interpretations"][0]["id"], "LITERAL")
        self.assertTrue((self.case.parent / "journal.jsonl").exists())

    def test_supported_obligation_requires_evidence(self) -> None:
        self.assertEqual(
            self.run_cli("obligation", str(self.case), "--statement", "Critical proposition").returncode,
            0,
        )
        self.assertEqual(
            self.run_cli("link", str(self.case), "--obligation", "O001", "--status", "SUPPORTED").returncode,
            0,
        )
        result = self.run_cli("validate", str(self.case))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has no linked evidence", result.stdout)

    def test_verified_release_passes_all_structural_gates(self) -> None:
        self.add_complete_verified_record()
        result = self.run_cli("validate", str(self.case), "--release", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["errors"], [])

    def test_checksum_tampering_fails_release(self) -> None:
        artifact = self.add_complete_verified_record()
        artifact.write_text("changed after registration\n", encoding="utf-8")
        result = self.run_cli("validate", str(self.case), "--release")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum mismatch", result.stdout)

    def test_release_rejects_model_only_completion(self) -> None:
        result = self.run_cli(
            "verdict",
            str(self.case),
            "--status",
            "VERIFIED",
            "--branch-status",
            "VERIFIED",
            "--safe-claim",
            "Claimed complete",
            "--unsupported-claim",
            "Anything stronger",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        release = self.run_cli("validate", str(self.case), "--release")
        self.assertNotEqual(release.returncode, 0)
        self.assertIn("independent review verdict", release.stdout)
        self.assertIn("critical obligation", release.stdout)

    def test_repeated_progress_signature_warns(self) -> None:
        first = self.run_cli(
            "round",
            str(self.case),
            "--goal",
            "Try method A",
            "--review-status",
            "continue",
            "--review-reason",
            "Gap remains",
            "--progress-signature",
            "same-output",
        )
        second = self.run_cli(
            "round",
            str(self.case),
            "--goal",
            "Try method A again",
            "--review-status",
            "continue",
            "--review-reason",
            "Same gap remains",
            "--progress-signature",
            "same-output",
        )
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertIn("change method", second.stderr)
        validation = self.run_cli("validate", str(self.case))
        self.assertIn("repeat the same progress signature", validation.stdout)

    def test_unknown_evidence_link_is_rejected(self) -> None:
        self.run_cli("obligation", str(self.case), "--statement", "Critical proposition")
        result = self.run_cli(
            "link",
            str(self.case),
            "--obligation",
            "O001",
            "--evidence",
            "E999",
            "--status",
            "SUPPORTED",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown evidence", result.stderr)

    def test_render_and_status_are_machine_usable(self) -> None:
        render = self.run_cli("render", str(self.case))
        self.assertEqual(render.returncode, 0, render.stderr)
        report = self.case.parent / "report.md"
        self.assertIn("## Exact objective", report.read_text(encoding="utf-8"))
        status = self.run_cli("status", str(self.case))
        payload = json.loads(status.stdout)
        self.assertEqual(payload["status"], "ACTIVE")
        self.assertEqual(payload["rounds"], 0)

    def test_source_and_blind_review_packet(self) -> None:
        source = self.run_cli(
            "source",
            str(self.case),
            "--title",
            "Primary formulation",
            "--locator",
            "paper.pdf#page=7",
            "--version",
            "v2",
            "--checked",
        )
        self.assertEqual(source.returncode, 0, source.stderr)
        self.run_cli("obligation", str(self.case), "--statement", "Check the decisive relation")
        packet = self.run_cli("review-packet", str(self.case))
        self.assertEqual(packet.returncode, 0, packet.stderr)
        text = (self.case.parent / "review-packet.md").read_text(encoding="utf-8")
        self.assertIn("No desired verdict is supplied", text)
        self.assertIn("Check the decisive relation", text)
        self.assertNotIn("Strongest safe claim", text)

    def test_not_applicable_requires_reason(self) -> None:
        self.run_cli("obligation", str(self.case), "--statement", "Potentially irrelevant obligation")
        update = self.run_cli(
            "link",
            str(self.case),
            "--obligation",
            "O001",
            "--status",
            "NOT_APPLICABLE",
        )
        self.assertEqual(update.returncode, 0, update.stderr)
        validation = self.run_cli("validate", str(self.case))
        self.assertNotEqual(validation.returncode, 0)
        self.assertIn("requires a decision note", validation.stdout)

    def test_supported_obligation_waits_for_dependencies(self) -> None:
        artifact = self.case.parent / "artifacts" / "check.txt"
        artifact.write_text("independent check\n", encoding="utf-8")
        self.run_cli("obligation", str(self.case), "--id", "O001", "--statement", "Base lemma")
        self.run_cli(
            "obligation",
            str(self.case),
            "--id",
            "O002",
            "--statement",
            "Dependent theorem",
            "--depends-on",
            "O001",
        )
        self.run_cli(
            "evidence",
            str(self.case),
            "--kind",
            "proof",
            "--summary",
            "Checks dependent theorem",
            "--file",
            str(artifact),
            "--independent",
        )
        self.run_cli("link", str(self.case), "--obligation", "O002", "--evidence", "E001", "--status", "SUPPORTED")
        validation = self.run_cli("validate", str(self.case))
        self.assertNotEqual(validation.returncode, 0)
        self.assertIn("supported before dependencies close", validation.stdout)

    def test_dependency_cycle_is_detected_after_manual_corruption(self) -> None:
        self.run_cli("obligation", str(self.case), "--id", "O001", "--statement", "First")
        self.run_cli("obligation", str(self.case), "--id", "O002", "--statement", "Second", "--depends-on", "O001")
        data = json.loads(self.case.read_text(encoding="utf-8"))
        data["obligations"][0]["depends_on"] = ["O002"]
        self.case.write_text(json.dumps(data), encoding="utf-8")
        validation = self.run_cli("validate", str(self.case))
        self.assertNotEqual(validation.returncode, 0)
        self.assertIn("dependency cycle", validation.stdout)

    def test_validated_distillation_requires_evidence(self) -> None:
        lesson = self.run_cli(
            "distill",
            str(self.case),
            "--lesson",
            "Use exact arithmetic for the decisive nonvanishing check",
            "--trigger",
            "A symbolic expression decides equality",
            "--scope",
            "Exact coefficient domains",
            "--status",
            "validated",
        )
        self.assertEqual(lesson.returncode, 0, lesson.stderr)
        validation = self.run_cli("validate", str(self.case))
        self.assertNotEqual(validation.returncode, 0)
        self.assertIn("validated distillation requires evidence", validation.stdout)


if __name__ == "__main__":
    unittest.main()
