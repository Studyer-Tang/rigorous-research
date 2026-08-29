---
name: rigorous-research
description: Audit or develop mathematical proofs, statistical analyses, and quantitative-finance studies through explicit assumptions, falsification tests, and domain-specific release gates. Use for theorem checking, counterexamples, estimand and identification design, simulations, empirical finance, factor research, or backtest validation; do not use for ordinary summaries or generic project management.
---

# Rigorous Research

Treat every research result as an **inference contract**: a scoped claim joined to the objects or estimand, assumptions, falsifiers, and evidence that make the conclusion valid. Do not let mathematical proof, statistical estimation, and financial backtesting borrow standards from one another without an explicit bridge.

## Start with the claim class

Classify the requested conclusion before doing substantial work:

- **Mathematics:** identity, bound, existence, uniqueness, classification, construction, or counterexample.
- **Statistics:** descriptive, associational, predictive, causal, structural, or decision-theoretic.
- **Finance:** stylized fact, forecast, factor, strategy, risk estimate, pricing result, or market-design claim.

If the class is ambiguous, state the strongest precise reading you can test and label nearby readings separately. A result for one reading does not transfer automatically.

For a multi-step investigation, initialize a case with `python scripts/inference_case.py init`. Read [references/evidence-contracts.md](references/evidence-contracts.md) before maintaining the case record.

## Build the inference contract

1. Write one falsifiable headline claim with quantifiers, population or universe, time horizon, and parameter domain.
2. Fill the domain contract:
   - mathematics: ambient object, coefficient domain, quantifiers, equality semantics;
   - statistics: population, sampling unit, outcome, estimand, identification route;
   - finance: universe, decision clock, information cutoff, holding period, split policy, cost model, benchmark.
3. List assumptions individually. Mark each `UNTESTED`, `JUSTIFIED`, `CONDITIONAL`, or `VIOLATED` and link its evidence.
4. Design checks that could fail the claim. A check without a concrete falsifier is an activity, not a test.
5. Attach raw evidence and record whether it is logically decisive, diagnostic, or merely suggestive.
6. Issue the narrowest verdict that passes the relevant domain gate.

## Domain routing

- For definitions, quotient objects, representations, limits, exact computation, proof, or counterexamples, read [references/mathematical-claims.md](references/mathematical-claims.md).
- For estimands, identification, uncertainty, diagnostics, simulation, or causal and predictive claims, read [references/statistical-inference.md](references/statistical-inference.md).
- For signals, portfolios, backtests, factor tests, market data, or risk models, read [references/financial-research.md](references/financial-research.md).
- Before presenting a theorem, empirical conclusion, paper, or public result, read [references/release-standards.md](references/release-standards.md).

Load only the references required by the current claim class.

## Work counterexample-first

Before investing in a long proof or model:

- type-check every definition and map;
- test boundary, degenerate, and smallest nontrivial cases;
- search for a minimal counterexample or adversarial data-generating process;
- inspect whether the claimed conclusion survives weakening each assumption;
- in finance, reconstruct the exact information set available at each decision time.

A failed attack is evidence only for the region actually searched. Record its coverage; never call it a proof unless exhaustiveness is established.

## Keep symbolic and empirical evidence separate

Numerical agreement can discover a theorem but does not prove an exact identity without certified bounds or reconstruction. A theorem about an estimator does not establish that an empirical implementation satisfies its assumptions. A profitable backtest does not establish a risk-adjusted opportunity without realistic timing, costs, selection accounting, and out-of-sample evidence.

When one evidence type supports another, write the bridge explicitly.

## Verdicts

Use one verdict per headline claim:

- `SUPPORTED`: the exact claim passes every required domain gate.
- `REFUTED`: a valid contradiction, counterexample, or failed identifying condition defeats it.
- `INCONCLUSIVE`: evidence is informative but at least one decisive gate remains open.
- `MISSPECIFIED`: the claim has no stable truth condition or estimand as written.

Confidence may describe uncertainty inside a supported statistical claim; it never substitutes for an open logical or design obligation.

## Release discipline

Run `python scripts/inference_case.py validate <case.json> --release` for a managed case. This checks contract completeness and evidence linkage, not the substantive truth of the inputs. Recompute the decisive step by a different method when feasible.

Report in this order:

1. verdict and exact scope;
2. claim and domain contract;
3. assumptions that carry the result;
4. decisive falsification attempts and evidence;
5. what remains unsupported;
6. reproducibility instructions.

Do not market a computation as a theorem, a fit statistic as identification, or a backtest as investable performance.
