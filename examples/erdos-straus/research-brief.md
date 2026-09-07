# Research workspace: erdos-straus

- Domain: `mathematics`
- Stage: `RELEASED`
- Question: For every integer n >= 2, can 4/n be written as three positive unit fractions?

## Work plan

| ID | Kind | Status | Task | Dependencies | Acceptance | Deliverable |
|---|---|---|---|---|---|---|
| W001 | literature | DONE | Check public statement and open status | - | Record retrieved sources, exact statement, date and coverage limitations | sources/status.md |
| W002 | proof | DONE | Attempt constructive proof and bounded exact search | - | Verify every witness exactly; distinguish universal claim, residue families and finite coverage | REPORT.md |
| W003 | replication | DONE | Independently check arithmetic and audit project weaknesses | - | Reject tampered, missing and out-of-domain witnesses; record unresolved proof obligations | artifacts/independent-check.json |

## Sources

- **S001** `secondary` supports `C001` — T. F. Bloom, Erdos Problem 242, accessed 2026-09-07 [https://www.erdosproblems.com/242]
- **S002** `secondary` supports `C001` — Eric W. Weisstein, Erdos-Straus Conjecture, MathWorld, accessed 2026-09-07 [https://mathworld.wolfram.com/Erdos-StrausConjecture.html]

## Reproducible runs

- **R001** task `W002`, return code `0`, accepted codes `[0]` — Exact distinct unit-fraction search for n=3..10000; outputs: artifacts/finite-search.json
- **R002** task `W003`, return code `0`, accepted codes `[0]` — Independent integer cross-multiplication verification; outputs: artifacts/independent-check.json
- **R003** task `W002`, return code `1`, accepted codes `[0, 1]` — Prespecified one-work-unit budget: expected inconclusive result; outputs: artifacts/budget-limited.json
- **R004** task `W002`, return code `0`, accepted codes `[0]` — Reproduce residue families and exact greedy obstruction; outputs: artifacts/summary.json, artifacts/residue-families.json, artifacts/greedy-obstruction.json, artifacts/greedy-obstruction-check.json

---

# Inference case: erdos-straus

- Domain: `mathematics`
- Recorded verdict: `INCONCLUSIVE` (release requires validation)
- Question: For every integer n >= 2, can 4/n be written as three positive unit fractions?

## Domain contract

| Field | Value |
|---|---|
| `ambient_object` | Positive integer triples x < y < z and integer n >= 3 |
| `coefficient_domain` | Exact rational arithmetic; denominators are positive integers |
| `quantifiers` | For every n >= 3 there exist x < y < z; finite searches do not cover the universal quantifier |
| `equality_semantics` | Literal equality 4xyz = n(xy+xz+yz); no floating-point tolerance |

## Claims

| ID | Status | Statement | Scope | Assumptions |
|---|---|---|---|---|
| C001 | INCONCLUSIVE | For every integer n >= 3 there exist positive integers x < y < z with 4/n = 1/x + 1/y + 1/z. | Distinct-denominator formulation of Erdos Problem 242; all integers n >= 3. | - |

## Assumption surface

| ID | Status | Role | Statement | Evidence |
|---|---|---|---|---|

## Falsification checks

| ID | Kind | Outcome | Target | Falsifier | Coverage | Result | Evidence |
|---|---|---|---|---|---|---|---|
| K001 | typecheck | CLEARED | Positive distinct integer witnesses and exact equality | A nonpositive, repeated, nonintegral denominator or false cross product | Every recorded finite witness; universal translation review remains open | Independent checker confirms all recorded witnesses satisfy their integer domain and equality | E001 |
| K002 | proof | UNRESOLVED | All remaining primes p = 1 mod 24 | A proof step assumes existence for an uncovered prime or silently extrapolates finite data | Four elementary infinite families and a reduction leave this infinite residue class open | The greedy route fails at 49; finite successes and residue families do not establish the universal quantifier | E002 |
| K003 | counterexample | UNRESOLVED | The original distinct-denominator conjecture | An integer n >= 3 with a proof that no positive distinct triple exists | Witness search for n=3..10000 with max_x=64 and shared work budget=1000000 | All finite inputs have witnesses; the infinite complement remains unsearched and unproved | E001 |

## Evidence

- **E001** `exact-computation` `diagnostic` (primary path) — 9998 independently verified finite distinct witnesses; no universal conclusion [artifacts/finite-search.json]
- **E002** `derivation` `diagnostic` (primary path) — Attempted proof routes, exact greedy obstruction, residue families and remaining gap [REPORT.md]
- **E003** `source` `diagnostic` (primary path) — Bounded public-source audit: conjecture still listed open; novelty not claimed [sources/status.md]
- **E004** `exact-computation` `diagnostic` (primary path) — Narrow modular certificate: 4/49 minus 1/13 has no two-unit-fraction completion [artifacts/greedy-obstruction.json]

## Proof obligations

| ID | Derived state | Statement |
|---|---|---|
| P001 | OPEN | Check the original claim's types, domain, quantifiers, assumptions, and scope against the proposed derivation. |
| P002 | BLOCKED | Establish the scoped claim or replace this obligation with an admissible counterexample. |
| P003 | OPEN | Supply an exhaustive argument covering every remaining prime p = 1 mod 24, with positivity, integrality and distinctness. |

REVIEWED is a local human attestation, not a machine proof or authenticated identity. Machine checks cover only the recorded subclaim.

## Decision

**INCONCLUSIVE** — Finite witnesses and elementary residue families verified; no proof or counterexample to the universal conjecture. A narrower greedy proof route is refuted at n=49.

Limitations: No novelty claimed. Existing public computational records are much stronger. Primes p=1 mod24 and prose translation review remain open.

Reproduction: Run python examples/erdos-straus/reproduce.py --output build/erdos-straus-replay and independently verify the generated certificates.
