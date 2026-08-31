from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "build_plugin.py"
SPEC = importlib.util.spec_from_file_location("build_plugin", MODULE)
assert SPEC and SPEC.loader
plugin = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = plugin
SPEC.loader.exec_module(plugin)


class PluginBuildTests(unittest.TestCase):
    def test_build_creates_standard_plugin_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plugin"
            archive = Path(directory) / "rigorous-research-plugin"
            plugin.build_plugin(ROOT, output, archive)
            manifest = json.loads((output / "plugin.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], plugin.project_version(ROOT))
            self.assertTrue((output / "skills" / "rigorous-research" / "SKILL.md").is_file())
            self.assertEqual(list((output / "skills" / "rigorous-research" / "scripts").glob("*.egg-info")), [])
            self.assertFalse((output / "skills" / "rigorous-research" / "scripts" / "build_plugin.py").exists())
            self.assertTrue(
                (output / "skills" / "rigorous-research" / "scripts" / "papertrail_frontend" / "app.js").is_file()
            )
            self.assertTrue(
                (output / "skills" / "rigorous-research" / "scripts" / "papertrail_frontend" / "i18n.js").is_file()
            )
            self.assertTrue(archive.with_suffix(".zip").is_file())

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plugin"
            output.mkdir()
            with self.assertRaises(ValueError):
                plugin.build_plugin(ROOT, output)


if __name__ == "__main__":
    unittest.main()
