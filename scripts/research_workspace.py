#!/usr/bin/env python3
"""Manage a reproducible research workspace around an inference case."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import finance_data as fd
import inference_case as ic
import research_seal as rs
import review_protocol as rp
from research_io import (
    atomic_write_json as atomic_json,
    contained_locator as locator,
    resolve_locator as resolve,
    utc_timestamp as timestamp,
)

SCHEMA_VERSION = 1
STAGES = ("SCOPING", "DISCOVERY", "ANALYSIS", "FALSIFICATION", "SYNTHESIS", "RELEASED")
TASK_KINDS = (
    "literature",
    "definition",
    "proof",
    "computation",
    "data",
    "analysis",
    "falsification",
    "replication",
    "writing",
)
TASK_STATUSES = ("PLANNED", "IN_PROGRESS", "BLOCKED", "DONE")
SOURCE_ROLES = ("primary", "secondary", "data", "software")


class WorkspaceError(ValueError):
    """Raised when a workspace operation is invalid."""


def load(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = path.resolve()
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkspaceError(f"workspace not found: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise WorkspaceError(f"invalid workspace JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkspaceError("workspace root must be an object")
    return resolved, data


def save(path: Path, data: dict[str, Any], event: str, details: dict[str, Any]) -> None:
    stamp = timestamp()
    data["updated_at"] = stamp
    atomic_json(path, data)
    journal = path.parent / "research-journal.jsonl"
    with journal.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps({"time": stamp, "event": event, **details}, ensure_ascii=False) + "\n")


def next_id(items: list[dict[str, Any]], prefix: str) -> str:
    used = {item.get("id") for item in items}
    number = 1
    while f"{prefix}{number:03d}" in used:
        number += 1
    return f"{prefix}{number:03d}"


def find(items: list[dict[str, Any]], item_id: str, label: str) -> dict[str, Any]:
    for item in items:
        if item.get("id") == item_id:
            return item
    raise WorkspaceError(f"unknown {label}: {item_id}")


def initialize(root: Path, slug: str, domain: str, question: str, claim: str) -> Path:
    case_path = ic.initialize(root, slug, domain, question, claim)
    workspace_path = case_path.parent / "workspace.json"
    stamp = timestamp()
    data = {
        "schema_version": SCHEMA_VERSION,
        "workspace_id": slug,
        "domain": domain,
        "question": question.strip(),
        "stage": "SCOPING",
        "created_at": stamp,
        "updated_at": stamp,
        "case_file": "case.json",
        "tasks": [],
        "sources": [],
        "runs": [],
        "release_policy": {
            "plan_seal_required": domain in {"statistics", "finance"},
            "data_snapshot_required": domain == "finance",
            "independent_review_required": True,
        },
        "plan_seal": "",
        "data_snapshots": [],
        "review_adjudication": "",
    }
    atomic_json(workspace_path, data)
    (workspace_path.parent / "research-journal.jsonl").write_text(
        json.dumps(
            {"time": stamp, "event": "workspace-initialized", "domain": domain},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return workspace_path


def validate_workspace(
    data: dict[str, Any], workspace_path: Path, release: bool = False
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required = (
        "schema_version",
        "workspace_id",
        "domain",
        "question",
        "stage",
        "case_file",
        "tasks",
        "sources",
        "runs",
    )
    missing = [field for field in required if field not in data]
    if missing:
        return [f"missing workspace field: {field}" for field in missing], warnings
    if data["schema_version"] != SCHEMA_VERSION:
        errors.append(f"unsupported workspace schema_version: {data['schema_version']!r}")
    if data["domain"] not in ic.DOMAINS:
        errors.append(f"invalid workspace domain: {data['domain']!r}")
    if data["stage"] not in STAGES:
        errors.append(f"invalid stage: {data['stage']!r}")
    if not str(data["question"]).strip():
        errors.append("workspace question must be non-empty")

    collections = {
        "task": data["tasks"],
        "source": data["sources"],
        "run": data["runs"],
    }
    id_sets: dict[str, set[str]] = {}
    expected = {"task": "W", "source": "S", "run": "R"}
    all_ids: set[str] = set()
    for label, items in collections.items():
        if not isinstance(items, list):
            errors.append(f"{label} collection must be a list")
            id_sets[label] = set()
            continue
        values = [item.get("id") for item in items if isinstance(item, dict)]
        if len(values) != len(items) or any(not isinstance(value, str) for value in values):
            errors.append(f"{label} entries require string IDs")
        malformed = [
            value
            for value in values
            if isinstance(value, str)
            and (not value.startswith(expected[label]) or len(value) != 4 or not value[1:].isdigit())
        ]
        if malformed:
            errors.append(f"malformed {label} IDs: {', '.join(sorted(malformed))}")
        duplicates = {value for value in values if values.count(value) > 1}
        if duplicates:
            errors.append(f"duplicate {label} IDs: {', '.join(sorted(duplicates))}")
        overlap = all_ids.intersection(value for value in values if isinstance(value, str))
        if overlap:
            errors.append(f"IDs reused across workspace collections: {', '.join(sorted(overlap))}")
        id_sets[label] = {value for value in values if isinstance(value, str)}
        all_ids.update(id_sets[label])

    task_ids = id_sets.get("task", set())
    for task in data["tasks"]:
        task_id = task.get("id", "?")
        if task.get("kind") not in TASK_KINDS:
            errors.append(f"{task_id}: invalid task kind")
        if task.get("status") not in TASK_STATUSES:
            errors.append(f"{task_id}: invalid task status")
        if not str(task.get("title", "")).strip() or not str(task.get("acceptance", "")).strip():
            errors.append(f"{task_id}: title and acceptance are required")
        dependencies = task.get("depends_on", [])
        if not isinstance(dependencies, list):
            errors.append(f"{task_id}: depends_on must be a list")
            dependencies = []
        unknown = [value for value in dependencies if value not in task_ids]
        if unknown:
            errors.append(f"{task_id}: unknown dependencies: {', '.join(unknown)}")
        if task_id in dependencies:
            errors.append(f"{task_id}: task cannot depend on itself")
        deliverable = str(task.get("deliverable", "")).strip()
        if task.get("status") == "DONE" and deliverable:
            artifact = resolve(deliverable, workspace_path.parent)
            if not artifact.is_file():
                errors.append(f"{task_id}: completed deliverable is missing: {deliverable}")

    # Detect dependency cycles with a small depth-first traversal.
    graph = {
        task.get("id"): task.get("depends_on", [])
        for task in data["tasks"]
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"dependency cycle includes {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for parent in graph.get(node, []):
            if parent in graph:
                visit(parent)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)

    for source in data["sources"]:
        source_id = source.get("id", "?")
        if source.get("role") not in SOURCE_ROLES:
            errors.append(f"{source_id}: invalid source role")
        if not str(source.get("citation", "")).strip():
            errors.append(f"{source_id}: citation is required")
        if not str(source.get("url", "")).strip() and not str(source.get("file", "")).strip():
            errors.append(f"{source_id}: url or file is required")
        supports = source.get("supports", [])
        if not isinstance(supports, list) or any(not isinstance(value, str) for value in supports):
            errors.append(f"{source_id}: supports must be a list of claim IDs")
        file_value = str(source.get("file", "")).strip()
        checksum = source.get("sha256")
        if file_value:
            artifact = resolve(file_value, workspace_path.parent)
            if not artifact.is_file():
                errors.append(f"{source_id}: source file is missing")
            elif checksum and ic.sha256(artifact) != checksum:
                errors.append(f"{source_id}: source checksum mismatch")

    for run in data["runs"]:
        run_id = run.get("id", "?")
        if run.get("task_id") not in task_ids:
            errors.append(f"{run_id}: unknown task")
        if not isinstance(run.get("command"), list) or not run.get("command"):
            errors.append(f"{run_id}: command must be a non-empty list")
        if run.get("returncode") is None:
            warnings.append(f"{run_id}: run has no return code")
        for stream_name in ("stdout", "stderr"):
            stream_file = resolve(str(run.get(stream_name, "")), workspace_path.parent)
            expected_hash = run.get(f"{stream_name}_sha256")
            if not stream_file.is_file():
                errors.append(f"{run_id}: {stream_name} capture is missing")
            elif expected_hash and ic.sha256(stream_file) != expected_hash:
                errors.append(f"{run_id}: {stream_name} checksum mismatch")
        for output in run.get("outputs", []):
            artifact = resolve(str(output.get("file", "")), workspace_path.parent)
            if not artifact.is_file():
                errors.append(f"{run_id}: declared output is missing: {output.get('file', '')}")
            elif output.get("sha256") and ic.sha256(artifact) != output["sha256"]:
                errors.append(f"{run_id}: output checksum mismatch: {output.get('file', '')}")

    case_path = resolve(str(data["case_file"]), workspace_path.parent)
    case_data: dict[str, Any] = {}
    try:
        resolved_case, case_data = ic.load_case(case_path)
        case_errors, case_warnings = ic.validate_case(case_data, resolved_case, release=release)
        errors.extend(f"case: {error}" for error in case_errors)
        warnings.extend(f"case: {warning}" for warning in case_warnings)
        if case_data.get("domain") != data.get("domain"):
            errors.append("workspace domain does not match inference case")
        if case_data.get("question") != data.get("question"):
            errors.append("workspace question does not match inference case")
        claim_ids = {claim.get("id") for claim in case_data.get("claims", [])}
        for source in data["sources"]:
            unknown = [value for value in source.get("supports", []) if value not in claim_ids]
            if unknown:
                errors.append(f"{source.get('id', '?')}: unknown supported claims: {', '.join(unknown)}")
    except ic.ContractError as exc:
        errors.append(f"case: {exc}")

    if release:
        if data["stage"] != "RELEASED":
            errors.append("release validation requires stage RELEASED")
        unfinished = [task["id"] for task in data["tasks"] if task.get("status") != "DONE"]
        if unfinished:
            errors.append(f"release has unfinished tasks: {', '.join(unfinished)}")
        failed_runs = [run["id"] for run in data["runs"] if run.get("returncode") != 0]
        if failed_runs:
            errors.append(f"release includes failed runs: {', '.join(failed_runs)}")
        if data["domain"] in {"statistics", "finance"} and not any(
            source.get("role") == "data" for source in data["sources"]
        ):
            errors.append(f"released {data['domain']} workspace requires a data source")
        policy = data.get("release_policy")
        if not isinstance(policy, dict):
            warnings.append("legacy workspace has no machine-enforced seal, snapshot, or independent-review policy")
        else:
            seal_value = str(data.get("plan_seal", "")).strip()
            if policy.get("plan_seal_required"):
                if not seal_value:
                    errors.append("release policy requires a sealed preregistration plan")
                else:
                    seal_path = resolve(seal_value, workspace_path.parent)
                    if not seal_path.is_file():
                        errors.append("plan seal is missing")
                    else:
                        seal_errors, _ = rs.verify_plan(seal_path)
                        errors.extend(f"plan seal: {error}" for error in seal_errors)
            if policy.get("data_snapshot_required"):
                manifests = data.get("data_snapshots", [])
                if not manifests:
                    errors.append("release policy requires an immutable financial-data snapshot")
                for value in manifests:
                    manifest_path = resolve(str(value), workspace_path.parent)
                    if not manifest_path.is_file():
                        errors.append(f"data snapshot manifest is missing: {value}")
                    else:
                        snapshot_errors, _ = fd.verify(manifest_path)
                        errors.extend(f"data snapshot: {error}" for error in snapshot_errors)
            if policy.get("independent_review_required") and case_data.get("decision", {}).get("verdict") in {
                "SUPPORTED",
                "REFUTED",
            }:
                review_value = str(data.get("review_adjudication", "")).strip()
                if not review_value:
                    errors.append("release policy requires an independent review adjudication")
                else:
                    review_path = resolve(review_value, workspace_path.parent)
                    if not review_path.is_file():
                        errors.append("review adjudication is missing")
                    else:
                        review_errors, _ = rp.verify_adjudication(review_path, require_clear=True)
                        errors.extend(f"review: {error}" for error in review_errors)
    return errors, warnings


def task_ready(task: dict[str, Any], tasks: list[dict[str, Any]]) -> bool:
    statuses = {item["id"]: item.get("status") for item in tasks}
    return task.get("status") == "PLANNED" and all(statuses.get(dep) == "DONE" for dep in task.get("depends_on", []))


def render_brief(data: dict[str, Any], workspace_path: Path) -> str:
    lines = [
        f"# Research workspace: {data['workspace_id']}",
        "",
        f"- Domain: `{data['domain']}`",
        f"- Stage: `{data['stage']}`",
        f"- Question: {data['question']}",
        "",
        "## Work plan",
        "",
        "| ID | Kind | Status | Task | Dependencies | Acceptance | Deliverable |",
        "|---|---|---|---|---|---|---|",
    ]
    for task in data["tasks"]:
        lines.append(
            f"| {task['id']} | {task['kind']} | {task['status']} | {ic.escape(task['title'])} | "
            f"{', '.join(task.get('depends_on', [])) or '-'} | {ic.escape(task['acceptance'])} | "
            f"{ic.escape(task.get('deliverable', '')) or '-'} |"
        )
    lines.extend(["", "## Sources", ""])
    for source in data["sources"]:
        location = source.get("url") or source.get("file")
        supports = ", ".join(source.get("supports", [])) or "context only"
        lines.append(
            f"- **{source['id']}** `{source['role']}` supports `{supports}` — {source['citation']} [{location}]"
        )
    lines.extend(["", "## Reproducible runs", ""])
    for run in data["runs"]:
        lines.append(
            f"- **{run['id']}** task `{run['task_id']}`, return code `{run.get('returncode')}` — "
            f"{run['label']}; outputs: {', '.join(item['file'] for item in run.get('outputs', [])) or 'none'}"
        )
    case_path = resolve(str(data["case_file"]), workspace_path.parent)
    _, case_data = ic.load_case(case_path)
    lines.extend(["", "---", "", ic.render(case_data)])
    return "\n".join(lines)


def mutate(path: Path, callback: Any, event: str) -> None:
    workspace_path, data = load(path)
    details = callback(data)
    errors, _ = validate_workspace(data, workspace_path, release=False)
    if errors:
        raise WorkspaceError("; ".join(errors))
    save(workspace_path, data, event, details or {})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a research workspace and inference case")
    init.add_argument("root", type=Path)
    init.add_argument("slug", type=ic.parse_slug)
    init.add_argument("--domain", choices=ic.DOMAINS, required=True)
    init.add_argument("--question", required=True)
    init.add_argument("--claim", required=True)

    task = commands.add_parser("task", help="add a research work item")
    task.add_argument("workspace", type=Path)
    task.add_argument("--title", required=True)
    task.add_argument("--kind", choices=TASK_KINDS, required=True)
    task.add_argument("--acceptance", required=True)
    task.add_argument("--depends-on", nargs="*", default=[])
    task.add_argument("--deliverable", default="")

    set_task = commands.add_parser("set-task", help="update a work item")
    set_task.add_argument("workspace", type=Path)
    set_task.add_argument("--id", required=True)
    set_task.add_argument("--status", choices=TASK_STATUSES, required=True)
    set_task.add_argument("--note", default="")

    source = commands.add_parser("source", help="record a paper, dataset, or software source")
    source.add_argument("workspace", type=Path)
    source.add_argument("--citation", required=True)
    source.add_argument("--role", choices=SOURCE_ROLES, required=True)
    source.add_argument("--url", default="")
    source.add_argument("--file", type=Path)
    source.add_argument("--note", default="")
    source.add_argument("--supports", nargs="*", default=[])

    set_source = commands.add_parser("set-source", help="update source notes or claim links")
    set_source.add_argument("workspace", type=Path)
    set_source.add_argument("--id", required=True)
    set_source.add_argument("--note")
    set_source.add_argument("--supports", nargs="*")

    governance = commands.add_parser("governance", help="attach plan seals, data snapshots, and review adjudication")
    governance.add_argument("workspace", type=Path)
    governance.add_argument("--plan-seal", type=Path)
    governance.add_argument("--data-snapshot", type=Path, action="append", default=[])
    governance.add_argument("--review-adjudication", type=Path)

    stage = commands.add_parser("set-stage", help="set the research stage")
    stage.add_argument("workspace", type=Path)
    stage.add_argument("--stage", choices=STAGES, required=True)

    run = commands.add_parser("run", help="execute and record a local research command")
    run.add_argument("workspace", type=Path)
    run.add_argument("--task", required=True)
    run.add_argument("--label", required=True)
    run.add_argument("--cwd", type=Path)
    run.add_argument("--output", action="append", default=[])
    run.add_argument("--timeout", type=int, default=300)
    run.add_argument("--complete", action="store_true")

    rehash_run = commands.add_parser("rehash-run", help="accept intentional revisions to captured run files")
    rehash_run.add_argument("workspace", type=Path)
    rehash_run.add_argument("--id", required=True)

    status = commands.add_parser("status", help="show work readiness and inference verdict")
    status.add_argument("workspace", type=Path)
    status.add_argument("--release", action="store_true", help="show release-gate gaps")

    validate = commands.add_parser("validate", help="validate workspace structure and evidence integrity")
    validate.add_argument("workspace", type=Path)
    validate.add_argument("--release", action="store_true")

    brief = commands.add_parser("brief", help="write research-brief.md")
    brief.add_argument("workspace", type=Path)
    brief.add_argument("--release", action="store_true")
    return parser


def execute_run(args: argparse.Namespace) -> int:
    workspace_path, data = load(args.workspace)
    task = find(data["tasks"], args.task, "task")
    statuses = {item["id"]: item.get("status") for item in data["tasks"]}
    incomplete = [dep for dep in task.get("depends_on", []) if statuses.get(dep) != "DONE"]
    if incomplete:
        raise WorkspaceError(f"task dependencies are not done: {', '.join(incomplete)}")
    command = list(args.command_args)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise WorkspaceError("run requires a command after --")
    cwd = args.cwd or workspace_path.parent
    if not cwd.is_absolute():
        cwd = workspace_path.parent / cwd
    cwd = cwd.resolve()
    if not cwd.is_dir():
        raise WorkspaceError(f"run directory does not exist: {cwd}")

    run_id = next_id(data["runs"], "R")
    run_dir = workspace_path.parent / "artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    started = timestamp()
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout,
            check=False,
        )
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stderr += f"\nTimed out after {args.timeout} seconds.\n"
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    stdout_path.write_text(stdout, encoding="utf-8", newline="\n")
    stderr_path.write_text(stderr, encoding="utf-8", newline="\n")
    outputs: list[dict[str, str]] = []
    missing_outputs: list[str] = []
    for value in args.output:
        path = Path(value)
        if not path.is_absolute():
            path = cwd / path
        if not path.is_file():
            missing_outputs.append(str(value))
            continue
        outputs.append({"file": locator(path, workspace_path.parent), "sha256": ic.sha256(path)})
    if missing_outputs and returncode == 0:
        returncode = 3
        stderr_path.write_text(
            stderr_path.read_text(encoding="utf-8") + f"Declared outputs missing: {', '.join(missing_outputs)}\n",
            encoding="utf-8",
            newline="\n",
        )
    record = {
        "id": run_id,
        "task_id": args.task,
        "label": args.label.strip(),
        "command": command,
        "cwd": locator(cwd, workspace_path.parent),
        "started_at": started,
        "finished_at": timestamp(),
        "returncode": returncode,
        "timed_out": timed_out,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "stdout": locator(stdout_path, workspace_path.parent),
        "stderr": locator(stderr_path, workspace_path.parent),
        "outputs": outputs,
    }
    data["runs"].append(record)
    if args.complete and returncode == 0:
        deliverable = str(task.get("deliverable", "")).strip()
        if deliverable and not resolve(deliverable, workspace_path.parent).is_file():
            returncode = 3
            record["returncode"] = returncode
            with stderr_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(f"Task deliverable is missing: {deliverable}\n")
        else:
            task["status"] = "DONE"
            task["note"] = f"Completed by {run_id}."
    record["stdout_sha256"] = ic.sha256(stdout_path)
    record["stderr_sha256"] = ic.sha256(stderr_path)
    errors, _ = validate_workspace(data, workspace_path, release=False)
    if errors:
        raise WorkspaceError("; ".join(errors))
    save(
        workspace_path,
        data,
        "run-recorded",
        {"run_id": run_id, "task_id": args.task, "returncode": returncode},
    )
    print(run_id)
    return returncode


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    run_command: list[str] = []
    if raw_args and raw_args[0] == "run" and "--" in raw_args:
        separator = raw_args.index("--")
        run_command = raw_args[separator + 1 :]
        raw_args = raw_args[:separator]
    args = build_parser().parse_args(raw_args)
    if args.command == "run":
        args.command_args = run_command
    try:
        if args.command == "init":
            print(initialize(args.root, args.slug, args.domain, args.question, args.claim))
            return 0
        if args.command == "run":
            return execute_run(args)
        if args.command == "validate":
            path, data = load(args.workspace)
            errors, warnings = validate_workspace(data, path, release=args.release)
            for warning in warnings:
                print(f"WARNING: {warning}")
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            if errors:
                return 1
            print("VALID")
            return 0
        if args.command == "status":
            path, data = load(args.workspace)
            errors, warnings = validate_workspace(data, path, release=args.release)
            ready = [task["id"] for task in data["tasks"] if task_ready(task, data["tasks"])]
            counts = {status: sum(task.get("status") == status for task in data["tasks"]) for status in TASK_STATUSES}
            case_path = resolve(str(data["case_file"]), path.parent)
            _, case_data = ic.load_case(case_path)
            print(
                f"Workspace: {data['workspace_id']} | stage={data['stage']} | verdict={case_data['decision']['verdict']}"
            )
            print("Tasks: " + ", ".join(f"{status}={counts[status]}" for status in TASK_STATUSES))
            print("Ready: " + (", ".join(ready) or "none"))
            print(f"Integrity: errors={len(errors)}, warnings={len(warnings)}")
            for error in errors:
                print(f"ERROR: {error}")
            for warning in warnings:
                print(f"WARNING: {warning}")
            return 1 if errors else 0
        if args.command == "brief":
            path, data = load(args.workspace)
            errors, warnings = validate_workspace(data, path, release=args.release)
            for warning in warnings:
                print(f"WARNING: {warning}")
            if errors:
                raise WorkspaceError("; ".join(errors))
            destination = path.parent / "research-brief.md"
            destination.write_text(render_brief(data, path), encoding="utf-8", newline="\n")
            print(destination)
            return 0

        if args.command == "task":

            def add_task(data: dict[str, Any]) -> dict[str, Any]:
                for dependency in args.depends_on:
                    find(data["tasks"], dependency, "task")
                task_id = next_id(data["tasks"], "W")
                data["tasks"].append(
                    {
                        "id": task_id,
                        "title": args.title.strip(),
                        "kind": args.kind,
                        "acceptance": args.acceptance.strip(),
                        "depends_on": list(dict.fromkeys(args.depends_on)),
                        "deliverable": args.deliverable.strip(),
                        "status": "PLANNED",
                        "note": "",
                    }
                )
                return {"task_id": task_id}

            mutate(args.workspace, add_task, "task-added")
        elif args.command == "set-task":

            def update_task(data: dict[str, Any]) -> dict[str, Any]:
                task = find(data["tasks"], args.id, "task")
                if args.status == "IN_PROGRESS":
                    statuses = {item["id"]: item.get("status") for item in data["tasks"]}
                    incomplete = [dep for dep in task.get("depends_on", []) if statuses.get(dep) != "DONE"]
                    if incomplete:
                        raise WorkspaceError(f"task dependencies are not done: {', '.join(incomplete)}")
                task["status"] = args.status
                task["note"] = args.note.strip()
                return {"task_id": args.id, "status": args.status}

            mutate(args.workspace, update_task, "task-updated")
        elif args.command == "source":

            def add_source(data: dict[str, Any]) -> dict[str, Any]:
                source_id = next_id(data["sources"], "S")
                file_value = ""
                checksum = None
                if args.file:
                    resolved = args.file.resolve()
                    if not resolved.is_file():
                        raise WorkspaceError(f"source file not found: {resolved}")
                    path, _ = load(args.workspace)
                    file_value = locator(resolved, path.parent)
                    checksum = ic.sha256(resolved)
                if not args.url.strip() and not file_value:
                    raise WorkspaceError("source requires --url or --file")
                data["sources"].append(
                    {
                        "id": source_id,
                        "citation": args.citation.strip(),
                        "role": args.role,
                        "url": args.url.strip(),
                        "file": file_value,
                        "sha256": checksum,
                        "accessed_at": timestamp(),
                        "note": args.note.strip(),
                        "supports": list(dict.fromkeys(args.supports)),
                    }
                )
                return {"source_id": source_id}

            mutate(args.workspace, add_source, "source-added")
        elif args.command == "set-source":

            def update_source(data: dict[str, Any]) -> dict[str, Any]:
                if args.note is None and args.supports is None:
                    raise WorkspaceError("set-source requires --note or --supports")
                source = find(data["sources"], args.id, "source")
                if args.note is not None:
                    source["note"] = args.note.strip()
                if args.supports is not None:
                    source["supports"] = list(dict.fromkeys(args.supports))
                return {"source_id": args.id}

            mutate(args.workspace, update_source, "source-updated")
        elif args.command == "governance":

            def update_governance(data: dict[str, Any]) -> dict[str, Any]:
                if args.plan_seal is None and not args.data_snapshot and args.review_adjudication is None:
                    raise WorkspaceError("governance requires at least one artifact")
                workspace_path, _ = load(args.workspace)
                if args.plan_seal is not None:
                    if not args.plan_seal.is_file():
                        raise WorkspaceError(f"plan seal not found: {args.plan_seal}")
                    data["plan_seal"] = locator(args.plan_seal, workspace_path.parent)
                for manifest in args.data_snapshot:
                    if not manifest.is_file():
                        raise WorkspaceError(f"data snapshot not found: {manifest}")
                    value = locator(manifest, workspace_path.parent)
                    data.setdefault("data_snapshots", [])
                    if value not in data["data_snapshots"]:
                        data["data_snapshots"].append(value)
                if args.review_adjudication is not None:
                    if not args.review_adjudication.is_file():
                        raise WorkspaceError(f"review adjudication not found: {args.review_adjudication}")
                    data["review_adjudication"] = locator(args.review_adjudication, workspace_path.parent)
                return {"governance_updated": True}

            mutate(args.workspace, update_governance, "governance-updated")
        elif args.command == "rehash-run":
            workspace_path, data = load(args.workspace)
            run = find(data["runs"], args.id, "run")
            for stream_name in ("stdout", "stderr"):
                stream_path = resolve(str(run.get(stream_name, "")), workspace_path.parent)
                if not stream_path.is_file():
                    raise WorkspaceError(f"{stream_name} capture not found: {stream_path}")
                run[f"{stream_name}_sha256"] = ic.sha256(stream_path)
            for output in run.get("outputs", []):
                output_path = resolve(str(output.get("file", "")), workspace_path.parent)
                if not output_path.is_file():
                    raise WorkspaceError(f"run output not found: {output_path}")
                output["sha256"] = ic.sha256(output_path)
            save(workspace_path, data, "run-rehashed", {"run_id": args.id})
        elif args.command == "set-stage":

            def update_stage(data: dict[str, Any]) -> dict[str, Any]:
                data["stage"] = args.stage
                return {"stage": args.stage}

            workspace_path, data = load(args.workspace)
            details = update_stage(data)
            errors, _ = validate_workspace(data, workspace_path, release=args.stage == "RELEASED")
            if errors:
                raise WorkspaceError("; ".join(errors))
            save(workspace_path, data, "stage-updated", details)
        print("OK")
        return 0
    except (WorkspaceError, ic.ContractError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
