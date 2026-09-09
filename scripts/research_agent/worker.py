"""Typed tool worker. No model-generated executable code or commands are accepted."""

import json
import sys
import tempfile
from pathlib import Path

from .schema import TOOLS, validate


def produce(action, asset=None):
    tool, args = action["tool"], action["arguments"]
    validate(args, TOOLS[tool])
    if tool in {"polynomial_sos", "polynomial_amgm", "inequality_search"}:
        from polynomial_research import inequality_search, polynomial_amgm, polynomial_sos

        return {
            "certificate": {
                "polynomial_sos": polynomial_sos,
                "polynomial_amgm": polynomial_amgm,
                "inequality_search": inequality_search,
            }[tool](**args)
        }
    if tool == "egyptian":
        from egyptian_fractions import search

        return {"certificate": search(**args)}
    if tool in {"egyptian_window", "egyptian_family", "egyptian_scan"}:
        from integer_research import family, scan, window

        return {
            "certificate": {"egyptian_window": window, "egyptian_family": family, "egyptian_scan": scan}[tool](**args)
        }
    if tool in {"identity", "counterexample", "bound"}:
        import math_backend as math

        if tool == "identity":
            return {"certificate": math.identity_certificate(args["lhs"], args["rhs"], args["symbols"])}
        if tool == "counterexample":
            return {
                "certificate": math.counterexample_search(args["lhs"], args["rhs"], args["symbols"], args["values"])
            }
        return {
            "certificate": math.polynomial_bound_certificate(
                args["lhs"], args["rhs"], args["symbol"], args["lower"], args["upper"], 6
            )
        }
    if tool == "literature":
        import literature_search

        with tempfile.TemporaryDirectory(prefix="research-literature-") as directory:
            root = Path(directory)
            literature_search.main(
                [
                    "--query",
                    args["query"],
                    "--provider",
                    args["provider"],
                    "--limit",
                    str(args["limit"]),
                    "--output",
                    str(root / "sources.json"),
                    "--markdown",
                    str(root / "sources.md"),
                    "--bibtex",
                    str(root / "sources.bib"),
                ]
            )
            return {
                "status": "CANDIDATE_SOURCES",
                "sources": json.loads((root / "sources.json").read_text(encoding="utf-8")),
            }
    import statistics_backend as stats

    if tool == "coverage":
        result = stats.coverage_simulation(**args)
    elif tool == "mean":
        result = stats.analyze(asset, **{k: v for k, v in args.items() if k != "asset"})
    else:
        result = (
            stats.holm(asset, args["level"])
            if args["method"] == "holm"
            else stats.benjamini_hochberg(asset, args["level"])
        )
    return {
        "status": "DIAGNOSTIC",
        "result": result,
        "assumptions_verified": False,
        "warning": "Calculations do not prove applicability, causal identification, or population claims.",
    }


def main():
    # Redirect backend chatter; stdout is exclusively the machine-readable result.
    import contextlib

    request = json.load(sys.stdin)
    with contextlib.redirect_stdout(sys.stderr):
        if request["mode"] == "model":
            from research_copilot import request_structured

            from .schema import INSTRUCTIONS, PROPOSAL

            result = request_structured(
                request["context"],
                PROPOSAL,
                INSTRUCTIONS,
                request["provider"],
                request["endpoint"],
                request["model"],
                request["api_key_env"],
            )
        elif request["mode"] == "check":
            from certificate_verifier import verify

            result = verify(request["certificate"])
        else:
            result = produce(request["action"], request.get("asset"))
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
