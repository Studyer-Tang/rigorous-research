#!/usr/bin/env python3
"""Audit recorded statistical theorem conditions without inferring them from simulations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_io import load_json_object, resolve_locator, sha256, write_json

# These are explicit contracts, not automatic tests of a data-generating process.
METHODS = {
    "student-t-mean": (
        "finite-sample",
        (
            "iid_sampling",
            "normal_population",
            "positive_variance",
            "fixed_sample_size",
            "no_outcome_selection",
            "student_t_implementation",
        ),
    ),
    "iid-mean-clt": (
        "asymptotic",
        ("iid_sampling", "finite_positive_variance", "no_outcome_selection", "clt_implementation"),
    ),
    "newey-west-mean": (
        "asymptotic",
        (
            "stationarity",
            "clt_conditions",
            "moment_conditions",
            "bandwidth_sequence",
            "no_outcome_selection",
            "hac_implementation",
        ),
    ),
    "holm": ("finite-sample", ("valid_marginal_p_values", "prespecified_family", "holm_implementation")),
    "bh": (
        "finite-sample",
        ("valid_marginal_p_values", "prespecified_family", "independence_or_prds", "bh_implementation"),
    ),
}


def template(method: str, claim_id: str) -> dict[str, Any]:
    guarantee, conditions = METHODS[method]
    return {
        "schema_version": 1,
        "method": method,
        "claim_id": claim_id,
        "target": "",
        "guarantee": guarantee,
        "conditions": {
            key: {"status": "UNTESTED", "basis": "", "statement": "", "evidence_file": "", "evidence_sha256": ""}
            for key in conditions
        },
    }


def audit(specification: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    errors, unresolved, violated = [], [], []
    method = specification.get("method")
    if not isinstance(method, str) or method not in METHODS or specification.get("schema_version") != 1:
        raise ValueError("unsupported statistical contract")
    guarantee, required = METHODS[method]
    if specification.get("guarantee") != guarantee:
        errors.append(f"{method} cannot supply the requested guarantee; its contract is {guarantee}")
    if not isinstance(specification.get("target"), str) or not specification["target"].strip():
        unresolved.append("estimand or testing target")
    conditions = specification.get("conditions")
    if not isinstance(conditions, dict) or set(conditions) - set(required):
        raise ValueError("conditions must use the selected method's requirement names")
    for key in required:
        condition = conditions.get(key, {})
        if not isinstance(condition, dict):
            raise ValueError(f"{key}: condition must be an object")
        status = condition.get("status", "UNTESTED")
        if status not in ("UNTESTED", "JUSTIFIED", "CONDITIONAL", "VIOLATED"):
            raise ValueError(f"{key}: invalid condition status")
        if status == "VIOLATED":
            violated.append(key)
        elif status != "JUSTIFIED":
            unresolved.append(key)
        else:
            if condition.get("basis") not in ("theorem", "design", "implementation", "derivation"):
                errors.append(f"{key}: simulation or diagnostic evidence cannot discharge a theorem condition")
            if not isinstance(condition.get("statement"), str) or not condition["statement"].strip():
                unresolved.append(key)
            path = resolve_locator(str(condition.get("evidence_file", "")), base_dir)
            if not path.is_file() or sha256(path) != condition.get("evidence_sha256"):
                errors.append(f"{key}: condition evidence is missing or changed")
    applicable = not errors and not unresolved and not violated
    return {
        "schema_version": 1,
        "kind": "statistical-applicability-audit",
        "method": method,
        "guarantee": guarantee,
        "applicable": applicable,
        "status": "APPLICABLE_UNDER_RECORDED_CONDITIONS"
        if applicable
        else "INAPPLICABLE"
        if errors or violated
        else "CONDITIONAL",
        "errors": errors,
        "unresolved_conditions": unresolved,
        "violated_conditions": violated,
        "falsification_tasks": [
            f"Check {key} against the design and theorem; construct a violating DGP or implementation counterexample."
            for key in unresolved + violated
        ],
        "warning": "Evidence bindings do not prove prose assumptions true. Review the theorem/design argument. Failed applicability is not evidence for an opposite parameter or causal effect; simulations do not prove universal coverage.",
    }


def audit_case(case: dict[str, Any], case_dir: Path) -> dict[str, Any]:
    """Resolve a case binding once for validation, reports, and model context."""
    try:
        binding = case.get("statistical_contract", {})
        path = resolve_locator(binding.get("locator", ""), case_dir)
        if not path.is_file() or sha256(path) != binding.get("sha256"):
            raise ValueError("SUPPORTED statistical/finance case requires a checksum-bound statistical contract")
        contract = load_json_object(path)
        if contract.get("claim_id") != case["decision"]["claim_id"]:
            raise ValueError("statistical contract targets a different claim")
        return audit(contract, path.parent)
    except (ValueError, OSError, TypeError, AttributeError, KeyError) as exc:
        return {
            "status": "INVALID",
            "applicable": False,
            "errors": [str(exc)],
            "unresolved_conditions": [],
            "violated_conditions": [],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--method", choices=METHODS, required=True)
    init.add_argument("--claim", default="C001")
    init.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("audit")
    check.add_argument("contract", type=Path)
    check.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            write_json(args.output, template(args.method, args.claim))
            return 0
        result = audit(load_json_object(args.contract), args.contract.resolve().parent)
        if args.output:
            write_json(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["applicable"] else 1
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
