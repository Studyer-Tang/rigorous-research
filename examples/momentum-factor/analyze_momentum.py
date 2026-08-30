#!/usr/bin/env python3
"""Reproduce a fixed-period inference audit for the monthly U.S. momentum factor."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import random
import re
import statistics
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip"
ROW = re.compile(r"^\s*(\d{6})\s*,\s*(-?\d+(?:\.\d+)?)")


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "rigorous-research/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def parse_archive(payload: bytes) -> tuple[str, list[tuple[int, float]]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV member, found {members}")
        member = members[0]
        text = archive.read(member).decode("utf-8-sig", errors="replace")
    rows = []
    for line in text.splitlines():
        match = ROW.match(line)
        if not match:
            continue
        date = int(match.group(1))
        percent = float(match.group(2))
        if percent <= -99:
            continue
        rows.append((date, percent / 100.0))
    if not rows:
        raise ValueError("no monthly rows parsed")
    return member, rows


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def hac_mean(values: list[float], lags: int) -> dict[str, float]:
    n = len(values)
    mean = statistics.fmean(values)
    centered = [value - mean for value in values]
    gamma0 = sum(value * value for value in centered) / n
    long_run_variance = gamma0
    for lag in range(1, lags + 1):
        covariance = sum(centered[index] * centered[index - lag] for index in range(lag, n)) / n
        weight = 1 - lag / (lags + 1)
        long_run_variance += 2 * weight * covariance
    standard_error = math.sqrt(max(long_run_variance, 0) / n)
    statistic = mean / standard_error if standard_error else math.inf
    p_value = math.erfc(abs(statistic) / math.sqrt(2)) if math.isfinite(statistic) else 0.0
    return {
        "mean": mean,
        "hac_lags": lags,
        "hac_standard_error": standard_error,
        "hac_t": statistic,
        "normal_two_sided_p": p_value,
        "normal_95_low": mean - 1.959963984540054 * standard_error,
        "normal_95_high": mean + 1.959963984540054 * standard_error,
    }


def circular_block_bootstrap(
    values: list[float], block_length: int, replications: int, seed: int
) -> dict[str, float | int]:
    rng = random.Random(seed)
    n = len(values)
    means = []
    blocks_needed = math.ceil(n / block_length)
    for _ in range(replications):
        sample = []
        for _ in range(blocks_needed):
            start = rng.randrange(n)
            sample.extend(values[(start + offset) % n] for offset in range(block_length))
        means.append(statistics.fmean(sample[:n]))
    return {
        "block_length": block_length,
        "replications": replications,
        "seed": seed,
        "mean_95_low": quantile(means, 0.025),
        "mean_95_high": quantile(means, 0.975),
        "fraction_nonpositive": sum(value <= 0 for value in means) / replications,
    }


def summarize(values: list[float]) -> dict[str, float | int]:
    mean = statistics.fmean(values)
    standard_deviation = statistics.stdev(values)
    return {
        "n": len(values),
        "mean_monthly": mean,
        "annualized_arithmetic_mean": 12 * mean,
        "monthly_standard_deviation": standard_deviation,
        "annualized_sharpe_zero_benchmark": math.sqrt(12) * mean / standard_deviation,
        "median_monthly": statistics.median(values),
        "positive_fraction": sum(value > 0 for value in values) / len(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def percent(value: float) -> str:
    return f"{100 * value:.3f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--start", type=int, default=199301)
    parser.add_argument("--end", type=int, default=202412)
    parser.add_argument("--hac-lags", type=int, default=6)
    parser.add_argument("--block-length", type=int, default=12)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    payload = download(args.url)
    member, all_rows = parse_archive(payload)
    rows = [(date, value) for date, value in all_rows if args.start <= date <= args.end]
    expected_months = (args.end // 100 - args.start // 100) * 12 + (args.end % 100 - args.start % 100) + 1
    if len(rows) != expected_months:
        raise ValueError(f"expected {expected_months} monthly rows, found {len(rows)}")
    dates = [date for date, _ in rows]
    values = [value for _, value in rows]

    full = summarize(values)
    hac = hac_mean(values, args.hac_lags)
    bootstrap = circular_block_bootstrap(values, args.block_length, args.bootstrap, args.seed)
    split_date = 200901
    early = [value for date, value in rows if date < split_date]
    late = [value for date, value in rows if date >= split_date]
    trim = max(1, math.floor(0.01 * len(values)))
    ordered = sorted(values)
    trimmed = ordered[trim:-trim]
    remove_extremes = ordered[5:-5]
    sensitivity = {
        "pre_2009": summarize(early),
        "2009_onward": summarize(late),
        "one_percent_symmetric_trim_mean": statistics.fmean(trimmed),
        "remove_five_best_and_worst_mean": statistics.fmean(remove_extremes),
        "leave_one_year_out_means": {},
    }
    years = sorted({date // 100 for date in dates})
    for year in years:
        retained = [value for date, value in rows if date // 100 != year]
        sensitivity["leave_one_year_out_means"][str(year)] = statistics.fmean(retained)

    supported = (
        full["mean_monthly"] > 0
        and hac["normal_95_low"] > 0
        and bootstrap["mean_95_low"] > 0
        and sensitivity["one_percent_symmetric_trim_mean"] > 0
        and min(sensitivity["leave_one_year_out_means"].values()) > 0
    )
    result = {
        "claim": "The 1993-01 to 2024-12 monthly momentum-factor mean is positive under the stated descriptive and weak-dependence scope.",
        "source": {
            "url": args.url,
            "download_sha256": hashlib.sha256(payload).hexdigest(),
            "archive_member": member,
            "download_bytes": len(payload),
            "available_first_month": all_rows[0][0],
            "available_last_month": all_rows[-1][0],
        },
        "fixed_design": {
            "start": args.start,
            "end": args.end,
            "observations": len(rows),
            "units": "decimal monthly return",
            "hac_lags": args.hac_lags,
            "bootstrap_block_length": args.block_length,
            "bootstrap_replications": args.bootstrap,
            "seed": args.seed,
        },
        "descriptive": full,
        "hac_inference": hac,
        "circular_block_bootstrap": bootstrap,
        "sensitivity": sensitivity,
        "analysis_completed": True,
        "release_condition_passed": supported,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )

    report = [
        "# Momentum factor replication",
        "",
        f"Fixed sample: {args.start}–{args.end}, {len(rows)} monthly observations.",
        "",
        f"- Arithmetic mean: {percent(full['mean_monthly'])} per month",
        f"- Newey–West HAC t-statistic ({args.hac_lags} lags): {hac['hac_t']:.3f}",
        f"- HAC 95% interval: [{percent(hac['normal_95_low'])}, {percent(hac['normal_95_high'])}]",
        f"- Circular block-bootstrap 95% interval: [{percent(bootstrap['mean_95_low'])}, {percent(bootstrap['mean_95_high'])}]",
        f"- 1993–2008 mean: {percent(sensitivity['pre_2009']['mean_monthly'])}",
        f"- 2009–2024 mean: {percent(sensitivity['2009_onward']['mean_monthly'])}",
        f"- 1% symmetrically trimmed mean: {percent(sensitivity['one_percent_symmetric_trim_mean'])}",
        f"- Every leave-one-year-out mean positive: {min(sensitivity['leave_one_year_out_means'].values()) > 0}",
        "",
        f"Release condition passed: **{supported}**.",
        "",
        "This is a fixed-period statistical fact about a published factor series. It is not evidence that the factor was directly tradable at zero cost, that the mean persists after 2024, or that the return is a causal premium.",
    ]
    args.report.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print(f"mean={full['mean_monthly']:.8f} hac_t={hac['hac_t']:.3f} supported={supported}")
    # A scientifically unsupported hypothesis is still a successfully completed analysis.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
