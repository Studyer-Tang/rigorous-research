"""Offline controller replay with real tool execution, not a model-capability benchmark."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from research_agent.core import Study
from research_agent.runner import run


def proposal(tool, arguments, rationale, falsifier, evidence=None):
    return {"proposal": {"action": {"tool": tool, "arguments": arguments}, "rationale": rationale,
                         "falsifier": falsifier, "evidence": evidence or []},
            "provenance": {"provider": "synthetic-controller-replay", "model": "none"}}


def mathematics(context, timeout):
    history = context["recent_actions"]
    if not history:
        return proposal("counterexample", {"lhs": "(x+1)**2", "rhs": "x**2+1", "symbols": ["x"], "values": ["0", "1"]},
                        "Test the candidate expansion before accepting it.", "One admissible unequal value rejects the candidate.")
    if len(history) == 1:
        if history[-1]["result"]["status"] != "REFUTED":
            raise ValueError("expected the deliberately false candidate to be refuted")
        return proposal("identity", {"lhs": "(x+1)**2", "rhs": "x**2+2*x+1", "symbols": ["x"]},
                        "Restore the cross term omitted by the refuted candidate.", "The exact difference must vanish.", [1])
    if history[-1]["result"]["status"] != "ESTABLISHED":
        raise ValueError("corrected expansion was not independently established")
    return proposal("finish", {"text": "The candidate without 2x is false at x=1. The corrected polynomial identity is independently checked. This is an elementary known identity, with no novelty claim. Review the translation before closing the original case."},
                    "Report the refutation and the verified correction with their exact scope.",
                    "A missing domain or incorrect translation prevents original-objective acceptance.", [1, 2])


def statistics(context, timeout):
    history = context["recent_actions"]
    if len(history) < 2:
        if history and history[-1]["execution"] != "FAILED":
            raise ValueError("expected the deliberately invalid HAC lag to fail")
        return proposal("coverage", {"n": 60, "phi": 0.8, "replications": 500, "hac_lags": 60 if not history else 5,
                                     "distribution": "gaussian", "seed": 2026},
                        "Compare IID and HAC interval coverage in the declared AR(1) simulation.",
                        "Reject invalid lag settings; estimated undercoverage challenges this simulation design's calibration.")
    result = history[-1]["result"]
    if result["status"] != "DIAGNOSTIC":
        raise ValueError("simulation must remain diagnostic")
    return proposal("finish", {"text": "The first computation failed because HAC lags must be smaller than sample size. The corrected seeded experiment records IID and HAC coverage under one AR(1) DGP. It is exploratory and does not prove uniform coverage, validate real-world stationarity, or establish a new statistical theorem. Inspect the result for numerical estimates."},
                    "Preserve the failed setup and report the bounded experiment.",
                    "A simulation at one parameter point cannot establish a universal coverage claim.", [2])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = {"tool": "identity", "arguments": {"lhs": "(x+1)**2", "rhs": "x**2+2*x+1", "symbols": ["x"]}, "status": "ESTABLISHED"}
    summary = {"kind": "offline-agent-replay", "model_used": False, "novel_research_claimed": False, "studies": {}}
    for slug, domain, objective, callback in [
        ("expansion", "mathematics", "Derive and verify the expansion of (x+1)^2.", mathematics),
        ("coverage", "statistics", "Assess IID and HAC mean-interval coverage under the declared dependent-data simulation.", statistics),
    ]:
        study = Study.create(args.output, slug, objective, domain, contract if slug == "expansion" else None)
        state = run(study, callback, steps=5)
        if state["stop_reason"] != "DELIVERED":
            raise ValueError(f"replay did not deliver: {state}")
        (study.directory / "agent-export.json").write_text(json.dumps(study.export(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary["studies"][slug] = state
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
