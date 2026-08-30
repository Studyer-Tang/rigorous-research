# Evidence contracts

Use a managed case when the investigation spans several artifacts, computations, or revisions. The case file is a dependency record, not a transcript and not a substitute for judgment.

## Core records

### Claim

A claim contains a stable ID, exact statement, scope, status, linked assumptions, and linked evidence. Split claims when they differ in quantifiers, parameter domains, populations, time periods, or interpretation.

### Assumption

Statuses have distinct meanings:

- `UNTESTED`: required but not yet supported;
- `JUSTIFIED`: backed by evidence appropriate to its role;
- `CONDITIONAL`: imposed transparently rather than empirically established;
- `VIOLATED`: evidence shows the assumption fails in the stated scope.

Conditional assumptions are legitimate in a conditional theorem or analysis. They must appear in the released claim or its immediate scope statement.

### Check

Every check records a target, falsifier, planned coverage, and result summary. Outcomes are:

- `OPEN`: not executed;
- `CLEARED`: the specified falsifier did not occur within documented coverage;
- `TRIGGERED`: the falsifier occurred;
- `UNRESOLVED`: execution was informative but could not decide the check.

`CLEARED` does not mean universally true unless coverage is exhaustive and that exhaustiveness is proved.

### Evidence

Evidence has a kind, role, summary, locator, optional SHA-256 checksum, and independence flag. Roles are `decisive`, `diagnostic`, and `suggestive`. Use the independence flag only for a materially different source, derivation, implementation, or sample—not a second paraphrase of the same work.

### Decision

A decision names one claim, one verdict, decisive evidence, reasoning, limitations, and reproduction instructions. The validator rejects verdicts whose supporting records do not satisfy the domain gate.

## Evidence roles

Distinguish:

- **decisive:** can logically establish or defeat the scoped claim;
- **diagnostic:** tests an assumption or failure mode;
- **suggestive:** motivates a hypothesis but cannot settle it.

State the bridge when evidence moves between roles. For example, modular computation proves nonzero over an integral domain only if the specialization map and exceptional set are controlled. Merely relabeling an artifact as decisive is not such a bridge.

## Reproducibility

For file evidence, use `--file`; the CLI records a checksum. Store raw outputs rather than screenshots when possible. Record software versions, exact commands, seeds, data vintages, and any private-data boundary in an adjacent artifact.

After interruption, validate the case, regenerate its report, inspect the latest evidence files, and continue from open required checks. Do not reconstruct case state from conversation memory when the ledger disagrees.
