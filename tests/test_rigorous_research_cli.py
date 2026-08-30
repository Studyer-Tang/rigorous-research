from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "rigorous_research_cli.py"
SPEC = importlib.util.spec_from_file_location("rigorous_research_cli", MODULE)
assert SPEC and SPEC.loader
cli = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cli
SPEC.loader.exec_module(cli)


class UnifiedCliTests(unittest.TestCase):
    def test_help_lists_every_public_command(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["--help"]), 0)
        for command in cli.COMMANDS:
            self.assertIn(command, output.getvalue())

    def test_unknown_command_is_usage_error(self):
        output = io.StringIO()
        with redirect_stderr(output):
            self.assertEqual(cli.main(["unknown"]), 2)
        self.assertIn("unknown command", output.getvalue())

    def test_subcommand_help_is_forwarded(self):
        output = io.StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stdout(output):
            cli.main(["workspace", "--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("usage:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
