#!/usr/bin/env python3
"""Reproduce a bounded investigation, explicitly leaving the open conjecture unresolved."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import certificate_verifier as cv
import egyptian_fractions as ef
import math_backend as mb
from research_io import sha256, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output
    finite = ef.search(4, 3, 10000, True)
    checked = cv.verify(finite)
    write_json(root / "finite-search.json", finite)
    write_json(root / "independent-check.json", checked)
    write_json(root / "budget-limited.json", ef.search(4, 3, 100, True, max_work=1))
    obstruction = {
        "schema_version": 1,
        "backend": "exact-integer",
        "backend_version": "1",
        "operation": "two-unit-fractions-obstruction",
        "claim": {"numerator": 4, "denominator": 49, "first_denominator": 13},
        "denominator_factorization": [{"prime": 7, "exponent": 2}, {"prime": 13, "exponent": 1}],
        "recommended_evidence_role": "decisive",
    }
    write_json(root / "greedy-obstruction.json", obstruction)
    obstruction_check = cv.verify(obstruction)
    write_json(root / "greedy-obstruction-check.json", obstruction_check)
    # Positive integer t. Integrality, ordering and coverage are explained in REPORT.md;
    # these symbolic checks establish the displayed equalities only.
    families = [
        ("even n >= 4", "2*t+2", ("t+1", "t+2", "(t+1)*(t+2)")),
        ("n = 3 mod 4", "4*t-1", ("t", "(4*t-1)*t+1", "(4*t-1)*t*((4*t-1)*t+1)")),
        ("n = 2 mod 3, n >= 5", "3*t+2", ("t+1", "3*t+2", "(t+1)*(3*t+2)")),
        ("n = 5 mod 8", "8*t-3", ("2*t", "(8*t-3)*t", "2*(8*t-3)*t")),
    ]
    family_records = []
    for name, n, denominators in families:
        certificate = mb.identity_certificate(
            f"4/({n})", "+".join(f"1/({value})" for value in denominators), ["t"], integer={"t"}, positive={"t"}
        )
        family_records.append({"family": name, "certificate": certificate, "independent_check": cv.verify(certificate)})
    write_json(root / "residue-families.json", {"families": family_records})
    greedy_failures = [n for n in range(3, 50) if ef.completion(4, n, n // 4 + 1, True, ef.Budget(100000)) is None]
    summary = {
        "main_conjecture": "INCONCLUSIVE",
        "novelty": "NOT_CLAIMED",
        "finite_domain": [3, 10000],
        "verified_witnesses": len(finite["witnesses"]),
        "unresolved_inputs": finite["unresolved"],
        "strategies": finite["strategies"],
        "budget": finite["budget"],
        "greedy_failures_in_3_to_49": greedy_failures,
        "n49_witness": next(row for row in finite["witnesses"] if row["n"] == 49),
        "remaining_prime_residue_mod_24": [1],
        "remaining_obligations": ["cover all remaining primes, not just a finite sample", "human review of prose translations and domain arguments", "no novelty established by this investigation"],
        "artifacts": {path.name: sha256(path) for path in sorted(root.glob("*.json")) if path.name != "summary.json"},
        "reproducer_sha256": sha256(Path(__file__)),
    }
    write_json(root / "summary.json", summary)
    checks = [checked, obstruction_check, *(row["independent_check"] for row in family_records)]
    if any(check["status"] != "ESTABLISHED" for check in checks) or greedy_failures != [49]:
        return 1
    print("finite_witnesses=9998 greedy_route_refuted_at=49 original_conjecture=INCONCLUSIVE novelty=NOT_CLAIMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
