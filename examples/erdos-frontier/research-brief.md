# Research workspace: erdos-frontier-20260908

- Domain: `mathematics`
- Stage: `RELEASED`
- Question: Attempt the Erdos-Straus conjecture: for every integer n>=3 find positive integers x<y<z with 4/n=1/x+1/y+1/z. Explore first-denominator windows, divisibility and polynomial residue families; do not replace this original goal with a subsidiary result.

## Work plan

| ID | Kind | Status | Task | Dependencies | Acceptance | Deliverable |
|---|---|---|---|---|---|---|
| W001 | definition | DONE | Record sources and exploratory routes | - | Explicit domain, falsifiers, evidence and unresolved original goal | literature/source.json |
| W002 | analysis | DONE | Attack short-window hypotheses | - | Explicit domain, falsifiers, evidence and unresolved original goal | window-summary.json |
| W003 | analysis | DONE | Discover and verify infinite families | - | Explicit domain, falsifiers, evidence and unresolved original goal | family-candidates.json |
| W004 | analysis | DONE | Synthesize proof, limits and architecture evaluation | - | Explicit domain, falsifiers, evidence and unresolved original goal | REPORT.zh-CN.md |

## Sources

- **S001** `primary` supports `C001` — Miguel Angel Lopez, A Complete Congruence System for the Erdos-Straus Conjecture, arXiv:2404.01508v3 (2024). [https://arxiv.org/html/2404.01508v3]

## Reproducible runs

- **R001** task `W003`, return code `0`, accepted codes `[0]` — explore-840-polynomial-families; outputs: family-candidates.json
- **R002** task `W003`, return code `0`, accepted codes `[0]` — expand-polynomial-ansatz; outputs: family-candidates-v2.json
- **R003** task `W002`, return code `0`, accepted codes `[0]` — independent-certificate-and-coverage-summary; outputs: window-summary.json

---

# Inference case: erdos-frontier-20260908

- Domain: `mathematics`
- Recorded verdict: `INCONCLUSIVE` (release requires validation)
- Question: Attempt the Erdos-Straus conjecture: for every integer n>=3 find positive integers x<y<z with 4/n=1/x+1/y+1/z. Explore first-denominator windows, divisibility and polynomial residue families; do not replace this original goal with a subsidiary result.

## Domain contract

| Field | Value |
|---|---|
| `ambient_object` | Positive integer denominators and rational numbers |
| `coefficient_domain` | Z for n,x,y,z; exact equality in Q |
| `quantifiers` | For every integer n>=3, there exist integers 0<x<y<z |
| `equality_semantics` | Exact rational identity 4/n=1/x+1/y+1/z |

## Claims

| ID | Status | Statement | Scope | Assumptions |
|---|---|---|---|---|
| C001 | INCONCLUSIVE | For every integer n>=3 there exist positive integers x<y<z with 4/n=1/x+1/y+1/z. | Original universal distinct-denominator version; restricted windows and polynomial families are subsidiary results. | - |

## Assumption surface

| ID | Status | Role | Statement | Evidence |
|---|---|---|---|---|

## Falsification checks

| ID | Kind | Outcome | Target | Falsifier | Coverage | Result | Evidence |
|---|---|---|---|---|---|---|---|
| K001 | proof | UNRESOLVED | Original universal conjecture | An unproved residue family or missing all-integer argument prevents support. | All n>=3 required; six residue classes remain outside the modular coverage. | No all-integer proof or original-conjecture counterexample. Auxiliary window refutations do not settle the original. | E001 |

## Evidence

- **E001** `derivation` `diagnostic` (primary path) — Scoped research report with written lifting lemma and explicit unresolved original goal. [REPORT.zh-CN.md]
- **E002** `diagnostic` `diagnostic` (primary path) — Independently checked finite windows and partial modular coverage; not decisive for the universal claim. [window-summary.json]

## Proof obligations

| ID | Derived state | Statement |
|---|---|---|
| P001 | OPEN | Check the original claim's types, domain, quantifiers, assumptions, and scope against the proposed derivation. |
| P002 | BLOCKED | Establish the scoped claim or replace this obligation with an admissible counterexample. |

REVIEWED is a local human attestation, not a machine proof or authenticated identity. Machine checks cover only the recorded subclaim.

## Decision

**INCONCLUSIVE** — Finite route counterexamples and partial infinite families do not close the universal quantifier.

Limitations: Six congruence classes remain; no general proof, original counterexample, novelty audit or human review.

Reproduction: From repository root: python examples/erdos-frontier/reproduce.py. Archived actions retain exact claims and evidence.
