# Financial research

## Contract fields

Fill:

- `universe`: securities, eligibility rules, exchanges, currencies, and survivorship treatment;
- `clock`: timestamp and calendar governing decisions and executions;
- `information_cutoff`: latest data legally available at each decision time, including publication lags;
- `holding_period`: formation, execution, holding, and rebalance rules;
- `split_policy`: chronological train, validation, test, and any rolling or expanding windows;
- `cost_model`: fees, spread, impact, borrow, financing, taxes, and turnover assumptions;
- `benchmark`: economically relevant passive or factor baseline.

## Required checks for a supported claim

The default finance gate requires cleared checks of kinds:

- `information-set`: every feature and universe decision uses point-in-time available data;
- `cost`: performance survives a documented cost and turnover model;
- `benchmark`: incremental value is measured against a relevant baseline;
- `walk-forward`: selection and evaluation are chronologically separated.

Add `multiple-testing` for searched signals, `capacity` for deployability, `borrow` for shorts, `regime` for stability, and `risk-model` when portfolio construction depends on estimated covariance or exposures.

## Point-in-time reconstruction

For each variable, record observation time, publication time, revision policy, and the first tradable time. Lag fundamentals by actual availability rather than fiscal period end. Use delisted securities and historical constituents when the claim concerns an investable historical universe.

Corporate actions, stale prices, exchange calendars, time zones, and execution conventions can create artificial returns. State how they are handled.

## Backtest design

Separate signal discovery, specification choice, hyperparameter selection, and final evaluation. A single final holdout should not be repeatedly inspected. Prefer walk-forward evaluation with frozen decisions inside each step.

Report turnover, gross and net performance, drawdown, exposure, concentration, tail behavior, and the distribution of period returns. Annualized ratios without path information are insufficient.

## Economic falsifiers

Stress:

- delayed execution and alternative price conventions;
- wider spread and impact assumptions;
- signal decay and rebalance frequency;
- subperiods, markets, sectors, and volatility regimes;
- neutralization and factor exposure;
- capacity and short availability;
- alternative but defensible universe definitions.

Treat a result as exploratory when it emerged from broad search without selection-adjusted inference or untouched evaluation data.

## Claim calibration

“Predictive” requires prospective or faithfully simulated out-of-sample evidence. “Tradable” additionally requires timing and cost realism. “Alpha” requires an explicit benchmark and risk adjustment. “Persistent” requires a time and regime statement, not a full-sample average.
