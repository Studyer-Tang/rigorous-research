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
