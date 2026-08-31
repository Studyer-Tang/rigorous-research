# Research Integrity Network

The integrity command checks one scholarly identifier against separate provider records and preserves what was checked, when it was checked, the response hash, and what remains uncovered.

```text
rigorous-research integrity check 10.1234/example --output-dir build/integrity
```

It writes:

- `integrity.json`: the complete machine-readable network;
- `integrity.md`: provider table, Mermaid version graph, events, and coverage gaps;
- `index.html`: a portable report that can be opened without a server.

DOI, PMID, OpenAlex work IDs, and arXiv IDs are accepted. A provider that cannot use the supplied identifier is recorded as `not_applicable`; it is never silently omitted.

## What the checks mean

| Provider | Automatic coverage | Important limitation |
|---|---|---|
| Crossref | Deposited metadata, update relations, and version relations | Depositor records can be incomplete or delayed |
| OpenAlex | Work identity, DOI/PMID/arXiv identifiers, and `is_retracted` | Aggregated metadata can inherit upstream errors |
| PubMed | Biomedical publication types and linked comments/corrections | Domain-specific indexing can lag publishers |
| Crossmark | Official manual dialog linked from the report | No stable public general-purpose API is assumed |

`NO_KNOWN_ISSUES_WITH_LIMITATIONS` does not mean “confirmed safe.” It means only that the selected automatic checks returned no recorded high-risk event at the stated time. Crossmark remains `manual_required`, and every provider limitation stays in the report.

## Deterministic replay

Tests and auditable investigations can freeze provider responses and replay without live network access:

```text
rigorous-research integrity check 10.1234/example \
  --checked-at 2026-08-31T00:00:00+00:00 \
  --fixture crossref=crossref.json \
  --fixture openalex=openalex.json \
  --fixture pubmed=pubmed.xml \
  --output-dir build/replay
```

The output records SHA-256 for every loaded response. Conflicting titles, years, or DOI identities are emitted as explicit metadata conflicts rather than merged silently.

