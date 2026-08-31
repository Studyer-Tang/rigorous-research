# Changelog

All notable changes are recorded here. Versions follow Semantic Versioning for the Python toolkit and compatible `major.minor` metadata in `SKILL.md`.

## Unreleased

## 1.5.0 - 2026-08-31

### Added

- Governed local claim extraction, possible supporting/contradicting evidence recommendations, and scope-overreach warnings.
- Optional Ollama and user-provided OpenAI-compatible model adapters with environment-only secrets and response-field allowlisting.
- Human confirmation receipts requiring a named reviewer, exact quote, and locator for decisive judgments.
- A browser-only governed review panel whose suggestions remain downloadable `AI_DRAFT` records.

### Safety

- Model-supplied verdict fields are discarded and cannot enter a PaperTrail audit.
- AI drafts never modify evidence manifests or create formal judgments.

## 1.4.0 - 2026-08-31

### Added

- A schema-versioned Research Integrity Network for Crossref, OpenAlex, PubMed, and explicit Crossmark manual review.
- Retraction, withdrawal, correction, expression-of-concern, metadata-conflict, and version-relation aggregation.
- Provider check timestamps, response hashes, source URLs, limitations, coverage gaps, and deterministic fixture replay.
- JSON, Markdown/Mermaid, portable HTML, and bilingual browser output.

### Safety

- “No known issue” is explicitly time- and provider-bounded; provider silence is never treated as proof of integrity.
- Crossmark is not presented as automatically covered through an undocumented interface.

## 1.3.0 - 2026-08-31

### Added

- PaperTrail Markdown claim extraction and evidence-manifest validation.
- Self-contained HTML and JSON claim-to-source audits with verdict filters, exact excerpts, source metadata, input hashes, and a reproducibility checklist.
- A privacy-preserving browser playground with paste/file input, live audit preview, JSON/HTML downloads, and no backend requirement.
- Recorded correction/retraction checks, source-version metadata, and explicit version-conflict failures.
- PDF, public-web, and DOI import commands with page hashes, Crossref metadata, response limits, redirect validation, and private-network blocking.
- Reviewer provenance, multi-review conflict detection, AI-assisted draft restrictions, local candidate-claim packets, and claim-to-source evidence graphs.
- English and Simplified Chinese playground localization with automatic language selection, a persistent manual switch, and localized HTML exports.
- A browser PDF evidence workspace with pinned PDF.js loading, page rendering, embedded-text extraction, file hashes, portable selection anchors, and explicit local OCR via pinned Tesseract.js.
- Click-to-select PDF passage cards, with manual drag selection retained as an optional precision control.
- A maintainable PaperTrail frontend split into dedicated HTML, CSS, and JavaScript assets instead of one embedded Python template.
- A worked PaperTrail demo, user guide, behavioral tests, and a manual GitHub Pages publication workflow.

### Safety

- Citation presence never implies source support; absent review remains `UNREVIEWED`.
- Supported, partially supported, and contradicted evidence rows require an exact quote and locator.
- Generated reports escape report content and permit only HTTP(S) source links.
- Browser inputs remain local and are rendered through text-safe DOM operations.
- AI-assisted rows cannot issue decisive verdicts; conflicting human reviews fail consensus visibly.

## 1.2.0 - 2026-08-30

### Added

- Unified `rigorous-research` command with lazy subcommand routing.
- Installable Python package metadata and optional `math` and `dev` dependencies.
- OpenAlex, Semantic Scholar, and PubMed literature metadata adapters.
- Release-gate benchmark with adversarial mutation cases.
- Portable skill-quality validator and regression tests.
- Agent Plugin build artifact, SBOM-enabled releases, CodeQL, Dependabot, and dependency review.
- Contribution, security, quick-start, roadmap, citation, issue, and pull-request documentation.

### Changed

- Skill metadata version is now `1.2`.
- CI tests Python 3.10, 3.11, and 3.12 and builds both Python and Agent Plugin artifacts.

## 1.1.0 - 2026-08-30

- Added repository-level skill validation and open-source publication safeguards.

## 1.0.0 - 2026-08-30

- Initial evidence-gated research workspace, inference contracts, verification backends, sealed plans, and blinded review protocol.
