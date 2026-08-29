# Durable state and evidence

Use a managed case for work likely to span several commands, agents, or context windows. The ledger is a compact control plane, not a transcript.

## Case contents

`scripts/research_loop.py init` creates:

```text
<case>/
  case.json       machine-readable source of truth
  journal.jsonl   append-only decisions and state transitions
  report.md       generated human-readable view
  artifacts/      case-owned reproducibility artifacts
```

Keep large datasets and private material outside the case. Record stable locators, access boundaries, and checksums where appropriate.

## Obligations

An obligation is a proposition or deliverable that must be checked. Make it atomic enough that one can say what evidence supports or defeats it. Mark it critical if the final claim fails without it.

Statuses:

- `OPEN`: no adequate evidence;
- `SUPPORTED`: evidence supports the exact obligation;
- `FAILED`: evidence defeats it;
- `NOT_APPLICABLE`: a recorded scope decision makes it irrelevant.

Every `SUPPORTED` or `FAILED` obligation needs at least one linked evidence item. Dependencies must refer to existing obligations and may not self-reference.

## Acceptance criteria

Acceptance criteria are observable end-state tests, not implementation intentions. Examples:

- the exact theorem is proved for the stated coefficient ring;
- all defining relations are checked in the target quotient;
- the test suite collects at least 120 tests and exits zero;
- the checkpoint loads and produces one valid inference;
- every factual paragraph has a primary-source locator.

Mark a criterion passed only with linked evidence.

## Evidence

Evidence kinds are `source`, `proof`, `computation`, `test`, `artifact`, `citation`, `testimony`, and `observation`.

An evidence record contains a concise summary, stable locator, optional SHA-256 checksum, and an independence flag. `independent=true` means the evidence was produced by a materially distinct method or source; explain that distinction in the summary or journal.

Private expert correspondence can clarify intent but does not itself prove a theorem or establish peer review. Numerical or model-generated output must state its logical bridge to the claim.

## Journal

The journal records state changes, not hidden reasoning. Add short entries for:

- target or scope changes;
- new or abandoned interpretations;
- failed branches;
- reviewer decisions;
- detected stalls;
- safety or authority blockers;
- release verdicts.

Never store secrets, raw chain-of-thought, or unnecessary personal data.

## Capability distillation

Use the `distill` command to record a reusable lesson only after a trajectory reveals one. Every lesson needs:

- the reusable decision or method;
- a trigger describing when it applies;
- a scope boundary describing when it should not be generalized;
- linked evidence;
- status `candidate`, `validated`, or `rejected`.

Keep one-run observations as `candidate`. Mark a lesson `validated` only after it succeeds across materially different cases or has a direct proof. Distillation records are proposals for future skill refinement; they do not automatically rewrite this skill or grant new permissions.

## Resume protocol

After interruption or context compaction:

1. validate the ledger;
2. read the generated report and latest journal entries;
3. inspect referenced artifacts that affect the next action;
4. restate the current target and open critical obligations;
5. continue with the smallest decisive test.

Do not reconstruct state from memory when the ledger disagrees.
