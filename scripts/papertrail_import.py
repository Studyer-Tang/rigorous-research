#!/usr/bin/env python3
"""Import PDF, web, and DOI sources into review-ready PaperTrail drafts."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from research_io import atomic_write_json, sha256

USER_AGENT = "rigorous-research/1.5 (PaperTrail; https://github.com/Studyer-Tang/rigorous-research)"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
CLAIM_SIGNAL = re.compile(
    r"(?:\d|%|percent|increase|decrease|associated|significant|demonstrat|suggest|show|find|表明|显示|增加|减少|显著|相关)",
    re.IGNORECASE,
)
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?。！？])\s+")


class ArticleTextParser(HTMLParser):
    """Conservatively collect visible prose without running page code."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._title_parts: list[str] = []
        self._parts: list[str] = []
        self._ignored_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "form"}:
            self._ignored_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in {"p", "article", "section", "div", "h1", "h2", "h3", "li", "br"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "form"} and self._ignored_depth:
            self._ignored_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if not self._ignored_depth and not self._in_title:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self._parts.append(value)

    def result(self) -> tuple[str, str]:
        title = re.sub(r"\s+", " ", " ".join(self._title_parts)).strip()
        lines = [re.sub(r"\s+", " ", line).strip() for line in " ".join(self._parts).splitlines()]
        text = "\n\n".join(line for line in lines if len(line) >= 20)
        return title, text


def candidate_claims(text: str, limit: int = 20) -> list[str]:
    """Extract review candidates without presenting them as verified claims."""
    prose_lines = [
        line
        for line in text.replace("\r", "\n").splitlines()
        if not re.match(r"^\s*(?:#{1,6}\s|```|>|[-*+]\s+\[?C[A-Za-z0-9_-]+]?)", line)
    ]
    normalized = re.sub(r"[ \t]+", " ", "\n".join(prose_lines))
    sentences = SENTENCE_BOUNDARY.split(re.sub(r"\n+", " ", normalized))
    signaled = [
        sentence.strip()
        for sentence in sentences
        if 30 <= len(sentence.strip()) <= 500 and CLAIM_SIGNAL.search(sentence)
    ]
    if not signaled:
        signaled = [sentence.strip() for sentence in sentences if 30 <= len(sentence.strip()) <= 500]
    found: list[str] = []
    for sentence in signaled:
        if sentence not in found:
            found.append(sentence)
        if len(found) >= limit:
            break
    return found


def render_imported_markdown(title: str, origin: str, body: str) -> str:
    claims = candidate_claims(body)
    lines = [
        f"# {title or 'Imported document'}",
        "",
        f"> Imported locally from `{origin}`. Candidate claims are drafts and have not been reviewed.",
        "",
        "## Imported text",
        "",
        body.strip(),
        "",
        "## Claims",
        "",
    ]
    lines.extend(f"- [C{index:03d}] {claim}" for index, claim in enumerate(claims, start=1))
    if not claims:
        lines.append("- [C001] No claim candidate was extracted; replace this line during review.")
    return "\n".join(lines).rstrip() + "\n"


def extract_pdf(path: Path) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on optional environment
        raise ValueError("PDF import requires: python -m pip install 'rigorous-research[papertrail]'") from exc
    reader = PdfReader(path)
    title = str((reader.metadata or {}).get("/Title") or path.stem).strip()
    pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        extracted = (page.extract_text() or "").strip()
        if extracted:
            pages.append(f"### Page {index}\n\n{extracted}")
    if not pages:
        raise ValueError("PDF contains no extractable text; scanned PDFs require OCR before import")
    return title, "\n\n".join(pages)


def _public_addresses(hostname: str) -> list[str]:
    addresses = sorted({item[4][0] for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)})
    if not addresses:
        raise ValueError("URL hostname did not resolve")
    for raw in addresses:
        address = ipaddress.ip_address(raw)
        if not address.is_global:
            raise ValueError("URL resolves to a non-public address")
    return addresses


def validate_public_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("URL must be a public HTTP(S) address without embedded credentials")
    _public_addresses(parsed.hostname)
    return value


def fetch_bytes(url: str, accept: str, max_bytes: int = MAX_RESPONSE_BYTES) -> tuple[bytes, str]:
    validate_public_url(url)
    request = Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:  # noqa: S310 - URL is validated against public addresses
        final_url = response.geturl()
        validate_public_url(final_url)
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > max_bytes:
            raise ValueError(f"response exceeds {max_bytes} bytes")
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError(f"response exceeds {max_bytes} bytes")
        charset = response.headers.get_content_charset() or "utf-8"
    return payload, charset


def import_webpage(url: str) -> tuple[str, str]:
    payload, charset = fetch_bytes(url, "text/html,application/xhtml+xml")
    parser = ArticleTextParser()
    parser.feed(payload.decode(charset, errors="replace"))
    title, body = parser.result()
    if not body:
        raise ValueError("web page contains no extractable article text")
    return title or url, body


def normalize_doi(value: str) -> str:
    doi = value.strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
        raise ValueError("invalid DOI")
    return doi


def crossref_source(doi: str, payload: dict[str, Any]) -> dict[str, Any]:
    message = payload.get("message")
    if not isinstance(message, dict):
        raise ValueError("Crossref response has no work message")
    titles = message.get("title") or []
    authors = [
        " ".join(part for part in (str(author.get("given", "")).strip(), str(author.get("family", "")).strip()) if part)
        for author in message.get("author", [])
        if isinstance(author, dict)
    ]
    date_parts = (message.get("published-print") or message.get("published-online") or message.get("issued") or {}).get(
        "date-parts", []
    )
    year = date_parts[0][0] if date_parts and date_parts[0] else None
    updates = message.get("updated-by") or []
    outgoing_updates = message.get("update-to") or []
    update_types = {str(item.get("type", "")).lower() for item in updates if isinstance(item, dict)}
    outgoing_types = {str(item.get("type", "")).lower() for item in outgoing_updates if isinstance(item, dict)}
    if "retraction" in update_types:
        status = "retracted"
    elif "withdrawal" in update_types:
        status = "withdrawn"
    elif update_types:
        status = "corrected"
    else:
        status = "active"
    return {
        "id": re.sub(r"[^a-z0-9]+", "-", doi.lower()).strip("-"),
        "title": str(titles[0] if titles else message.get("container-title", [doi])[0]),
        "authors": [author for author in authors if author],
        "year": year,
        "doi": doi,
        "url": f"https://doi.org/{doi}",
        "publication_status": status,
        "integrity_checked_at": date.today().isoformat(),
        "integrity_url": f"https://api.crossref.org/works/{quote(doi, safe='')}",
        "version": "version of record",
        "version_url": str(message.get("URL") or f"https://doi.org/{doi}"),
        "version_conflict": None,
        "version_notes": "Crossref updates applying to this work: "
        + (", ".join(sorted(update_types)) if update_types else "none recorded")
        + "; this work updates: "
        + (", ".join(sorted(outgoing_types)) if outgoing_types else "none recorded"),
        "data_availability": "unknown",
        "code_availability": "unknown",
        "crossref_type": str(message.get("type") or "unknown"),
    }


def fetch_doi_source(value: str) -> dict[str, Any]:
    doi = normalize_doi(value)
    url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    payload, charset = fetch_bytes(url, "application/json")
    data = json.loads(payload.decode(charset))
    if not isinstance(data, dict):
        raise ValueError("Crossref response root must be an object")
    return crossref_source(doi, data)


def assistance_packet(markdown: str, source_name: str) -> dict[str, Any]:
    claims = candidate_claims(markdown)
    return {
        "schema_version": 1,
        "status": "DRAFT_REQUIRES_HUMAN_REVIEW",
        "method": "local_candidate_extraction",
        "source": source_name,
        "instructions": [
            "Confirm each candidate is actually asserted by the input.",
            "Add citations, exact quotes, and locators before assigning a decisive verdict.",
            "AI-assisted evidence rows must remain UNREVIEWED until a named human reviewer confirms them.",
        ],
        "claims": [
            {"id": f"C{index:03d}", "statement": claim, "citations": [], "status": "UNREVIEWED"}
            for index, claim in enumerate(claims, start=1)
        ],
    }


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    pdf_parser = subparsers.add_parser("pdf", help="extract a text PDF into a Markdown review draft")
    pdf_parser.add_argument("input", type=Path)
    pdf_parser.add_argument("--output", required=True, type=Path)
    web_parser = subparsers.add_parser("url", help="extract a public web page into a Markdown review draft")
    web_parser.add_argument("url")
    web_parser.add_argument("--output", required=True, type=Path)
    doi_parser = subparsers.add_parser("doi", help="resolve DOI and Crossref integrity metadata")
    doi_parser.add_argument("doi")
    doi_parser.add_argument("--output", required=True, type=Path)
    assist_parser = subparsers.add_parser("assist", help="draft candidate claims for mandatory human review")
    assist_parser.add_argument("input", type=Path)
    assist_parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "pdf":
            title, body = extract_pdf(args.input.resolve())
            _write_text(
                args.output, render_imported_markdown(title, f"{args.input.name} (SHA-256 {sha256(args.input)})", body)
            )
        elif args.command == "url":
            title, body = import_webpage(args.url)
            _write_text(args.output, render_imported_markdown(title, args.url, body))
        elif args.command == "doi":
            atomic_write_json(args.output, {"sources": [fetch_doi_source(args.doi)], "evidence": []})
        else:
            markdown = args.input.read_text(encoding="utf-8")
            atomic_write_json(args.output, assistance_packet(markdown, args.input.name))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
