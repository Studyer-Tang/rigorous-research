# Research workspace: momentum-factor

- Domain: `statistics`
- Stage: `RELEASED`
- Question: Is the 1993-01 to 2024-12 U.S. monthly momentum-factor mean positive under weak-dependence inference?

## Work plan

| ID | Kind | Status | Task | Dependencies | Acceptance | Deliverable |
|---|---|---|---|---|---|---|
| W001 | definition | DONE | Freeze estimand, sample, and falsifiers | - | Dates, units, HAC lags, block length, seed, and release conditions are fixed before analysis. | artifacts/design.md |
| W002 | analysis | DONE | Download and analyze the fixed momentum sample | W001 | The archive vintage is hashed; all 384 months are present; descriptive, HAC, bootstrap, split, trim, and leave-one-year-out results are emitted. | artifacts/momentum-analysis.json |
| W003 | falsification | DONE | Audit interpretation and unsupported extrapolations | W002 | The audit separates historical mean, weak-dependence inference, tradability, alpha, causality, and persistence. | artifacts/limitations.md |
| W004 | writing | DONE | Calibrate the final verdict | W002, W003 | The verdict follows the predeclared interval and sensitivity gates even if the sample mean is positive. | artifacts/release-note.md |

## Sources

- **S001** `data` supports `C001` — Kenneth R. French Data Library, Momentum Factor (Mom), monthly CSV archive. [https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip]
- **S002** `primary` supports `C001` — Kenneth R. French Data Library, description of the Momentum Factor construction. [https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor.html]

## Reproducible runs

- **R001** task `W002`, return code `0` — Frozen momentum-factor analysis; outputs: artifacts/momentum-analysis.json, artifacts/analysis-summary.md

---

# Inference case: momentum-factor

- Domain: `statistics`
- Verdict: `INCONCLUSIVE`
- Question: Is the 1993-01 to 2024-12 U.S. monthly momentum-factor mean positive under weak-dependence inference?

## Domain contract

| Field | Value |
|---|---|
| `population` | The fixed 384 monthly U.S. Momentum Factor observations from 1993-01 through 2024-12; any superpopulation interpretation is conditional. |
| `sampling_unit` | Calendar month, with serial dependence allowed and addressed by HAC and circular block resampling. |
| `outcome` | Published Kenneth French Momentum Factor monthly return, converted from percent to decimal return. |
| `estimand` | Arithmetic mean monthly factor return over the fixed interval; conditional long-run mean under weak dependence for inference. |
| `identification` | Direct descriptive identification from all published months in the frozen interval; no causal or investability interpretation. |

## Claims

| ID | Status | Statement | Scope | Assumptions |
|---|---|---|---|---|
| C001 | INCONCLUSIVE | The long-run monthly mean of the published U.S. momentum factor is positive over the fixed 1993-01 to 2024-12 evaluation scope. | Fixed 1993-01 to 2024-12 monthly series; long-run interpretation is conditional on weak stationarity and dependence assumptions. | A001, A002 |

## Assumption surface

| ID | Status | Role | Statement | Evidence |
|---|---|---|---|---|
| A001 | JUSTIFIED | measurement | The downloaded provider archive accurately records the published monthly momentum-factor series for the frozen dates. | E001, E002 |
| A002 | CONDITIONAL | inference | A weak-stationarity and weak-dependence approximation makes HAC and circular block-bootstrap intervals meaningful for a long-run mean. | - |

## Falsification checks

| ID | Kind | Outcome | Target | Falsifier | Coverage | Result | Evidence |
|---|---|---|---|---|---|---|---|
| K001 | identification | CLEARED | Whether the frozen observations identify the stated historical arithmetic mean. | Missing months, ambiguous units, an adaptive date window, or substitution of a different factor series. | Every month from 1993-01 through 2024-12, with expected row count 384 and recorded archive vintage. | All 384 frozen months were parsed in declared units and the arithmetic mean is directly identified. | E002, E003 |
| K002 | uncertainty | TRIGGERED | Whether dependence-aware 95% intervals exclude a zero long-run monthly mean. | A nonpositive lower endpoint from either the HAC or circular block-bootstrap interval. | Newey-West with six lags and 10,000 circular 12-month block-bootstrap replications at a fixed seed. | HAC interval [-0.085%, 0.902%] and block-bootstrap interval [-0.117%, 0.856%] both include zero. | E002 |
| K003 | sensitivity | UNRESOLVED | Whether the positive full-period point estimate is stable to predeclared perturbations and time splits. | A nonpositive trimmed or leave-one-year-out mean, or economically material regime reversal. | 1% symmetric trim, removal of five best and worst months, all leave-one-year-out samples, and equal 1993-2008/2009-2024 splits. | Trimmed and leave-one-year-out means remain positive, but the 2009-2024 subperiod mean is -0.097% per month versus 0.913% before 2009. | E002, E004 |
| K004 | leakage | CLEARED | Whether dates, transformations, lag choices, or sensitivity gates were selected using the evaluated result. | A parameter or sample boundary chosen after inspecting the headline estimate. | All analysis parameters are explicit in the frozen executable and design artifact; no model or trading signal is fitted. | The fixed script reproduces the declared design and records the source vintage; no predictive evaluation is claimed. | E003 |

## Evidence

- **E001** `source` `diagnostic` (primary path) — Provider archive and factor-construction documentation. [https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor.html]
- **E002** `numerical-computation` `diagnostic` (primary path) — Frozen analysis with archive hash, HAC inference, block bootstrap, subperiods, trimming, and leave-one-year-out results. [artifacts/momentum-analysis.json]
- **E003** `derivation` `diagnostic` (primary path) — Predeclared estimand, dates, dependence methods, seed, and falsifiers. [artifacts/design.md]
- **E004** `diagnostic` `diagnostic` (primary path) — Firewall separating the historical factor result from alpha, tradability, causality, and persistence. [artifacts/limitations.md]
- **E005** `numerical-computation` `suggestive` (primary path) — Human-readable analysis summary exposing the positive point estimate and nonpositive interval bounds. [artifacts/analysis-summary.md]

## Decision

**INCONCLUSIVE** — The historical point estimate is positive, but both dependence-aware 95% intervals include zero and the post-2008 subperiod mean is negative.

Limitations: The data support a positive fixed-sample arithmetic mean, not a statistically resolved positive long-run mean, future persistence, causal premium, direct tradability, or net alpha.

Reproduction: Run analyze_momentum.py with the frozen arguments recorded in workspace.json; compare the downloaded archive SHA-256 and inspect artifacts/momentum-analysis.json.
