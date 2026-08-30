# Inference case: math-counterexample

- Domain: `mathematics`
- Verdict: `REFUTED`
- Question: Does x^2 >= x hold for every real x?

## Domain contract

| Field | Value |
|---|---|
| `ambient_object` | The ordered field of real numbers R. |
| `coefficient_domain` | Exact rational arithmetic embedded in R. |
| `quantifiers` | For every x in R. |
| `equality_semantics` | The usual exact order relation on R. |

## Claims

| ID | Status | Statement | Scope | Assumptions |
|---|---|---|---|---|
| C001 | REFUTED | For every real x, x^2 >= x. | - | - |

## Assumption surface

| ID | Status | Role | Statement | Evidence |
|---|---|---|---|---|

## Falsification checks

| ID | Kind | Outcome | Target | Falsifier | Coverage | Result | Evidence |
|---|---|---|---|---|---|---|---|
| K001 | counterexample | TRIGGERED | The universal quantifier over all real x. | One admissible real x satisfying x^2 < x. | The exact rational witness x=1/2. | The admissible witness x=1/2 violates the claimed inequality. | E001 |

## Evidence

- **E001** `counterexample` `decisive` (primary path) — Exact substitution gives 1/4 < 1/2 at x=1/2. [artifacts/witness.md]

## Decision

**REFUTED** — One exact admissible witness defeats the universal statement.

Limitations: This does not refute the restricted inequality on x <= 0 or x >= 1.

Reproduction: Substitute x=1/2 and compare 1/4 with 1/2 using exact rational arithmetic.
