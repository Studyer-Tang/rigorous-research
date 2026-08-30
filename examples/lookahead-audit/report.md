# Inference case: lookahead-audit

- Domain: `finance`
- Verdict: `REFUTED`
- Question: Is the same-day sign strategy tradable under its stated clock?

## Domain contract

| Field | Value |
|---|---|
| `universe` | Any security with consecutive tradable closing prices; no survivorship claim is needed for the timing contradiction. |
| `clock` | The position for the P_(t-1) to P_t interval must be fixed no later than the start of that return interval. |
| `information_cutoff` | Only information observed before P_t is realized may determine the position earning r_t. |
| `holding_period` | One close-to-close interval, from P_(t-1) to P_t. |
| `split_policy` | Not applicable to the logical timing audit; any performance estimate would require chronological evaluation. |
| `cost_model` | Zero costs are granted; the timing contradiction occurs before cost modeling. |
| `benchmark` | Cash with zero return; benchmark choice does not repair unavailable information. |

## Claims

| ID | Status | Statement | Scope | Assumptions |
|---|---|---|---|---|
| C001 | REFUTED | Choosing the sign of day t close-to-close return and earning that same return is a tradable strategy. | - | - |

## Assumption surface

| ID | Status | Role | Statement | Evidence |
|---|---|---|---|---|

## Falsification checks

| ID | Kind | Outcome | Target | Falsifier | Coverage | Result | Evidence |
|---|---|---|---|---|---|---|---|
| K001 | information-set | TRIGGERED | Whether w_t = sign(r_t) is known before the interval return r_t is earned. | The signal requires the terminal price P_t that is only observed after the earning interval. | The algebraic definition r_t = P_t/P_(t-1)-1 for every nonzero price move. | The decision requires future information relative to the claimed holding interval. | E001 |

## Evidence

- **E001** `derivation` `decisive` (primary path) — The strategy uses P_t to choose a position that is credited with the return ending at P_t. [artifacts/timing-proof.md]

## Decision

**REFUTED** — The stated payoff is a look-ahead construction and is not tradable under the stated clock.

Limitations: This refutes only the same-interval implementation; it does not test whether a lagged signal predicts future returns.

Reproduction: Write r_t from P_(t-1) and P_t, note when P_t becomes observable, and compare that time with when w_t must be fixed.
