#!/usr/bin/env python3
"""Unified command-line entry point for the Rigorous Research toolkit."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Command:
    module: str
    summary: str


COMMANDS = {
    "case": Command("inference_case", "create and validate a focused inference case"),
    "data": Command("finance_data", "freeze and verify public financial-data vintages"),
    "eval": Command("research_eval", "run release-gate benchmark and mutation cases"),
    "literature": Command("literature_search", "search and deduplicate scholarly metadata"),
    "math": Command("math_backend", "run exact SymPy or optional Lean checks"),
    "quality": Command("skill_quality", "validate the portable skill package"),
    "review": Command("review_protocol", "prepare and verify blinded review packets"),
    "seal": Command("research_seal", "seal plans and verify computation receipts"),
    "statistics": Command("statistics_backend", "run dependence-aware statistical checks"),
    "workspace": Command("research_workspace", "manage a multi-step research workspace"),
}


def render_help() -> str:
    width = max(len(name) for name in COMMANDS)
    lines = [
        "usage: rigorous-research <command> [arguments]",
        "",
        "Evidence-gated research tools for mathematics, statistics, and quantitative finance.",
        "",
        "commands:",
    ]
    lines.extend(f"  {name:<{width}}  {command.summary}" for name, command in COMMANDS.items())
    lines.extend(
        [
            "",
            "Run 'rigorous-research <command> --help' for command-specific options.",
        ]
    )
    return "\n".join(lines)


def load_main(module_name: str) -> Callable[[list[str] | None], int]:
    module = importlib.import_module(module_name)
    entry = getattr(module, "main", None)
    if not callable(entry):
        raise RuntimeError(f"{module_name} does not expose a callable main()")
    return entry


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help", "help"}:
        print(render_help())
        return 0
    name, *forwarded = arguments
    command = COMMANDS.get(name)
    if command is None:
        print(f"ERROR: unknown command '{name}'\n", file=sys.stderr)
        print(render_help(), file=sys.stderr)
        return 2
    try:
        return int(load_main(command.module)(forwarded))
    except (ImportError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
