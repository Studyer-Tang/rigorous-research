#!/usr/bin/env python3
"""Small, dependency-free I/O primitives shared by the research tools."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any


class JsonObjectError(ValueError):
    """Raised when a JSON document does not have an object at its root."""


def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise JsonObjectError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Replace a JSON file atomically so an interrupted update cannot truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    except Exception:
        with suppress(OSError):
            os.unlink(temp_name)
        raise


def portable_locator(path: Path, base_dir: Path | None = None) -> str:
    resolved = path.resolve()
    if base_dir is None:
        return str(resolved)
    return os.path.relpath(resolved, base_dir.resolve()).replace("\\", "/")


def contained_locator(path: Path, base_dir: Path) -> str:
    """Use a relative locator inside a workspace and an absolute one outside it."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def resolve_locator(value: str, base_dir: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path
