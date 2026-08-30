#!/usr/bin/env python3
"""Validate the portable skill package before release or contribution."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote

ALLOWED_FRONTMATTER = {
    "allowed-tools",
    "description",
    "license",
    "metadata",
    "name",
}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)")
LOCAL_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.IGNORECASE),
    re.compile(r"/(?:Users|home)/[^/\s]+"),
)
SECRET_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("OpenAI-style token", re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b")),
)
DOC_ROOTS = (
    "SKILL.md",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "ROADMAP.md",
    "CODE_OF_CONDUCT.md",
    "docs",
    "references",
    "assets",
)
SCAN_ROOTS = DOC_ROOTS + ("CITATION.cff", "agents", "evals", "scripts")


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str
    line: int | None = None

    def render(self) -> str:
        location = f"{self.path}:{self.line}" if self.line else self.path
        return f"{self.code} {location} - {self.message}"


def repository_files(root: Path, entries: tuple[str, ...], suffixes: set[str] | None = None) -> list[Path]:
    files: set[Path] = set()
    for entry in entries:
        path = root / entry
        if path.is_file():
            files.add(path)
        elif path.is_dir():
            files.update(candidate for candidate in path.rglob("*") if candidate.is_file())
    selected = sorted(files)
    if suffixes is not None:
        selected = [path for path in selected if path.suffix.lower() in suffixes]
    return selected


def parse_frontmatter(path: Path) -> tuple[dict[str, str], dict[str, str], list[Finding]]:
    findings: list[Finding] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, {}, [Finding("FRONTMATTER", path.name, "missing opening YAML delimiter", 1)]
    try:
        closing = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return {}, {}, [Finding("FRONTMATTER", path.name, "missing closing YAML delimiter", 1)]

    top: dict[str, str] = {}
    metadata: dict[str, str] = {}
    section = ""
    for line_number, line in enumerate(lines[1:closing], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            match = re.fullmatch(r"([A-Za-z0-9_-]+):(?:\s*(.*))?", line)
            if not match:
                findings.append(Finding("FRONTMATTER", path.name, "invalid top-level YAML line", line_number))
                section = ""
                continue
            key, value = match.groups()
            top[key] = (value or "").strip()
            section = key
        elif section == "metadata":
            match = re.fullmatch(r"\s{2,}([A-Za-z0-9_-]+):\s*(.+)", line)
            if match:
                metadata[match.group(1)] = match.group(2).strip()

    unknown = sorted(set(top) - ALLOWED_FRONTMATTER)
    if unknown:
        findings.append(Finding("FRONTMATTER", path.name, f"unsupported top-level fields: {', '.join(unknown)}"))
    name = top.get("name", "").strip("'\"")
    description = top.get("description", "").strip("'\"")
    if not NAME_PATTERN.fullmatch(name) or not 1 <= len(name) <= 64:
        findings.append(Finding("FRONTMATTER", path.name, "name must be 1-64 lowercase letters, digits, or hyphens"))
    if not description or len(description) > 1024:
        findings.append(Finding("FRONTMATTER", path.name, "description must contain 1-1024 characters"))
    version = metadata.get("version", "")
    if not re.fullmatch(r"['\"]\d+\.\d+(?:\.\d+)?['\"]", version):
        findings.append(Finding("FRONTMATTER", path.name, "metadata.version must be a quoted numeric version"))
    if "skill-author" not in metadata:
        findings.append(Finding("FRONTMATTER", path.name, "metadata.skill-author is required"))
    if len(lines) > 500:
        findings.append(Finding("SKILL_SIZE", path.name, f"SKILL.md has {len(lines)} lines; keep it at or below 500"))
    return top, metadata, findings


def validate_links(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in repository_files(root, DOC_ROOTS, {".md"}):
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK_PATTERN.finditer(line):
                target = unquote(match.group(1).strip("<>"))
                if not target or target.startswith("#") or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                    continue
                file_target = target.split("#", 1)[0].split("?", 1)[0]
                resolved = (path.parent / file_target).resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    findings.append(Finding("LINK_ESCAPE", str(path.relative_to(root)), target, line_number))
                    continue
                if not resolved.exists():
                    findings.append(Finding("BROKEN_LINK", str(path.relative_to(root)), target, line_number))
    return findings


def validate_python(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in repository_files(root, ("scripts",), {".py"}):
        relative = str(path.relative_to(root))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except SyntaxError as error:
            findings.append(Finding("PYTHON_SYNTAX", relative, error.msg, error.lineno))
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                findings.append(
                    Finding("UNSAFE_CALL", relative, f"avoid {node.func.id}(); parse explicit formats", node.lineno)
                )
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "system"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
            ):
                findings.append(
                    Finding(
                        "UNSAFE_CALL", relative, "avoid os.system(); use argument-list subprocess calls", node.lineno
                    )
                )
    return findings


def validate_sensitive_content(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    suffixes = {".cff", ".json", ".md", ".py", ".txt", ".yaml", ".yml"}
    for path in repository_files(root, SCAN_ROOTS, suffixes):
        relative = str(path.relative_to(root))
        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if any(pattern.search(line) for pattern in LOCAL_PATH_PATTERNS):
                findings.append(Finding("LOCAL_PATH", relative, "hardcoded user-specific filesystem path", line_number))
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(Finding("SECRET", relative, f"possible {label}", line_number))
    return findings


def validate_versions(root: Path, metadata: dict[str, str]) -> list[Finding]:
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return []
    text = pyproject.read_text(encoding="utf-8")
    project = text.split("[project]", 1)[-1]
    match = re.search(r'^version\s*=\s*"(\d+\.\d+\.\d+)"', project, re.MULTILINE)
    if not match:
        return [Finding("VERSION", "pyproject.toml", "project.version must use quoted semantic versioning")]
    package_version = match.group(1)
    skill_version = metadata.get("version", "").strip("'\"")
    findings = []
    if ".".join(package_version.split(".")[:2]) != skill_version:
        findings.append(
            Finding("VERSION", "SKILL.md", f"skill version {skill_version!r} does not match package {package_version}")
        )
    citation = root / "CITATION.cff"
    if citation.is_file() and not re.search(
        rf"^version:\s*['\"]?{re.escape(package_version)}['\"]?\s*$",
        citation.read_text(encoding="utf-8"),
        re.MULTILINE,
    ):
        findings.append(Finding("VERSION", "CITATION.cff", f"citation version must be {package_version}"))
    changelog = root / "CHANGELOG.md"
    if changelog.is_file() and f"## {package_version} " not in changelog.read_text(encoding="utf-8"):
        findings.append(Finding("VERSION", "CHANGELOG.md", f"missing release heading for {package_version}"))
    return findings


def validate(root: Path) -> list[Finding]:
    root = root.resolve()
    skill = root / "SKILL.md"
    if not skill.is_file():
        return [Finding("MISSING_SKILL", "SKILL.md", "SKILL.md does not exist")]
    _, metadata, findings = parse_frontmatter(skill)
    findings.extend(validate_versions(root, metadata))
    findings.extend(validate_links(root))
    findings.extend(validate_python(root))
    findings.extend(validate_sensitive_content(root))
    return sorted(findings, key=lambda item: (item.path, item.line or 0, item.code))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    checkout = Path.cwd()
    module_root = Path(__file__).resolve().parents[1]
    default_root = checkout if (checkout / "SKILL.md").is_file() else module_root
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    findings = validate(args.root)
    if args.json:
        print(json.dumps({"ok": not findings, "findings": [asdict(item) for item in findings]}, indent=2))
    elif findings:
        print(f"Skill quality validation failed with {len(findings)} finding(s):")
        for finding in findings:
            print(f"- {finding.render()}")
    else:
        print("Skill quality validation passed.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
