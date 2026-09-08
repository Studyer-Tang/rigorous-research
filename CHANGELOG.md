# Changelog

All notable changes are recorded here. Versions follow Semantic Versioning for the Python toolkit and compatible `major.minor` metadata in `SKILL.md`.

## Unreleased

## 1.11.0 - 2026-09-08

- Added a shared persistent research-agent kernel with SQLite study records, immutable original objectives, content-addressed numeric assets, proposal validation, process locking, interruption recovery and separate execution/evidence/acceptance states.
- Added a bounded standalone model loop for OpenAI Responses, compatible Chat Completions and Ollama. Failed actions and rejected proposals feed back into subsequent context. Pause, per-action deadlines, model-call budgets and repeated-failure limits prevent unbounded unattended execution.
- Added typed mathematical checks, independent certificate rechecking, dependence-aware statistics, coverage simulation, multiplicity adjustments, opt-in scholarly metadata retrieval and unverified proof/lemma notes. Finish actions deliver reports without declaring research objectives solved.
- Added CLI/Python, real stdio MCP and a loopback research workbench over the same kernel. Plugin builds now include a Codex manifest and MCP configuration alongside the generic Agent Plugin layout; installation remains explicit.
- Added bilingual runtime documentation and reproducible offline mathematics/statistics loops with real tool execution. Added adversarial runtime, local model-protocol, HTTP-origin and MCP integration tests. No external-model capability improvement or novel research result is claimed by these tests.

## 1.10.0 - 2026-09-07

- Exercised the toolkit on the publicly open Erdős–Straus conjecture: 9,998 exact distinct witnesses, a checked obstruction to the greedy first-denominator route at 49, four elementary residue families, sourced status, and an explicitly inconclusive original claim. No novelty or larger verification record is claimed.
- Added budgeted, standard-library three-unit-fraction search and a separate integer certificate verifier. Finite quantifiers, positivity, integrality, ordering, distinctness, coverage gaps, and a narrow modular noncompletion argument are checked independently of the producer.
- Added `--output` to independent checking and exact-integer support to strict receipts. Unsupported universal extensions of finite certificates fail validation.
- Workspace runs can explicitly accept documented semantic exit codes with `--accept-returncode`; actual codes remain recorded, scientific verdicts remain separate, and operational failures cannot be accepted this way.
- Added replayable adversarial evaluations, bilingual entry-point documentation, and LF rules for checksummed example artifacts.
- Record run working directories relatively where possible, so a repository-parent working directory does not leak the author's home path into a shared example.

## 1.9.0 - 2026-09-06

### Added

- Schema 4 proof-obligation graphs with domain dependencies, targeted falsification tasks, evidence-bound resolutions, and visible derived states in case/workspace reports and Copilot context.
- Independent exact checking of rational identities, matrix determinants, rational witnesses, and Bernstein interval certificates. Strict SymPy receipt verification recomputes mathematical content, including established bounds.
- Statistical applicability contracts for Student-t means, IID mean CLTs, Newey-West means, Holm, and Benjamini-Hochberg, with checksummed condition evidence and finite-sample/asymptotic separation.
- Adversarial regression cases for forged certificates, omitted domains, interval gaps, false witnesses, inappropriate guarantees, and selection assumptions.

### Changed

- Lean compilation is always diagnostic: compiler success and source scanning do not establish the target theorem or imported axiom closure. Strict established receipts reject these records.
- Schema 3 cases retain legacy validation with a warning. New schema 4 supported statistics/finance cases require a registered applicable statistical contract; unsupported methods remain outside this gate's coverage.
- Proof-graph changes invalidate recorded resolutions. Human reviews are explicitly local attestations, not authenticated identities or machine proofs. Copilot producer and independent checker share a bounded per-test timeout.
- Holm validates the significance level, and mean summaries expose their unverified assumptions and asymptotic limits.

## 1.8.0 - 2026-09-06

### Added

- Exact Bernstein subdivision certificates for one-variable polynomial inequalities on closed rational intervals, with rational counterexamples and explicit inconclusive results.
- Research Copilot context export, offline model-response import, and adapters for OpenAI Responses structured output, compatible chat endpoints, and local Ollama.
- Allowlisted mathematical proposal checks in child processes, with per-test timeouts, stale-workspace rejection, bounded grids, and no automatic claim or task mutation.
- English and Simplified Chinese README entry points and a reproducible offline copilot example.

### Trust boundaries

- Model suggestions remain drafts. A successful subclaim check cannot establish its translation into the original scientific claim.
- Remote requests are explicit, use environment-only keys, reject redirects, and have no automatic paid retries. Adapter validation uses offline replay tests; provider/model compatibility must be checked against the user's endpoint.

## 1.7.0 - 2026-09-05

### Added

- Bounded exact rational counterexample search with reproducible assignments, assumption/domain filtering, and explicit search coverage; no witness remains `INCONCLUSIVE`.
- Read-only `workspace next` JSON proposals for ready tasks, dependency blockers, failed runs, acceptance checks, and release gaps.

### Fixed

- Identity and determinant certificates retain original denominator exclusions after cancellation and keep non-rational simplifications diagnostic.
- Mathematical input is parsed as explicit arithmetic without Python evaluation; undeclared symbols and floating-point literals are rejected with actionable errors.
- Failed command launches produce hashed execution records and preserve retry history; invalid workspaces are rejected before launching a process.
- Workspace validation reports malformed collections, IDs, dependency links, source links, and output lists instead of raising unexpected exceptions.
- Dependency cycle detection uses an iterative traversal so long research plans do not hit Python's recursion limit.

### Changed

- Duplicate workspace IDs are counted in one pass instead of repeatedly scanning each collection.

## 1.6.0 - 2026-08-31

### Added

- A bilingual browser human-review desk that writes decisive evidence judgments back to the local manifest.
- Stable evidence IDs plus append-only create, update, and revoke history events with preserved before/after states.
- Visible AI-recommendation versus human-verdict differences; AI remains unable to confirm a judgment.
- Cross-provider identifier claims, preprint-aware root roles, and domain-coverage `not_found` results with response hashes.
- A redistributable Cartea-Jin-Shi paper experiment with short excerpts, source hash, minimal frozen provider payloads, and no source PDF.
- Playwright acceptance coverage for the full integrity, governed-AI, bilingual, human-confirmation, edit, and revoke workflow.

### Changed

- AI evidence direction is computed from the best-matching passage instead of unrelated text concatenated across a source.
- GitHub Pages now opens with the real preprint experiment while keeping every extracted evidence row `UNREVIEWED`.
- GitHub workflows use the current checkout and CodeQL action generations instead of deprecated Node runtimes.

### Safety

- Decisive audits now require `review_method: human` and reject missing or AI/model/bot-like reviewer identities.
- PubMed non-coverage is distinguished from network/provider failure and cannot invalidate a DOI by implication.

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
