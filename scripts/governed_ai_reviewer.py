#!/usr/bin/env python3
"""Create governed AI review drafts that require explicit human confirmation."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from papertrail_audit import parse_markdown_report
from papertrail_import import candidate_claims
from research_io import load_json_object, sha256, utc_timestamp, write_json

SCHEMA_VERSION = 1
PROVIDERS = ("heuristic", "ollama", "openai-compatible")
FORMAL_VERDICTS = {"SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED", "UNVERIFIABLE"}
DECISIVE_VERDICTS = FORMAL_VERDICTS - {"UNVERIFIABLE"}
TOKEN = re.compile(r"[\w\u3400-\u9fff]+", re.UNICODE)
NEGATION = re.compile(
    r"\b(?:no|not|never|without|failed|declin\w*|reduc\w*|diminish\w*|degrad\w*|worse|harm\w*|distrust\w*)\b"
    r"|不|未|无|没有|下降|减少|降低|恶化|反驳",
    re.IGNORECASE,
)
UNIVERSAL = re.compile(
    r"\b(?:all|always|every|everyone|entirely|guarantees?|proves?|never)\b|所有|全部|总是|必然|证明|绝不",
    re.IGNORECASE,
)
CAUSAL = re.compile(r"\b(?:causes?|leads? to|results? in|drives?)\b|导致|造成|使得", re.IGNORECASE)
QUALIFIED = re.compile(
    r"\b(?:may|might|suggests?|associated|sample|respondents?|observed|correlat)\b|可能|或许|表明|样本|受访者|观察到|相关",
    re.IGNORECASE,
)


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in TOKEN.findall(value) if len(token) > 1}


def _source_text(source: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    source_id = str(source.get("id") or "")
    quotes = [str(item.get("quote") or "") for item in evidence if item.get("source_id") == source_id]
    return " ".join(
        [
            str(source.get("title") or ""),
            str(source.get("abstract") or ""),
            str(source.get("version_notes") or ""),
            *quotes,
        ]
    )


def _source_passages(source: dict[str, Any], evidence: list[dict[str, Any]]) -> list[tuple[str, str]]:
    source_id = str(source.get("id") or "")
    passages: list[tuple[str, str]] = []
    for field in ("title", "abstract", "version_notes"):
        text = str(source.get(field) or "").strip()
        passages.extend((field, part.strip()) for part in re.split(r"(?<=[.!?。！？])\s+", text) if part.strip())
    passages.extend(
        ("evidence_quote", str(item.get("quote") or "").strip())
        for item in evidence
        if item.get("source_id") == source_id and str(item.get("quote") or "").strip()
    )
    return passages


def recommend_evidence(
    statement: str, sources: list[dict[str, Any]], evidence: list[dict[str, Any]], limit: int = 5
) -> list[dict[str, Any]]:
    claim_tokens = _tokens(statement)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for source in sources:
        source_id = str(source.get("id") or "").strip()
        if not source_id:
            continue
        passages = _source_passages(source, evidence)
        if not passages:
            continue
        matched_field, matched_text = max(
            passages,
            key=lambda passage: (len(claim_tokens & _tokens(passage[1])), len(_tokens(passage[1]))),
        )
        overlap = len(claim_tokens & _tokens(matched_text)) / max(1, len(claim_tokens))
        if not overlap:
            continue
        opposite_polarity = bool(NEGATION.search(statement)) != bool(NEGATION.search(matched_text))
        ranked.append(
            (
                overlap,
                {
                    "source_id": source_id,
                    "relation": "potential_contradiction" if opposite_polarity else "potential_support",
                    "score": round(overlap, 4),
                    "reason": "lexical_overlap_with_opposite_polarity" if opposite_polarity else "lexical_overlap",
                    "matched_field": matched_field,
                    "status": "SUGGESTION_NOT_A_VERDICT",
                },
            )
        )
    return [item for _, item in sorted(ranked, key=lambda pair: (-pair[0], pair[1]["source_id"]))[:limit]]


def detect_scope_issues(
    statement: str, recommendations: list[dict[str, Any]], source_bodies: dict[str, str]
) -> list[dict[str, str]]:
    evidence_text = " ".join(source_bodies.get(item["source_id"], "") for item in recommendations)
    issues: list[dict[str, str]] = []
    if UNIVERSAL.search(statement) and (not evidence_text or QUALIFIED.search(evidence_text)):
        issues.append(
            {
                "type": "possible_overgeneralization",
                "severity": "review",
                "detail": "The claim uses universal or certainty language that candidate evidence may not preserve.",
            }
        )
    if CAUSAL.search(statement) and (
        not evidence_text or re.search(r"associated|correlat|相关", evidence_text, re.IGNORECASE)
    ):
        issues.append(
            {
                "type": "possible_causal_overreach",
                "severity": "review",
                "detail": "The claim uses causal language while candidate evidence may describe only association.",
            }
        )
    if (
        re.search(
            r"\b(?:people|users|patients|students|developers)\b|人群|用户|患者|学生|开发者", statement, re.IGNORECASE
        )
        and evidence_text
        and not re.search(
            r"population|sample|respondents?|participants?|人群|样本|受访者|参与者", evidence_text, re.IGNORECASE
        )
    ):
        issues.append(
            {
                "type": "population_scope_unclear",
                "severity": "review",
                "detail": "The target population is not clearly recoverable from the candidate evidence text.",
            }
        )
    if not recommendations:
        issues.append(
            {
                "type": "no_candidate_evidence",
                "severity": "review",
                "detail": "No local source had enough lexical overlap to recommend; search or attach evidence manually.",
            }
        )
    return issues


def _claims(report: Path) -> list[dict[str, Any]]:
    parsed = parse_markdown_report(report)
    if parsed["claims"]:
        return [
            {"id": item["id"], "statement": item["statement"], "origin": "report_claim_section"}
            for item in parsed["claims"]
        ]
    text = report.read_text(encoding="utf-8")
    return [
        {"id": f"C{index:03d}", "statement": statement, "origin": "candidate_extraction"}
        for index, statement in enumerate(candidate_claims(text), start=1)
    ]


def heuristic_draft(report: Path, manifest: Path | None = None) -> dict[str, Any]:
    manifest_data = load_json_object(manifest) if manifest else {"sources": [], "evidence": []}
    sources = manifest_data.get("sources", [])
    evidence = manifest_data.get("evidence", [])
    if not isinstance(sources, list) or not isinstance(evidence, list):
        raise ValueError("manifest sources and evidence must be arrays")
    source_bodies = {
        str(source.get("id") or ""): _source_text(source, evidence) for source in sources if isinstance(source, dict)
    }
    candidates = []
    for claim in _claims(report):
        recommendations = recommend_evidence(claim["statement"], sources, evidence)
        candidates.append(
            {
                **claim,
                "status": "AI_DRAFT_REQUIRES_HUMAN_REVIEW",
                "evidence_recommendations": recommendations,
                "scope_issues": detect_scope_issues(claim["statement"], recommendations, source_bodies),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "governed-ai-review-draft",
        "created_at": utc_timestamp(),
        "inputs": {
            "report": report.name,
            "report_sha256": sha256(report),
            "manifest": manifest.name if manifest else "",
            "manifest_sha256": sha256(manifest) if manifest else "",
        },
        "governance": {
            "state": "AI_DRAFT",
            "formal_judgments_created": False,
            "human_confirmation_required": True,
            "provider": "heuristic",
            "model": "deterministic-local-rules",
            "data_sent": "none",
        },
        "candidates": candidates,
        "instructions": [
            "Treat every recommendation and issue as a draft, never as a source verdict.",
            "Open the source and verify an exact quote, locator, scope, and version before confirmation.",
            "A decisive confirmation requires a named human reviewer, exact quote, and locator.",
        ],
    }


def _endpoint(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("model endpoint must be an HTTP(S) URL without embedded credentials")
    return value.rstrip("/")


def request_model(
    draft: dict[str, Any],
    provider: str,
    endpoint: str,
    model: str,
    api_key_env: str,
    requester: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    endpoint = _endpoint(endpoint)
    prompt = (
        "Review the candidate claims and evidence recommendations. Return JSON with a candidates array. "
        "Each item may contain only id, rationale, additional_scope_issues, and search_suggestions. "
        "Do not issue verdicts or claim that evidence supports a claim.\n"
        + json.dumps({"candidates": draft["candidates"]}, ensure_ascii=False)
    )
    if provider == "ollama":
        url = endpoint if endpoint.endswith("/api/chat") else f"{endpoint}/api/chat"
        body = {"model": model, "stream": False, "format": "json", "messages": [{"role": "user", "content": prompt}]}
        headers = {"Content-Type": "application/json"}
    elif provider == "openai-compatible":
        url = endpoint if endpoint.endswith("/chat/completions") else f"{endpoint}/chat/completions"
        body = {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {"Content-Type": "application/json"}
        secret = os.environ.get(api_key_env, "")
        if not secret:
            raise ValueError(f"API key environment variable is empty: {api_key_env}")
        headers["Authorization"] = f"Bearer {secret}"
    else:
        raise ValueError("external model provider must be ollama or openai-compatible")
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with requester(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
    content = (
        result.get("message", {}).get("content", "")
        if provider == "ollama"
        else (result.get("choices") or [{}])[0].get("message", {}).get("content", "")
    )
    proposed = json.loads(content)
    if not isinstance(proposed, dict) or not isinstance(proposed.get("candidates"), list):
        raise ValueError("model response must contain a candidates array")
    by_id = {item["id"]: item for item in draft["candidates"]}
    for item in proposed["candidates"]:
        if not isinstance(item, dict) or item.get("id") not in by_id:
            continue
        allowed = {
            "rationale": str(item.get("rationale") or "")[:4000],
            "additional_scope_issues": item.get("additional_scope_issues", []),
            "search_suggestions": item.get("search_suggestions", []),
        }
        allowed["additional_scope_issues"] = [
            str(value)[:500] for value in allowed["additional_scope_issues"] if isinstance(value, str)
        ][:10]
        allowed["search_suggestions"] = [
            str(value)[:500] for value in allowed["search_suggestions"] if isinstance(value, str)
        ][:10]
        by_id[item["id"]]["model_analysis"] = allowed
    draft["governance"].update(
        {
            "provider": provider,
            "model": model,
            "endpoint_origin": f"{urllib.parse.urlparse(endpoint).scheme}://{urllib.parse.urlparse(endpoint).netloc}",
            "data_sent": "candidate claims and local evidence recommendation text",
        }
    )
    return draft


def confirm_draft(
    draft_path: Path,
    claim_id: str,
    source_id: str,
    verdict: str,
    quote: str,
    locator: str,
    reviewer_id: str,
    note: str,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    draft = load_json_object(draft_path)
    if draft.get("kind") != "governed-ai-review-draft" or draft.get("governance", {}).get("state") != "AI_DRAFT":
        raise ValueError("input is not a governed AI draft")
    candidate = next(
        (item for item in draft.get("candidates", []) if item.get("id", "").upper() == claim_id.upper()), None
    )
    if not candidate:
        raise ValueError(f"claim is not present in draft: {claim_id}")
    reviewer = reviewer_id.strip()
    if not reviewer or re.fullmatch(r"(?:ai|assistant|model|bot|automated)(?:[-_ ].*)?", reviewer, re.IGNORECASE):
        raise ValueError("reviewer-id must identify a human reviewer")
    normalized_verdict = verdict.upper()
    if normalized_verdict not in FORMAL_VERDICTS:
        raise ValueError(f"verdict must be one of: {', '.join(sorted(FORMAL_VERDICTS))}")
    if not source_id.strip():
        raise ValueError("source-id is required")
    if normalized_verdict in DECISIVE_VERDICTS and (not quote.strip() or not locator.strip()):
        raise ValueError("decisive human verdicts require an exact quote and locator")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "governed-ai-review-confirmation",
        "status": "HUMAN_CONFIRMED",
        "draft_sha256": sha256(draft_path),
        "claim": {"id": candidate["id"], "statement": candidate["statement"]},
        "evidence": {
            "claim_id": candidate["id"],
            "source_id": source_id.strip(),
            "verdict": normalized_verdict,
            "quote": quote.strip(),
            "locator": locator.strip(),
            "note": note.strip(),
            "reviewer_id": reviewer,
            "reviewed_at": reviewed_at or utc_timestamp(),
            "review_method": "human",
            "review_receipt": f"sha256:{sha256(draft_path)}",
        },
        "governance": {
            "ai_draft_was_non_decisive": True,
            "human_assumed_responsibility": True,
            "confirmation_does_not_bypass_independent_review": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    draft = commands.add_parser("draft", help="extract claims and draft governed review suggestions")
    draft.add_argument("report", type=Path)
    draft.add_argument("--manifest", type=Path)
    draft.add_argument("--provider", choices=PROVIDERS, default="heuristic")
    draft.add_argument("--endpoint", default="http://127.0.0.1:11434")
    draft.add_argument("--model", default="")
    draft.add_argument("--api-key-env", default="PAPERTRAIL_AI_API_KEY")
    draft.add_argument("--output", type=Path, required=True)
    confirm = commands.add_parser("confirm", help="record a named human evidence judgment from a draft")
    confirm.add_argument("draft", type=Path)
    confirm.add_argument("--claim-id", required=True)
    confirm.add_argument("--source-id", required=True)
    confirm.add_argument("--verdict", required=True, choices=sorted(FORMAL_VERDICTS))
    confirm.add_argument("--quote", default="")
    confirm.add_argument("--locator", default="")
    confirm.add_argument("--reviewer-id", required=True)
    confirm.add_argument("--note", default="")
    confirm.add_argument("--reviewed-at")
    confirm.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "draft":
            result = heuristic_draft(args.report, args.manifest)
            if args.provider != "heuristic":
                if not args.model:
                    raise ValueError("--model is required for ollama or openai-compatible providers")
                result = request_model(result, args.provider, args.endpoint, args.model, args.api_key_env)
        else:
            result = confirm_draft(
                args.draft,
                args.claim_id,
                args.source_id,
                args.verdict,
                args.quote,
                args.locator,
                args.reviewer_id,
                args.note,
                args.reviewed_at,
            )
        write_json(args.output, result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"status={result.get('status') or result['governance']['state']} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
