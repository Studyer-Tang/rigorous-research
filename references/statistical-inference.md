# Statistical inference

## Contract fields

Fill:

- `population`: target population and time or environment scope;
- `sampling_unit`: unit of observation and dependence structure;
- `outcome`: measured outcome, timing, and transformation;
- `estimand`: the exact population quantity, not only an estimator name;
- `identification`: assumptions and design connecting observed data to the estimand.

Classify the claim as descriptive, associational, predictive, causal, structural, or decision-theoretic. Predictive accuracy does not identify a causal effect, and an unbiased estimator under a model does not show the model holds.

If the outcome, population, or estimand has no stable definition, record a `specification` failure and use `MISSPECIFIED`. If identification fails for a well-defined estimand, the causal effect is generally `INCONCLUSIVE`, not `REFUTED`.

## Required checks for a supported claim

The default statistical gate requires cleared checks of kinds:

- `identification`: the data and assumptions identify the stated estimand;
- `uncertainty`: uncertainty respects the sampling and dependence structure;
- `sensitivity`: the conclusion is tested against plausible modeling choices;
- `leakage`: features, preprocessing, selection, and evaluation do not use forbidden information.

Use `diagnostic`, `simulation`, `placebo`, `negative-control`, or `replication` checks when they address material assumptions.

## Design before estimator

Write the estimand and assignment or sampling mechanism before selecting a model. Distinguish the unit of observation from the unit of randomization and the unit of inference. For clustered, spatial, panel, or time-series data, justify the dependence treatment.

For prediction, freeze the loss, deployment population, horizon, and baseline. Use nested validation when model or hyperparameter selection touches evaluation data.

For causal claims, state consistency, exchangeability or design-based alternative, positivity, interference assumptions, and measurement timing. Test overlap and report the population retained after trimming.

## Uncertainty and multiplicity

Report an interval or calibrated distribution when uncertainty is material. Bootstrap, robust covariance, randomization inference, and Bayesian intervals answer different questions; name the target and conditions.

Account for researcher degrees of freedom, multiple outcomes, model searches, subgroup discovery, and repeated peeking. A nominal p-value after adaptive selection is not a valid confirmatory error rate without adjustment or fresh data.

## Stress tests

Prefer tests that could reverse the decision: alternative outcome definitions, missing-data mechanisms, dependence assumptions, influential observations, functional forms, hyperparameter ranges, and plausible unmeasured confounding. Separate robustness of the estimate from robustness of its interpretation.
