# Literature provider routing

Select providers for coverage rather than querying every service automatically. Search strings are sent to external services, so do not include private participant information, unpublished secrets, credentials, or proprietary text.

| Provider | Prefer when | Important limitation |
|---|---|---|
| Crossref | DOI-centered journal and proceedings metadata | Metadata completeness varies by depositor |
| arXiv | Mathematics, statistics, physics, and computing preprints | A preprint is not the version of record; rate limits can be strict |
| OpenAlex | Broad cross-disciplinary discovery and work-level identifiers | Aggregated metadata can inherit upstream errors |
| Semantic Scholar | Citation-oriented discovery and abstracts across many fields | Unauthenticated requests may be rate-limited |
| PubMed | Biomedical and life-science literature indexed by NCBI | Coverage is domain-specific and summary metadata may omit abstracts or DOI values |

The default search uses Crossref, arXiv, and OpenAlex. Add `--provider semantic-scholar` or `--provider pubmed` when those indexes match the claim; supplying any `--provider` option replaces the default list, so repeat it for multiple providers.

Record the exact query, selected providers, per-provider limit, retrieval time, request URLs, and failures. A zero-result or failed provider is a coverage statement, not evidence that no literature exists. Inspect the primary source and its manifestation status before linking it to a claim.
