#!/usr/bin/env python3
"""Search scholarly metadata providers, deduplicate records, and export a literature matrix."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from research_io import utc_timestamp as timestamp, write_json

CROSSREF = "https://api.crossref.org/works"
ARXIV = "https://export.arxiv.org/api/query"
OPENALEX = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR = "https://api.semanticscholar.org/graph/v1/paper/search"
PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PROVIDERS = ("crossref", "arxiv", "openalex", "semantic-scholar", "pubmed")
ATOM = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}


def request_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "rigorous-research/1.2 (literature audit)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def clean_text(value: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", value or "").split())


def normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    characters = [character if unicodedata.category(character)[:1] in {"L", "N"} else " " for character in normalized]
    return " ".join("".join(characters).split())


def normalize_doi(value: str) -> str:
    lowered = value.strip().casefold()
    lowered = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", lowered)
    return re.sub(r"^doi:\s*", "", lowered)


def arxiv_identifier(value: str) -> str:
    match = re.search(r"arxiv\.org/abs/([^?#]+)", value, re.IGNORECASE)
    identifier = match.group(1) if match else value
    return re.sub(r"v\d+$", "", identifier.strip())


def year_from_parts(*parts: Any) -> int | None:
    for part in parts:
        try:
            value = part["date-parts"][0][0]
            return int(value)
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return None


def parse_crossref(payload: bytes) -> list[dict[str, Any]]:
    data = json.loads(payload.decode("utf-8"))
    records = []
    for item in data.get("message", {}).get("items", []):
        titles = item.get("title") or []
        title = clean_text(titles[0]) if titles else ""
        if not title:
            continue
        authors = []
        for author in item.get("author", []):
            name = " ".join(part for part in (author.get("given", ""), author.get("family", "")) if part).strip()
            if name:
                authors.append(name)
        doi = normalize_doi(item.get("DOI", ""))
        records.append(
            {
                "title": title,
                "authors": authors,
                "year": year_from_parts(
                    item.get("published-print"),
                    item.get("published-online"),
                    item.get("created"),
                ),
                "doi": doi,
                "arxiv_id": "",
                "url": item.get("URL") or (f"https://doi.org/{doi}" if doi else ""),
                "venue": (item.get("container-title") or [""])[0],
                "abstract": clean_text(item.get("abstract", "")),
                "record_type": item.get("type", ""),
                "providers": ["crossref"],
            }
        )
    return records


def parse_arxiv(payload: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    records = []
    for entry in root.findall("a:entry", ATOM):
        title = clean_text(entry.findtext("a:title", default="", namespaces=ATOM))
        if not title:
            continue
        authors = [
            clean_text(node.findtext("a:name", default="", namespaces=ATOM)) for node in entry.findall("a:author", ATOM)
        ]
        published = entry.findtext("a:published", default="", namespaces=ATOM)
        entry_url = entry.findtext("a:id", default="", namespaces=ATOM)
        doi = normalize_doi(entry.findtext("x:doi", default="", namespaces=ATOM))
        categories = [node.attrib.get("term", "") for node in entry.findall("a:category", ATOM)]
        records.append(
            {
                "title": title,
                "authors": [value for value in authors if value],
                "year": int(published[:4]) if re.match(r"^\d{4}", published) else None,
                "doi": doi,
                "arxiv_id": arxiv_identifier(entry_url),
                "url": entry_url,
                "venue": "arXiv" + (f" ({', '.join(categories)})" if categories else ""),
                "abstract": clean_text(entry.findtext("a:summary", default="", namespaces=ATOM)),
                "record_type": "preprint",
                "providers": ["arxiv"],
            }
        )
    return records


def parse_openalex(payload: bytes) -> list[dict[str, Any]]:
    data = json.loads(payload.decode("utf-8"))
    records = []
    for item in data.get("results", []):
        title = clean_text(item.get("display_name") or item.get("title") or "")
        if not title:
            continue
        authors = [
            clean_text(authorship.get("author", {}).get("display_name", ""))
            for authorship in item.get("authorships", [])
        ]
        ids = item.get("ids") or {}
        doi = normalize_doi(item.get("doi") or ids.get("doi") or "")
        primary = item.get("primary_location") or {}
        source = primary.get("source") or {}
        records.append(
            {
                "title": title,
                "authors": [author for author in authors if author],
                "year": item.get("publication_year"),
                "doi": doi,
                "arxiv_id": arxiv_identifier(ids.get("arxiv", "")) if ids.get("arxiv") else "",
                "url": primary.get("landing_page_url") or item.get("id", ""),
                "venue": source.get("display_name", ""),
                "abstract": "",
                "record_type": item.get("type", ""),
                "providers": ["openalex"],
            }
        )
    return records


def parse_semantic_scholar(payload: bytes) -> list[dict[str, Any]]:
    data = json.loads(payload.decode("utf-8"))
    records = []
    for item in data.get("data", []):
        title = clean_text(item.get("title", ""))
        if not title:
            continue
        external = item.get("externalIds") or {}
        arxiv_id = arxiv_identifier(external.get("ArXiv", "")) if external.get("ArXiv") else ""
        records.append(
            {
                "title": title,
                "authors": [
                    clean_text(author.get("name", "")) for author in item.get("authors", []) if author.get("name")
                ],
                "year": item.get("year"),
                "doi": normalize_doi(external.get("DOI", "")),
                "arxiv_id": arxiv_id,
                "url": item.get("url", ""),
                "venue": clean_text(item.get("venue", "")),
                "abstract": clean_text(item.get("abstract", "")),
                "record_type": "scholarly-work",
                "providers": ["semantic-scholar"],
            }
        )
    return records


def pubmed_item(doc: ET.Element, name: str) -> str:
    for item in doc.iter("Item"):
        if item.attrib.get("Name", "").casefold() == name.casefold() and item.text:
            return clean_text(item.text)
    return ""


def parse_pubmed(payload: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    records = []
    for doc in root.findall(".//DocSum"):
        identifier = clean_text(doc.findtext("Id", default=""))
        title = pubmed_item(doc, "Title")
        if not title:
            continue
        author_list = next((item for item in doc.iter("Item") if item.attrib.get("Name") == "AuthorList"), None)
        authors = [] if author_list is None else [clean_text(item.text or "") for item in author_list.findall("Item")]
        publication = pubmed_item(doc, "PubDate") or pubmed_item(doc, "EPubDate")
        year_match = re.search(r"\b(18|19|20|21)\d{2}\b", publication)
        records.append(
            {
                "title": title,
                "authors": [author for author in authors if author],
                "year": int(year_match.group(0)) if year_match else None,
                "doi": normalize_doi(pubmed_item(doc, "doi")),
                "arxiv_id": "",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{identifier}/" if identifier else "",
                "venue": pubmed_item(doc, "FullJournalName") or pubmed_item(doc, "Source"),
                "abstract": "",
                "record_type": pubmed_item(doc, "PubType") or "biomedical-article",
                "providers": ["pubmed"],
            }
        )
    return records


def surname(record: dict[str, Any]) -> str:
    authors = record.get("authors") or []
    return normalize_title(authors[0]).split()[-1] if authors and normalize_title(authors[0]) else ""


def duplicate_reason(left: dict[str, Any], right: dict[str, Any], threshold: float) -> str | None:
    if left.get("doi") and left["doi"] == right.get("doi"):
        return "same-doi"
    if left.get("arxiv_id") and left["arxiv_id"] == right.get("arxiv_id"):
        return "same-arxiv-id"
    left_title = normalize_title(left.get("title", ""))
    right_title = normalize_title(right.get("title", ""))
    years = (left.get("year"), right.get("year"))
    years_compatible = None in years or abs(int(years[0]) - int(years[1])) <= 1
    authors_compatible = bool(surname(left) and surname(left) == surname(right))
    if left_title and left_title == right_title and years_compatible and authors_compatible:
        return "same-title-author-year"
    return None


def review_reason(left: dict[str, Any], right: dict[str, Any], threshold: float) -> str | None:
    left_title = normalize_title(left.get("title", ""))
    right_title = normalize_title(right.get("title", ""))
    if not left_title or not right_title:
        return None
    years = (left.get("year"), right.get("year"))
    years_compatible = None in years or abs(int(years[0]) - int(years[1])) <= 1
    authors_compatible = bool(surname(left) and surname(left) == surname(right))
    if left_title == right_title:
        return "same-title-metadata-conflict"
    similarity = SequenceMatcher(None, left_title, right_title).ratio()
    if years_compatible and authors_compatible and similarity >= threshold:
        return f"fuzzy-title:{similarity:.3f}"
    return None


def merge_records(
    records: list[dict[str, Any]], threshold: float = 0.94
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    unique: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    ordered = sorted(
        enumerate(records, start=1),
        key=lambda item: (
            item[1].get("doi", ""),
            item[1].get("arxiv_id", ""),
            normalize_title(item[1].get("title", "")),
            item[1].get("year") or 0,
            surname(item[1]),
        ),
    )
    for source_index, record in ordered:
        match_index = None
        reason = None
        for index, candidate in enumerate(unique):
            reason = duplicate_reason(record, candidate, threshold)
            if reason:
                match_index = index
                break
        if match_index is None:
            item = dict(record)
            item["merged_from"] = [source_index]
            unique.append(item)
            for candidate_index, candidate in enumerate(unique[:-1]):
                review = review_reason(record, candidate, threshold)
                if review:
                    decisions.append(
                        {
                            "source_record": source_index,
                            "target_record": candidate_index + 1,
                            "reason": review,
                            "disposition": "REVIEW_REQUIRED",
                            "source_title": record.get("title", ""),
                            "target_title": candidate.get("title", ""),
                        }
                    )
                    break
            continue
        target = unique[match_index]
        target["providers"] = sorted(set(target.get("providers", [])) | set(record.get("providers", [])))
        target["merged_from"].append(source_index)
        for field in ("doi", "arxiv_id", "url", "venue", "abstract", "year"):
            if not target.get(field) and record.get(field):
                target[field] = record[field]
        if len(record.get("authors", [])) > len(target.get("authors", [])):
            target["authors"] = record["authors"]
        decisions.append(
            {
                "source_record": source_index,
                "target_record": match_index + 1,
                "reason": reason,
                "disposition": "AUTO_MERGED",
                "source_title": record.get("title", ""),
                "target_title": target.get("title", ""),
            }
        )
    for index, record in enumerate(unique, start=1):
        record["id"] = f"L{index:03d}"
        record["normalized_title"] = normalize_title(record["title"])
    return unique, decisions


def bibtex_key(record: dict[str, Any], used: set[str]) -> str:
    first = surname(record) or "unknown"
    year = record.get("year") or "nd"
    title_words = normalize_title(record.get("title", "")).split()
    word = next((item for item in title_words if len(item) > 3), "work")
    base = re.sub(r"[^a-z0-9]", "", f"{first}{year}{word}")
    key = base
    number = 2
    while key in used:
        key = f"{base}{number}"
        number += 1
    used.add(key)
    return key


def render_bibtex(records: list[dict[str, Any]]) -> str:
    entries = []
    used: set[str] = set()
    for record in records:
        key = bibtex_key(record, used)
        fields = [
            ("title", "{" + record["title"].replace("{", "").replace("}", "") + "}"),
            ("author", " and ".join(record.get("authors", []))),
            ("year", str(record.get("year") or "")),
            ("journal", record.get("venue", "")),
            ("doi", record.get("doi", "")),
            ("eprint", record.get("arxiv_id", "")),
            ("url", record.get("url", "")),
        ]
        body = ",\n".join(f"  {name} = {{{value}}}" for name, value in fields if value)
        entries.append(f"@article{{{key},\n{body}\n}}")
    return "\n\n".join(entries) + ("\n" if entries else "")


def render_markdown(data: dict[str, Any]) -> str:
    auto_merges = sum(item["disposition"] == "AUTO_MERGED" for item in data["dedup_decisions"])
    review_pairs = sum(item["disposition"] == "REVIEW_REQUIRED" for item in data["dedup_decisions"])
    summary = f"Raw records: {data['raw_count']}; unique candidates: {data['unique_count']}; auto-merged: {auto_merges}; review-required pairs: {review_pairs}."
    lines = [
        "# Literature candidate matrix",
        "",
        f"Query: `{data['query']}`",
        "",
        f"Retrieved: {data['retrieved_at']}",
        "",
        summary,
        "",
        "| ID | Year | Title | Authors | DOI / arXiv | Providers | Verification |",
        "|---|---:|---|---|---|---|---|",
    ]
    for record in data["records"]:
        identifier = record.get("doi") or record.get("arxiv_id") or record.get("url")
        authors = ", ".join(record.get("authors", [])[:3])
        if len(record.get("authors", [])) > 3:
            authors += " et al."
        title = record["title"].replace("|", "\\|")
        lines.append(
            f"| {record['id']} | {record.get('year') or '-'} | {title} | {authors or '-'} | "
            f"{identifier or '-'} | {', '.join(record['providers'])} | CANDIDATE |"
        )
    lines.extend(
        [
            "",
            "Candidate metadata is not claim evidence. Inspect the paper, verify the exact contribution and assumptions, then add only relevant primary sources to the research workspace.",
            "",
        ]
    )
    if data.get("request_errors"):
        lines.extend(["## Retrieval gaps", ""])
        for item in data["request_errors"]:
            lines.append(f"- `{item['provider']}` failed: {item['error']}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--provider", action="append", choices=PROVIDERS, default=[])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--fuzzy-threshold", type=float, default=0.94)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--bibtex", type=Path, required=True)
    args = parser.parse_args(argv)
    providers = args.provider or ["crossref", "arxiv", "openalex"]
    if not 1 <= args.limit <= 100:
        parser.error("limit must be between 1 and 100")
    raw_records: list[dict[str, Any]] = []
    requests = []
    request_errors = []
    if "crossref" in providers:
        params = urllib.parse.urlencode(
            {
                "query.bibliographic": args.query,
                "rows": args.limit,
                "select": "DOI,title,author,published-print,published-online,created,URL,type,container-title,abstract",
            }
        )
        url = f"{CROSSREF}?{params}"
        try:
            payload = request_bytes(url)
            parsed = parse_crossref(payload)
            raw_records.extend(parsed)
            requests.append(
                {
                    "provider": "crossref",
                    "url": url,
                    "records": len(parsed),
                    "status": "OK",
                }
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            request_errors.append(
                {
                    "provider": "crossref",
                    "url": url,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    if "arxiv" in providers:
        params = urllib.parse.urlencode(
            {
                "search_query": f"all:{args.query}",
                "start": 0,
                "max_results": args.limit,
                "sortBy": "relevance",
            }
        )
        url = f"{ARXIV}?{params}"
        try:
            payload = request_bytes(url)
            parsed = parse_arxiv(payload)
            raw_records.extend(parsed)
            requests.append(
                {
                    "provider": "arxiv",
                    "url": url,
                    "records": len(parsed),
                    "status": "OK",
                }
            )
        except (OSError, ValueError, ET.ParseError) as exc:
            request_errors.append(
                {
                    "provider": "arxiv",
                    "url": url,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    if "openalex" in providers:
        params = urllib.parse.urlencode({"search": args.query, "per-page": args.limit})
        url = f"{OPENALEX}?{params}"
        try:
            parsed = parse_openalex(request_bytes(url))
            raw_records.extend(parsed)
            requests.append({"provider": "openalex", "url": url, "records": len(parsed), "status": "OK"})
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            request_errors.append({"provider": "openalex", "url": url, "error": f"{type(exc).__name__}: {exc}"})
    if "semantic-scholar" in providers:
        fields = "title,authors,year,externalIds,url,venue,abstract"
        params = urllib.parse.urlencode({"query": args.query, "limit": args.limit, "fields": fields})
        url = f"{SEMANTIC_SCHOLAR}?{params}"
        try:
            parsed = parse_semantic_scholar(request_bytes(url))
            raw_records.extend(parsed)
            requests.append({"provider": "semantic-scholar", "url": url, "records": len(parsed), "status": "OK"})
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            request_errors.append({"provider": "semantic-scholar", "url": url, "error": f"{type(exc).__name__}: {exc}"})
    if "pubmed" in providers:
        search_params = urllib.parse.urlencode(
            {"db": "pubmed", "term": args.query, "retmode": "json", "retmax": args.limit}
        )
        search_url = f"{PUBMED_SEARCH}?{search_params}"
        try:
            search_data = json.loads(request_bytes(search_url).decode("utf-8"))
            identifiers = search_data.get("esearchresult", {}).get("idlist", [])
            if identifiers:
                summary_params = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(identifiers), "retmode": "xml"})
                summary_url = f"{PUBMED_SUMMARY}?{summary_params}"
                parsed = parse_pubmed(request_bytes(summary_url))
            else:
                summary_url = ""
                parsed = []
            raw_records.extend(parsed)
            requests.append(
                {
                    "provider": "pubmed",
                    "url": search_url,
                    "summary_url": summary_url,
                    "records": len(parsed),
                    "status": "OK",
                }
            )
        except (OSError, ValueError, json.JSONDecodeError, ET.ParseError) as exc:
            request_errors.append({"provider": "pubmed", "url": search_url, "error": f"{type(exc).__name__}: {exc}"})
    records, decisions = merge_records(raw_records, args.fuzzy_threshold)
    data = {
        "schema_version": 1,
        "query": args.query,
        "retrieved_at": timestamp(),
        "requests": requests,
        "request_errors": request_errors,
        "fuzzy_threshold": args.fuzzy_threshold,
        "raw_count": len(raw_records),
        "unique_count": len(records),
        "records": records,
        "dedup_decisions": decisions,
        "raw_records": raw_records,
    }
    for path in (args.output, args.markdown, args.bibtex):
        path.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, data)
    args.markdown.write_text(render_markdown(data), encoding="utf-8", newline="\n")
    args.bibtex.write_text(render_bibtex(records), encoding="utf-8", newline="\n")
    print(f"raw={len(raw_records)} unique={len(records)} merged={len(decisions)}")
    return 0 if raw_records else 1


if __name__ == "__main__":
    raise SystemExit(main())
