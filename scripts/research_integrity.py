#!/usr/bin/env python3
"""Build a replayable multi-provider research-integrity record and version graph."""

from __future__ import annotations

import argparse
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable

from research_io import sha256_bytes, utc_timestamp, write_json

SCHEMA_VERSION = 1
PROVIDERS = ("crossref", "openalex", "pubmed", "crossmark")
USER_AGENT = "rigorous-research/1.5 (Research Integrity Network)"
CROSSREF_WORKS = "https://api.crossref.org/works"
OPENALEX_WORKS = "https://api.openalex.org/works"
PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

EVENT_TYPES = {
    "retraction": "retraction",
    "retracted": "retraction",
    "withdrawal": "withdrawal",
    "withdrawn": "withdrawal",
    "correction": "correction",
    "corrigendum": "correction",
    "erratum": "correction",
    "expression-of-concern": "expression_of_concern",
    "expression of concern": "expression_of_concern",
    "update": "update",
}
HIGH_RISK_EVENTS = {"retraction", "withdrawal", "expression_of_concern"}


class ProviderNotFound(ValueError):
    """Raised when a provider completed a query but has no matching work."""

    def __init__(self, message: str, response: bytes = b"", source_url: str = "") -> None:
        super().__init__(message)
        self.response = response
        self.source_url = source_url


def normalize_doi(value: str) -> str:
    normalized = re.sub(r"^doi:\s*", "", value.strip(), flags=re.IGNORECASE)
    normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", normalized, flags=re.IGNORECASE)
    normalized = normalized.rstrip(".,;)").casefold()
    return normalized if re.fullmatch(r"10\.\d{4,9}/\S+", normalized) else ""


def normalize_identifier(value: str) -> dict[str, str]:
    raw = value.strip()
    doi = normalize_doi(raw)
    if doi:
        return {"kind": "doi", "value": doi}
    pmid = re.sub(r"^(?:pmid\s*:?\s*|https?://pubmed\.ncbi\.nlm\.nih\.gov/)", "", raw, flags=re.IGNORECASE)
    if re.fullmatch(r"\d{1,10}/?", pmid):
        return {"kind": "pmid", "value": pmid.rstrip("/")}
    openalex = re.sub(r"^https?://openalex\.org/", "", raw, flags=re.IGNORECASE).upper()
    if re.fullmatch(r"W\d+", openalex):
        return {"kind": "openalex", "value": openalex}
    arxiv = re.sub(r"^(?:arxiv\s*:?|https?://arxiv\.org/abs/)", "", raw, flags=re.IGNORECASE)
    if re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?", arxiv, flags=re.IGNORECASE):
        return {"kind": "arxiv", "value": arxiv}
    raise ValueError("identifier must be a DOI, PMID, OpenAlex work ID, or arXiv ID")


def clean_text(value: Any) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", str(value or "")).split())


def _year(parts: Any) -> int | None:
    try:
        return int(parts["date-parts"][0][0])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _event_type(value: str) -> str:
    normalized = re.sub(r"[_\s]+", "-", value.strip().casefold())
    return EVENT_TYPES.get(normalized, EVENT_TYPES.get(normalized.replace("-", " "), "update"))


def _relation_identifier(item: dict[str, Any]) -> str:
    return normalize_doi(str(item.get("DOI") or item.get("doi") or item.get("id") or "")) or clean_text(
        item.get("PMID") or item.get("pmid") or item.get("id")
    )


def _check(
    provider: str,
    checked_at: str,
    source_url: str,
    response: bytes | None,
    *,
    status: str = "ok",
    limitation: str,
    identity: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
    versions: list[dict[str, Any]] | None = None,
    error: str = "",
) -> dict[str, Any]:
    return {
        "provider": provider,
        "checked_at": checked_at,
        "source_url": source_url,
        "status": status,
        "response_sha256": sha256_bytes(response) if response is not None else "",
        "limitation": limitation,
        "error": error,
        "identity": identity or {},
        "events": events or [],
        "versions": versions or [],
    }


def parse_crossref(payload: bytes, checked_at: str, source_url: str) -> dict[str, Any]:
    data = json.loads(payload.decode("utf-8"))
    message = data.get("message")
    if not isinstance(message, dict):
        raise ValueError("Crossref response has no work message")
    doi = normalize_doi(str(message.get("DOI") or ""))
    authors = [
        " ".join(filter(None, (clean_text(author.get("given")), clean_text(author.get("family")))))
        for author in message.get("author", [])
        if isinstance(author, dict)
    ]
    identity = {
        "title": clean_text((message.get("title") or [""])[0]),
        "authors": [value for value in authors if value],
        "year": next(
            (
                value
                for value in (
                    _year(message.get("published-print")),
                    _year(message.get("published-online")),
                    _year(message.get("issued")),
                )
                if value is not None
            ),
            None,
        ),
        "doi": doi,
        "url": clean_text(message.get("URL")) or (f"https://doi.org/{doi}" if doi else ""),
        "type": clean_text(message.get("type")),
    }
    events: list[dict[str, Any]] = []
    versions: list[dict[str, Any]] = []
    for field, direction in (("update-to", "updates_related"), ("updated-by", "applies_to_work")):
        for relation in message.get(field) or []:
            if not isinstance(relation, dict):
                continue
            event_type = _event_type(clean_text(relation.get("type")))
            target = _relation_identifier(relation)
            events.append(
                {
                    "type": event_type,
                    "provider": "crossref",
                    "direction": direction,
                    "related_identifier": target,
                    "recorded_at": clean_text(relation.get("updated", {}).get("date-time"))
                    if isinstance(relation.get("updated"), dict)
                    else "",
                    "description": clean_text(relation.get("label") or relation.get("type")),
                }
            )
    relation_roles = {
        "is-preprint-of": ("preprint", "is_preprint_of"),
        "has-preprint": ("preprint", "has_preprint"),
        "is-version-of": ("revision", "is_version_of"),
        "has-version": ("revision", "has_version"),
        "is-identical-to": ("related", "is_identical_to"),
        "is-retracted-by": ("retraction", "is_retracted_by"),
    }
    for name, items in (message.get("relation") or {}).items():
        role, relation = relation_roles.get(name, ("related", name.replace("-", "_")))
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            identifier = _relation_identifier(item)
            if identifier:
                versions.append({"identifier": identifier, "role": role, "relation": relation, "provider": "crossref"})
    return _check(
        "crossref",
        checked_at,
        source_url,
        payload,
        limitation="Depositor-supplied metadata can be incomplete or delayed; absence of an update is not proof of integrity.",
        identity=identity,
        events=events,
        versions=versions,
    )


def _openalex_abstract(index: Any) -> str:
    if not isinstance(index, dict):
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        for position in positions if isinstance(positions, list) else []:
            if isinstance(position, int):
                words.append((position, word))
    return " ".join(word for _, word in sorted(words))


def parse_openalex(payload: bytes, checked_at: str, source_url: str) -> dict[str, Any]:
    item = json.loads(payload.decode("utf-8"))
    if not isinstance(item, dict) or not item.get("id"):
        raise ValueError("OpenAlex response has no work")
    ids = item.get("ids") or {}
    doi = normalize_doi(str(item.get("doi") or ids.get("doi") or ""))
    openalex_id = re.sub(r"^https?://openalex\.org/", "", str(item.get("id")), flags=re.IGNORECASE).upper()
    authors = [
        clean_text(authorship.get("author", {}).get("display_name"))
        for authorship in item.get("authorships") or []
        if isinstance(authorship, dict)
    ]
    identity = {
        "title": clean_text(item.get("display_name") or item.get("title")),
        "authors": [value for value in authors if value],
        "year": item.get("publication_year"),
        "doi": doi,
        "openalex": openalex_id,
        "pmid": re.sub(r".*/", "", str(ids.get("pmid") or "")),
        "arxiv": re.sub(r"^https?://arxiv\.org/abs/", "", str(ids.get("arxiv") or ""), flags=re.IGNORECASE),
        "url": clean_text((item.get("primary_location") or {}).get("landing_page_url") or item.get("id")),
        "type": clean_text(item.get("type")),
        "abstract": _openalex_abstract(item.get("abstract_inverted_index")),
    }
    events = []
    if item.get("is_retracted") is True:
        events.append(
            {
                "type": "retraction",
                "provider": "openalex",
                "direction": "applies_to_work",
                "related_identifier": doi or openalex_id,
                "recorded_at": clean_text(item.get("updated_date")),
                "description": "OpenAlex marks this work as retracted.",
            }
        )
    versions = []
    arxiv = identity["arxiv"]
    if arxiv:
        versions.append({"identifier": arxiv, "role": "preprint", "relation": "has_preprint", "provider": "openalex"})
    return _check(
        "openalex",
        checked_at,
        source_url,
        payload,
        limitation="OpenAlex aggregates upstream metadata and does not provide an exhaustive correction or concern registry.",
        identity=identity,
        events=events,
        versions=versions,
    )


def _xml_text(node: ET.Element | None, path: str) -> str:
    return clean_text(
        "" if node is None else "".join(node.find(path).itertext()) if node.find(path) is not None else ""
    )


def parse_pubmed(payload: bytes, checked_at: str, source_url: str) -> dict[str, Any]:
    root = ET.fromstring(payload)
    article = root.find(".//PubmedArticle")
    if article is None:
        raise ValueError("PubMed response has no PubmedArticle")
    pmid = _xml_text(article, "./MedlineCitation/PMID")
    doi = ""
    for item in article.findall("./PubmedData/ArticleIdList/ArticleId"):
        if item.attrib.get("IdType", "").casefold() == "doi":
            doi = normalize_doi(item.text or "")
    authors = []
    for author in article.findall("./MedlineCitation/Article/AuthorList/Author"):
        name = " ".join(filter(None, (_xml_text(author, "ForeName"), _xml_text(author, "LastName"))))
        if name:
            authors.append(name)
    year_text = _xml_text(article, "./MedlineCitation/Article/Journal/JournalIssue/PubDate/Year") or _xml_text(
        article, "./MedlineCitation/Article/ArticleDate/Year"
    )
    identity = {
        "title": _xml_text(article, "./MedlineCitation/Article/ArticleTitle"),
        "authors": authors,
        "year": int(year_text) if year_text.isdigit() else None,
        "doi": doi,
        "pmid": pmid,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        "type": "; ".join(
            _xml_text(node, ".")
            for node in article.findall("./MedlineCitation/Article/PublicationTypeList/PublicationType")
            if _xml_text(node, ".")
        ),
    }
    events: list[dict[str, Any]] = []
    versions: list[dict[str, Any]] = []
    for relation in article.findall("./MedlineCitation/CommentsCorrectionsList/CommentsCorrections"):
        ref_type = clean_text(relation.attrib.get("RefType"))
        event_type = _event_type(ref_type)
        related_pmid = _xml_text(relation, "PMID")
        applies_to_work = ref_type.casefold().endswith("in") or ref_type.casefold() in {
            "retractedpublication",
            "expressionofconcernin",
        }
        events.append(
            {
                "type": event_type,
                "provider": "pubmed",
                "direction": "applies_to_work" if applies_to_work else "updates_related",
                "related_identifier": related_pmid,
                "recorded_at": "",
                "description": ref_type or _xml_text(relation, "RefSource"),
            }
        )
        if related_pmid:
            versions.append(
                {
                    "identifier": related_pmid,
                    "role": event_type if event_type != "update" else "revision",
                    "relation": re.sub(r"(?<!^)(?=[A-Z])", "_", ref_type).casefold(),
                    "provider": "pubmed",
                }
            )
    publication_types = identity["type"].casefold()
    if "retracted publication" in publication_types and not any(event["type"] == "retraction" for event in events):
        events.append(
            {
                "type": "retraction",
                "provider": "pubmed",
                "direction": "applies_to_work",
                "related_identifier": pmid,
                "recorded_at": "",
                "description": "PubMed publication type marks this work as retracted.",
            }
        )
    return _check(
        "pubmed",
        checked_at,
        source_url,
        payload,
        limitation="PubMed is biomedical-domain specific; indexing and linked notices can lag publishers.",
        identity=identity,
        events=events,
        versions=versions,
    )


def crossmark_manual(identifier: dict[str, str], checked_at: str) -> dict[str, Any]:
    doi = identifier["value"] if identifier["kind"] == "doi" else ""
    url = f"https://crossmark.crossref.org/dialog/?doi={urllib.parse.quote(doi, safe='')}" if doi else ""
    return _check(
        "crossmark",
        checked_at,
        url,
        None,
        status="manual_required" if doi else "not_applicable",
        limitation=(
            "The official Crossmark dialog is a human-facing publisher status surface, not a stable public bulk API. "
            "Crossref deposited updates are checked automatically; the dialog still requires human review."
            if doi
            else "Crossmark checks require a DOI."
        ),
    )


def request_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"Accept": "application/json, application/xml", "User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def provider_url(provider: str, identifier: dict[str, str]) -> str:
    kind, value = identifier["kind"], identifier["value"]
    if provider == "crossref" and kind == "doi":
        return f"{CROSSREF_WORKS}/{urllib.parse.quote(value, safe='')}"
    if provider == "openalex":
        external = (
            f"https://doi.org/{value}"
            if kind == "doi"
            else f"https://pubmed.ncbi.nlm.nih.gov/{value}"
            if kind == "pmid"
            else value
        )
        return f"{OPENALEX_WORKS}/{urllib.parse.quote(external, safe='')}"
    if provider == "pubmed":
        if kind == "pmid":
            return f"{PUBMED_FETCH}?{urllib.parse.urlencode({'db': 'pubmed', 'id': value, 'retmode': 'xml'})}"
        if kind == "doi":
            return f"{PUBMED_SEARCH}?{urllib.parse.urlencode({'db': 'pubmed', 'term': value + '[doi]', 'retmode': 'json'})}"
    return ""


def _fetch_pubmed(identifier: dict[str, str], fetcher: Callable[[str], bytes]) -> tuple[bytes, str]:
    if identifier["kind"] == "pmid":
        url = provider_url("pubmed", identifier)
        return fetcher(url), url
    search_url = provider_url("pubmed", identifier)
    search_payload = fetcher(search_url)
    search = json.loads(search_payload.decode("utf-8"))
    ids = search.get("esearchresult", {}).get("idlist", [])
    if not ids:
        raise ProviderNotFound("PubMed has no work for this DOI", search_payload, search_url)
    fetch_url = f"{PUBMED_FETCH}?{urllib.parse.urlencode({'db': 'pubmed', 'id': ids[0], 'retmode': 'xml'})}"
    return fetcher(fetch_url), fetch_url


def run_checks(
    raw_identifier: str,
    providers: list[str] | None = None,
    fixtures: dict[str, Path] | None = None,
    checked_at: str | None = None,
    fetcher: Callable[[str], bytes] = request_bytes,
) -> dict[str, Any]:
    identifier = normalize_identifier(raw_identifier)
    selected = providers or list(PROVIDERS)
    fixture_map = fixtures or {}
    now = checked_at or utc_timestamp()
    checks: list[dict[str, Any]] = []
    parsers = {"crossref": parse_crossref, "openalex": parse_openalex, "pubmed": parse_pubmed}
    for provider in selected:
        if provider == "crossmark":
            checks.append(crossmark_manual(identifier, now))
            continue
        url = provider_url(provider, identifier)
        if not url:
            checks.append(
                _check(
                    provider,
                    now,
                    "",
                    None,
                    status="not_applicable",
                    limitation=f"{provider} cannot be queried automatically with a {identifier['kind']} identifier.",
                )
            )
            continue
        try:
            if provider in fixture_map:
                payload = fixture_map[provider].read_bytes()
                source_url = f"fixture:{fixture_map[provider].name}"
                if provider == "pubmed" and payload.lstrip().startswith(b"{"):
                    search = json.loads(payload.decode("utf-8"))
                    if not search.get("esearchresult", {}).get("idlist", []):
                        raise ProviderNotFound(
                            "PubMed fixture records no matching work for this DOI", payload, source_url
                        )
            elif provider == "pubmed":
                payload, source_url = _fetch_pubmed(identifier, fetcher)
            else:
                payload, source_url = fetcher(url), url
            checks.append(parsers[provider](payload, now, source_url))
        except ProviderNotFound as exc:
            checks.append(
                _check(
                    provider,
                    now,
                    exc.source_url or url,
                    exc.response or None,
                    status="not_found",
                    limitation=(
                        f"{provider} returned no matching record. The work may be outside provider coverage; "
                        "this does not establish that the identifier is invalid."
                    ),
                    error=str(exc),
                )
            )
        except urllib.error.HTTPError as exc:
            status = "not_found" if exc.code == 404 else "error"
            checks.append(
                _check(
                    provider,
                    now,
                    url,
                    None,
                    status=status,
                    limitation=(
                        f"{provider} returned no matching record; coverage is not established."
                        if status == "not_found"
                        else f"{provider} coverage is unknown because this check failed."
                    ),
                    error=f"HTTPError {exc.code}: {exc.reason}",
                )
            )
        except (OSError, ValueError, json.JSONDecodeError, ET.ParseError) as exc:
            checks.append(
                _check(
                    provider,
                    now,
                    url,
                    None,
                    status="error",
                    limitation=f"{provider} coverage is unknown because this check failed.",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
    return aggregate_network(identifier, checks, now, selected)


def _normalized_title(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold(), flags=re.UNICODE).split())


def work_role(identity: dict[str, Any]) -> str:
    record_type = str(identity.get("type") or "").casefold()
    if any(value in record_type for value in ("posted-content", "preprint")):
        return "preprint"
    if any(value in record_type for value in ("correction", "erratum", "retraction", "withdrawal")):
        return "notice"
    if any(value in record_type for value in ("journal-article", "article", "proceedings")):
        return "version_of_record"
    return "scholarly_work"


def aggregate_network(
    identifier: dict[str, str], checks: list[dict[str, Any]], checked_at: str, requested: list[str]
) -> dict[str, Any]:
    identities = [
        (check["provider"], check["identity"]) for check in checks if check["status"] == "ok" and check["identity"]
    ]
    priority = {"crossref": 0, "pubmed": 1, "openalex": 2}
    canonical = dict(min(identities, key=lambda item: priority.get(item[0], 9))[1]) if identities else {}
    canonical.setdefault(identifier["kind"], identifier["value"])
    identifier_claims: dict[str, list[dict[str, str]]] = {}
    for provider, identity_value in identities:
        for kind in ("doi", "pmid", "openalex", "arxiv"):
            normalized = str(identity_value.get(kind) or "").strip()
            if not normalized:
                continue
            claim = {"provider": provider, "value": normalized}
            if claim not in identifier_claims.setdefault(kind, []):
                identifier_claims[kind].append(claim)
            canonical.setdefault(kind, normalized)
    canonical["identifiers"] = {
        kind: sorted({claim["value"] for claim in claims}) for kind, claims in identifier_claims.items()
    }
    events = [dict(event) for check in checks for event in check["events"]]
    conflicts: list[dict[str, Any]] = []
    for index, (left_provider, left) in enumerate(identities):
        for right_provider, right in identities[index + 1 :]:
            left_title, right_title = (
                _normalized_title(left.get("title", "")),
                _normalized_title(right.get("title", "")),
            )
            if left_title and right_title and SequenceMatcher(None, left_title, right_title).ratio() < 0.8:
                conflicts.append(
                    {
                        "field": "title",
                        "providers": [left_provider, right_provider],
                        "values": [left.get("title"), right.get("title")],
                    }
                )
            if left.get("year") and right.get("year") and abs(int(left["year"]) - int(right["year"])) > 1:
                conflicts.append(
                    {
                        "field": "year",
                        "providers": [left_provider, right_provider],
                        "values": [left["year"], right["year"]],
                    }
                )
            if left.get("doi") and right.get("doi") and left["doi"] != right["doi"]:
                conflicts.append(
                    {
                        "field": "doi",
                        "providers": [left_provider, right_provider],
                        "values": [left["doi"], right["doi"]],
                    }
                )
    root_id = canonical.get("doi") or canonical.get("pmid") or canonical.get("openalex") or identifier["value"]
    nodes = [{"id": root_id, "role": work_role(canonical), "label": canonical.get("title") or root_id}]
    edges: list[dict[str, str]] = []
    seen = {root_id}
    for check in checks:
        for version in check["versions"]:
            related = version.get("identifier", "")
            if not related:
                continue
            if related not in seen:
                nodes.append({"id": related, "role": version.get("role", "related"), "label": related})
                seen.add(related)
            relation = version.get("relation", "related_to")
            if relation.startswith("is_"):
                source, target = root_id, related
            else:
                source, target = related, root_id
            edge = {"source": source, "target": target, "relation": relation, "provider": check["provider"]}
            if edge not in edges:
                edges.append(edge)
    gaps = [
        {
            "provider": check["provider"],
            "status": check["status"],
            "limitation": check["limitation"],
            "source_url": check["source_url"],
        }
        for check in checks
        if check["status"] != "ok"
    ]
    for provider in PROVIDERS:
        if provider not in requested:
            gaps.append(
                {
                    "provider": provider,
                    "status": "not_requested",
                    "limitation": "Provider was not selected for this run.",
                    "source_url": "",
                }
            )
    high_risk = sorted(
        {
            event["type"]
            for event in events
            if event["type"] in HIGH_RISK_EVENTS and event.get("direction") != "updates_related"
        }
    )
    status = (
        "REVIEW_REQUIRED"
        if high_risk or conflicts
        else "NO_KNOWN_ISSUES_WITH_LIMITATIONS"
        if gaps
        else "NO_KNOWN_ISSUES"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "research-integrity-network",
        "status": status,
        "checked_at": checked_at,
        "query": identifier,
        "work": canonical,
        "identifier_claims": identifier_claims,
        "provider_checks": checks,
        "integrity_events": events,
        "high_risk_events": high_risk,
        "metadata_conflicts": conflicts,
        "coverage_gaps": gaps,
        "version_graph": {"nodes": nodes, "edges": edges},
        "interpretation": "No provider result is exhaustive. Absence of a recorded issue means only that selected checks returned no known issue at the stated time.",
    }


def render_markdown(network: dict[str, Any]) -> str:
    work = network["work"]
    lines = [
        "# Research Integrity Network",
        "",
        f"**Status:** `{network['status']}`  ",
        f"**Checked:** {network['checked_at']}  ",
        f"**Work:** {work.get('title') or network['query']['value']}",
        "",
        network["interpretation"],
        "",
        "## Provider checks",
        "",
        "| Provider | Status | Response SHA-256 | Limitation |",
        "|---|---|---|---|",
    ]
    for check in network["provider_checks"]:
        lines.append(
            f"| {check['provider']} | {check['status']} | {check['response_sha256'] or '-'} | {check['limitation'].replace('|', '/')} |"
        )
    lines.extend(["", "## Integrity events", ""])
    if network["integrity_events"]:
        lines.extend(
            f"- **{event['type']}** — {event['description'] or 'recorded relation'} ({event['provider']})"
            for event in network["integrity_events"]
        )
    else:
        lines.append("- No selected provider returned a recorded event. This is not proof that no event exists.")
    lines.extend(["", "## Version graph", "", "```mermaid", "flowchart LR"])
    for index, node in enumerate(network["version_graph"]["nodes"]):
        label = str(node["label"]).replace('"', "'")[:80]
        lines.append(f'  N{index}["{label}<br/>{node["role"]}"]')
    node_index = {node["id"]: index for index, node in enumerate(network["version_graph"]["nodes"])}
    for edge in network["version_graph"]["edges"]:
        lines.append(f"  N{node_index[edge['source']]} -->|{edge['relation']}| N{node_index[edge['target']]}")
    lines.extend(["```", "", "## Coverage gaps", ""])
    if network["coverage_gaps"]:
        lines.extend(
            f"- **{gap['provider']} / {gap['status']}:** {gap['limitation']}" for gap in network["coverage_gaps"]
        )
    else:
        lines.append("- No execution gap was recorded; provider-level limitations above still apply.")
    lines.append("")
    return "\n".join(lines)


def render_html(network: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value or ""))

    checks = "".join(
        f"<tr><td>{esc(item['provider'])}</td><td>{esc(item['status'])}</td><td><code>{esc(item['response_sha256'] or '—')}</code></td><td>{esc(item['limitation'])}</td></tr>"
        for item in network["provider_checks"]
    )
    events = (
        "".join(
            f"<li><strong>{esc(item['type'])}</strong> — {esc(item['description'] or 'recorded relation')} <small>{esc(item['provider'])}</small></li>"
            for item in network["integrity_events"]
        )
        or "<li>No selected provider returned a recorded event. This is not proof that no event exists.</li>"
    )
    nodes = {node["id"]: node for node in network["version_graph"]["nodes"]}
    graph = (
        "".join(
            f"<li><code>{esc(nodes[edge['source']]['label'])}</code> —{esc(edge['relation'])}→ <code>{esc(nodes[edge['target']]['label'])}</code> <small>{esc(edge['provider'])}</small></li>"
            for edge in network["version_graph"]["edges"]
        )
        or "<li>No explicit version relation was returned.</li>"
    )
    gaps = (
        "".join(
            f"<li><strong>{esc(item['provider'])} / {esc(item['status'])}</strong>: {esc(item['limitation'])}</li>"
            for item in network["coverage_gaps"]
        )
        or "<li>No execution gap was recorded; provider-level limitations still apply.</li>"
    )
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Research Integrity Network</title><style>body{{font:16px system-ui;max-width:1100px;margin:auto;padding:2rem;line-height:1.5;color:#18212b}}.status{{display:inline-block;padding:.35rem .65rem;border-radius:999px;background:#f3e8ff}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd5df;padding:.55rem;text-align:left;vertical-align:top}}code{{word-break:break-all}}small{{color:#64748b}}</style><main><h1>Research Integrity Network</h1><p class="status">{esc(network["status"])}</p><h2>{esc(network["work"].get("title") or network["query"]["value"])}</h2><p>Checked: {esc(network["checked_at"])}</p><p>{esc(network["interpretation"])}</p><h2>Provider checks</h2><table><thead><tr><th>Provider</th><th>Status</th><th>Response SHA-256</th><th>Limitations</th></tr></thead><tbody>{checks}</tbody></table><h2>Integrity events</h2><ul>{events}</ul><h2>Version relations</h2><ul>{graph}</ul><h2>Coverage gaps</h2><ul>{gaps}</ul></main></html>"""


def _fixtures(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        provider, separator, path = value.partition("=")
        if not separator or provider not in PROVIDERS or provider == "crossmark":
            raise ValueError("fixture must use provider=path for crossref, openalex, or pubmed")
        result[provider] = Path(path)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check one DOI or scholarly identifier")
    check.add_argument("identifier")
    check.add_argument("--provider", action="append", choices=PROVIDERS, default=[])
    check.add_argument("--fixture", action="append", default=[], metavar="PROVIDER=PATH")
    check.add_argument("--checked-at", help="fixed ISO timestamp for deterministic replay")
    check.add_argument("--output-dir", type=Path, default=Path("integrity-network"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        network = run_checks(
            args.identifier,
            providers=args.provider or None,
            fixtures=_fixtures(args.fixture),
            checked_at=args.checked_at,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(args.output_dir / "integrity.json", network)
        (args.output_dir / "integrity.md").write_text(render_markdown(network), encoding="utf-8", newline="\n")
        (args.output_dir / "index.html").write_text(render_html(network), encoding="utf-8", newline="\n")
    except (OSError, ValueError, json.JSONDecodeError, ET.ParseError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"status={network['status']} output={args.output_dir}")
    return 1 if network["high_risk_events"] or network["metadata_conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
