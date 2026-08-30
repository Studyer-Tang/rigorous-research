from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "skill_quality.py"
SPEC = importlib.util.spec_from_file_location("skill_quality", MODULE)
assert SPEC and SPEC.loader
quality = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = quality
SPEC.loader.exec_module(quality)


VALID_SKILL = """---
name: fixture-skill
description: Validate a fixture when repository quality needs testing.
license: MIT
metadata:
  version: "1.0"
  skill-author: Test contributors
---

# Fixture
"""


class SkillQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "SKILL.md").write_text(VALID_SKILL, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def codes(self) -> set[str]:
        return {finding.code for finding in quality.validate(self.root)}

    def test_valid_minimal_skill_passes(self):
        self.assertEqual(quality.validate(self.root), [])

    def test_unknown_frontmatter_and_unquoted_version_fail(self):
        broken = VALID_SKILL.replace('version: "1.0"', "version: 1.0").replace("license: MIT", "owner: private")
        (self.root / "SKILL.md").write_text(broken, encoding="utf-8")
        self.assertIn("FRONTMATTER", self.codes())

    def test_broken_local_link_fails(self):
        (self.root / "README.md").write_text("[missing](references/missing.md)", encoding="utf-8")
        self.assertIn("BROKEN_LINK", self.codes())

    def test_local_user_path_is_rejected(self):
        scripts = self.root / "scripts"
        scripts.mkdir()
        (scripts / "bad.py").write_text('path = r"C:\\Users\\alice\\secret.csv"\n', encoding="utf-8")
        self.assertIn("LOCAL_PATH", self.codes())

    def test_dynamic_execution_is_rejected(self):
        scripts = self.root / "scripts"
        scripts.mkdir()
        (scripts / "bad.py").write_text("exec(user_input)\n", encoding="utf-8")
        self.assertIn("UNSAFE_CALL", self.codes())

    def test_package_and_skill_versions_must_agree(self):
        (self.root / "pyproject.toml").write_text('[project]\nname = "fixture"\nversion = "2.0.0"\n', encoding="utf-8")
        self.assertIn("VERSION", self.codes())


if __name__ == "__main__":
    unittest.main()
