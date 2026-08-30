#!/usr/bin/env python3
"""Run the preregistered dependence and heavy-tail coverage grid."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import statistics_backend as stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replications", type=int, default=5000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cells = []
    seed = 20260830
    for innovation in ("gaussian", "student-t3"):
        for phi in (0.0, 0.4, 0.8):
            cells.append(stats.coverage_simulation(120, phi, args.replications, 8, innovation, seed))
            seed += 1
    result = {
        "schema_version": 1,
        "experiment": "AR(1) mean-interval coverage grid",
        "preregistered_cells": 6,
        "cells": cells,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
