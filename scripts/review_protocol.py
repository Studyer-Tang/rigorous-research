#!/usr/bin/env python3
"""Prepare tamper-evident blind review packets and adjudicate independent reviews."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from research_io import (
    canonical_hash,
    load_json_object as load,
    portable_locator as locator,
    resolve_locator as resolve,
    sha256,
    utc_timestamp as timestamp,
    write_json as write,
)

SCHEMA_VERSION = 1
ASSESSMENTS = ("ACCEPT", "REJECT", "REVISE")


def blind_case(case: dict[str, Any]) -> dict[str, Any]:
    """Retain truth-relevant material while hiding the author's conclusion and evidence labels."""
    evidence = []
    for item in case.get("evidence", []):
        evidence.append({key: value for key, value in item.items() if key not in {"role", "independent", "summary"}})
    claims = []
    for item in case.get("claims", []):
        claims.append({key: value for key, value in item.items() if key not in {"status", "scope"}})
    checks = []
    for item in case.get("checks", []):
        checks.append({key: value for key, value in item.items() if key not in {"outcome", "result"}})
    return {
        "domain": case.get("domain"),
        "question": case.get("question"),
        "contract": case.get("contract"),
        "claims": claims,
        "assumptions": [
            {key: value for key, value in item.items() if key != "status"} for item in case.get("assumptions", [])
        ],
        "checks": checks,
        "evidence": evidence,
    }


def prepare(case_path: Path, artifact_paths: list[Path], base_dir: Path | None = None) -> dict[str, Any]:
    case = load(case_path)
    missing = [str(path) for path in artifact_paths if not path.is_file()]
    if missing:
        raise ValueError("review artifact is missing: " + ", ".join(missing))
    if base_dir is None:
        raise ValueError("blind packet preparation requires an isolated output directory")
    blinded = blind_case(case)
    snapshot_dir = base_dir / "sealed-artifacts"
    if snapshot_dir.exists():
        raise ValueError(f"refusing to overwrite existing blind artifacts: {snapshot_dir}")
    snapshot_dir.mkdir(parents=True)
    snapshots = []
    for index, source in enumerate(artifact_paths, start=1):
        suffix = source.suffix if source.suffix.lower() in {".md", ".txt", ".json", ".py", ".lean"} else ".bin"
        destination = snapshot_dir / f"A{index:03d}{suffix}"
        shutil.copyfile(source, destination)
        snapshots.append(
            {
                "id": f"A{index:03d}",
                "file": locator(destination, base_dir),
                "sha256": sha256(destination),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "blind-review-packet",
        "created_at": timestamp(),
        "author_case_commitment": sha256(case_path),
        "blinded_case": blinded,
        "blinded_case_sha256": canonical_hash(blinded),
        "artifacts": snapshots,
        "redactions": [
            "author identity",
            "author verdict",
            "claim status",
            "check outcomes",
            "evidence role",
        ],
    }


def verify_packet(packet_path: Path) -> tuple[list[str], dict[str, Any]]:
    packet = load(packet_path)
    errors: list[str] = []
    if packet.get("kind") != "blind-review-packet" or packet.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported blind review packet")
        return errors, packet
    if canonical_hash(packet.get("blinded_case")) != packet.get("blinded_case_sha256"):
        errors.append("blinded case changed")
    for item in packet.get("artifacts", []):
        path = resolve(str(item.get("file", "")), packet_path.parent)
        if not path.is_file() or sha256(path) != item.get("sha256"):
            errors.append(f"review artifact changed: {path}")
    return errors, packet


def submit(
    packet_path: Path,
    reviewer: str,
    assessment: str,
    reproduced: bool,
    fatal: list[str],
    major: list[str],
    minor: list[str],
    author_ids: list[str],
    base_dir: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    errors, packet = verify_packet(packet_path)
    if errors:
        raise ValueError("; ".join(errors))
    reviewer_key = reviewer.strip().casefold()
    conflicts = [identity for identity in author_ids if identity.strip().casefold() == reviewer_key]
    if report_path is not None and not report_path.is_file():
        raise ValueError(f"review report is missing: {report_path}")
    result = {
        "schema_version": SCHEMA_VERSION,
        "kind": "review-receipt",
        "created_at": timestamp(),
        "packet_file": locator(packet_path, base_dir),
        "packet_sha256": sha256(packet_path),
        "blinded_case_sha256": packet["blinded_case_sha256"],
        "reviewer": reviewer.strip(),
        "identity_assurance": "SELF_DECLARED",
        "independence": "CONFLICT" if conflicts else "DECLARED_INDEPENDENT",
        "assessment": assessment,
        "reproduced": reproduced,
        "issues": {"fatal": fatal, "major": major, "minor": minor},
    }
    if report_path is not None:
        result["review_report"] = {
            "file": locator(report_path, base_dir),
            "sha256": sha256(report_path),
        }
    return result


def verify_review(review_path: Path) -> tuple[list[str], dict[str, Any]]:
    review = load(review_path)
    errors: list[str] = []
    if review.get("kind") != "review-receipt" or review.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported review receipt")
        return errors, review
    packet_path = resolve(str(review.get("packet_file", "")), review_path.parent)
    if not packet_path.is_file() or sha256(packet_path) != review.get("packet_sha256"):
        errors.append("reviewed packet changed")
        return errors, review
    packet_errors, packet = verify_packet(packet_path)
    errors.extend(packet_errors)
    if review.get("blinded_case_sha256") != packet.get("blinded_case_sha256"):
        errors.append("review does not bind the blinded case")
    if review.get("assessment") not in ASSESSMENTS:
        errors.append("invalid review assessment")
    if review.get("independence") != "DECLARED_INDEPENDENT":
        errors.append("reviewer independence conflict")
    if not str(review.get("reviewer", "")).strip():
        errors.append("reviewer identity is blank")
    if review.get("identity_assurance") != "SELF_DECLARED":
        errors.append("reviewer identity assurance is not declared")
    report = review.get("review_report")
    if report:
        report_path = resolve(str(report.get("file", "")), review_path.parent)
        if not report_path.is_file() or sha256(report_path) != report.get("sha256"):
            errors.append("review report changed")
    return errors, review


def adjudicate(case_path: Path, reviews: list[Path], base_dir: Path | None = None) -> dict[str, Any]:
    case = load(case_path)
    author_verdict = case.get("decision", {}).get("verdict", "OPEN")
    verified: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in reviews:
        review_errors, review = verify_review(path)
        errors.extend(f"{path}: {error}" for error in review_errors)
        packet_path = resolve(str(review.get("packet_file", "")), path.parent)
        if packet_path.is_file():
            packet = load(packet_path)
            if packet.get("author_case_commitment") != sha256(case_path):
                errors.append(f"{path}: author case changed after blind packet preparation")
        verified.append(review)
    if errors or any(item.get("assessment") != "ACCEPT" or item.get("issues", {}).get("fatal") for item in verified):
        status = "RECONCILIATION_REQUIRED"
    elif not verified:
        status = "REVIEW_REQUIRED"
    else:
        status = "CLEARED_FOR_RELEASE"
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "review-adjudication",
        "created_at": timestamp(),
        "case_file": locator(case_path, base_dir),
        "case_sha256": sha256(case_path),
        "author_verdict_revealed": author_verdict,
        "review_count": len(verified),
        "reviewers": [item.get("reviewer") for item in verified],
        "reviews": [{"file": locator(path, base_dir), "sha256": sha256(path)} for path in reviews],
        "status": status,
        "errors": errors,
    }


def verify_adjudication(path: Path, require_clear: bool = True) -> tuple[list[str], dict[str, Any]]:
    value = load(path)
    errors: list[str] = []
    if value.get("kind") != "review-adjudication" or value.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported review adjudication")
        return errors, value
    case_path = resolve(str(value.get("case_file", "")), path.parent)
    if not case_path.is_file() or sha256(case_path) != value.get("case_sha256"):
        errors.append("adjudicated case changed")
    review_paths: list[Path] = []
    for record in value.get("reviews", []):
        review_path = resolve(str(record.get("file", "")), path.parent)
        review_paths.append(review_path)
        if not review_path.is_file() or sha256(review_path) != record.get("sha256"):
            errors.append(f"adjudicated review changed: {review_path}")
        else:
            review_errors, _ = verify_review(review_path)
            errors.extend(review_errors)
    if len(review_paths) != value.get("review_count"):
        errors.append("adjudication review count mismatch")
    if require_clear and value.get("status") != "CLEARED_FOR_RELEASE":
        errors.append("independent review is not cleared for release")
    if value.get("errors"):
        errors.append("adjudication contains unresolved errors")
    return errors, value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--case", type=Path, required=True)
    prep.add_argument("--artifact", type=Path, action="append", default=[])
    prep.add_argument("--output", type=Path, required=True)
    sub = commands.add_parser("submit")
    sub.add_argument("--packet", type=Path, required=True)
    sub.add_argument("--reviewer", required=True)
    sub.add_argument("--author-id", action="append", default=[])
    sub.add_argument("--assessment", choices=ASSESSMENTS, required=True)
    sub.add_argument("--reproduced", action="store_true")
    sub.add_argument("--fatal", action="append", default=[])
    sub.add_argument("--major", action="append", default=[])
    sub.add_argument("--minor", action="append", default=[])
    sub.add_argument("--report", type=Path)
    sub.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--review", type=Path, required=True)
    verify_packet_cmd = commands.add_parser("verify-packet")
    verify_packet_cmd.add_argument("--packet", type=Path, required=True)
    adj = commands.add_parser("adjudicate")
    adj.add_argument("--case", type=Path, required=True)
    adj.add_argument("--review", type=Path, action="append", default=[])
    adj.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            write(args.output, prepare(args.case, args.artifact, args.output.parent))
        elif args.command == "submit":
            write(
                args.output,
                submit(
                    args.packet,
                    args.reviewer,
                    args.assessment,
                    args.reproduced,
                    args.fatal,
                    args.major,
                    args.minor,
                    args.author_id,
                    args.output.parent,
                    args.report,
                ),
            )
        elif args.command == "adjudicate":
            result = adjudicate(args.case, args.review, args.output.parent)
            write(args.output, result)
            print(result["status"])
            return 0 if result["status"] == "CLEARED_FOR_RELEASE" else 1
        elif args.command == "verify":
            errors, _ = verify_review(args.review)
            for error in errors:
                print(f"ERROR: {error}")
            if errors:
                return 1
            print("VALID")
            return 0
        else:
            errors, _ = verify_packet(args.packet)
            for error in errors:
                print(f"ERROR: {error}")
            if errors:
                return 1
            print("VALID")
            return 0
        print(args.output)
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
