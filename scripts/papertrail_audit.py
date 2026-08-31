#!/usr/bin/env python3
"""Build a claim-to-source audit and a self-contained static PaperTrail report."""

from __future__ import annotations

import argparse
import html
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from research_io import atomic_write_json, load_json_object, sha256, utc_timestamp

VERDICTS = {
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONTRADICTED",
    "NOT_FOUND",
    "UNVERIFIABLE",
    "UNREVIEWED",
}
VERDICT_LABELS = {
    "SUPPORTED": "Supported",
    "PARTIALLY_SUPPORTED": "Partially supported",
    "CONTRADICTED": "Contradicted",
    "NOT_FOUND": "Not found",
    "UNVERIFIABLE": "Unverifiable",
    "UNREVIEWED": "Unreviewed",
}
HIGH_RISK_PUBLICATION_STATUSES = {"retracted", "withdrawn", "expression_of_concern"}
CLAIM_SECTIONS = {"claims", "key claims", "conclusions", "主要结论", "核心结论", "结论"}
CITATION_PATTERN = re.compile(r"\[@([^\]]+)\]")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LIST_PATTERN = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+(.+?)\s*$")
EXPLICIT_ID_PATTERN = re.compile(r"^\[(C[A-Za-z0-9_-]+)]\s*(.+)$", re.IGNORECASE)


def citation_ids(text: str) -> list[str]:
    """Return stable citation keys from Pandoc-style ``[@key; @other]`` groups."""
    found: list[str] = []
    for group in CITATION_PATTERN.findall(text):
        for raw in re.split(r"[;,]", group):
            key = raw.strip().lstrip("@").strip()
            if key and key not in found:
                found.append(key)
    return found


def clean_statement(text: str) -> str:
    return re.sub(r"\s+", " ", CITATION_PATTERN.sub("", text)).strip()


def parse_markdown_report(path: Path) -> dict[str, Any]:
    """Extract explicitly listed claims, falling back to cited paragraphs."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = path.stem
    claims: list[dict[str, Any]] = []
    in_claim_section = False

    for line_number, line in enumerate(lines, start=1):
        heading = HEADING_PATTERN.match(line)
        if heading:
            heading_text = heading.group(2).strip().rstrip("#").strip()
            if len(heading.group(1)) == 1 and title == path.stem:
                title = heading_text
            in_claim_section = heading_text.casefold() in CLAIM_SECTIONS
            continue
        if not in_claim_section:
            continue
        item = LIST_PATTERN.match(line)
        if not item:
            continue
        raw = item.group(1).strip()
        explicit = EXPLICIT_ID_PATTERN.match(raw)
        claim_id = explicit.group(1).upper() if explicit else f"C{len(claims) + 1:03d}"
        body = explicit.group(2) if explicit else raw
        statement = clean_statement(body)
        if statement:
            claims.append(
                {
                    "id": claim_id,
                    "statement": statement,
                    "citations": citation_ids(body),
                    "locator": f"{path.name}#line-{line_number}",
                }
            )

    if not claims:
        paragraph: list[str] = []
        paragraph_start = 1
        for line_number, line in enumerate([*lines, ""], start=1):
            if line.strip() and not HEADING_PATTERN.match(line):
                if not paragraph:
                    paragraph_start = line_number
                paragraph.append(line.strip())
                continue
            joined = " ".join(paragraph)
            if joined and citation_ids(joined):
                claims.append(
                    {
                        "id": f"C{len(claims) + 1:03d}",
                        "statement": clean_statement(joined),
                        "citations": citation_ids(joined),
                        "locator": f"{path.name}#line-{paragraph_start}",
                    }
                )
            paragraph = []

    identifiers = [claim["id"] for claim in claims]
    duplicates = sorted(key for key, count in Counter(identifiers).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate claim IDs: {', '.join(duplicates)}")
    if not claims:
        raise ValueError("no claims found; add a '## Claims' or '## 结论' list")
    return {"title": title, "claims": claims}


def _text(value: Any, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value.strip()


def _optional_bool(value: Any, field: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be true, false, or null")
    return value


def load_manifest(path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    data = load_json_object(path)
    raw_sources = data.get("sources", [])
    raw_evidence = data.get("evidence", [])
    if not isinstance(raw_sources, list) or not isinstance(raw_evidence, list):
        raise ValueError("manifest sources and evidence must be arrays")

    sources: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_sources):
        if not isinstance(raw, dict):
            raise ValueError(f"sources[{index}] must be an object")
        source_id = _text(raw.get("id"), f"sources[{index}].id")
        title = _text(raw.get("title"), f"sources[{index}].title")
        if not source_id or not title:
            raise ValueError(f"sources[{index}] requires id and title")
        if source_id in sources:
            raise ValueError(f"duplicate source ID: {source_id}")
        authors = raw.get("authors", [])
        if isinstance(authors, str):
            authors = [authors]
        if not isinstance(authors, list) or not all(isinstance(author, str) for author in authors):
            raise ValueError(f"sources[{index}].authors must be an array of strings")
        sources[source_id] = {
            "id": source_id,
            "title": title,
            "authors": [author.strip() for author in authors if author.strip()],
            "year": raw.get("year"),
            "doi": _text(raw.get("doi"), f"sources[{index}].doi"),
            "url": _text(raw.get("url"), f"sources[{index}].url"),
            "publication_status": _text(
                raw.get("publication_status", "unknown"), f"sources[{index}].publication_status"
            ).lower(),
            "integrity_checked_at": _text(raw.get("integrity_checked_at"), f"sources[{index}].integrity_checked_at"),
            "integrity_url": _text(raw.get("integrity_url"), f"sources[{index}].integrity_url"),
            "version": _text(raw.get("version"), f"sources[{index}].version"),
            "version_url": _text(raw.get("version_url"), f"sources[{index}].version_url"),
            "version_conflict": _optional_bool(raw.get("version_conflict"), f"sources[{index}].version_conflict"),
            "version_notes": _text(raw.get("version_notes"), f"sources[{index}].version_notes"),
            "data_availability": _text(
                raw.get("data_availability", "unknown"), f"sources[{index}].data_availability"
            ).lower(),
            "data_url": _text(raw.get("data_url"), f"sources[{index}].data_url"),
            "code_availability": _text(
                raw.get("code_availability", "unknown"), f"sources[{index}].code_availability"
            ).lower(),
            "code_url": _text(raw.get("code_url"), f"sources[{index}].code_url"),
        }

    evidence: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_evidence):
        if not isinstance(raw, dict):
            raise ValueError(f"evidence[{index}] must be an object")
        verdict = _text(raw.get("verdict", "UNREVIEWED"), f"evidence[{index}].verdict").upper()
        if verdict not in VERDICTS:
            raise ValueError(f"evidence[{index}] has invalid verdict: {verdict}")
        item = {
            "claim_id": _text(raw.get("claim_id"), f"evidence[{index}].claim_id").upper(),
            "source_id": _text(raw.get("source_id"), f"evidence[{index}].source_id"),
            "verdict": verdict,
            "quote": _text(raw.get("quote"), f"evidence[{index}].quote"),
            "locator": _text(raw.get("locator"), f"evidence[{index}].locator"),
            "note": _text(raw.get("note"), f"evidence[{index}].note"),
        }
        if not item["claim_id"] or not item["source_id"]:
            raise ValueError(f"evidence[{index}] requires claim_id and source_id")
        if verdict in {"SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED"} and (
            not item["quote"] or not item["locator"]
        ):
            raise ValueError(f"evidence[{index}] verdict {verdict} requires quote and locator")
        evidence.append(item)
    return sources, evidence


def claim_verdict(citations: list[str], rows: list[dict[str, Any]]) -> str:
    if not citations or any(not row["source_resolved"] for row in rows):
        return "UNVERIFIABLE"
    verdicts = [row["verdict"] for row in rows]
    if not verdicts or all(verdict == "UNREVIEWED" for verdict in verdicts):
        return "UNREVIEWED"
    if "CONTRADICTED" in verdicts:
        return "CONTRADICTED"
    if "PARTIALLY_SUPPORTED" in verdicts:
        return "PARTIALLY_SUPPORTED"
    if all(verdict == "SUPPORTED" for verdict in verdicts):
        return "SUPPORTED"
    if all(verdict == "NOT_FOUND" for verdict in verdicts):
        return "NOT_FOUND"
    if "UNVERIFIABLE" in verdicts:
        return "UNVERIFIABLE"
    return "PARTIALLY_SUPPORTED"


def _availability_check(sources: list[dict[str, Any]], kind: str) -> dict[str, str]:
    if not sources:
        return {"status": "WARN", "detail": "No resolved sources were available."}
    states = [source[f"{kind}_availability"] for source in sources]
    if all(state in {"available", "not_applicable"} for state in states):
        return {"status": "PASS", "detail": f"Every source declares {kind} availability."}
    if "unavailable" in states:
        return {"status": "FAIL", "detail": f"At least one source declares {kind} unavailable."}
    return {"status": "WARN", "detail": f"At least one source has unknown {kind} availability."}


def build_audit(report_path: Path, manifest_path: Path) -> dict[str, Any]:
    report = parse_markdown_report(report_path)
    sources, evidence = load_manifest(manifest_path)
    claims_by_id = {claim["id"]: claim for claim in report["claims"]}
    for item in evidence:
        if item["claim_id"] not in claims_by_id:
            raise ValueError(f"evidence references unknown claim: {item['claim_id']}")
        if item["source_id"] not in sources:
            raise ValueError(f"evidence references unknown source: {item['source_id']}")

    evidence_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in evidence:
        evidence_by_pair[(item["claim_id"], item["source_id"])].append(item)

    audited_claims: list[dict[str, Any]] = []
    cited_source_ids: list[str] = []
    for claim in report["claims"]:
        rows: list[dict[str, Any]] = []
        for source_id in claim["citations"]:
            if source_id not in cited_source_ids:
                cited_source_ids.append(source_id)
            matched = evidence_by_pair.get((claim["id"], source_id), [])
            if not matched:
                matched = [
                    {
                        "claim_id": claim["id"],
                        "source_id": source_id,
                        "verdict": "UNREVIEWED",
                        "quote": "",
                        "locator": "",
                        "note": "No human or automated evidence review has been recorded.",
                    }
                ]
            for item in matched:
                rows.append({**item, "source_resolved": source_id in sources})
        audited_claims.append({**claim, "verdict": claim_verdict(claim["citations"], rows), "evidence": rows})

    resolved_sources = [sources[source_id] for source_id in cited_source_ids if source_id in sources]
    unresolved_sources = [source_id for source_id in cited_source_ids if source_id not in sources]
    reviewed = [item for item in evidence if item["verdict"] != "UNREVIEWED"]
    risky_sources = [
        source for source in resolved_sources if source["publication_status"] in HIGH_RISK_PUBLICATION_STATUSES
    ]
    conflicting_versions = [source for source in resolved_sources if source["version_conflict"] is True]
    checklist = {
        "claims_have_citations": {
            "status": "PASS" if all(claim["citations"] for claim in audited_claims) else "FAIL",
            "detail": "Every claim has at least one citation."
            if all(claim["citations"] for claim in audited_claims)
            else "At least one claim has no citation.",
        },
        "sources_resolved": {
            "status": "PASS" if not unresolved_sources else "FAIL",
            "detail": "Every citation resolves in the manifest."
            if not unresolved_sources
            else f"Unresolved source IDs: {', '.join(unresolved_sources)}",
        },
        "reviewed_evidence_has_quotes": {
            "status": "PASS" if reviewed and all(item["quote"] for item in reviewed) else "WARN",
            "detail": "Every reviewed evidence row includes an exact quote."
            if reviewed and all(item["quote"] for item in reviewed)
            else "Some reviewed evidence is missing an exact quote, or no review has been recorded.",
        },
        "reviewed_evidence_has_locators": {
            "status": "PASS" if reviewed and all(item["locator"] for item in reviewed) else "WARN",
            "detail": "Every reviewed evidence row includes a locator."
            if reviewed and all(item["locator"] for item in reviewed)
            else "Some reviewed evidence is missing a page, section, paragraph, table, or URL locator.",
        },
        "source_metadata": {
            "status": "PASS"
            if resolved_sources
            and all(
                source["authors"] and source["year"] and (source["doi"] or source["url"]) for source in resolved_sources
            )
            else "WARN",
            "detail": "Every resolved source has authors, year, and DOI or URL."
            if resolved_sources
            and all(
                source["authors"] and source["year"] and (source["doi"] or source["url"]) for source in resolved_sources
            )
            else "At least one source is missing authors, year, or a DOI/URL.",
        },
        "publication_status": {
            "status": "FAIL"
            if risky_sources
            else "PASS"
            if resolved_sources and all(source["publication_status"] != "unknown" for source in resolved_sources)
            else "WARN",
            "detail": f"High-risk publication status: {', '.join(source['id'] for source in risky_sources)}."
            if risky_sources
            else "Publication status is recorded for every resolved source."
            if resolved_sources and all(source["publication_status"] != "unknown" for source in resolved_sources)
            else "At least one source has unknown correction or retraction status.",
        },
        "version_conflicts": {
            "status": "FAIL"
            if conflicting_versions
            else "PASS"
            if resolved_sources and all(source["version_conflict"] is False for source in resolved_sources)
            else "WARN",
            "detail": f"Version conflicts require review: {', '.join(source['id'] for source in conflicting_versions)}."
            if conflicting_versions
            else "Every resolved source explicitly records no known version conflict."
            if resolved_sources and all(source["version_conflict"] is False for source in resolved_sources)
            else "At least one source has not been checked for version conflicts.",
        },
        "data_availability": _availability_check(resolved_sources, "data"),
        "code_availability": _availability_check(resolved_sources, "code"),
    }
    counts = Counter(claim["verdict"] for claim in audited_claims)
    return {
        "schema_version": 1,
        "tool": "PaperTrail",
        "generated_at": utc_timestamp(),
        "report": {
            "title": report["title"],
            "file": report_path.name,
            "sha256": sha256(report_path),
        },
        "manifest": {"file": manifest_path.name, "sha256": sha256(manifest_path)},
        "summary": {
            "claims": len(audited_claims),
            "sources": len(resolved_sources),
            "unresolved_sources": len(unresolved_sources),
            "verdicts": {verdict: counts.get(verdict, 0) for verdict in sorted(VERDICTS)},
        },
        "claims": audited_claims,
        "sources": resolved_sources,
        "unresolved_source_ids": unresolved_sources,
        "reproducibility_checklist": checklist,
        "limitations": [
            "A citation match does not by itself establish that a source supports a claim.",
            "Verdicts reflect recorded evidence rows and must be independently reviewed for high-stakes use.",
            "Not found means the recorded search failed to locate evidence; it does not prove the claim false.",
        ],
    }


def _safe_url(value: str) -> str:
    parsed = urlparse(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def render_html(audit: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value), quote=True)

    cards = "".join(
        f'<div class="metric {verdict.lower()}"><strong>{count}</strong><span>{esc(VERDICT_LABELS[verdict])}</span></div>'
        for verdict, count in audit["summary"]["verdicts"].items()
        if count
    )
    source_map = {source["id"]: source for source in audit["sources"]}
    claim_sections: list[str] = []
    for claim in audit["claims"]:
        evidence_rows: list[str] = []
        for item in claim["evidence"]:
            source = source_map.get(item["source_id"])
            source_title = source["title"] if source else f"Unresolved source: {item['source_id']}"
            source_url = _safe_url(source["url"]) if source else ""
            source_markup = (
                f'<a href="{esc(source_url)}" rel="noreferrer">{esc(source_title)}</a>'
                if source_url
                else esc(source_title)
            )
            quote = (
                f"<blockquote>{esc(item['quote'])}</blockquote>"
                if item["quote"]
                else '<p class="muted">No quote recorded.</p>'
            )
            evidence_rows.append(
                "<tr>"
                f'<td data-label="Source">{source_markup}<small>{esc(item["source_id"])}</small></td>'
                f'<td data-label="Assessment"><span class="badge {item["verdict"].lower()}">{esc(VERDICT_LABELS[item["verdict"]])}</span></td>'
                f'<td data-label="Exact evidence">{quote}</td>'
                f'<td data-label="Locator">{esc(item["locator"] or "Not recorded")}</td>'
                f'<td data-label="Review note">{esc(item["note"])}</td>'
                "</tr>"
            )
        if not evidence_rows:
            evidence_rows.append(
                '<tr><td colspan="5" class="muted">No citations were recorded for this claim.</td></tr>'
            )
        claim_sections.append(
            f'<article class="claim" data-verdict="{esc(claim["verdict"])}">'
            '<div class="claim-heading">'
            f'<span class="claim-id">{esc(claim["id"])}</span>'
            f'<span class="badge {claim["verdict"].lower()}">{esc(VERDICT_LABELS[claim["verdict"]])}</span>'
            "</div>"
            f"<h3>{esc(claim['statement'])}</h3>"
            f'<p class="muted">Report location: {esc(claim["locator"])}</p>'
            '<div class="table-wrap"><table class="evidence-table"><thead><tr><th>Source</th><th>Assessment</th><th>Exact evidence</th>'
            f"<th>Locator</th><th>Review note</th></tr></thead><tbody>{''.join(evidence_rows)}</tbody></table></div>"
            "</article>"
        )

    checklist_rows = "".join(
        f'<li><span class="check {item["status"].lower()}">{esc(item["status"])}</span>'
        f"<div><strong>{esc(name.replace('_', ' ').title())}</strong><p>{esc(item['detail'])}</p></div></li>"
        for name, item in audit["reproducibility_checklist"].items()
    )
    source_rows = "".join(
        "<tr>"
        f'<td data-label="ID">{esc(source["id"])}</td><td data-label="Title">{esc(source["title"])}</td>'
        f'<td data-label="Authors">{esc(", ".join(source["authors"]) or "Unknown")}</td>'
        f'<td data-label="Year">{esc(source["year"] or "Unknown")}</td>'
        f'<td data-label="DOI">{esc(source["doi"] or "—")}</td>'
        f'<td data-label="Version">{esc(source["version"] or "—")}</td>'
        f'<td data-label="Integrity">{esc(source["publication_status"])}</td>'
        f'<td data-label="Conflict">{esc("yes" if source["version_conflict"] is True else "no" if source["version_conflict"] is False else "unknown")}</td>'
        "</tr>"
        for source in audit["sources"]
    )
    limitations = "".join(f"<li>{esc(item)}</li>" for item in audit["limitations"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{esc(audit["report"]["title"])} · PaperTrail</title>
  <style>
    :root {{ --bg:#f5f5f0; --panel:#fff; --ink:#17211b; --muted:#637068; --line:#d9ded9; --accent:#155eef;
      --supported:#18794e; --partially:#9a6700; --contradicted:#c9372c; --notfound:#6f42c1; --unverifiable:#b54708; --unreviewed:#59636e; }}
    @media (prefers-color-scheme:dark) {{ :root {{ --bg:#101411; --panel:#181e1a; --ink:#edf2ee; --muted:#a7b0aa; --line:#344039; --accent:#79a6ff; }} }}
    * {{ box-sizing:border-box }} body {{ margin:0; overflow-x:hidden; background:var(--bg); color:var(--ink); font:15px/1.55 Inter,ui-sans-serif,system-ui,sans-serif }} code {{ overflow-wrap:anywhere }}
    main {{ width:min(1180px,calc(100% - 32px)); margin:0 auto; padding:48px 0 80px }}
    header {{ border-bottom:1px solid var(--line); padding-bottom:28px }} h1 {{ margin:.15em 0; font-size:clamp(2rem,5vw,4rem); letter-spacing:-.04em }}
    h2 {{ margin-top:48px; font-size:1.5rem }} h3 {{ margin:12px 0 4px; font-size:1.15rem }} .eyebrow {{ color:var(--accent); font-weight:800; letter-spacing:.12em; text-transform:uppercase }}
    .muted, small {{ color:var(--muted) }} small {{ display:block; margin-top:4px }} .metrics {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:22px }}
    .metric {{ min-width:145px; padding:14px 16px; background:var(--panel); border:1px solid var(--line); border-radius:14px }} .metric strong {{ display:block; font-size:1.7rem }}
    .toolbar {{ display:flex; gap:8px; flex-wrap:wrap; margin:24px 0 }} button {{ color:var(--ink); background:var(--panel); border:1px solid var(--line); border-radius:999px; padding:8px 13px; cursor:pointer }} button.active {{ color:white; background:var(--accent); border-color:var(--accent) }}
    .claim {{ background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:20px; margin:16px 0; box-shadow:0 8px 30px #0000000a }} .claim[hidden] {{ display:none }}
    .claim-heading {{ display:flex; align-items:center; justify-content:space-between; gap:12px }} .claim-id {{ font:700 13px ui-monospace,monospace; color:var(--muted) }}
    .badge,.check {{ display:inline-flex; align-items:center; border-radius:999px; padding:4px 9px; color:white; font-size:12px; font-weight:800; white-space:nowrap }}
    .supported {{ background:var(--supported) }} .partially_supported {{ background:var(--partially) }} .contradicted {{ background:var(--contradicted) }}
    .not_found {{ background:var(--notfound) }} .unverifiable {{ background:var(--unverifiable) }} .unreviewed {{ background:var(--unreviewed) }}
    .table-wrap {{ overflow:auto; margin-top:16px }} table {{ width:100%; border-collapse:collapse; min-width:760px }} th,td {{ text-align:left; vertical-align:top; border-bottom:1px solid var(--line); padding:12px }} th {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.06em }}
    blockquote {{ margin:0; padding-left:12px; border-left:3px solid var(--accent) }} .checklist {{ list-style:none; padding:0; display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:10px }}
    .checklist li {{ display:flex; align-items:flex-start; gap:12px; background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:15px }} .checklist p {{ margin:3px 0 0 }} .check.pass {{ background:var(--supported) }} .check.warn {{ background:var(--partially) }} .check.fail {{ background:var(--contradicted) }}
    .notice {{ border-left:4px solid var(--partially); background:var(--panel); padding:14px 18px; border-radius:8px }} footer {{ color:var(--muted); margin-top:50px }} a {{ color:var(--accent) }}
    @media (max-width:640px) {{
      main {{ width:min(100% - 20px,1180px); padding:28px 0 56px }} header {{ padding-bottom:20px }} h2 {{ margin-top:36px }}
      .metric {{ min-width:0; flex:1 1 130px }} .claim {{ padding:15px }} .table-wrap {{ overflow:visible }}
      .evidence-table,.evidence-table tbody,.evidence-table tr,.evidence-table td,
      .source-table,.source-table tbody,.source-table tr,.source-table td {{ display:block; min-width:0; width:100% }}
      .evidence-table thead,.source-table thead {{ display:none }}
      .evidence-table tr,.source-table tr {{ border-top:1px solid var(--line); padding:8px 0 }}
      .evidence-table td,.source-table td {{ border:0; padding:7px 0 7px 112px; position:relative; overflow-wrap:anywhere }}
      .evidence-table td::before,.source-table td::before {{ content:attr(data-label); color:var(--muted); font-size:11px; font-weight:800; left:0; letter-spacing:.06em; position:absolute; text-transform:uppercase; top:8px; width:100px }}
    }}
  </style>
</head>
<body><main>
  <header><div class="eyebrow">PaperTrail evidence audit</div><h1>{esc(audit["report"]["title"])}</h1>
    <p>Generated {esc(audit["generated_at"])} from <code>{esc(audit["report"]["file"])}</code>. Report SHA-256: <code>{esc(audit["report"]["sha256"])}</code></p>
    <div class="metrics">{cards}</div>
  </header>
  <section><h2>Claim audit</h2><div class="toolbar"><button class="active" data-filter="ALL">All claims</button>
    {"".join(f'<button data-filter="{verdict}">{esc(VERDICT_LABELS[verdict])}</button>' for verdict, count in audit["summary"]["verdicts"].items() if count)}</div>
    {"".join(claim_sections)}</section>
  <section><h2>Reproducibility checklist</h2><ul class="checklist">{checklist_rows}</ul></section>
  <section><h2>Source registry</h2><div class="table-wrap"><table class="source-table"><thead><tr><th>ID</th><th>Title</th><th>Authors</th><th>Year</th><th>DOI</th><th>Version</th><th>Integrity</th><th>Conflict</th></tr></thead><tbody>{source_rows}</tbody></table></div></section>
  <section><h2>Interpretation limits</h2><div class="notice"><ul>{limitations}</ul></div></section>
  <footer>Generated locally by PaperTrail. The report contains recorded assessments, not an automatic guarantee of truth.</footer>
</main><script>
  const buttons=[...document.querySelectorAll('[data-filter]')]; const claims=[...document.querySelectorAll('.claim')];
  for(const button of buttons) button.addEventListener('click',()=>{{ const value=button.dataset.filter; buttons.forEach(x=>x.classList.toggle('active',x===button)); claims.forEach(claim=>claim.hidden=value!=='ALL'&&claim.dataset.verdict!==value); }});
</script></body></html>"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Markdown report containing a Claims or 结论 list")
    parser.add_argument("--manifest", required=True, type=Path, help="JSON source and evidence manifest")
    parser.add_argument("--output-dir", type=Path, default=Path("papertrail-site"))
    parser.add_argument("--strict", action="store_true", help="fail unless every claim is supported")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        audit = build_audit(args.report.resolve(), args.manifest.resolve())
        args.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(args.output_dir / "audit.json", audit)
        (args.output_dir / "index.html").write_text(render_html(audit), encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"claims={audit['summary']['claims']} sources={audit['summary']['sources']}")
    print(f"html={args.output_dir / 'index.html'}")
    print(f"json={args.output_dir / 'audit.json'}")
    if args.strict and any(claim["verdict"] != "SUPPORTED" for claim in audit["claims"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
