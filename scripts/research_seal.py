#!/usr/bin/env python3
"""Seal preregistered plans and verify computation receipts against immutable files."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import sys
import os
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
VALIDATOR_VERSION = "1.0.0"
PLAN_FIELDS = (
    "claim",
    "estimand",
    "sample_window",
    "exclusion_rules",
    "primary_method",
    "sensitivity_set",
    "decision_rule",
    "multiplicity_family",
)


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def portable_locator(path: Path, base_dir: Path | None) -> str:
    resolved = path.resolve()
    return os.path.relpath(resolved, base_dir.resolve()).replace("\\", "/") if base_dir else str(resolved)


def resolve_locator(value: str, base_dir: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def seal_plan(plan_path: Path, protocol: str, base_dir: Path | None = None) -> dict[str, Any]:
    plan = load_object(plan_path)
    missing = [field for field in PLAN_FIELDS if field not in plan]
    if missing:
        raise ValueError("plan is missing preregistration fields: " + ", ".join(missing))
    blank = [field for field in PLAN_FIELDS if plan[field] in (None, "", [])]
    if blank:
        raise ValueError("plan has blank preregistration fields: " + ", ".join(blank))
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "plan-seal",
        "protocol": protocol,
        "created_at": timestamp(),
        "plan_file": portable_locator(plan_path, base_dir),
        "plan_sha256": sha256(plan_path),
        "semantic_sha256": canonical_hash({field: plan[field] for field in PLAN_FIELDS}),
        "sealed_fields": list(PLAN_FIELDS),
        "status": "SEALED",
        "validator_version": VALIDATOR_VERSION,
    }


def verify_plan(seal_path: Path) -> tuple[list[str], dict[str, Any]]:
    seal = load_object(seal_path)
    errors: list[str] = []
    if seal.get("kind") != "plan-seal" or seal.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported plan seal")
        return errors, seal
    plan_path = resolve_locator(str(seal.get("plan_file", "")), seal_path.parent)
    if not plan_path.is_file():
        errors.append("sealed plan file is missing")
        return errors, seal
    if sha256(plan_path) != seal.get("plan_sha256"):
        errors.append("sealed plan bytes changed")
    try:
        plan = load_object(plan_path)
        semantic = {field: plan[field] for field in PLAN_FIELDS}
        if canonical_hash(semantic) != seal.get("semantic_sha256"):
            errors.append("sealed plan semantics changed")
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(f"sealed plan is invalid: {exc}")
    return errors, seal


def file_binding(path: Path, base_dir: Path | None = None) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"bound file does not exist: {path}")
    return {"file": portable_locator(path, base_dir), "sha256": sha256(path)}


def make_receipt(
    inputs: list[Path],
    outputs: list[Path],
    locks: list[Path],
    *,
    command: str,
    backend: str,
    backend_version: str,
    semantic_domain: str,
    returncode: int,
    result: str,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    if not command.strip() or not backend.strip() or not backend_version.strip() or not semantic_domain.strip():
        raise ValueError("command, backend, backend version, and semantic domain are required")
    if not inputs or not outputs:
        raise ValueError("a receipt requires at least one input and one output")
    if result not in {"ESTABLISHED", "NOT_ESTABLISHED", "FAILED"}:
        raise ValueError("invalid semantic result")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "verification-receipt",
        "created_at": timestamp(),
        "validator_version": VALIDATOR_VERSION,
        "semantic_domain": semantic_domain,
        "backend": {"name": backend, "version": backend_version},
        "command": command,
        "returncode": returncode,
        "result": result,
        "inputs": [file_binding(path, base_dir) for path in inputs],
        "outputs": [file_binding(path, base_dir) for path in outputs],
        "environment_locks": [file_binding(path, base_dir) for path in locks],
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
    }


def verify_receipt(receipt_path: Path, require_established: bool = False) -> tuple[list[str], dict[str, Any]]:
    receipt = load_object(receipt_path)
    errors: list[str] = []
    if receipt.get("kind") != "verification-receipt" or receipt.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported verification receipt")
        return errors, receipt
    for field in ("semantic_domain", "command", "backend", "inputs", "outputs", "result", "returncode"):
        if field not in receipt:
            errors.append(f"receipt is missing {field}")
    for collection in ("inputs", "outputs", "environment_locks"):
        records = receipt.get(collection, [])
        if not isinstance(records, list):
            errors.append(f"receipt {collection} must be a list")
            continue
        for record in records:
            path = resolve_locator(str(record.get("file", "")), receipt_path.parent) if isinstance(record, dict) else Path("")
            if not path.is_file():
                errors.append(f"receipt-bound {collection} file is missing: {path}")
            elif sha256(path) != record.get("sha256"):
                errors.append(f"receipt-bound {collection} file changed: {path}")
    if not receipt.get("inputs") or not receipt.get("outputs"):
        errors.append("receipt must bind at least one input and one output")
    if require_established and (receipt.get("returncode") != 0 or receipt.get("result") != "ESTABLISHED"):
        errors.append("receipt does not establish the claim")
    if require_established and receipt.get("outputs"):
        backend = receipt.get("backend", {})
        backend_name = backend.get("name") if isinstance(backend, dict) else None
        if backend_name not in {"sympy", "lean"}:
            errors.append("decisive machine receipt requires a supported semantic verifier (sympy or lean)")
        for record in receipt.get("outputs", []):
            try:
                output = load_object(resolve_locator(str(record["file"]), receipt_path.parent))
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                errors.append(f"cannot inspect backend output semantics: {exc}")
                continue
            if backend_name == "sympy":
                if output.get("backend") != "sympy" or output.get("backend_version") != backend.get("version"):
                    errors.append("SymPy output/backend version does not match receipt")
                if output.get("identity_established") is not True or output.get("recommended_evidence_role") != "decisive":
                    errors.append("SymPy output is not a decisive exact certificate")
            elif backend_name == "lean":
                if output.get("backend") != "lean" or output.get("backend_version") != backend.get("version"):
                    errors.append("Lean output/backend version does not match receipt")
                if output.get("trusted_certificate") is not True or output.get("returncode") != 0:
                    errors.append("Lean output is not a closed trusted certificate")
    return errors, receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    seal = commands.add_parser("seal-plan")
    seal.add_argument("--plan", type=Path, required=True)
    seal.add_argument("--protocol", required=True)
    seal.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify-plan")
    verify.add_argument("--seal", type=Path, required=True)
    receipt = commands.add_parser("wrap-receipt")
    receipt.add_argument("--input", type=Path, action="append", required=True)
    receipt.add_argument("--output-file", type=Path, action="append", required=True)
    receipt.add_argument("--lock", type=Path, action="append", default=[])
    receipt.add_argument("--command-line", required=True)
    receipt.add_argument("--backend", required=True)
    receipt.add_argument("--backend-version", required=True)
    receipt.add_argument("--semantic-domain", required=True)
    receipt.add_argument("--returncode", type=int, required=True)
    receipt.add_argument("--result", choices=("ESTABLISHED", "NOT_ESTABLISHED", "FAILED"), required=True)
    receipt.add_argument("--receipt", type=Path, required=True)
    check = commands.add_parser("verify-receipt")
    check.add_argument("--receipt", type=Path, required=True)
    check.add_argument("--require-established", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "seal-plan":
            write_json(args.output, seal_plan(args.plan, args.protocol, args.output.parent))
            print(args.output)
            return 0
        if args.command == "verify-plan":
            errors, _ = verify_plan(args.seal)
        elif args.command == "wrap-receipt":
            receipt = make_receipt(
                args.input,
                args.output_file,
                args.lock,
                command=args.command_line,
                backend=args.backend,
                backend_version=args.backend_version,
                semantic_domain=args.semantic_domain,
                returncode=args.returncode,
                result=args.result,
                base_dir=args.receipt.parent,
            )
            write_json(args.receipt, receipt)
            print(args.receipt)
            return 0
        else:
            errors, _ = verify_receipt(args.receipt, args.require_established)
        for error in errors:
            print(f"ERROR: {error}")
        if errors:
            return 1
        print("VALID")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
