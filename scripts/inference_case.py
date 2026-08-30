#!/usr/bin/env python3
"""Create and validate inference contracts for mathematics, statistics, and finance."""

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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import research_seal as rs


SCHEMA_VERSION = 3
DOMAINS = ("mathematics", "statistics", "finance")
VERDICTS = ("OPEN", "SUPPORTED", "REFUTED", "INCONCLUSIVE", "MISSPECIFIED")
CLAIM_STATUSES = ("OPEN", "SUPPORTED", "REFUTED", "INCONCLUSIVE", "MISSPECIFIED")
ASSUMPTION_STATUSES = ("UNTESTED", "JUSTIFIED", "CONDITIONAL", "VIOLATED")
CHECK_OUTCOMES = ("OPEN", "CLEARED", "TRIGGERED", "UNRESOLVED")
EVIDENCE_KINDS = (
    "source",
    "derivation",
    "exact-computation",
    "numerical-computation",
    "simulation",
    "dataset",
    "diagnostic",
    "replication",
    "formal-certificate",
    "counterexample",
)
EVIDENCE_ROLES = ("decisive", "diagnostic", "suggestive")
CONTRACT_FIELDS = {
    "mathematics": ("ambient_object", "coefficient_domain", "quantifiers", "equality_semantics"),
    "statistics": ("population", "sampling_unit", "outcome", "estimand", "identification"),
    "finance": (
        "universe",
        "clock",
        "information_cutoff",
        "holding_period",
        "split_policy",
        "cost_model",
        "benchmark",
    ),
}
REQUIRED_CHECKS = {
    "mathematics": ("typecheck", "proof", "counterexample"),
    "statistics": ("identification", "uncertainty", "sensitivity", "leakage"),
    "finance": ("information-set", "cost", "benchmark", "walk-forward"),
}
CHECK_KINDS = {
    "mathematics": (
        "specification",
        "typecheck",
        "proof",
        "counterexample",
        "relation",
        "formal",
        "exact-computation",
        "boundary",
    ),
    "statistics": (
        "specification",
        "identification",
        "uncertainty",
        "sensitivity",
        "leakage",
        "diagnostic",
        "simulation",
        "placebo",
        "negative-control",
        "replication",
    ),
    "finance": (
        "specification",
        "information-set",
        "cost",
        "benchmark",
        "walk-forward",
        "multiple-testing",
        "capacity",
        "borrow",
        "regime",
        "risk-model",
    ),
}
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,62}\Z")
ID_RE = re.compile(r"[CAKE][0-9]{3}\Z")
ID_PREFIXES = {"claim": "C", "assumption": "A", "check": "K", "evidence": "E"}


class ContractError(ValueError):
    """Raised when a case mutation would violate the schema."""


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_slug(value: str) -> str:
    if not SLUG_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("use lowercase letters, digits, and hyphens (max 63 characters)")
    return value


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def load_case(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = path.resolve()
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"case file not found: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError("case root must be a JSON object")
    return resolved, data


def save_case(path: Path, data: dict[str, Any], event: str, details: dict[str, Any]) -> None:
    stamp = timestamp()
    data["updated_at"] = stamp
    atomic_json(path, data)
    with (path.parent / "journal.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
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
    raise ContractError(f"unknown {label}: {item_id}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_locator(locator: str, case_dir: Path) -> Path:
    path = Path(locator)
    return path if path.is_absolute() else case_dir / path


def file_record(path: Path, case_dir: Path) -> tuple[str, str]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ContractError(f"evidence file not found: {resolved}")
    try:
        locator = resolved.relative_to(case_dir).as_posix()
    except ValueError:
        locator = str(resolved)
    return locator, sha256(resolved)


def initialize(root: Path, slug: str, domain: str, question: str, claim: str) -> Path:
    if not question.strip() or not claim.strip():
        raise ContractError("question and claim must be non-empty")
    case_dir = root.resolve() / slug
    case_path = case_dir / "case.json"
    if case_path.exists():
        raise ContractError(f"case already exists: {case_path}")
    stamp = timestamp()
    data = {
        "schema_version": SCHEMA_VERSION,
        "case_id": slug,
        "domain": domain,
        "question": question.strip(),
        "created_at": stamp,
        "updated_at": stamp,
        "contract": {field: "" for field in CONTRACT_FIELDS[domain]},
        "claims": [
            {
                "id": "C001",
                "statement": claim.strip(),
                "scope": "",
                "status": "OPEN",
                "assumption_ids": [],
                "evidence_ids": [],
            }
        ],
        "assumptions": [],
        "checks": [],
        "evidence": [],
        "decision": {
            "verdict": "OPEN",
            "claim_id": "C001",
            "reason": "",
            "evidence_ids": [],
            "limitations": "",
            "reproduction": "",
        },
    }
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "artifacts").mkdir(exist_ok=True)
    atomic_json(case_path, data)
    (case_dir / "journal.jsonl").write_text(
        json.dumps({"time": stamp, "event": "initialized", "domain": domain}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return case_path


def validate_case(data: dict[str, Any], case_path: Path, release: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required = (
        "schema_version",
        "case_id",
        "domain",
        "question",
        "contract",
        "claims",
        "assumptions",
        "checks",
        "evidence",
        "decision",
    )
    missing_top = [key for key in required if key not in data]
    if missing_top:
        return [f"missing top-level field: {key}" for key in missing_top], warnings
    if data["schema_version"] != SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {data['schema_version']!r}")
    domain = data["domain"]
    if domain not in DOMAINS:
        errors.append(f"invalid domain: {domain!r}")
        return errors, warnings
    if not str(data["question"]).strip():
        errors.append("question must be non-empty")
    if not isinstance(data["contract"], dict):
        errors.append("contract must be an object")
        return errors, warnings

    collections = {"claim": data["claims"], "assumption": data["assumptions"], "check": data["checks"], "evidence": data["evidence"]}
    ids: dict[str, set[str]] = {}
    all_ids: set[str] = set()
    for label, items in collections.items():
        if not isinstance(items, list):
            errors.append(f"{label} collection must be a list")
            ids[label] = set()
            continue
        values = [item.get("id") for item in items if isinstance(item, dict)]
        if len(values) != len(items) or any(not isinstance(value, str) for value in values):
            errors.append(f"{label} entries require string IDs")
        malformed = [
            value
            for value in values
            if isinstance(value, str)
            and (not ID_RE.fullmatch(value) or not value.startswith(ID_PREFIXES[label]))
        ]
        if malformed:
            errors.append(f"malformed {label} IDs: {', '.join(sorted(malformed))}")
        duplicates = {value for value in values if values.count(value) > 1}
        if duplicates:
            errors.append(f"duplicate {label} IDs: {', '.join(sorted(duplicates))}")
        overlap = all_ids.intersection(value for value in values if isinstance(value, str))
        if overlap:
            errors.append(f"IDs reused across collections: {', '.join(sorted(overlap))}")
        ids[label] = {value for value in values if isinstance(value, str)}
        all_ids.update(ids[label])

    evidence_ids = ids.get("evidence", set())
    for item in data["evidence"]:
        eid = item.get("id", "?")
        if item.get("kind") not in EVIDENCE_KINDS:
            errors.append(f"{eid}: invalid evidence kind")
        if item.get("role") not in EVIDENCE_ROLES:
            errors.append(f"{eid}: invalid evidence role")
        if not isinstance(item.get("independent"), bool):
            errors.append(f"{eid}: independent must be boolean")
        if not str(item.get("summary", "")).strip() or not str(item.get("locator", "")).strip():
            errors.append(f"{eid}: summary and locator are required")
        checksum = item.get("sha256")
        if checksum:
            artifact = resolve_locator(str(item.get("locator", "")), case_path.parent)
            if not artifact.is_file():
                errors.append(f"{eid}: checksummed artifact is missing")
            elif sha256(artifact) != checksum:
                errors.append(f"{eid}: checksum mismatch")

    for item in data["assumptions"]:
        aid = item.get("id", "?")
        status = item.get("status")
        if status not in ASSUMPTION_STATUSES:
            errors.append(f"{aid}: invalid assumption status")
        if not str(item.get("statement", "")).strip() or not str(item.get("role", "")).strip():
            errors.append(f"{aid}: statement and role are required")
        links = item.get("evidence_ids", [])
        if not isinstance(links, list):
            errors.append(f"{aid}: evidence_ids must be a list")
            links = []
        unknown = [value for value in links if value not in evidence_ids]
        if unknown:
            errors.append(f"{aid}: unknown evidence IDs: {', '.join(unknown)}")
        if status in {"JUSTIFIED", "VIOLATED"} and not links:
            errors.append(f"{aid}: {status} assumption requires evidence")

    claim_ids = ids.get("claim", set())
    assumption_ids = ids.get("assumption", set())
    for item in data["claims"]:
        cid = item.get("id", "?")
        if item.get("status") not in CLAIM_STATUSES:
            errors.append(f"{cid}: invalid claim status")
        if not str(item.get("statement", "")).strip():
            errors.append(f"{cid}: statement is required")
        for field, allowed in (("assumption_ids", assumption_ids), ("evidence_ids", evidence_ids)):
            links = item.get(field, [])
            if not isinstance(links, list):
                errors.append(f"{cid}: {field} must be a list")
                continue
            unknown = [value for value in links if value not in allowed]
            if unknown:
                errors.append(f"{cid}: unknown {field}: {', '.join(unknown)}")

    check_ids = ids.get("check", set())
    for item in data["checks"]:
        kid = item.get("id", "?")
        if item.get("kind") not in CHECK_KINDS[domain]:
            errors.append(f"{kid}: check kind {item.get('kind')!r} is invalid for {domain}")
        if item.get("target_claim") not in claim_ids:
            errors.append(f"{kid}: unknown target claim")
        if item.get("outcome") not in CHECK_OUTCOMES:
            errors.append(f"{kid}: invalid check outcome")
        if (
            not str(item.get("target", "")).strip()
            or not str(item.get("falsifier", "")).strip()
            or not str(item.get("coverage", "")).strip()
        ):
            errors.append(f"{kid}: target, falsifier, and coverage are required")
        links = item.get("evidence_ids", [])
        unknown = [value for value in links if value not in evidence_ids]
        if unknown:
            errors.append(f"{kid}: unknown evidence IDs: {', '.join(unknown)}")
        if item.get("outcome") in {"CLEARED", "TRIGGERED"} and not links:
            errors.append(f"{kid}: decisive outcome requires evidence")
        if item.get("outcome") != "OPEN" and not str(item.get("result", "")).strip():
            errors.append(f"{kid}: non-OPEN outcome requires a result summary")

    decision = data["decision"]
    if not isinstance(decision, dict) or decision.get("verdict") not in VERDICTS:
        errors.append("decision verdict is invalid")
        return errors, warnings
    decision_claim = decision.get("claim_id")
    if decision_claim not in claim_ids:
        errors.append("decision references an unknown claim")
    decision_evidence = decision.get("evidence_ids", [])
    if not isinstance(decision_evidence, list):
        errors.append("decision evidence_ids must be a list")
        decision_evidence = []
    unknown = [value for value in decision_evidence if value not in evidence_ids]
    if unknown:
        errors.append(f"decision references unknown evidence: {', '.join(unknown)}")

    if not release:
        return errors, warnings

    empty_contract = [field for field in CONTRACT_FIELDS[domain] if not str(data["contract"].get(field, "")).strip()]
    if empty_contract:
        errors.append(f"release requires contract fields: {', '.join(empty_contract)}")
    verdict = decision.get("verdict")
    if verdict == "OPEN":
        errors.append("release requires a non-OPEN verdict")
    if not str(decision.get("reason", "")).strip():
        errors.append("release requires a decision reason")
    if not decision_evidence:
        errors.append("release requires decision evidence")
    if not str(decision.get("limitations", "")).strip():
        errors.append("release requires explicit limitations")
    if not str(decision.get("reproduction", "")).strip():
        errors.append("release requires reproduction instructions")
    claim = next((item for item in data["claims"] if item.get("id") == decision_claim), None)
    if not claim:
        return errors, warnings
    if claim.get("status") != verdict:
        errors.append("decision verdict must match the target claim status")

    linked_assumptions = [item for item in data["assumptions"] if item.get("id") in claim.get("assumption_ids", [])]
    target_checks = [item for item in data["checks"] if item.get("target_claim") == decision_claim]
    evidence_by_id = {item["id"]: item for item in data["evidence"]}
    decisive_decision_evidence = [
        evidence_by_id[evidence_id]
        for evidence_id in decision_evidence
        if evidence_id in evidence_by_id and evidence_by_id[evidence_id].get("role") == "decisive"
    ]
    for item in decisive_decision_evidence:
        artifact = resolve_locator(str(item.get("locator", "")), case_path.parent)
        if not item.get("sha256") or not artifact.is_file():
            errors.append(f"{item['id']}: decisive release evidence must be a checksummed local artifact")
        if item.get("kind") in {"exact-computation", "formal-certificate"}:
            receipt_value = str(item.get("verification_receipt", "")).strip()
            if not receipt_value:
                errors.append(f"{item['id']}: decisive machine evidence requires a verification receipt")
            else:
                receipt_path = resolve_locator(receipt_value, case_path.parent)
                if not receipt_path.is_file():
                    errors.append(f"{item['id']}: verification receipt is missing")
                else:
                    receipt_errors, receipt = rs.verify_receipt(receipt_path, require_established=True)
                    errors.extend(f"{item['id']}: {error}" for error in receipt_errors)
                    output_files = {
                        str(rs.resolve_locator(str(record.get("file", "")), receipt_path.parent).resolve())
                        for record in receipt.get("outputs", []) if isinstance(record, dict)
                    }
                    if str(artifact.resolve()) not in output_files:
                        errors.append(f"{item['id']}: verification receipt does not bind the evidence artifact")
    if verdict == "SUPPORTED":
        if domain in {"statistics", "finance"} and not linked_assumptions:
            errors.append(f"SUPPORTED {domain} release requires at least one explicit assumption")
        bad_assumptions = [item["id"] for item in linked_assumptions if item.get("status") in {"UNTESTED", "VIOLATED"}]
        if bad_assumptions:
            errors.append(f"SUPPORTED claim has unresolved or violated assumptions: {', '.join(bad_assumptions)}")
        conditional = [item["id"] for item in linked_assumptions if item.get("status") == "CONDITIONAL"]
        if conditional and not str(claim.get("scope", "")).strip():
            errors.append(f"SUPPORTED conditional claim requires an explicit scope: {', '.join(conditional)}")
        triggered = [item["id"] for item in target_checks if item.get("outcome") == "TRIGGERED"]
        if triggered:
            errors.append(f"SUPPORTED claim has triggered falsifiers: {', '.join(triggered)}")
        cleared = {item.get("kind") for item in target_checks if item.get("outcome") == "CLEARED" and item.get("evidence_ids")}
        missing_checks = [kind for kind in REQUIRED_CHECKS[domain] if kind not in cleared]
        if missing_checks:
            errors.append(f"SUPPORTED {domain} claim lacks cleared checks: {', '.join(missing_checks)}")
        support_evidence = set(decision_evidence) | set(claim.get("evidence_ids", []))
        for item in target_checks:
            support_evidence.update(item.get("evidence_ids", []))
        independent = {item["id"] for item in data["evidence"] if item.get("independent") is True}
        if not support_evidence.intersection(independent):
            warnings.append("SUPPORTED release has no independently produced evidence")
        if not decisive_decision_evidence:
            errors.append("SUPPORTED release requires decisive decision evidence")
    elif verdict == "REFUTED":
        triggered = [item for item in target_checks if item.get("outcome") == "TRIGGERED" and item.get("evidence_ids")]
        if not triggered:
            errors.append("REFUTED release requires a triggered falsifier of the headline claim")
        if not decisive_decision_evidence:
            errors.append("REFUTED release requires decisive decision evidence")
    elif verdict in {"INCONCLUSIVE", "MISSPECIFIED"}:
        if verdict == "MISSPECIFIED" and not any(
            item.get("kind") == "specification" and item.get("outcome") == "TRIGGERED"
            for item in target_checks
        ):
            errors.append("MISSPECIFIED release requires a triggered specification check")
        if verdict == "MISSPECIFIED" and not decisive_decision_evidence:
            errors.append("MISSPECIFIED release requires decisive decision evidence")

    open_checks = [item["id"] for item in target_checks if item.get("outcome") == "OPEN"]
    if open_checks and verdict == "SUPPORTED":
        warnings.append(f"non-required checks remain open: {', '.join(open_checks)}")
    return errors, warnings


def escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(data: dict[str, Any]) -> str:
    lines = [
        f"# Inference case: {data.get('case_id', 'untitled')}",
        "",
        f"- Domain: `{data.get('domain', '-')}`",
        f"- Verdict: `{data.get('decision', {}).get('verdict', '-')}`",
        f"- Question: {data.get('question', '')}",
        "",
        "## Domain contract",
        "",
        "| Field | Value |",
        "|---|---|",
    ]
    for key, value in data.get("contract", {}).items():
        lines.append(f"| `{key}` | {escape(value) or '-'} |")
    lines.extend(["", "## Claims", "", "| ID | Status | Statement | Scope | Assumptions |", "|---|---|---|---|---|"])
    for item in data.get("claims", []):
        lines.append(
            f"| {item['id']} | {item['status']} | {escape(item['statement'])} | {escape(item.get('scope', '')) or '-'} | "
            f"{', '.join(item.get('assumption_ids', [])) or '-'} |"
        )
    lines.extend(["", "## Assumption surface", "", "| ID | Status | Role | Statement | Evidence |", "|---|---|---|---|---|"])
    for item in data.get("assumptions", []):
        lines.append(
            f"| {item['id']} | {item['status']} | {escape(item['role'])} | {escape(item['statement'])} | "
            f"{', '.join(item.get('evidence_ids', [])) or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Falsification checks",
            "",
            "| ID | Kind | Outcome | Target | Falsifier | Coverage | Result | Evidence |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in data.get("checks", []):
        lines.append(
            f"| {item['id']} | {item['kind']} | {item['outcome']} | {escape(item['target'])} | "
            f"{escape(item['falsifier'])} | {escape(item.get('coverage', '')) or '-'} | "
            f"{escape(item.get('result', '')) or '-'} | {', '.join(item.get('evidence_ids', [])) or '-'} |"
        )
    lines.extend(["", "## Evidence", ""])
    for item in data.get("evidence", []):
        independence = "independent" if item.get("independent") else "primary path"
        lines.append(
            f"- **{item['id']}** `{item['kind']}` `{item.get('role', 'unclassified')}` "
            f"({independence}) — {item['summary']} [{item['locator']}]"
        )
    decision = data.get("decision", {})
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"**{decision.get('verdict', 'OPEN')}** — {decision.get('reason') or 'not set'}",
            "",
            f"Limitations: {decision.get('limitations') or 'not set'}",
            "",
            f"Reproduction: {decision.get('reproduction') or 'not set'}",
            "",
        ]
    )
    return "\n".join(lines)


def mutate(path: Path, callback: Any, event: str) -> None:
    case_path, data = load_case(path)
    details = callback(data)
    errors, _ = validate_case(data, case_path, release=False)
    if errors:
        raise ContractError("; ".join(errors))
    save_case(case_path, data, event, details or {})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a new inference case")
    init.add_argument("root", type=Path)
    init.add_argument("slug", type=parse_slug)
    init.add_argument("--domain", choices=DOMAINS, required=True)
    init.add_argument("--question", required=True)
    init.add_argument("--claim", required=True)

    contract = commands.add_parser("set-contract", help="set one domain contract field")
    contract.add_argument("case", type=Path)
    contract.add_argument("--field", required=True)
    contract.add_argument("--value", required=True)

    claim = commands.add_parser("claim", help="add a secondary claim")
    claim.add_argument("case", type=Path)
    claim.add_argument("--statement", required=True)
    claim.add_argument("--scope", default="")

    set_claim = commands.add_parser("set-claim", help="update a claim statement or scope")
    set_claim.add_argument("case", type=Path)
    set_claim.add_argument("--id", default="C001")
    set_claim.add_argument("--statement")
    set_claim.add_argument("--scope")

    assumption = commands.add_parser("assumption", help="add an assumption")
    assumption.add_argument("case", type=Path)
    assumption.add_argument("--statement", required=True)
    assumption.add_argument("--role", required=True)

    check = commands.add_parser("check", help="add a falsification check")
    check.add_argument("case", type=Path)
    check.add_argument("--claim", default="C001")
    check.add_argument("--kind", required=True)
    check.add_argument("--target", required=True)
    check.add_argument("--falsifier", required=True)
    check.add_argument("--coverage", required=True)

    evidence = commands.add_parser("evidence", help="add evidence")
    evidence.add_argument("case", type=Path)
    evidence.add_argument("--kind", choices=EVIDENCE_KINDS, required=True)
    evidence.add_argument("--role", choices=EVIDENCE_ROLES, required=True)
    evidence.add_argument("--summary", required=True)
    location = evidence.add_mutually_exclusive_group(required=True)
    location.add_argument("--file", type=Path)
    location.add_argument("--locator")
    evidence.add_argument("--independent", action="store_true")

    rehash_evidence = commands.add_parser("rehash-evidence", help="accept an intentional file-evidence revision")
    rehash_evidence.add_argument("case", type=Path)
    rehash_evidence.add_argument("--id", required=True)

    link = commands.add_parser("link", help="link evidence to a claim, assumption, or check")
    link.add_argument("case", type=Path)
    link.add_argument("--evidence", required=True)
    link.add_argument("--target", required=True)

    use_assumption = commands.add_parser("use-assumption", help="bind an assumption to a claim")
    use_assumption.add_argument("case", type=Path)
    use_assumption.add_argument("--claim", default="C001")
    use_assumption.add_argument("--assumption", required=True)

    set_assumption = commands.add_parser("set-assumption", help="set assumption status")
    set_assumption.add_argument("case", type=Path)
    set_assumption.add_argument("--id", required=True)
    set_assumption.add_argument("--status", choices=ASSUMPTION_STATUSES, required=True)

    set_check = commands.add_parser("set-check", help="set check outcome")
    set_check.add_argument("case", type=Path)
    set_check.add_argument("--id", required=True)
    set_check.add_argument("--outcome", choices=CHECK_OUTCOMES, required=True)
    set_check.add_argument("--result", default="")

    decide = commands.add_parser("decide", help="record the scoped verdict")
    decide.add_argument("case", type=Path)
    decide.add_argument("--claim", default="C001")
    decide.add_argument("--verdict", choices=VERDICTS[1:], required=True)
    decide.add_argument("--reason", required=True)
    decide.add_argument("--evidence", nargs="+", required=True)
    decide.add_argument("--limitations", required=True)
    decide.add_argument("--reproduction", required=True)

    validate = commands.add_parser("validate", help="validate a case")
    validate.add_argument("case", type=Path)
    validate.add_argument("--release", action="store_true")

    report = commands.add_parser("report", help="validate the case and write report.md")
    report.add_argument("case", type=Path)
    report.add_argument("--release", action="store_true", help="require the release gate before writing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            path = initialize(args.root, args.slug, args.domain, args.question, args.claim)
            print(path)
            return 0
        if args.command == "validate":
            path, data = load_case(args.case)
            errors, warnings = validate_case(data, path, release=args.release)
            for warning in warnings:
                print(f"WARNING: {warning}")
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            if errors:
                return 1
            print("VALID")
            return 0
        if args.command == "report":
            path, data = load_case(args.case)
            errors, warnings = validate_case(data, path, release=args.release)
            for warning in warnings:
                print(f"WARNING: {warning}")
            if errors:
                raise ContractError("; ".join(errors))
            destination = path.parent / "report.md"
            destination.write_text(render(data), encoding="utf-8", newline="\n")
            print(destination)
            return 0

        if args.command == "set-contract":
            def change_contract(data: dict[str, Any]) -> dict[str, Any]:
                if args.field not in CONTRACT_FIELDS[data["domain"]]:
                    raise ContractError(f"{args.field!r} is not a contract field for {data['domain']}")
                data["contract"][args.field] = args.value.strip()
                return {"field": args.field}
            mutate(args.case, change_contract, "contract-set")
        elif args.command == "claim":
            def add_claim(data: dict[str, Any]) -> dict[str, Any]:
                item_id = next_id(data["claims"], "C")
                data["claims"].append({"id": item_id, "statement": args.statement.strip(), "scope": args.scope.strip(), "status": "OPEN", "assumption_ids": [], "evidence_ids": []})
                return {"claim_id": item_id}
            mutate(args.case, add_claim, "claim-added")
        elif args.command == "set-claim":
            def update_claim(data: dict[str, Any]) -> dict[str, Any]:
                if args.statement is None and args.scope is None:
                    raise ContractError("set-claim requires --statement or --scope")
                item = find(data["claims"], args.id, "claim")
                if args.statement is not None:
                    if not args.statement.strip():
                        raise ContractError("claim statement must be non-empty")
                    item["statement"] = args.statement.strip()
                if args.scope is not None:
                    item["scope"] = args.scope.strip()
                return {"claim_id": args.id}
            mutate(args.case, update_claim, "claim-updated")
        elif args.command == "assumption":
            def add_assumption(data: dict[str, Any]) -> dict[str, Any]:
                item_id = next_id(data["assumptions"], "A")
                data["assumptions"].append({"id": item_id, "statement": args.statement.strip(), "role": args.role.strip(), "status": "UNTESTED", "evidence_ids": []})
                return {"assumption_id": item_id}
            mutate(args.case, add_assumption, "assumption-added")
        elif args.command == "check":
            def add_check(data: dict[str, Any]) -> dict[str, Any]:
                if args.kind not in CHECK_KINDS[data["domain"]]:
                    raise ContractError(f"check kind {args.kind!r} is invalid for {data['domain']}")
                find(data["claims"], args.claim, "claim")
                item_id = next_id(data["checks"], "K")
                data["checks"].append(
                    {
                        "id": item_id,
                        "target_claim": args.claim,
                        "kind": args.kind,
                        "target": args.target.strip(),
                        "falsifier": args.falsifier.strip(),
                        "coverage": args.coverage.strip(),
                        "outcome": "OPEN",
                        "result": "",
                        "evidence_ids": [],
                    }
                )
                return {"check_id": item_id}
            mutate(args.case, add_check, "check-added")
        elif args.command == "evidence":
            def add_evidence(data: dict[str, Any]) -> dict[str, Any]:
                path, _ = load_case(args.case)
                checksum = None
                if args.file:
                    locator, checksum = file_record(args.file, path.parent)
                else:
                    locator = args.locator.strip()
                item_id = next_id(data["evidence"], "E")
                data["evidence"].append(
                    {
                        "id": item_id,
                        "kind": args.kind,
                        "role": args.role,
                        "summary": args.summary.strip(),
                        "locator": locator,
                        "sha256": checksum,
                        "independent": args.independent,
                    }
                )
                return {"evidence_id": item_id}
            mutate(args.case, add_evidence, "evidence-added")
        elif args.command == "rehash-evidence":
            case_path, data = load_case(args.case)
            item = find(data["evidence"], args.id, "evidence")
            if not item.get("sha256"):
                raise ContractError("only checksummed file evidence can be rehashed")
            artifact = resolve_locator(str(item.get("locator", "")), case_path.parent)
            if not artifact.is_file():
                raise ContractError(f"evidence file not found: {artifact}")
            previous = item["sha256"]
            item["sha256"] = sha256(artifact)
            save_case(
                case_path,
                data,
                "evidence-rehashed",
                {"evidence_id": args.id, "previous_sha256": previous, "sha256": item["sha256"]},
            )
        elif args.command == "link":
            def add_link(data: dict[str, Any]) -> dict[str, Any]:
                find(data["evidence"], args.evidence, "evidence")
                prefix = args.target[:1]
                mapping = {"C": ("claims", "claim"), "A": ("assumptions", "assumption"), "K": ("checks", "check")}
                if prefix not in mapping:
                    raise ContractError("target must be a claim, assumption, or check ID")
                collection, label = mapping[prefix]
                target = find(data[collection], args.target, label)
                target.setdefault("evidence_ids", [])
                if args.evidence not in target["evidence_ids"]:
                    target["evidence_ids"].append(args.evidence)
                return {"target": args.target, "evidence_id": args.evidence}
            mutate(args.case, add_link, "evidence-linked")
        elif args.command == "use-assumption":
            def bind_assumption(data: dict[str, Any]) -> dict[str, Any]:
                claim_item = find(data["claims"], args.claim, "claim")
                find(data["assumptions"], args.assumption, "assumption")
                if args.assumption not in claim_item["assumption_ids"]:
                    claim_item["assumption_ids"].append(args.assumption)
                return {"claim_id": args.claim, "assumption_id": args.assumption}
            mutate(args.case, bind_assumption, "assumption-bound")
        elif args.command == "set-assumption":
            def update_assumption(data: dict[str, Any]) -> dict[str, Any]:
                find(data["assumptions"], args.id, "assumption")["status"] = args.status
                return {"assumption_id": args.id, "status": args.status}
            mutate(args.case, update_assumption, "assumption-updated")
        elif args.command == "set-check":
            def update_check(data: dict[str, Any]) -> dict[str, Any]:
                if args.outcome != "OPEN" and not args.result.strip():
                    raise ContractError("a non-OPEN check outcome requires --result")
                item = find(data["checks"], args.id, "check")
                item["outcome"] = args.outcome
                item["result"] = args.result.strip() if args.outcome != "OPEN" else ""
                return {"check_id": args.id, "outcome": args.outcome}
            mutate(args.case, update_check, "check-updated")
        elif args.command == "decide":
            def record_decision(data: dict[str, Any]) -> dict[str, Any]:
                claim_item = find(data["claims"], args.claim, "claim")
                for evidence_id in args.evidence:
                    find(data["evidence"], evidence_id, "evidence")
                claim_item["status"] = args.verdict
                claim_item["evidence_ids"] = list(dict.fromkeys([*claim_item.get("evidence_ids", []), *args.evidence]))
                data["decision"] = {
                    "verdict": args.verdict,
                    "claim_id": args.claim,
                    "reason": args.reason.strip(),
                    "evidence_ids": list(dict.fromkeys(args.evidence)),
                    "limitations": args.limitations.strip(),
                    "reproduction": args.reproduction.strip(),
                }
                return {"claim_id": args.claim, "verdict": args.verdict}
            mutate(args.case, record_decision, "decision-recorded")
        print("OK")
        return 0
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
