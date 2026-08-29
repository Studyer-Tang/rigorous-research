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

Every check records the observation that would defeat the claim. Boundary examples, adversarial data-generating processes, leakage probes, and cost stress tests are designed before a positive conclusion is accepted.

### Evidence-type firewalls

Symbolic, numerical, statistical, and market evidence remain distinct. Moving from one type to another requires a written logical bridge.

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
python scripts/inference_case.py init cases/nonvanishing \
  --domain mathematics \
  --question "Is the specified element nonzero in the exact quotient?" \
  --claim "The element is nonzero over K(q)."

python scripts/inference_case.py validate cases/nonvanishing/case.json
python scripts/inference_case.py report cases/nonvanishing/case.json
```

Run `python scripts/inference_case.py --help` for the commands that add assumptions, checks, evidence, contract fields, and verdicts.

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
tests/                           behavioral tests for every release gate
```

The validator proves that a case is structurally honest about its dependencies. It cannot decide whether a cited theorem is correct, a dataset is trustworthy, or an assumption is scientifically justified; those remain research judgments that must be supported by inspectable evidence.

## Requirements

- Codex for skill use
- Python 3.10+ only for the optional CLI
- No third-party Python packages

## License

MIT. See [LICENSE](LICENSE).
