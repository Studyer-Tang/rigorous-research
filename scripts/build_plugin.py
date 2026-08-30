#!/usr/bin/env python3
"""Build a standards-shaped Agent Plugin from this single-skill repository."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

SKILL_ENTRIES = ("SKILL.md", "agents", "assets", "references", "scripts")


def project_version(root: Path) -> str:
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    project = text.split("[project]", 1)[-1]
    match = re.search(r'^version\s*=\s*"([^"]+)"', project, re.MULTILINE)
    if not match:
        raise ValueError("project.version is missing from pyproject.toml")
    return match.group(1)


def build_plugin(root: Path, output: Path, archive: Path | None = None) -> Path:
    root = root.resolve()
    output = output.resolve()
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    skill_output = output / "skills" / "rigorous-research"
    skill_output.mkdir(parents=True)
    for entry in SKILL_ENTRIES:
        source = root / entry
        if not source.exists():
            raise ValueError(f"required plugin source is missing: {entry}")
        destination = skill_output / entry
        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    "*.pyc",
                    "*.egg-info",
                    "build_plugin.py",
                    "research_eval.py",
                    "rigorous_research_cli.py",
                ),
            )
        else:
            shutil.copy2(source, destination)
    shutil.copy2(root / "LICENSE", output / "LICENSE")
    manifest = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "rigorous-research",
        "version": project_version(root),
        "description": "Evidence-gated research workflows for mathematics, statistics, and quantitative finance.",
        "author": {"name": "Rigorous Research contributors"},
        "homepage": "https://github.com/Studyer-Tang/rigorous-research",
        "repository": "https://github.com/Studyer-Tang/rigorous-research",
        "license": "MIT",
        "keywords": ["agent-skills", "research", "reproducibility", "statistics", "quantitative-finance"],
    }
    (output / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if archive:
        archive = archive.resolve()
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.make_archive(str(archive), "zip", root_dir=output)
    return output


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path, help="optional archive base path; .zip is added")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output = build_plugin(args.root, args.output, args.archive)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
