# Rigorous Research

A Codex skill for mathematical reasoning, statistical inference, and quantitative-finance research.

The project is built around one unit: the **inference contract**. A result is releasable only when its claim, domain, assumptions, falsifiers, and evidence agree. This prevents three common category errors:

- treating a numerical pattern as an exact proof;
- treating model fit as identification;
- treating an in-sample backtest as investable evidence.

## What is new

### Domain-specific contracts

Mathematics, statistics, and finance use different required fields and different release gates. A proof must close type and logical obligations. A statistical result must name its estimand, identification route, uncertainty, and sensitivity. A financial result must reconstruct its information set and survive timing, costs, benchmark, and walk-forward checks.

### Assumption surfaces

Assumptions are first-class records rather than prose hidden in limitations. Each claim declares the assumptions it uses; a violated or unexamined assumption blocks release.

### Falsification before confirmation

Every check records the observation that would defeat the claim, the region actually tested, and the observed result. Boundary examples, adversarial data-generating processes, leakage probes, and cost stress tests are designed before a positive conclusion is accepted. A supported claim cannot pass while one of its own falsifiers is triggered.

### Evidence-type firewalls

Symbolic, numerical, statistical, and market evidence remain distinct. Evidence is labeled decisive, diagnostic, or suggestive, and moving from one role to another requires a written logical bridge.

### Verdict semantics

A violated assumption blocks support but does not automatically refute the claim. A false, well-defined claim is `REFUTED`; a claim without a stable truth condition is `MISSPECIFIED`. These distinctions are enforced by the release gate.

## What it can produce

- a theorem-audit packet with definitions, exact scope, proof obligations, and counterexample coverage;
- a statistical design packet with estimand, identification assumptions, uncertainty, and sensitivity checks;
- a point-in-time backtest audit covering leakage, costs, benchmark choice, and walk-forward evaluation;
- a checksum-linked evidence ledger and a human-readable release report.

The skill organizes, attacks, and audits research. It does not manufacture mathematical truth or turn weak data into identification; decisive artifacts still have to be computed, proved, or sourced.

## Included workflow

```text
Claim class
   ↓
Domain contract
   ↓
Assumption surface
   ↓
Falsification suite
   ↓
Evidence links
   ↓
Domain release gate
```

The optional standard-library CLI stores this structure in a portable JSON case file:

```text
python scripts/inference_case.py init cases nonvanishing \
  --domain mathematics \
  --question "Is the specified element nonzero in the exact quotient?" \
  --claim "The element is nonzero over K(q)."

python scripts/inference_case.py validate cases/nonvanishing/case.json
python scripts/inference_case.py report cases/nonvanishing/case.json --release
```

Run `python scripts/inference_case.py --help` for the commands that add assumptions, checks, evidence, contract fields, and verdicts. Evidence commands require a role; checks require planned coverage and a result summary when closed; decisions require limitations and reproduction instructions.

## Worked audits

- [`examples/math-counterexample`](examples/math-counterexample/report.md) records an exact witness that refutes a universal real inequality without overstating the restricted cases.
- [`examples/lookahead-audit`](examples/lookahead-audit/report.md) shows why a same-interval return-sign strategy is untradable while leaving the genuinely different lagged-signal question open.

Both reports are generated from checksum-linked case files and pass the release validator.

## Repository layout

```text
SKILL.md                         routing and operating rules
references/mathematical-claims.md
references/statistical-inference.md
references/financial-research.md
references/evidence-contracts.md
references/release-standards.md
scripts/inference_case.py        inference-contract ledger and gates
assets/                          domain templates
examples/                        release-validated worked audits
tests/                           behavioral tests for every release gate
```

The validator proves that a case is structurally honest about its dependencies. It cannot decide whether a cited theorem is correct, a dataset is trustworthy, or an assumption is scientifically justified; those remain research judgments that must be supported by inspectable evidence.

## Requirements

- Codex for skill use
- Python 3.10+ only for the optional CLI
- No third-party Python packages

## License

MIT. See [LICENSE](LICENSE).
