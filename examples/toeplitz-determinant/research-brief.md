# Research workspace: toeplitz-determinant

- Domain: `mathematics`
- Stage: `RELEASED`
- Question: For T_n(rho)=(rho^|i-j|), what is det T_n(rho) over Z[rho]?

## Work plan

| ID | Kind | Status | Task | Dependencies | Acceptance | Deliverable |
|---|---|---|---|---|---|---|
| W001 | definition | DONE | Type the matrix and coefficient domain | - | All indices, quantifiers, specializations, and singular parameters are explicit. | artifacts/problem.md |
| W002 | computation | DONE | Expand determinants symbolically for small n | W001 | Leibniz expansion matches the proposed polynomial coefficient-by-coefficient for n=1..7. | artifacts/polynomial-check.json |
| W003 | proof | DONE | Prove the all-n polynomial identity | W001, W002 | A division-free determinant argument closes every n>=1 and includes rho=+-1. | artifacts/proof.md |
| W004 | replication | DONE | Independently recompute exact rational specializations | W003 | A different elimination implementation matches the formula for n=1..12 at seven adversarial rho values. | artifacts/rational-check.json |
| W005 | falsification | DONE | Attack boundaries and proof failure modes | W003, W004 | The audit covers n=1, rho=+-1, row-order dependence, hidden division, and finite-versus-general evidence. | artifacts/falsification.md |
| W006 | writing | DONE | Calibrate and release the result | W005 | The note distinguishes the decisive proof from diagnostic finite computations. | artifacts/release-note.md |

## Sources

- **S001** `primary` supports `C001` — Kac, Murdock, and Szego (1953), On the eigen-values of certain Hermitian forms. [https://doi.org/10.1512/iumj.1953.2.52023]

## Reproducible runs

- **R001** task `W002`, return code `0` — Exact symbolic permutation expansion; outputs: artifacts/polynomial-check.json
- **R002** task `W004`, return code `0` — Independent rational elimination; outputs: artifacts/rational-check.json

---

# Inference case: toeplitz-determinant

- Domain: `mathematics`
- Verdict: `SUPPORTED`
- Question: For T_n(rho)=(rho^|i-j|), what is det T_n(rho) over Z[rho]?

## Domain contract

| Field | Value |
|---|---|
| `ambient_object` | Matrices M_n(Z[rho]) and their determinants in the commutative polynomial ring Z[rho]. |
| `coefficient_domain` | Z[rho], with specialization to an arbitrary commutative ring only after the polynomial identity is proved. |
| `quantifiers` | Every integer n>=1; rho is an indeterminate. No genericity exclusion at rho=+-1. |
| `equality_semantics` | Exact equality of polynomials in Z[rho]. |

## Claims

| ID | Status | Statement | Scope | Assumptions |
|---|---|---|---|---|
| C001 | SUPPORTED | For every integer n>=1, det T_n(rho)=(1-rho^2)^(n-1) in Z[rho]. | - | - |

## Assumption surface

| ID | Status | Role | Statement | Evidence |
|---|---|---|---|---|

## Falsification checks

| ID | Kind | Outcome | Target | Falsifier | Coverage | Result | Evidence |
|---|---|---|---|---|---|---|---|
| K001 | typecheck | CLEARED | The matrix, determinant, coefficient ring, indices, and specializations. | An undefined entry, illegal index, noncommutative determinant step, or excluded specialization. | All definitions in Z[rho], n=1 boundary, and rho=+-1 specializations. | Every operation is defined in Z[rho] and no division excludes singular parameters. | E001, E002 |
| K002 | proof | CLEARED | The all-n determinant identity. | A determinant-changing operation, wrong triangular entries, or an uncovered n. | A symbolic argument for arbitrary n>=1 over Z[rho]. | Descending row operations yield diagonal 1,1-rho^2,...,1-rho^2. | E002 |
| K003 | counterexample | CLEARED | Boundary and adversarial instances of the universal identity. | Any exact polynomial or rational specialization differing from the formula. | Exact polynomials n=1..7 and 84 rational cases through n=12, including rho=0,+-1 and nonintegral values. | No counterexample occurred in the documented exact coverage; the general scope is carried by K002, not finite search. | E003, E004, E005 |
| K004 | exact-computation | CLEARED | Two executable exact-arithmetic implementations. | Coefficient disagreement, rational determinant disagreement, or a failed recorded run. | Leibniz coefficient collection through n=7 and independent rational elimination through n=12. | Both exact implementations returned complete agreement in their declared domains. | E003, E004 |

## Evidence

- **E001** `derivation` `diagnostic` (primary path) — Definition and coefficient-domain audit for the Toeplitz matrix. [artifacts/problem.md]
- **E002** `derivation` `decisive` (primary path) — Division-free descending row operations triangularize T_n for every n. [artifacts/proof.md]
- **E003** `exact-computation` `diagnostic` (primary path) — Exact Leibniz expansion matches polynomial coefficients for n=1..7. [artifacts/polynomial-check.json]
- **E004** `exact-computation` `diagnostic` (independent) — Independent exact-rational elimination matches 84 parameterized cases. [artifacts/rational-check.json]
- **E005** `diagnostic` `diagnostic` (primary path) — Boundary, singular-parameter, row-order, and evidence-scope attacks. [artifacts/falsification.md]

## Decision

**SUPPORTED** — A division-free proof establishes the exact identity for arbitrary n, and an independent exact implementation attacks computational and boundary errors.

Limitations: This is a determinant identity; it does not by itself establish spectral or positive-definiteness claims for all parameter regimes.

Reproduction: Run verify_symbolic.py and verify_rational.py as recorded in workspace.json, then check the descending row operations in artifacts/proof.md.
