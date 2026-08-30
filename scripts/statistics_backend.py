#!/usr/bin/env python3
"""Dependence-aware inference, multiplicity control, and coverage stress tests."""

from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
from pathlib import Path
from typing import Any

from research_io import write_json as write

SCHEMA_VERSION = 1


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("sample is empty")
    return math.fsum(values) / len(values)


def iid_standard_error(values: list[float]) -> float:
    if len(values) < 2:
        raise ValueError("IID standard error requires at least two observations")
    return statistics.stdev(values) / math.sqrt(len(values))


def hac_standard_error(values: list[float], lags: int) -> float:
    """Newey-West standard error of the mean with Bartlett weights."""
    n = len(values)
    if n < 2 or lags < 0 or lags >= n:
        raise ValueError("HAC requires 0 <= lags < sample size and at least two observations")
    center = mean(values)
    residuals = [value - center for value in values]
    long_run = math.fsum(value * value for value in residuals) / n
    for lag in range(1, lags + 1):
        covariance = math.fsum(residuals[index] * residuals[index - lag] for index in range(lag, n)) / n
        long_run += 2.0 * (1.0 - lag / (lags + 1.0)) * covariance
    return math.sqrt(max(long_run, 0.0) / n)


def circular_block_bootstrap_ci(
    values: list[float],
    block_length: int,
    replications: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    n = len(values)
    if n < 2 or not 1 <= block_length <= n or replications < 100 or not 0 < alpha < 1:
        raise ValueError("invalid block bootstrap configuration")
    rng = random.Random(seed)
    estimates: list[float] = []
    blocks = math.ceil(n / block_length)
    for _ in range(replications):
        sample: list[float] = []
        for _ in range(blocks):
            start = rng.randrange(n)
            sample.extend(values[(start + offset) % n] for offset in range(block_length))
        estimates.append(mean(sample[:n]))
    estimates.sort()
    lower = estimates[max(0, math.floor((alpha / 2) * replications))]
    upper = estimates[min(replications - 1, math.ceil((1 - alpha / 2) * replications) - 1)]
    return lower, upper


def holm(p_values: list[float], alpha: float = 0.05) -> list[dict[str, Any]]:
    if not p_values or any(not 0 <= value <= 1 for value in p_values):
        raise ValueError("p-values must lie in [0,1]")
    m = len(p_values)
    ordered = sorted(enumerate(p_values), key=lambda item: (item[1], item[0]))
    adjusted_sorted: list[float] = []
    running = 0.0
    for rank, (_, value) in enumerate(ordered):
        running = max(running, (m - rank) * value)
        adjusted_sorted.append(min(1.0, running))
    reject_prefix = True
    result = [None] * m
    for rank, ((index, value), adjusted) in enumerate(zip(ordered, adjusted_sorted)):
        threshold = alpha / (m - rank)
        reject_prefix = reject_prefix and value <= threshold
        result[index] = {
            "p_value": value,
            "adjusted_p": adjusted,
            "reject": reject_prefix,
        }
    return result  # type: ignore[return-value]


def benjamini_hochberg(p_values: list[float], q: float = 0.05) -> list[dict[str, Any]]:
    if not p_values or any(not 0 <= value <= 1 for value in p_values) or not 0 < q < 1:
        raise ValueError("invalid BH configuration")
    m = len(p_values)
    ordered = sorted(enumerate(p_values), key=lambda item: (item[1], item[0]))
    adjusted = [0.0] * m
    running = 1.0
    for reverse_rank in range(m - 1, -1, -1):
        index, value = ordered[reverse_rank]
        rank = reverse_rank + 1
        running = min(running, value * m / rank)
        adjusted[index] = min(1.0, running)
    cutoff_rank = max(
        (rank for rank, (_, value) in enumerate(ordered, start=1) if value <= q * rank / m),
        default=0,
    )
    rejected = {index for index, _ in ordered[:cutoff_rank]}
    return [
        {"p_value": value, "adjusted_p": adjusted[index], "reject": index in rejected}
        for index, value in enumerate(p_values)
    ]


def analyze(values: list[float], hac_lags: int, block_length: int, replications: int, seed: int) -> dict[str, Any]:
    estimate = mean(values)
    iid_se = iid_standard_error(values)
    hac_se = hac_standard_error(values, hac_lags)
    block_ci = circular_block_bootstrap_ci(values, block_length, replications, seed)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "mean-inference",
        "estimand": "population mean under the declared sampling process",
        "sample_size": len(values),
        "mean": estimate,
        "methods": {
            "iid": {
                "standard_error": iid_se,
                "ci95": [estimate - 1.96 * iid_se, estimate + 1.96 * iid_se],
            },
            "newey_west": {
                "lags": hac_lags,
                "kernel": "Bartlett",
                "standard_error": hac_se,
                "ci95": [estimate - 1.96 * hac_se, estimate + 1.96 * hac_se],
            },
            "circular_block_bootstrap": {
                "block_length": block_length,
                "replications": replications,
                "seed": seed,
                "percentile_ci95": list(block_ci),
            },
        },
        "warning": "Intervals target a mean and are only valid under the corresponding dependence and stationarity assumptions.",
    }


def draw_innovation(rng: random.Random, distribution: str) -> float:
    if distribution == "gaussian":
        return rng.gauss(0.0, 1.0)
    if distribution == "student-t3":
        normal = rng.gauss(0.0, 1.0)
        chi_square = sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(3))
        return normal / math.sqrt(chi_square / 3) / math.sqrt(3)
    raise ValueError("unknown innovation distribution")


def coverage_simulation(
    n: int, phi: float, replications: int, hac_lags: int, distribution: str, seed: int
) -> dict[str, Any]:
    if n < 20 or replications < 100 or abs(phi) >= 1 or not 0 <= hac_lags < n:
        raise ValueError("invalid coverage simulation configuration")
    rng = random.Random(seed)
    covered_iid = 0
    covered_hac = 0
    widths_iid: list[float] = []
    widths_hac: list[float] = []
    for _ in range(replications):
        value = 0.0
        sample = []
        for _ in range(n + 100):
            value = phi * value + draw_innovation(rng, distribution)
            if len(sample) < n and _ >= 100:
                sample.append(value)
        estimate = mean(sample)
        iid_se = iid_standard_error(sample)
        hac_se = hac_standard_error(sample, hac_lags)
        covered_iid += abs(estimate) <= 1.96 * iid_se
        covered_hac += abs(estimate) <= 1.96 * hac_se
        widths_iid.append(2 * 1.96 * iid_se)
        widths_hac.append(2 * 1.96 * hac_se)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "coverage-simulation",
        "dgp": {
            "model": "stationary AR(1)",
            "phi": phi,
            "innovation": distribution,
            "true_mean": 0.0,
        },
        "sample_size": n,
        "replications": replications,
        "seed": seed,
        "methods": {
            "iid_normal": {
                "coverage": covered_iid / replications,
                "mean_width": mean(widths_iid),
            },
            "newey_west_normal": {
                "lags": hac_lags,
                "coverage": covered_hac / replications,
                "mean_width": mean(widths_hac),
            },
        },
        "target_coverage": 0.95,
        "monte_carlo_se_at_target": math.sqrt(0.95 * 0.05 / replications),
    }


def read_column(path: Path, column: str) -> list[float]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if column not in (reader.fieldnames or []):
            raise ValueError(f"column not found: {column}")
        values = []
        for row_number, row in enumerate(reader, start=2):
            text = str(row[column]).strip()
            if not text:
                continue
            try:
                values.append(float(text))
            except ValueError as exc:
                raise ValueError(f"non-numeric value at row {row_number}: {text}") from exc
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    analyze_cmd = commands.add_parser("mean")
    analyze_cmd.add_argument("--csv", type=Path, required=True)
    analyze_cmd.add_argument("--column", required=True)
    analyze_cmd.add_argument("--hac-lags", type=int, required=True)
    analyze_cmd.add_argument("--block-length", type=int, required=True)
    analyze_cmd.add_argument("--replications", type=int, default=10000)
    analyze_cmd.add_argument("--seed", type=int, required=True)
    analyze_cmd.add_argument("--output", type=Path, required=True)
    multi = commands.add_parser("multiplicity")
    multi.add_argument("--p", type=float, nargs="+", required=True)
    multi.add_argument("--method", choices=("holm", "bh"), required=True)
    multi.add_argument("--level", type=float, default=0.05)
    multi.add_argument("--output", type=Path, required=True)
    simulate = commands.add_parser("coverage")
    simulate.add_argument("--n", type=int, required=True)
    simulate.add_argument("--phi", type=float, required=True)
    simulate.add_argument("--replications", type=int, default=5000)
    simulate.add_argument("--hac-lags", type=int, required=True)
    simulate.add_argument("--innovation", choices=("gaussian", "student-t3"), required=True)
    simulate.add_argument("--seed", type=int, required=True)
    simulate.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "mean":
            result = analyze(
                read_column(args.csv, args.column),
                args.hac_lags,
                args.block_length,
                args.replications,
                args.seed,
            )
        elif args.command == "multiplicity":
            method = holm if args.method == "holm" else benjamini_hochberg
            result = {
                "schema_version": SCHEMA_VERSION,
                "kind": "multiplicity",
                "method": args.method,
                "level": args.level,
                "hypotheses": method(args.p, args.level),
            }
        else:
            result = coverage_simulation(
                args.n,
                args.phi,
                args.replications,
                args.hac_lags,
                args.innovation,
                args.seed,
            )
        write(args.output, result)
        print(args.output)
        return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
