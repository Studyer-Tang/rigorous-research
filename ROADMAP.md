# Roadmap

The roadmap favors stronger evidence and easier independent reproduction over adding broad but weak automation.

## Current release: 1.2

- One installable CLI for cases, workspaces, literature, mathematics, statistics, data, sealing, review, evaluation, and repository quality.
- Five literature metadata providers with conservative deduplication and visible retrieval gaps.
- Positive release fixtures and adversarial release-gate mutations.
- Python 3.10-3.12 CI, Agent Plugin packaging, SBOM generation, provenance attestation, and security scanning.

## Next: 1.3

- Promote the initial Crossref DOI enrichment to a schema-versioned, multi-provider integrity pipeline with Crossmark/Retraction Watch checks and deterministic replay fixtures.
- Vendor optional PDF.js/OCR assets for fully offline deployments and add deterministic browser fixtures for scanned documents.
- Bind PaperTrail reviewer provenance to signed portable review receipts and authenticated reviewer identities.
- Add deterministic replay fixtures for every literature provider and explicit retry/backoff records.
- Introduce JSON Schemas for inference cases, workspaces, receipts, review packets, and literature matrices.
- Add signed review identities and optional Sigstore verification for released evidence packets.
- Benchmark larger families of statistical misspecification and financial look-ahead failures.

## Later

- Add pluggable data-provider interfaces without weakening vintage and license requirements.
- Export RO-Crate or a similar interoperable research object while retaining current checksums.
- Expand the manual PaperTrail Pages demo into a documentation and public audit gallery generated entirely from versioned repository content.
- Evaluate additional proof assistants only when their trust model and receipt semantics can be stated precisely.

Items may move when a demonstrated research failure exposes a more important gap. Proprietary data redistribution, automated claims of novelty, unauthenticated high-stakes review, and “successful run means supported result” behavior are explicitly out of scope.
