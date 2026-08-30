#!/usr/bin/env python3
"""Create immutable, replayable financial-data snapshots with point-in-time metadata."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from research_io import sha256, sha256_bytes, utc_timestamp as timestamp, write_json

SCHEMA_VERSION = 1
PROVIDERS = {
    "kenneth-french-mom-monthly": {
        "provider": "Kenneth French Data Library",
        "dataset": "F-F Momentum Factor monthly archive",
        "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip",
        "revision_policy": "latest archive; historical values may be revised by provider",
        "license": "provider terms apply",
        "format": "zip/csv",
    },
    "fred-csv": {
        "provider": "Federal Reserve Bank of St. Louis (FRED)",
        "dataset": "FRED series CSV",
        "revision_policy": "latest revised observations; not point-in-time ALFRED vintage",
        "license": "FRED terms apply",
        "format": "csv",
    },
}


def safe_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "-" for character in value).strip("-")


def provider_request(adapter: str, series: str) -> dict[str, str]:
    if adapter not in PROVIDERS:
        raise ValueError(f"unknown adapter: {adapter}")
    result = dict(PROVIDERS[adapter])
    if adapter == "fred-csv":
        if not series or not series.replace("_", "").isalnum():
            raise ValueError("FRED adapter requires an alphanumeric --series")
        result["dataset"] = f"FRED {series}"
        result["url"] = "https://fred.stlouisfed.org/graph/fredgraph.csv?" + urllib.parse.urlencode({"id": series})
    return result


def create_snapshot(
    raw: bytes,
    root: Path,
    *,
    provider: str,
    dataset: str,
    url: str,
    query: dict[str, str],
    as_of: str,
    revision_policy: str,
    schema: str,
    units: str,
    timezone: str,
    calendar: str,
    identifier_system: str,
    adjustment_policy: str,
    license_text: str,
    extension: str,
    retrieved_at: str | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    if not raw:
        raise ValueError("refusing to snapshot an empty response")
    retrieved_at = retrieved_at or timestamp()
    digest = sha256_bytes(raw)
    folder = root.resolve() / safe_name(provider) / safe_name(dataset) / f"{safe_name(as_of)}-{digest[:12]}"
    folder.mkdir(parents=True, exist_ok=False)
    raw_path = folder / f"raw.{extension.lstrip('.') or 'bin'}"
    raw_path.write_bytes(raw)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "kind": "financial-data-snapshot",
        "provider": provider,
        "dataset": dataset,
        "request": {"url": url, "query": query},
        "retrieved_at": retrieved_at,
        "as_of": as_of,
        "revision_policy": revision_policy,
        "raw_file": raw_path.name,
        "raw_sha256": digest,
        "raw_bytes": len(raw),
        "schema": schema,
        "units": units,
        "timezone": timezone,
        "calendar": calendar,
        "identifier_system": identifier_system,
        "adjustment_policy": adjustment_policy,
        "license": license_text,
    }
    manifest_path = folder / "manifest.json"
    write_json(manifest_path, manifest)
    return raw_path, manifest_path, manifest


def verify(manifest_path: Path) -> tuple[list[str], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if manifest.get("kind") != "financial-data-snapshot" or manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported snapshot manifest")
        return errors, manifest
    required = (
        "provider",
        "dataset",
        "request",
        "retrieved_at",
        "as_of",
        "revision_policy",
        "raw_file",
        "raw_sha256",
        "schema",
        "units",
        "timezone",
        "calendar",
        "identifier_system",
        "adjustment_policy",
        "license",
    )
    for field in required:
        if manifest.get(field) in (None, ""):
            errors.append(f"manifest field is blank: {field}")
    raw_path = manifest_path.parent / str(manifest.get("raw_file", ""))
    if not raw_path.is_file():
        errors.append("raw snapshot is missing")
    elif sha256(raw_path) != manifest.get("raw_sha256"):
        errors.append("raw snapshot checksum mismatch")
    return errors, manifest


def compare(old_path: Path, new_path: Path) -> dict[str, Any]:
    old_errors, old = verify(old_path)
    new_errors, new = verify(new_path)
    if old_errors or new_errors:
        raise ValueError("cannot compare invalid snapshots: " + "; ".join(old_errors + new_errors))
    metadata_fields = (
        "as_of",
        "revision_policy",
        "schema",
        "units",
        "adjustment_policy",
    )
    return {
        "kind": "snapshot-diff",
        "old_manifest": str(old_path.resolve()),
        "new_manifest": str(new_path.resolve()),
        "raw_changed": old["raw_sha256"] != new["raw_sha256"],
        "old_raw_sha256": old["raw_sha256"],
        "new_raw_sha256": new["raw_sha256"],
        "metadata_changes": {
            field: {"old": old.get(field), "new": new.get(field)}
            for field in metadata_fields
            if old.get(field) != new.get(field)
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch")
    fetch.add_argument("--adapter", choices=tuple(PROVIDERS), required=True)
    fetch.add_argument("--series", default="")
    fetch.add_argument("--root", type=Path, required=True)
    fetch.add_argument("--as-of", required=True)
    fetch.add_argument("--schema", required=True)
    fetch.add_argument("--units", required=True)
    fetch.add_argument("--timezone", required=True)
    fetch.add_argument("--calendar", required=True)
    fetch.add_argument("--identifier-system", required=True)
    fetch.add_argument("--adjustment-policy", required=True)
    fetch.add_argument("--timeout", type=int, default=60)
    verify_cmd = commands.add_parser("verify")
    verify_cmd.add_argument("--manifest", type=Path, required=True)
    diff = commands.add_parser("diff")
    diff.add_argument("--old", type=Path, required=True)
    diff.add_argument("--new", type=Path, required=True)
    diff.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "fetch":
            request = provider_request(args.adapter, args.series)
            http_request = urllib.request.Request(request["url"], headers={"User-Agent": "rigorous-research/1.0"})
            with urllib.request.urlopen(http_request, timeout=args.timeout) as response:
                raw = response.read()
            query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(request["url"]).query))
            extension = "zip" if request["format"].startswith("zip") else "csv"
            _, manifest, _ = create_snapshot(
                raw,
                args.root,
                provider=request["provider"],
                dataset=request["dataset"],
                url=request["url"],
                query=query,
                as_of=args.as_of,
                revision_policy=request["revision_policy"],
                schema=args.schema,
                units=args.units,
                timezone=args.timezone,
                calendar=args.calendar,
                identifier_system=args.identifier_system,
                adjustment_policy=args.adjustment_policy,
                license_text=request["license"],
                extension=extension,
            )
            print(manifest)
            return 0
        if args.command == "verify":
            errors, _ = verify(args.manifest)
            for error in errors:
                print(f"ERROR: {error}")
            if errors:
                return 1
            print("VALID")
            return 0
        result = compare(args.old, args.new)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8", newline="\n")
            print(args.output)
        else:
            print(rendered, end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
