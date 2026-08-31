# Rigorous Research

A Codex skill and evidence-gated research laboratory for mathematics, statistics, and quantitative finance.

[![validate](https://github.com/Studyer-Tang/rigorous-research/actions/workflows/ci.yml/badge.svg)](https://github.com/Studyer-Tang/rigorous-research/actions/workflows/ci.yml)

The repository has one purpose: make important research claims traceable, testable, and releasable without hiding uncertainty.

There are two user paths:

| Path | Best for | Main entry point |
|---|---|---|
| **PaperTrail** | Anyone checking whether a report's claims are actually supported by its sources | [Public browser playground](https://studyer-tang.github.io/rigorous-research/) or `rigorous-research audit` |
| **Research engine** | Researchers building mathematics, statistics, or quantitative-finance investigations | `rigorous-research workspace` and `rigorous-research case` |

PaperTrail is the public product surface. The research engine is the deeper reproducibility and release-governance layer behind serious investigations. They share evidence rules, hashes, review provenance, and conservative verdicts, but can be used independently.

The research engine supports the full path from a vague question to a reproducible research brief:

```text
scope the claim
    ↓
map sources and work-package dependencies
    ↓
run and hash computations
    ↓
attack assumptions and failure modes
    ↓
calibrate the verdict
    ↓
release a reproducible evidence packet
```

The project does not assume that a completed computation confirms a hypothesis. `SUPPORTED`, `REFUTED`, `INCONCLUSIVE`, and `MISSPECIFIED` are distinct releasable outcomes.

## Core research engine

### Research workspace

`scripts/research_workspace.py` manages a multi-step investigation:

- work packages with dependencies, acceptance conditions, and deliverables;
- papers, datasets, and software sources linked to specific claims;
- locally executed commands with captured output, environment, artifacts, and SHA-256 hashes;
- recovery after interruption through a persistent status ledger;
- a generated research brief combining plan, provenance, results, and verdict;
- release validation that rejects unfinished tasks, failed runs, changed artifacts, and open inference obligations.

### Inference case

`scripts/inference_case.py` governs the scientific conclusion:

- domain-specific contracts for mathematics, statistics, and finance;
- explicit assumptions and their evidence;
- predeclared falsifiers, tested coverage, and observed results;
- decisive, diagnostic, and suggestive evidence roles;
- logical separation between false claims, malformed claims, and unidentified claims;
- calibrated release gates for proofs, statistical inference, and backtests.

The workspace contains an inference case. A short, focused audit can use the inference case by itself.

For code ownership and module boundaries, see [Architecture](docs/architecture.md).

## Verification stack

| Layer | What it does | What it refuses to claim |
|---|---|---|
| Literature | Searches Crossref, arXiv, OpenAlex, Semantic Scholar, and PubMed; deduplicates DOI/arXiv/title-author-year records; exports JSON, Markdown, and BibTeX | A search hit is not evidence, provider overlap is not independent confirmation, and a fuzzy title match is not an automatic duplicate |
| Exact mathematics | Produces conservative SymPy identity/determinant certificates and optional Lean compilation records | General symbolic simplification is not automatically a proof; Lean holes and custom axioms are not closed certificates |
| Statistical inference | Computes IID and Newey-West uncertainty, circular block-bootstrap intervals, Holm/BH corrections, and DGP coverage grids | A standard estimator name does not establish finite-sample validity |
| Financial data | Freezes raw Kenneth French or FRED responses with vintage, schema, units, calendar, adjustments, license, and SHA-256 | Latest-revised data is not point-in-time information |
| Governance | Seals preregistered plans, binds backend receipts to inputs and versions, and creates blind independent-review packets | Self-authored evidence labels and stale review receipts cannot clear a strict release gate |
| PaperTrail | Turns Markdown claims plus exact source excerpts into static HTML and JSON audits | A nearby citation is not treated as support, and missing review stays `UNREVIEWED` |

The strict path is tamper-evident: changing a claim input, dependency lock, certificate, raw data file, author case, or review packet invalidates the corresponding receipt.
Reviewer identity is self-declared locally; high-stakes use still needs an authenticated external identity or signature bound to the receipt hash.

## Audit a report with PaperTrail

PaperTrail is the public-facing claim audit layer. It maps each conclusion to its cited sources, records whether the source supports or contradicts it, exposes publication/data/code metadata, and produces a reproducibility checklist.

```text
rigorous-research audit report.md \
  --manifest evidence.json \
  --output-dir papertrail-site
```

The result is a self-contained `index.html` plus machine-readable `audit.json`; neither needs a backend, database, account, or API key. Decisive assessments require an exact quote and locator. See the [PaperTrail guide](docs/papertrail.md) and [worked demo](examples/papertrail-demo/report.md).

Build the public, browser-only playground locally:

```text
rigorous-research papertrail \
  --output-dir build/papertrail-site \
  --demo-report examples/papertrail-demo/report.md \
  --demo-manifest examples/papertrail-demo/evidence.json
```

Its homepage accepts pasted text or local `.md`, `.json`, and `.pdf` files, audits them inside the browser, and downloads the result as JSON or a standalone HTML report. The PDF workspace renders pages, extracts embedded text, hashes the file, and attaches selected passages to claims as `UNREVIEWED` evidence with page and selection anchors. The English/简体中文 interface follows the browser language by default, can be switched manually, and exports the HTML report in the selected language. The page has no upload endpoint, analytics script, account requirement, or embedded API key.

PDF.js is fetched from a pinned jsDelivr URL only after the user selects a PDF. Optional OCR fetches a pinned Tesseract.js runtime and language data only after the user explicitly requests OCR; the PDF and rendered page stay in the browser. The ordinary Markdown/JSON audit path does not load either dependency.

Import research material before auditing it:

```text
# Text PDF -> Markdown review draft (scanned PDFs need OCR first)
rigorous-research import pdf paper.pdf --output paper-draft.md

# Public webpage -> Markdown review draft
rigorous-research import url https://example.org/article --output article-draft.md

# DOI -> Crossref source metadata and recorded update/retraction status
rigorous-research import doi 10.1234/example --output source.json

# Candidate claim packet; every candidate remains UNREVIEWED
rigorous-research import assist report.md --output assistance.json
```

Install PDF support with `python -m pip install -e ".[papertrail]"`. Public URL import blocks loopback, private, link-local, and reserved network destinations and limits response size. The browser playground may contact Crossref only after an explicit DOI lookup; report and evidence text remain local.

## Why the gates matter

- A finite symbolic pattern cannot silently become an all-parameter theorem.
- Failed identification cannot be presented as evidence for the opposite causal effect.
- A positive sample mean cannot become a resolved long-run premium merely because a program exited successfully.
- A profitable backtest cannot become tradable alpha without timing, costs, benchmark, and chronological evaluation.
- A violated assumption blocks support but does not automatically refute a conditional theorem.
- A supported claim cannot pass while one of its own falsifiers is triggered.

## Substantive worked research

### Parameterized Toeplitz determinant — `SUPPORTED`

[`examples/toeplitz-determinant`](examples/toeplitz-determinant/research-brief.md) studies

\[
T_n(\rho)=(\rho^{|i-j|})_{i,j=1}^n
\]

over \(\mathbb Z[\rho]\). The workspace contains:

- a coefficient-domain and singular-parameter audit;
- an all-\(n\), division-free proof that \(\det T_n(\rho)=(1-\rho^2)^{n-1}\);
- exact Leibniz polynomial expansion through \(n=7\);
- an independent exact-rational elimination implementation covering 84 cases through \(n=12\);
- a SymPy exact-polynomial determinant certificate for the nontrivial \(n=6\) matrix, with a portable receipt binding the matrix, theorem statement, SymPy 1.14 environment lock, command, and output;
- attacks on \(n=1\), \(\rho=\pm1\), row-operation order, hidden division, and finite-versus-general evidence.

The proof is decisive; the two executable computations remain diagnostic. The release gate preserves that distinction.

### U.S. momentum-factor inference — `INCONCLUSIVE`

[`examples/momentum-factor`](examples/momentum-factor/research-brief.md) downloads the Kenneth French monthly Momentum Factor archive and freezes the 1993-01 to 2024-12 sample. It records the data-vintage hash and runs:

- Newey–West inference with six lags;
- 10,000 circular 12-month block-bootstrap replications;
- equal pre/post-2009 subperiods;
- symmetric trimming, removal of extreme months, and every leave-one-year-out sample.

The observed mean is **0.408% per month**, but the HAC \(t\)-statistic is **1.621**; both dependence-aware 95% intervals include zero, and the 2009–2024 mean is **−0.097% per month**. The project therefore releases `INCONCLUSIVE`, despite the positive full-period point estimate. It does not upgrade the result to persistence, causality, tradability, or net alpha.

The exact provider ZIP is now retained as an immutable offline snapshot. Its SHA-256 matches the archive used by the original analysis, and the preregistered estimand, window, inference method, sensitivity family, and decision rule are sealed.

### Dependence and heavy-tail coverage — 30,000 simulated samples

[`examples/dependence-coverage`](examples/dependence-coverage/report.md) tests mean intervals in six preregistered AR(1) data-generating processes. With \(\phi=0.8\), the nominal IID 95% interval covers only **48.58%** of Gaussian cases and **46.36%** of Student-\(t_3\) cases. Eight-lag Newey–West improves coverage to **82.08%** and **81.22%**, respectively, but still misses the nominal target.

This is a deliberately nontrivial negative control: the backend must expose that a familiar correction remains inadequate under strong persistence instead of declaring success because HAC was computed.

The example also contains a live Crossref/arXiv retrieval audit. Crossref returned eight records; conservative deduplication retained seven candidates, auto-merged one exact work-level duplicate, and flagged one metadata pair for review. arXiv rate-limited the request, and that coverage gap is preserved in the literature matrix instead of being hidden.

The smaller [`math-counterexample`](examples/math-counterexample/report.md) and [`lookahead-audit`](examples/lookahead-audit/report.md) cases remain as fast validator examples.

## Start a research workspace

```text
python scripts/research_workspace.py init cases toeplitz-question \
  --domain mathematics \
  --question "What is the determinant of the parameterized matrix?" \
  --claim "The proposed closed form holds for every n."

python scripts/research_workspace.py task cases/toeplitz-question/workspace.json \
  --title "Verify exact small cases" \
  --kind computation \
  --acceptance "Coefficient-by-coefficient equality through n=7" \
  --deliverable artifacts/check.json

python scripts/research_workspace.py run cases/toeplitz-question/workspace.json \
  --task W001 \
  --label "Exact verification" \
  --output artifacts/check.json \
  --complete \
  -- python verify.py --output artifacts/check.json

python scripts/research_workspace.py status cases/toeplitz-question/workspace.json
python scripts/research_workspace.py brief cases/toeplitz-question/workspace.json
```

The command runner records research commands; it is not a sandbox and does not expand the user's authorization.

For a focused audit, initialize only an inference case:

```text
python scripts/inference_case.py init cases nonvanishing \
  --domain mathematics \
  --question "Is the specified element nonzero in the exact quotient?" \
  --claim "The element is nonzero over K(q)."
```

Run either script with `--help` for the complete command set.

## Research backends

```text
# Retrieve and conservatively deduplicate literature
rigorous-research literature --help

# Certify an exact polynomial identity
python scripts/math_backend.py sympy-identity \
  --lhs "(x + 1)**3" --rhs "x**3 + 3*x**2 + 3*x + 1" \
  --symbols x --output certificate.json

# Seal a confirmatory plan before reading results
python scripts/research_seal.py seal-plan \
  --plan plan.json --protocol confirmatory-v1 --output plan-seal.json

# Run an AR(1) finite-sample coverage audit
python scripts/statistics_backend.py coverage \
  --n 120 --phi 0.8 --replications 5000 --hac-lags 8 \
  --innovation student-t3 --seed 20260830 --output coverage.json

# Freeze a replayable public-data vintage
python scripts/finance_data.py fetch --help

# Prepare a packet that hides the author's answer from the reviewer
python scripts/review_protocol.py prepare --help

# Generate a static claim-to-source audit
rigorous-research audit examples/papertrail-demo/report.md \
  --manifest examples/papertrail-demo/evidence.json \
  --output-dir build/papertrail-demo
```

## Outputs

Depending on the question, the skill can produce:

- a sourced research plan and literature evidence matrix;
- a theorem audit, exact computation packet, proof, or counterexample dossier;
- a statistical design with estimand, identification, uncertainty, and sensitivity analysis;
- a point-in-time factor or backtest audit;
- a checksum-linked computation ledger;
- a browsable PaperTrail claim-to-source audit and reproducibility checklist;
- a paper-ready research brief stating the strongest supported and unsupported claims.

It cannot manufacture novelty, infer the truth of an unchecked prose proof, obtain proprietary data, or turn a weak design into identification. Those obligations remain visible rather than hidden behind fluent prose.

## Repository layout

```text
SKILL.md                           skill routing and operating rules
agents/openai.yaml                 Codex interface metadata
references/research-workflow.md    staged research workflow
references/mathematical-claims.md  proof and construction gates
references/statistical-inference.md
references/financial-research.md
references/evidence-contracts.md
references/release-standards.md
scripts/research_workspace.py      planning, sources, runs, recovery, briefs
scripts/inference_case.py          inference ledger and release gates
scripts/research_io.py             shared JSON, hashing, and portable-path primitives
scripts/rigorous_research_cli.py    unified terminal entry point
scripts/papertrail_audit.py         Markdown-to-HTML/JSON claim audit generator
scripts/papertrail_import.py        PDF, public-web, DOI, and candidate-claim imports
scripts/papertrail_web.py           browser-only static playground builder
scripts/literature_search.py       five-provider retrieval and conservative deduplication
scripts/math_backend.py            SymPy certificates and optional Lean checking
scripts/statistics_backend.py      HAC, bootstrap, multiplicity, coverage simulation
scripts/finance_data.py            immutable financial-data snapshots and vintage diffs
scripts/research_seal.py            plan seals and verification receipts
scripts/review_protocol.py         blind packets, review receipts, adjudication
scripts/research_eval.py           release fixtures and adversarial mutations
scripts/skill_quality.py            portable package and privacy checks
scripts/build_plugin.py             Agent Plugin distribution builder
assets/                            reusable research templates
examples/papertrail-demo/          static audit input and evidence manifest
examples/                          complete released workspaces and small audits
evals/                             deterministic release-gate benchmark manifest
tests/                             behavioral and integrity tests
pyproject.toml                     package, CLI, optional dependencies, and Ruff rules
```

## Requirements

- Codex for skill invocation
- Python 3.10+ for the optional local tools
- standard-library core; SymPy is the only optional mathematical dependency
- network access only for examples that explicitly download public data

Install the exact-mathematics backend with `pip install -r requirements-math.txt`. Lean 4 is optional and is invoked only when present; the project never substitutes a simulated formal check.

The official Codex skill validator additionally uses PyYAML; it is not a runtime dependency of this project.

## Install and verify

Install it as an Agent Skill, a Python terminal tool, or both. Standards-compatible hosts can use `npx skills add Studyer-Tang/rigorous-research` or `gh skill install Studyer-Tang/rigorous-research rigorous-research`; confirm the destination with the current host documentation. For a manual Codex installation, clone the repository as one directory under the configured Codex skills path.

The Python toolkit has no mandatory runtime package beyond Python 3.10 for its standard-library core:

```text
git clone https://github.com/Studyer-Tang/rigorous-research.git
cd rigorous-research
python -m pip install -e ".[math]"
rigorous-research quality
rigorous-research eval
python -m unittest discover -s tests -v
```

Install `requirements-math.txt` only when exact SymPy checks are needed. Live literature and financial-data retrieval require network access; validation, workspace management, sealing, and most tests work offline.

`skill_quality.py` enforces the portable package contract before publication: Agent Skills frontmatter and version metadata, local Markdown links, Python syntax, unsafe dynamic execution, likely committed credentials, and user-specific absolute paths. Use `--json` for CI or other machine consumers. `research_eval.py` separately confirms that released examples pass and known corruptions fail.

To build a standards-shaped Agent Plugin without restructuring the source repository:

```text
python scripts/build_plugin.py --output build/agent-plugin --archive dist/rigorous-research-agent-plugin
```

Tagged GitHub releases attach the Python wheel, source archive, Agent Plugin ZIP, dependency SBOM, and GitHub build-provenance attestation. Installing the Agent Plugin ZIP is host-specific; its extracted root contains `plugin.json` and `skills/rigorous-research/SKILL.md`.

See the [quick start](docs/quickstart.md) for a first case, [ROADMAP.md](ROADMAP.md) for planned work, and [CHANGELOG.md](CHANGELOG.md) for version history.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the change protocol, [SECURITY.md](SECURITY.md) for execution and publication trust boundaries, and [CITATION.cff](CITATION.cff) for citation metadata.

## Design relationship to Scientific Agent Skills

This project borrows repository-maintenance ideas from [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills): standards-compatible metadata, progressive disclosure, repository-level structural validation, tests for bundled scripts, and explicit security review. It does not copy that repository's large catalog or replace this project's inference contracts with generic scientific workflows. Both repositories use the MIT license; the implementation here is independent and tailored to one evidence-gated research skill.

## License

MIT. See [LICENSE](LICENSE).
