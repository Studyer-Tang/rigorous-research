#!/usr/bin/env python3
"""Run deterministic release-gate benchmarks, including adversarial mutations."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import inference_case as ic
import research_workspace as rw
from research_io import write_json


def set_pointer(document: Any, pointer: str, value: Any) -> None:
    if not pointer.startswith("/"):
        raise ValueError("mutation pointer must start with '/'")
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]
    target = document
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    final = parts[-1]
    if isinstance(target, list):
        target[int(final)] = value
    else:
        target[final] = value


def validate_artifact(kind: str, path: Path) -> list[str]:
    if kind == "case":
        data = json.loads(path.read_text(encoding="utf-8"))
        errors, _ = ic.validate_case(data, path, release=True)
        return errors
    if kind == "workspace":
        _, data = rw.load(path)
        errors, _ = rw.validate_workspace(data, path, release=True)
        return errors
    raise ValueError(f"unsupported validator: {kind}")


def run_case(root: Path, specification: dict[str, Any]) -> dict[str, Any]:
    source = (root / specification["source"]).resolve()
    try:
        source.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"benchmark source escapes repository: {source}") from exc
    if not source.is_file():
        raise ValueError(f"benchmark source does not exist: {source}")
    with tempfile.TemporaryDirectory() as directory:
        copied_root = Path(directory) / source.parent.name
        shutil.copytree(source.parent, copied_root)
        copied = copied_root / source.name
        mutation = specification.get("mutation")
        if mutation:
            data = json.loads(copied.read_text(encoding="utf-8"))
            set_pointer(data, mutation["pointer"], mutation.get("value"))
            write_json(copied, data)
        errors = validate_artifact(specification["validator"], copied)
    observed_valid = not errors
    expected_valid = bool(specification["expect_valid"])
    return {
        "id": specification["id"],
        "expected_valid": expected_valid,
        "observed_valid": observed_valid,
        "passed": expected_valid == observed_valid,
        "errors": errors,
        "mutation": mutation or None,
    }


def run_benchmark(root: Path, manifest: Path) -> dict[str, Any]:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    results = [run_case(root, case) for case in data.get("cases", [])]
    return {
        "schema_version": 1,
        "benchmark": data.get("name", manifest.stem),
        "total": len(results),
        "passed": sum(result["passed"] for result in results),
        "failed": sum(not result["passed"] for result in results),
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    checkout = Path.cwd()
    module_root = Path(__file__).resolve().parents[1]
    default_root = checkout if (checkout / "evals" / "benchmark.json").is_file() else module_root
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--manifest", type=Path, default=default_root / "evals" / "benchmark.json")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_benchmark(args.root.resolve(), args.manifest.resolve())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    if args.output:
        write_json(args.output, result)
    for item in result["results"]:
        status = "PASS" if item["passed"] else "FAIL"
        print(f"{status} {item['id']} expected={item['expected_valid']} observed={item['observed_valid']}")
    print(f"benchmark={result['benchmark']} passed={result['passed']}/{result['total']}")
    return 0 if not result["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
