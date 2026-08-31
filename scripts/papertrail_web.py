#!/usr/bin/env python3
"""Build the private-by-default, browser-only PaperTrail playground."""

from __future__ import annotations

import argparse
import json
from importlib.resources import files
from pathlib import Path

from papertrail_audit import build_audit, render_html
from research_io import atomic_write_json

FRONTEND = files("papertrail_frontend")
FRONTEND_ASSETS = (
    "app.css",
    "i18n.js",
    "integrity-network.js",
    "governed-review.js",
    "human-review.js",
    "app.js",
)


def _frontend_text(name: str) -> str:
    return FRONTEND.joinpath(name).read_text(encoding="utf-8")


def render_app_html(demo_report: str, demo_manifest: str) -> str:
    payload = json.dumps(
        {"report": demo_report, "manifest": demo_manifest},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    css = _frontend_text("app.css").replace("</", "<\\/")
    return _frontend_text("index.html").replace("__DEMO_DATA__", payload).replace("__APP_CSS__", css)


def build_site(output_dir: Path, demo_report: Path, demo_manifest: Path) -> None:
    report_text = demo_report.read_text(encoding="utf-8")
    manifest_text = demo_manifest.read_text(encoding="utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(render_app_html(report_text, manifest_text), encoding="utf-8", newline="\n")
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")

    asset_dir = output_dir / "assets"
    asset_dir.mkdir(exist_ok=True)
    for name in FRONTEND_ASSETS:
        (asset_dir / name).write_text(_frontend_text(name), encoding="utf-8", newline="\n")

    demo_dir = output_dir / "demo"
    demo_dir.mkdir(exist_ok=True)
    audit = build_audit(demo_report.resolve(), demo_manifest.resolve())
    atomic_write_json(demo_dir / "audit.json", audit)
    (demo_dir / "index.html").write_text(render_html(audit), encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("papertrail-site"))
    parser.add_argument("--demo-report", required=True, type=Path)
    parser.add_argument("--demo-manifest", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        build_site(args.output_dir, args.demo_report, args.demo_manifest)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"site={args.output_dir / 'index.html'}")
    print(f"demo={args.output_dir / 'demo' / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
