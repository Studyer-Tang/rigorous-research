"""Bounded autonomous control loop over the same operations used by Codex."""

import os
import time

from .core import run_worker


def api_model(provider, endpoint, model, api_key_env="RESEARCH_AI_API_KEY"):
    if not model.strip():
        raise ValueError("select a model before starting the API runner")
    if provider != "ollama" and not os.environ.get(api_key_env):
        raise ValueError(f"API key environment variable is empty: {api_key_env}")

    def propose(context, timeout):
        return run_worker(
            {
                "mode": "model",
                "context": context,
                "provider": provider,
                "endpoint": endpoint,
                "model": model,
                "api_key_env": api_key_env,
            },
            min(timeout, 120),
        )

    return propose


def run(study, propose, steps=12, seconds=600, tool_timeout=30, failure_limit=3):
    """Budgets apply per invocation; total attempted model calls stay in the study ledger."""
    if (
        type(steps) is not int
        or not 1 <= steps <= 1000
        or not 1 <= seconds <= 86400
        or not 0 < tool_timeout <= 120
        or not 1 <= failure_limit <= 10
    ):
        raise ValueError("invalid run budget")
    started = time.monotonic()
    reason = "STEP_BUDGET"
    failures = 0
    with study.controller():
        try:
            for _ in range(steps):
                context = study.context()
                if context["state"]["paused"]:
                    reason = "PAUSED"
                    break
                if context["state"]["execution"] in {"DELIVERED", "NEEDS_INPUT"}:
                    reason = context["state"]["execution"]
                    break
                remaining = seconds - (time.monotonic() - started)
                if remaining <= 0:
                    reason = "TIME_BUDGET"
                    break
                with study.connect() as db:
                    db.execute("BEGIN IMMEDIATE")
                    state = study.read_state(db)
                    state["model_calls"] += 1
                    study.write_state(db, state)
                try:
                    envelope = propose(context, remaining)
                    if not isinstance(envelope, dict) or "proposal" not in envelope:
                        raise ValueError("model did not return a proposal envelope")
                except Exception as exc:
                    # No automatic paid retry, and no arbitrary provider error text in the public record.
                    study.event(
                        "model_error", {"type": type(exc).__name__, "message": "Request failed; no automatic retry."}
                    )
                    reason = "MODEL_ERROR"
                    break
                study.event("model_response", {"provenance": envelope.get("provenance", {"provider": "host-callback"})})
                if study.state()["paused"]:
                    reason = "PAUSED"
                    break
                remaining = seconds - (time.monotonic() - started)
                if remaining <= 0:
                    reason = "TIME_BUDGET"
                    break
                try:
                    result = study._submit(
                        envelope["proposal"], context["state"]["revision"], min(tool_timeout, remaining)
                    )
                    failures = failures + 1 if result["execution"] != "SUCCEEDED" else 0
                    tool = result["proposal"]["action"]["tool"]
                    if tool in {"finish", "need_input"}:
                        reason = "DELIVERED" if tool == "finish" else "NEEDS_INPUT"
                        break
                except (ValueError, KeyError, TypeError) as exc:
                    study.event("proposal_rejected", {"error": str(exc)[:1000]})
                    failures += 1
                if failures >= failure_limit:
                    reason = "REPEATED_FAILURE"
                    break
        except KeyboardInterrupt:
            reason = "INTERRUPTED"
        finally:
            with study.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                state = study.read_state(db)
                state["stop_reason"] = reason
                study.write_state(db, state)
            study.event("run_stopped", {"reason": reason, "elapsed_seconds": round(time.monotonic() - started, 3)})
    return study.state()
