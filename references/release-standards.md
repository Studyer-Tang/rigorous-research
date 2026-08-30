# Release standards

## Claim ladder

Use the highest supported level:

1. hypothesis or exploratory pattern;
2. reproducible finite computation or descriptive estimate;
3. conditional result under explicit assumptions;
4. supported theorem, statistical conclusion, or out-of-sample financial result;
5. general or practical conclusion beyond the evaluated scope.

Moving upward requires new evidence, not stronger adjectives.

## Minimum release packet

Include:

- exact claim and claim class;
- completed domain contract;
- assumption table with statuses;
- falsification checks and coverage;
- decisive evidence with stable locators;
- methods and environment needed to reproduce it;
- limitations and the strongest nearby unsupported claim.

For a paper or public repository, ensure the title and abstract do not exceed the body. Do not use “proved” for uncertified numerical evidence, “causal” for predictive associations, or “alpha” for an unbenchmarked gross backtest.

## Independent recomputation

For decisive work, prefer a method with a different failure surface:

- a second proof route or independently encoded formal check;
- exact arithmetic versus certified specialization;
- analytic derivation versus simulation;
- a clean-room implementation or independently sourced dataset;
- a preregistered or untouched evaluation period.

Agreement is meaningful only when the methods do not share the same hidden assumptions or code path.

Absence of an independent recomputation should be reported, not concealed. It is a release warning unless the claim itself promises independent replication or a domain-specific standard makes it mandatory.

## Verdict wording

Lead with the verdict and scope. Then state the assumptions that carry it and the strongest attempted falsifier. If a gate remains open, use `INCONCLUSIVE`; do not hide it behind a confidence percentage.

When the claim is refuted, bind the refutation to the exact statement. A failed universal claim may leave useful restricted variants open.
