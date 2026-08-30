# Rigorous Research

A Codex skill and standard-library research workspace for mathematics, statistics, and quantitative finance.

[![validate](https://github.com/Studyer-Tang/rigorous-research/actions/workflows/ci.yml/badge.svg)](https://github.com/Studyer-Tang/rigorous-research/actions/workflows/ci.yml)

It supports the full path from a vague question to a reproducible research brief:

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

## Two layers

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
- attacks on \(n=1\), \(\rho=\pm1\), row-operation order, hidden division, and finite-versus-general evidence.

The proof is decisive; the two executable computations remain diagnostic. The release gate preserves that distinction.

### U.S. momentum-factor inference — `INCONCLUSIVE`

[`examples/momentum-factor`](examples/momentum-factor/research-brief.md) downloads the Kenneth French monthly Momentum Factor archive and freezes the 1993-01 to 2024-12 sample. It records the data-vintage hash and runs:

- Newey–West inference with six lags;
- 10,000 circular 12-month block-bootstrap replications;
- equal pre/post-2009 subperiods;
- symmetric trimming, removal of extreme months, and every leave-one-year-out sample.

The observed mean is **0.408% per month**, but the HAC \(t\)-statistic is **1.621**; both dependence-aware 95% intervals include zero, and the 2009–2024 mean is **−0.097% per month**. The project therefore releases `INCONCLUSIVE`, despite the positive full-period point estimate. It does not upgrade the result to persistence, causality, tradability, or net alpha.

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

## Outputs

Depending on the question, the skill can produce:

- a sourced research plan and literature evidence matrix;
- a theorem audit, exact computation packet, proof, or counterexample dossier;
- a statistical design with estimand, identification, uncertainty, and sensitivity analysis;
- a point-in-time factor or backtest audit;
- a checksum-linked computation ledger;
- a paper-ready research brief stating the strongest supported and unsupported claims.

It cannot manufacture novelty, verify that a mislabeled artifact is mathematically true, obtain proprietary data, or turn a weak design into identification. Those obligations remain visible rather than hidden behind fluent prose.

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
assets/                            reusable research templates
examples/                          complete released workspaces and small audits
tests/                             behavioral and integrity tests
```

## Requirements

- Codex for skill invocation
- Python 3.10+ for the optional local tools
- no third-party Python packages
- network access only for examples that explicitly download public data

The official Codex skill validator additionally uses PyYAML; it is not a runtime dependency of this project.

## License

MIT. See [LICENSE](LICENSE).
