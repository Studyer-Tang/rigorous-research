#!/usr/bin/env python3
"""Maintain a durable, evidence-gated research case with no third-party dependencies."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
MODES = ("research", "proof", "implementation", "reproduction", "investigation")
CASE_STATUSES = ("ACTIVE", "VERIFIED", "REFUTED", "INCOMPLETE", "ILL-POSED", "BLOCKED")
BRANCH_STATUSES = ("OPEN", "VERIFIED", "REFUTED", "INCOMPLETE", "ILL-POSED", "BLOCKED")
OBLIGATION_STATUSES = ("OPEN", "SUPPORTED", "FAILED", "NOT_APPLICABLE")
CRITERION_STATUSES = ("OPEN", "PASSED", "FAILED", "NOT_APPLICABLE")
EVIDENCE_KINDS = (
    "source",
    "proof",
    "computation",
    "test",
    "artifact",
    "citation",
    "testimony",
    "observation",
)
DISTILLATION_STATUSES = ("candidate", "validated", "rejected")
REVIEW_STATUSES = ("not-run", "accept", "revise", "reject", "blocked")
ROUND_REVIEW_STATUSES = ("continue", "accept", "revise", "reject", "blocked")
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,62}\Z")
ID_RE = re.compile(r"[A-Z][A-Z0-9-]{0,31}\Z")


class CaseError(ValueError):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_slug(value: str) -> str:
    if not SLUG_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("use lowercase letters, digits, and hyphens (max 63 characters)")
    return value


def parse_id(value: str) -> str:
    normalized = value.strip().upper()
    if not ID_RE.fullmatch(normalized):
        raise argparse.ArgumentTypeError("IDs must begin with a letter and contain only A-Z, 0-9, or hyphens")
    return normalized


def load_case(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = path.resolve()
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CaseError(f"case file not found: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise CaseError(f"invalid JSON in {resolved}: {exc}") from exc
    if not isinstance(data, dict):
        raise CaseError("case root must be a JSON object")
    return resolved, data


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def save_case(path: Path, data: dict[str, Any], event: str, details: dict[str, Any]) -> None:
    stamp = now()
    data["updated_at"] = stamp
    atomic_write_json(path, data)
    entry = {"ts": stamp, "event": event, **details}
    journal = path.parent / "journal.jsonl"
    with journal.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")


def next_id(items: list[dict[str, Any]], prefix: str) -> str:
    used = {str(item.get("id", "")) for item in items}
    number = 1
    while f"{prefix}{number:03d}" in used:
        number += 1
    return f"{prefix}{number:03d}"


def find_by_id(items: list[dict[str, Any]], item_id: str, label: str) -> dict[str, Any]:
    for item in items:
        if item.get("id") == item_id:
            return item
    raise CaseError(f"unknown {label} ID: {item_id}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_locator(file_path: Path, case_dir: Path) -> tuple[str, str]:
    resolved = file_path.resolve()
    if not resolved.is_file():
        raise CaseError(f"evidence file not found: {resolved}")
    try:
        locator = resolved.relative_to(case_dir).as_posix()
    except ValueError:
        locator = str(resolved)
    return locator, sha256_file(resolved)


def resolve_artifact(locator: str, case_dir: Path) -> Path:
    value = Path(locator)
    return value if value.is_absolute() else case_dir / value


def validate_case(data: dict[str, Any], case_path: Path, release: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    required = (
        "schema_version",
        "case_id",
        "objective",
        "mode",
        "status",
        "interpretations",
        "obligations",
        "criteria",
        "evidence",
        "rounds",
        "review",
        "claims",
        "distillations",
    )
    for key in required:
        if key not in data:
            errors.append(f"missing top-level field: {key}")
    if errors:
        return errors, warnings

    if data["schema_version"] != SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {data['schema_version']!r}")
    if not isinstance(data["objective"], str) or not data["objective"].strip():
        errors.append("objective must be non-empty")
    if data["mode"] not in MODES:
        errors.append(f"invalid mode: {data['mode']!r}")
    if data["status"] not in CASE_STATUSES:
        errors.append(f"invalid case status: {data['status']!r}")

    collections = {
        "source": data.get("sources", []),
        "interpretation": data["interpretations"],
        "obligation": data["obligations"],
        "criterion": data["criteria"],
        "evidence": data["evidence"],
        "distillation": data["distillations"],
    }
    ids: dict[str, set[str]] = {}
    all_ids: set[str] = set()
    for label, items in collections.items():
        if not isinstance(items, list):
            errors.append(f"{label} collection must be a list")
            ids[label] = set()
            continue
        values: list[str] = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                errors.append(f"{label} entry missing string ID")
                continue
            values.append(item["id"])
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            errors.append(f"duplicate {label} IDs: {', '.join(duplicates)}")
        overlap = all_ids.intersection(values)
        if overlap:
            errors.append(f"IDs reused across collections: {', '.join(sorted(overlap))}")
        ids[label] = set(values)
        all_ids.update(values)

    for branch in data["interpretations"]:
        if not isinstance(branch, dict):
            continue
        if branch.get("status") not in BRANCH_STATUSES:
            errors.append(f"{branch.get('id', '?')}: invalid branch status")
        if not str(branch.get("statement", "")).strip():
            errors.append(f"{branch.get('id', '?')}: interpretation statement is empty")

    evidence_ids = ids.get("evidence", set())
    obligation_ids = ids.get("obligation", set())
    branch_ids = ids.get("interpretation", set())
    for source in data.get("sources", []):
        if not isinstance(source, dict):
            continue
        sid = str(source.get("id", "?"))
        if not str(source.get("title", "")).strip():
            errors.append(f"{sid}: source title is empty")
        if not str(source.get("locator", "")).strip():
            errors.append(f"{sid}: source locator is empty")

    independent_evidence: set[str] = set()
    for evidence in data["evidence"]:
        if not isinstance(evidence, dict):
            continue
        eid = str(evidence.get("id", "?"))
        if evidence.get("kind") not in EVIDENCE_KINDS:
            errors.append(f"{eid}: invalid evidence kind")
        if not str(evidence.get("summary", "")).strip():
            errors.append(f"{eid}: evidence summary is empty")
        if evidence.get("independent") is True:
            independent_evidence.add(eid)
        checksum = evidence.get("sha256")
        file_locator = evidence.get("file")
        if checksum and file_locator:
            artifact = resolve_artifact(str(file_locator), case_path.parent)
            if not artifact.is_file():
                errors.append(f"{eid}: checksummed artifact is missing: {artifact}")
            elif sha256_file(artifact) != checksum:
                errors.append(f"{eid}: artifact checksum mismatch: {artifact}")

    critical_linked_independent = False
    obligation_by_id = {item.get("id"): item for item in data["obligations"] if isinstance(item, dict)}
    for obligation in data["obligations"]:
        if not isinstance(obligation, dict):
            continue
        oid = str(obligation.get("id", "?"))
        status = obligation.get("status")
        if status not in OBLIGATION_STATUSES:
            errors.append(f"{oid}: invalid obligation status")
        if obligation.get("branch") not in branch_ids:
            errors.append(f"{oid}: unknown interpretation branch {obligation.get('branch')!r}")
        dependencies = obligation.get("depends_on", [])
        if not isinstance(dependencies, list):
            errors.append(f"{oid}: depends_on must be a list")
            dependencies = []
        for dependency in dependencies:
            if dependency == oid:
                errors.append(f"{oid}: self-dependency")
            elif dependency not in obligation_ids:
                errors.append(f"{oid}: unknown dependency {dependency}")
        links = obligation.get("evidence_ids", [])
        if not isinstance(links, list):
            errors.append(f"{oid}: evidence_ids must be a list")
            links = []
        missing = [value for value in links if value not in evidence_ids]
        if missing:
            errors.append(f"{oid}: unknown evidence IDs: {', '.join(missing)}")
        if status in {"SUPPORTED", "FAILED"} and not links:
            errors.append(f"{oid}: {status} obligation has no linked evidence")
        if status == "NOT_APPLICABLE" and not str(obligation.get("decision_note", "")).strip():
            errors.append(f"{oid}: NOT_APPLICABLE requires a decision note")
        if status == "SUPPORTED":
            unresolved_dependencies = [
                dependency
                for dependency in dependencies
                if obligation_by_id.get(dependency, {}).get("status") not in {"SUPPORTED", "NOT_APPLICABLE"}
            ]
            if unresolved_dependencies:
                errors.append(f"{oid}: supported before dependencies close: {', '.join(unresolved_dependencies)}")
        if obligation.get("critical") and independent_evidence.intersection(links):
            critical_linked_independent = True

    dependency_graph = {
        oid: list(item.get("depends_on", []))
        for oid, item in obligation_by_id.items()
        if isinstance(oid, str)
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, path: list[str]) -> None:
        if node in visiting:
            start = path.index(node) if node in path else 0
            errors.append(f"obligation dependency cycle: {' -> '.join(path[start:] + [node])}")
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in dependency_graph.get(node, []):
            if dependency in dependency_graph:
                visit(dependency, [*path, node])
        visiting.remove(node)
        visited.add(node)

    for obligation_id in dependency_graph:
        visit(obligation_id, [])

    for criterion in data["criteria"]:
        if not isinstance(criterion, dict):
            continue
        cid = str(criterion.get("id", "?"))
        status = criterion.get("status")
        if status not in CRITERION_STATUSES:
            errors.append(f"{cid}: invalid criterion status")
        links = criterion.get("evidence_ids", [])
        if not isinstance(links, list):
            errors.append(f"{cid}: evidence_ids must be a list")
            links = []
        missing = [value for value in links if value not in evidence_ids]
        if missing:
            errors.append(f"{cid}: unknown evidence IDs: {', '.join(missing)}")
        if status in {"PASSED", "FAILED"} and not links:
            errors.append(f"{cid}: {status} criterion has no linked evidence")
        if status == "NOT_APPLICABLE" and not str(criterion.get("decision_note", "")).strip():
            errors.append(f"{cid}: NOT_APPLICABLE requires a decision note")

    for lesson in data["distillations"]:
        if not isinstance(lesson, dict):
            continue
        did = str(lesson.get("id", "?"))
        if lesson.get("status") not in DISTILLATION_STATUSES:
            errors.append(f"{did}: invalid distillation status")
        if not str(lesson.get("lesson", "")).strip() or not str(lesson.get("trigger", "")).strip():
            errors.append(f"{did}: reusable lesson and trigger must be non-empty")
        links = lesson.get("evidence_ids", [])
        if not isinstance(links, list):
            errors.append(f"{did}: evidence_ids must be a list")
            links = []
        missing = [value for value in links if value not in evidence_ids]
        if missing:
            errors.append(f"{did}: unknown evidence IDs: {', '.join(missing)}")
        if lesson.get("status") == "validated" and not links:
            errors.append(f"{did}: validated distillation requires evidence")

    signatures = [str(item.get("progress_signature", "")).strip() for item in data["rounds"]]
    repeated = any(a and a == b for a, b in zip(signatures, signatures[1:]))
    if repeated:
        warnings.append("consecutive rounds repeat the same progress signature")

    review = data["review"]
    if not isinstance(review, dict) or review.get("verdict") not in REVIEW_STATUSES:
        errors.append("review verdict is missing or invalid")
    else:
        review_links = review.get("evidence_ids", [])
        if not isinstance(review_links, list):
            errors.append("review evidence_ids must be a list")
        else:
            missing = [value for value in review_links if value not in evidence_ids]
            if missing:
                errors.append(f"review references unknown evidence: {', '.join(missing)}")

    if release:
        status = data["status"]
        if status in {"ACTIVE", "INCOMPLETE", "BLOCKED"}:
            errors.append(f"release status is not terminal: {status}")
        if not str(data["claims"].get("safe", "")).strip():
            errors.append("release requires strongest safe claim")
        if not str(data["claims"].get("unsupported", "")).strip():
            errors.append("release requires strongest nearby unsupported claim")
        if review.get("verdict") != "accept":
            errors.append("release requires independent review verdict: accept")
        if not critical_linked_independent:
            errors.append("release requires independent evidence linked to a critical obligation")

        critical = [item for item in data["obligations"] if item.get("critical")]
        if not critical:
            errors.append("release requires at least one critical obligation")
        if status == "VERIFIED":
            if not any(item.get("status") == "VERIFIED" for item in data["interpretations"]):
                errors.append("VERIFIED case requires a verified interpretation branch")
            open_critical = [item["id"] for item in critical if item.get("status") not in {"SUPPORTED", "NOT_APPLICABLE"}]
            if open_critical:
                errors.append(f"VERIFIED case has unresolved critical obligations: {', '.join(open_critical)}")
            if not data["criteria"]:
                errors.append("VERIFIED case requires at least one acceptance criterion")
            failed_criteria = [
                item["id"] for item in data["criteria"] if item.get("status") not in {"PASSED", "NOT_APPLICABLE"}
            ]
            if failed_criteria:
                errors.append(f"VERIFIED case has unmet criteria: {', '.join(failed_criteria)}")
        elif status == "REFUTED":
            if not any(item.get("status") == "REFUTED" for item in data["interpretations"]):
                errors.append("REFUTED case requires a refuted interpretation branch")
            if not any(item.get("status") == "FAILED" for item in critical):
                errors.append("REFUTED case requires a failed critical obligation")
        elif status == "ILL-POSED":
            if not any(item.get("status") == "ILL-POSED" for item in data["interpretations"]):
                errors.append("ILL-POSED case requires an ill-posed interpretation branch")

    return errors, warnings


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        f"# Research case: {data.get('title') or data.get('case_id', 'untitled')}",
        "",
        "## Status",
        "",
        f"- Case: `{data.get('case_id', '-')}`",
        f"- Mode: `{data.get('mode', '-')}`",
        f"- Verdict: `{data.get('status', '-')}`",
        f"- Updated: `{data.get('updated_at', '-')}`",
        f"- Strongest safe claim: {data.get('claims', {}).get('safe') or 'not set'}",
        f"- Strongest unsupported nearby claim: {data.get('claims', {}).get('unsupported') or 'not set'}",
        "",
        "## Exact objective",
        "",
        str(data.get("objective", "")),
        "",
        "## Sources",
        "",
    ]
    if data.get("sources"):
        for item in data["sources"]:
            lines.append(
                f"- **{item['id']}** {item['title']} — {item['locator']} "
                f"(version: {item.get('version') or 'unspecified'}, role: {item.get('role')})"
            )
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Interpretations",
        "",
        "| ID | Status | Statement | Relation |",
        "|---|---|---|---|",
    ])
    for item in data.get("interpretations", []):
        lines.append(
            f"| {item['id']} | {item['status']} | {escape_table(item['statement'])} | {escape_table(item.get('relation', ''))} |"
        )
    lines.extend(["", "## Obligations", "", "| ID | Branch | Critical | Status | Statement | Evidence |", "|---|---|---:|---|---|---|"])
    for item in data.get("obligations", []):
        links = ", ".join(item.get("evidence_ids", [])) or "-"
        lines.append(
            f"| {item['id']} | {item['branch']} | {'yes' if item.get('critical') else 'no'} | {item['status']} | "
            f"{escape_table(item['statement'])} | {links} |"
        )
    lines.extend(["", "## Acceptance criteria", "", "| ID | Status | Criterion | Evidence |", "|---|---|---|---|"])
    for item in data.get("criteria", []):
        lines.append(
            f"| {item['id']} | {item['status']} | {escape_table(item['statement'])} | "
            f"{', '.join(item.get('evidence_ids', [])) or '-'} |"
        )
    lines.extend(["", "## Evidence", ""])
    if data.get("evidence"):
        for item in data["evidence"]:
            location = item.get("file") or item.get("locator") or "no locator"
            independent = "independent" if item.get("independent") else "supporting"
            lines.append(f"- **{item['id']}** `{item['kind']}` `{independent}` — {item['summary']} ({location})")
    else:
        lines.append("- none")
    review = data.get("review", {})
    lines.extend(
        [
            "",
            "## Independent review",
            "",
            f"- Verdict: `{review.get('verdict', 'not-run')}`",
            f"- Reviewer: {review.get('reviewer') or 'not recorded'}",
            f"- Reason: {review.get('reason') or 'not recorded'}",
            f"- Evidence examined: {', '.join(review.get('evidence_ids', [])) or 'none'}",
            "",
            "## Reusable lessons",
            "",
        ]
    )
    if data.get("distillations"):
        for item in data["distillations"]:
            lines.append(
                f"- **{item['id']}** `{item['status']}` — {item['lesson']} "
                f"(use when: {item['trigger']}; scope: {item.get('scope') or 'unspecified'})"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Rounds",
            "",
        ]
    )
    if data.get("rounds"):
        for item in data["rounds"]:
            lines.append(
                f"- Round {item['number']}: `{item['review_status']}` — {item['goal']} "
                f"(signature: `{item.get('progress_signature') or '-'}`)"
            )
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def render_review_packet(data: dict[str, Any]) -> str:
    lines = [
        f"# Independent review packet: {data.get('case_id', 'untitled')}",
        "",
        "The reviewer should form a verdict from the frozen target and evidence below. No desired verdict is supplied.",
        "",
        "## Frozen objective",
        "",
        str(data.get("objective", "")),
        "",
        "## Interpretations",
        "",
    ]
    for item in data.get("interpretations", []):
        lines.append(f"- **{item['id']}**: {item['statement']} ({item.get('relation', '')})")
    lines.extend(["", "## Critical obligations", ""])
    for item in data.get("obligations", []):
        if item.get("critical"):
            lines.append(
                f"- **{item['id']}** [{item['branch']}] {item['statement']} — ledger status `{item['status']}`; "
                f"evidence: {', '.join(item.get('evidence_ids', [])) or 'none'}"
            )
    lines.extend(["", "## Acceptance criteria", ""])
    for item in data.get("criteria", []):
        lines.append(
            f"- **{item['id']}** {item['statement']} — ledger status `{item['status']}`; "
            f"evidence: {', '.join(item.get('evidence_ids', [])) or 'none'}"
        )
    lines.extend(["", "## Evidence to inspect", ""])
    for item in data.get("evidence", []):
        locator = item.get("file") or item.get("locator") or "no locator"
        lines.append(
            f"- **{item['id']}** `{item['kind']}` — {item['summary']} — `{locator}`"
            + (f" — sha256 `{item['sha256']}`" if item.get("sha256") else "")
        )
    lines.extend(
        [
            "",
            "## Required response",
            "",
            "Return `accept`, `revise`, or `reject`; identify the exact failed obligation or criterion; list evidence examined; "
            "give the strongest failure attempt; and state the minimum next action that could change the verdict.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def escape_table(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def command_init(args: argparse.Namespace) -> None:
    destination = args.output_directory.resolve() / args.case_name
    if destination.exists():
        raise CaseError(f"destination already exists: {destination}")
    destination.mkdir(parents=True)
    (destination / "artifacts").mkdir()
    stamp = now()
    data: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "case_id": args.case_name,
        "title": args.title or args.case_name.replace("-", " ").title(),
        "objective": args.objective.strip(),
        "mode": args.mode,
        "status": "ACTIVE",
        "created_at": stamp,
        "updated_at": stamp,
        "scope": {"non_goals": [], "authority_boundaries": [], "assumptions": []},
        "sources": [],
        "interpretations": [
            {"id": "LITERAL", "statement": args.objective.strip(), "relation": "frozen baseline", "status": "OPEN"}
        ],
        "obligations": [],
        "criteria": [],
        "evidence": [],
        "rounds": [],
        "review": {"verdict": "not-run", "reviewer": "", "reason": "", "evidence_ids": [], "updated_at": None},
        "claims": {"safe": "", "unsupported": ""},
        "distillations": [],
    }
    case_path = destination / "case.json"
    atomic_write_json(case_path, data)
    entry = {"ts": stamp, "event": "case.initialized", "case_id": args.case_name, "mode": args.mode}
    (destination / "journal.jsonl").write_text(
        json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n"
    )
    report = destination / "report.md"
    report.write_text(render_markdown(data), encoding="utf-8", newline="\n")
    print(case_path)


def command_branch(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    branch_id = args.id
    if any(item.get("id") == branch_id for item in data["interpretations"]):
        raise CaseError(f"interpretation already exists: {branch_id}")
    data["interpretations"].append(
        {"id": branch_id, "statement": args.statement.strip(), "relation": args.relation.strip(), "status": "OPEN"}
    )
    save_case(path, data, "interpretation.added", {"id": branch_id})
    print(branch_id)


def command_source(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    source_id = args.id or next_id(data["sources"], "S")
    if any(item.get("id") == source_id for item in data["sources"]):
        raise CaseError(f"source already exists: {source_id}")
    data["sources"].append(
        {
            "id": source_id,
            "title": args.title.strip(),
            "locator": args.locator.strip(),
            "version": args.version.strip(),
            "role": args.role,
            "checked": args.checked,
        }
    )
    save_case(path, data, "source.added", {"id": source_id, "role": args.role})
    print(source_id)


def command_scope(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    scope = data.setdefault("scope", {"non_goals": [], "authority_boundaries": [], "assumptions": []})
    for key, values in (
        ("non_goals", args.non_goal),
        ("authority_boundaries", args.authority_boundary),
        ("assumptions", args.assumption),
    ):
        scope[key] = list(dict.fromkeys([*scope.get(key, []), *(value.strip() for value in values if value.strip())]))
    save_case(path, data, "scope.updated", {"scope": scope})
    print("scope")


def command_obligation(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    find_by_id(data["interpretations"], args.branch, "interpretation")
    obligation_id = args.id or next_id(data["obligations"], "O")
    if any(item.get("id") == obligation_id for item in data["obligations"]):
        raise CaseError(f"obligation already exists: {obligation_id}")
    for dependency in args.depends_on:
        find_by_id(data["obligations"], dependency, "obligation dependency")
    data["obligations"].append(
        {
            "id": obligation_id,
            "branch": args.branch,
            "statement": args.statement.strip(),
            "critical": not args.noncritical,
            "status": "OPEN",
            "depends_on": args.depends_on,
            "falsifier": args.falsifier.strip(),
            "evidence_ids": [],
        }
    )
    save_case(path, data, "obligation.added", {"id": obligation_id, "branch": args.branch})
    print(obligation_id)


def command_criterion(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    criterion_id = args.id or next_id(data["criteria"], "C")
    if any(item.get("id") == criterion_id for item in data["criteria"]):
        raise CaseError(f"criterion already exists: {criterion_id}")
    data["criteria"].append(
        {"id": criterion_id, "statement": args.statement.strip(), "status": "OPEN", "evidence_ids": []}
    )
    save_case(path, data, "criterion.added", {"id": criterion_id})
    print(criterion_id)


def command_evidence(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    evidence_id = args.id or next_id(data["evidence"], "E")
    if any(item.get("id") == evidence_id for item in data["evidence"]):
        raise CaseError(f"evidence already exists: {evidence_id}")
    file_locator = ""
    checksum = ""
    if args.file:
        file_locator, checksum = artifact_locator(args.file, path.parent)
    locator = args.locator.strip()
    if not locator and not file_locator:
        raise CaseError("evidence needs --locator or --file")
    data["evidence"].append(
        {
            "id": evidence_id,
            "kind": args.kind,
            "summary": args.summary.strip(),
            "locator": locator,
            "file": file_locator,
            "sha256": checksum,
            "independent": args.independent,
            "created_at": now(),
        }
    )
    save_case(path, data, "evidence.added", {"id": evidence_id, "kind": args.kind})
    print(evidence_id)


def command_link(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    obligation = find_by_id(data["obligations"], args.obligation, "obligation")
    for evidence_id in args.evidence:
        find_by_id(data["evidence"], evidence_id, "evidence")
    obligation["evidence_ids"] = list(dict.fromkeys([*obligation.get("evidence_ids", []), *args.evidence]))
    obligation["status"] = args.status
    obligation["decision_note"] = args.note.strip()
    save_case(
        path,
        data,
        "obligation.updated",
        {"id": args.obligation, "status": args.status, "evidence_ids": args.evidence},
    )
    print(args.obligation)


def command_satisfy(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    criterion = find_by_id(data["criteria"], args.criterion, "criterion")
    for evidence_id in args.evidence:
        find_by_id(data["evidence"], evidence_id, "evidence")
    criterion["evidence_ids"] = list(dict.fromkeys([*criterion.get("evidence_ids", []), *args.evidence]))
    criterion["status"] = args.status
    criterion["decision_note"] = args.note.strip()
    save_case(
        path,
        data,
        "criterion.updated",
        {"id": args.criterion, "status": args.status, "evidence_ids": args.evidence},
    )
    print(args.criterion)


def command_round(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    number = len(data["rounds"]) + 1
    signature = args.progress_signature.strip()
    previous = data["rounds"][-1].get("progress_signature", "") if data["rounds"] else ""
    stalled = bool(signature and signature == previous)
    data["rounds"].append(
        {
            "number": number,
            "goal": args.goal.strip(),
            "actions": args.action,
            "checks": args.check,
            "review_status": args.review_status,
            "review_reason": args.review_reason.strip(),
            "progress_signature": signature,
            "stalled": stalled,
            "created_at": now(),
        }
    )
    save_case(path, data, "round.closed", {"number": number, "review_status": args.review_status, "stalled": stalled})
    if stalled:
        print("WARNING: progress signature repeats the previous round; change method before continuing", file=sys.stderr)
    print(number)


def command_review(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    for evidence_id in args.evidence:
        find_by_id(data["evidence"], evidence_id, "evidence")
    data["review"] = {
        "verdict": args.verdict,
        "reviewer": args.reviewer.strip(),
        "reason": args.reason.strip(),
        "evidence_ids": args.evidence,
        "updated_at": now(),
    }
    save_case(path, data, "review.recorded", {"verdict": args.verdict, "reviewer": args.reviewer.strip()})
    print(args.verdict)


def command_distill(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    for evidence_id in args.evidence:
        find_by_id(data["evidence"], evidence_id, "evidence")
    lesson_id = args.id or next_id(data["distillations"], "D")
    if any(item.get("id") == lesson_id for item in data["distillations"]):
        raise CaseError(f"distillation already exists: {lesson_id}")
    data["distillations"].append(
        {
            "id": lesson_id,
            "lesson": args.lesson.strip(),
            "trigger": args.trigger.strip(),
            "scope": args.scope.strip(),
            "status": args.status,
            "evidence_ids": args.evidence,
            "created_at": now(),
        }
    )
    save_case(path, data, "distillation.added", {"id": lesson_id, "status": args.status})
    print(lesson_id)


def command_verdict(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    branch = find_by_id(data["interpretations"], args.branch, "interpretation")
    branch["status"] = args.branch_status or (args.status if args.status in BRANCH_STATUSES else branch["status"])
    data["status"] = args.status
    data["claims"] = {"safe": args.safe_claim.strip(), "unsupported": args.unsupported_claim.strip()}
    save_case(path, data, "case.verdict", {"status": args.status, "branch": args.branch})
    print(args.status)


def command_journal(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    save_case(path, data, f"note.{args.kind}", {"message": args.message.strip()})
    print("recorded")


def command_render(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    output = args.output.resolve() if args.output else path.parent / "report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(data), encoding="utf-8", newline="\n")
    print(output)


def command_review_packet(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    output = args.output.resolve() if args.output else path.parent / "review-packet.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_review_packet(data), encoding="utf-8", newline="\n")
    print(output)


def command_validate(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    errors, warnings = validate_case(data, path, args.release)
    if args.json:
        print(json.dumps({"valid": not errors, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    else:
        for warning in warnings:
            print(f"WARNING: {warning}")
        for error in errors:
            print(f"ERROR: {error}")
        if not errors:
            gate = "release" if args.release else "structure"
            print(f"PASS: {gate} gate is structurally consistent (truth not certified)")
    if errors:
        raise SystemExit(1)


def command_status(args: argparse.Namespace) -> None:
    path, data = load_case(args.casefile)
    critical = [item for item in data.get("obligations", []) if item.get("critical")]
    open_critical = [item["id"] for item in critical if item.get("status") == "OPEN"]
    payload = {
        "case": data.get("case_id"),
        "status": data.get("status"),
        "mode": data.get("mode"),
        "rounds": len(data.get("rounds", [])),
        "evidence": len(data.get("evidence", [])),
        "open_critical_obligations": open_critical,
        "review": data.get("review", {}).get("verdict"),
        "updated_at": data.get("updated_at"),
        "path": str(path),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    command = subparsers.add_parser("init", help="create a managed research case")
    command.add_argument("output_directory", type=Path)
    command.add_argument("case_name", type=parse_slug)
    command.add_argument("--objective", required=True)
    command.add_argument("--mode", choices=MODES, default="research")
    command.add_argument("--title")
    command.set_defaults(func=command_init)

    command = subparsers.add_parser("branch", help="add a material interpretation")
    command.add_argument("casefile", type=Path)
    command.add_argument("--id", required=True, type=parse_id)
    command.add_argument("--statement", required=True)
    command.add_argument("--relation", default="alternative interpretation")
    command.set_defaults(func=command_branch)

    command = subparsers.add_parser("source", help="add a frozen source record")
    command.add_argument("casefile", type=Path)
    command.add_argument("--id", type=parse_id)
    command.add_argument("--title", required=True)
    command.add_argument("--locator", required=True)
    command.add_argument("--version", default="")
    command.add_argument("--role", choices=("primary", "secondary", "correction", "data", "implementation"), default="primary")
    command.add_argument("--checked", action="store_true")
    command.set_defaults(func=command_source)

    command = subparsers.add_parser("scope", help="record non-goals, authority boundaries, or assumptions")
    command.add_argument("casefile", type=Path)
    command.add_argument("--non-goal", action="append", default=[])
    command.add_argument("--authority-boundary", action="append", default=[])
    command.add_argument("--assumption", action="append", default=[])
    command.set_defaults(func=command_scope)

    command = subparsers.add_parser("obligation", help="add a proof or delivery obligation")
    command.add_argument("casefile", type=Path)
    command.add_argument("--id", type=parse_id)
    command.add_argument("--branch", type=parse_id, default="LITERAL")
    command.add_argument("--statement", required=True)
    command.add_argument("--noncritical", action="store_true")
    command.add_argument("--depends-on", type=parse_id, action="append", default=[])
    command.add_argument("--falsifier", default="")
    command.set_defaults(func=command_obligation)

    command = subparsers.add_parser("criterion", help="add an observable acceptance criterion")
    command.add_argument("casefile", type=Path)
    command.add_argument("--id", type=parse_id)
    command.add_argument("--statement", required=True)
    command.set_defaults(func=command_criterion)

    command = subparsers.add_parser("evidence", help="register evidence and optional artifact checksum")
    command.add_argument("casefile", type=Path)
    command.add_argument("--id", type=parse_id)
    command.add_argument("--kind", choices=EVIDENCE_KINDS, required=True)
    command.add_argument("--summary", required=True)
    command.add_argument("--locator", default="")
    command.add_argument("--file", type=Path)
    command.add_argument("--independent", action="store_true")
    command.set_defaults(func=command_evidence)

    command = subparsers.add_parser("link", help="link evidence and decide an obligation")
    command.add_argument("casefile", type=Path)
    command.add_argument("--obligation", type=parse_id, required=True)
    command.add_argument("--evidence", type=parse_id, action="append", default=[])
    command.add_argument("--status", choices=OBLIGATION_STATUSES, required=True)
    command.add_argument("--note", default="")
    command.set_defaults(func=command_link)

    command = subparsers.add_parser("satisfy", help="link evidence and decide an acceptance criterion")
    command.add_argument("casefile", type=Path)
    command.add_argument("--criterion", type=parse_id, required=True)
    command.add_argument("--evidence", type=parse_id, action="append", default=[])
    command.add_argument("--status", choices=CRITERION_STATUSES, required=True)
    command.add_argument("--note", default="")
    command.set_defaults(func=command_satisfy)

    command = subparsers.add_parser("round", help="record a completed execution/review round")
    command.add_argument("casefile", type=Path)
    command.add_argument("--goal", required=True)
    command.add_argument("--action", action="append", default=[])
    command.add_argument("--check", action="append", default=[])
    command.add_argument("--review-status", choices=ROUND_REVIEW_STATUSES, required=True)
    command.add_argument("--review-reason", required=True)
    command.add_argument("--progress-signature", default="")
    command.set_defaults(func=command_round)

    command = subparsers.add_parser("review", help="record the independent review verdict")
    command.add_argument("casefile", type=Path)
    command.add_argument("--verdict", choices=REVIEW_STATUSES, required=True)
    command.add_argument("--reviewer", required=True)
    command.add_argument("--reason", required=True)
    command.add_argument("--evidence", type=parse_id, action="append", default=[])
    command.set_defaults(func=command_review)

    command = subparsers.add_parser("distill", help="record an evidence-linked reusable lesson candidate")
    command.add_argument("casefile", type=Path)
    command.add_argument("--id", type=parse_id)
    command.add_argument("--lesson", required=True)
    command.add_argument("--trigger", required=True)
    command.add_argument("--scope", default="")
    command.add_argument("--status", choices=DISTILLATION_STATUSES, default="candidate")
    command.add_argument("--evidence", type=parse_id, action="append", default=[])
    command.set_defaults(func=command_distill)

    command = subparsers.add_parser("verdict", help="set case and interpretation verdicts plus claim boundary")
    command.add_argument("casefile", type=Path)
    command.add_argument("--status", choices=CASE_STATUSES, required=True)
    command.add_argument("--branch", type=parse_id, default="LITERAL")
    command.add_argument("--branch-status", choices=BRANCH_STATUSES)
    command.add_argument("--safe-claim", required=True)
    command.add_argument("--unsupported-claim", required=True)
    command.set_defaults(func=command_verdict)

    command = subparsers.add_parser("journal", help="append a decision summary without hidden reasoning")
    command.add_argument("casefile", type=Path)
    command.add_argument("--kind", choices=("scope", "failure", "pivot", "blocker", "decision", "note"), required=True)
    command.add_argument("--message", required=True)
    command.set_defaults(func=command_journal)

    command = subparsers.add_parser("render", help="render the case as Markdown")
    command.add_argument("casefile", type=Path)
    command.add_argument("--output", type=Path)
    command.set_defaults(func=command_render)

    command = subparsers.add_parser("review-packet", help="render a verdict-blind evidence packet")
    command.add_argument("casefile", type=Path)
    command.add_argument("--output", type=Path)
    command.set_defaults(func=command_review_packet)

    command = subparsers.add_parser("validate", help="check ledger consistency and optional release gates")
    command.add_argument("casefile", type=Path)
    command.add_argument("--release", action="store_true")
    command.add_argument("--json", action="store_true")
    command.set_defaults(func=command_validate)

    command = subparsers.add_parser("status", help="print a compact machine-readable status")
    command.add_argument("casefile", type=Path)
    command.set_defaults(func=command_status)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except CaseError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
