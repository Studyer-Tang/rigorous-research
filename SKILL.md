---
name: rigorous-research
description: Plan, execute, audit, and package mathematical, statistical, or quantitative-finance research with sourced work plans, reproducible computations, explicit assumptions, falsification tests, and domain release gates. Use for multi-step research, literature-grounded theorem work, counterexamples, estimand design, simulations, empirical studies, factor research, or backtest validation; do not use for ordinary summaries or generic project management.
license: MIT
metadata:
  version: "1.6"
  skill-author: Rigorous Research contributors
---

# Rigorous Research

Treat every research result as an **inference contract**: a scoped claim joined to the objects or estimand, assumptions, falsifiers, and evidence that make the conclusion valid. Build the surrounding investigation as a recoverable research workspace. Do not let mathematical proof, statistical estimation, and financial backtesting borrow standards from one another without an explicit bridge.

## Choose the operating layer

- For a focused claim audit, use `scripts/inference_case.py` and read [references/evidence-contracts.md](references/evidence-contracts.md).
- For research spanning literature, dependent tasks, computations, revisions, or a paper-quality output, use `scripts/research_workspace.py` and read [references/research-workflow.md](references/research-workflow.md). The workspace initializes and validates an inference case inside it.

After installation, the same tools are available through `rigorous-research case ...` and `rigorous-research workspace ...`. For command selection, optional dependencies, and direct-script fallbacks, read [references/tool-routing.md](references/tool-routing.md).

Do not create a managed workspace for a short explanation or an answer that has no persistent artifacts.

For literature retrieval, machine-checkable mathematics, statistical stress tests, financial-data snapshots, sealed plans, or independent review, read [references/verification-backends.md](references/verification-backends.md). Use the supplied scripts instead of inventing an untracked workflow.

## Start with the claim class

Classify the requested conclusion before doing substantial work:

- **Mathematics:** identity, bound, existence, uniqueness, classification, construction, or counterexample.
- **Statistics:** descriptive, associational, predictive, causal, structural, or decision-theoretic.
- **Finance:** stylized fact, forecast, factor, strategy, risk estimate, pricing result, or market-design claim.

If the class is ambiguous, state the strongest precise reading you can test and label nearby readings separately. A result for one reading does not transfer automatically.

Before substantial work, create claim-scoped work packages with acceptance conditions, dependencies, and intended deliverables. Record primary sources and data vintages against the claims they support. A literature search is incomplete evidence until its query and coverage limits are stated.

For confirmatory statistical or financial work, seal the estimand, sample window, exclusions, primary method, sensitivity set, decision rule, and multiplicity family before reading the first result. A post-result design change creates a new exploratory protocol; never silently reseal it as if preregistered.

## Build the inference contract

1. Write one falsifiable headline claim with quantifiers, population or universe, time horizon, and parameter domain.
2. Fill the domain contract:
   - mathematics: ambient object, coefficient domain, quantifiers, equality semantics;
   - statistics: population, sampling unit, outcome, estimand, identification route;
   - finance: universe, decision clock, information cutoff, holding period, split policy, cost model, benchmark.
3. List assumptions individually. Mark each `UNTESTED`, `JUSTIFIED`, `CONDITIONAL`, or `VIOLATED` and link its evidence.
4. Design checks that could fail the claim. Record the intended coverage before execution and the observed result afterward. A check without a concrete falsifier is an activity, not a test.
5. Attach raw evidence and classify its role as `decisive`, `diagnostic`, or `suggestive`.
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

Use a `specification` check only when the claim lacks a stable truth condition: for example, an undefined generator, incompatible domain and codomain, or an unidentified estimand. A false but well-defined claim is `REFUTED`, not `MISSPECIFIED`. A failed assumption blocks support but does not by itself prove the opposite claim.

## Keep symbolic and empirical evidence separate

Numerical agreement can discover a theorem but does not prove an exact identity without certified bounds or reconstruction. A theorem about an estimator does not establish that an empirical implementation satisfies its assumptions. A profitable backtest does not establish a risk-adjusted opportunity without realistic timing, costs, selection accounting, and out-of-sample evidence.

When one evidence type supports another, write the bridge explicitly.

## Use backends conservatively

- Retrieve candidates from Crossref, arXiv, OpenAlex, Semantic Scholar, or PubMed with `literature_search.py`; read [references/literature-providers.md](references/literature-providers.md) when choosing coverage. Merge automatically only on a shared DOI, a shared arXiv identifier, or compatible title-author-year metadata. Send fuzzy and conflicting matches to `REVIEW_REQUIRED`, and preserve provider failures as coverage gaps.
- Use `math_backend.py` for exact polynomial or rational identities and optional Lean compilation. SymPy simplification of a general transcendental expression is diagnostic. A Lean file containing `sorry`, `admit`, or a declared axiom is not a closed proof certificate.
- Bind decisive machine evidence to its inputs, outputs, backend version, command, environment locks, semantic domain, and return code with `research_seal.py`. Changed inputs invalidate the receipt.
- Use `statistics_backend.py` to compare IID and dependence-aware uncertainty, run circular block bootstrap, control Holm or BH multiplicity, and test empirical coverage under prespecified data-generating processes.
- Fetch financial series through `finance_data.py` when an adapter exists. Preserve the raw response, retrieval time, as-of meaning, revision policy, units, calendar, identifiers, adjustments, license, and SHA-256. A latest-revised FRED series is not point-in-time data.
- Use `review_protocol.py` to prepare a blinded packet before requesting independent review. Do not expose the author verdict, check outcomes, or evidence roles. Any author-side artifact change invalidates the review receipt.

## Verdicts

Use one verdict per headline claim:

- `SUPPORTED`: the exact claim passes every required domain gate.
- `REFUTED`: a valid contradiction, counterexample, or failed identifying condition defeats it.
- `INCONCLUSIVE`: evidence is informative but at least one decisive gate remains open.
- `MISSPECIFIED`: the claim has no stable truth condition or estimand as written.

Confidence may describe uncertainty inside a supported statistical claim; it never substitutes for an open logical or design obligation.

## Release discipline

For a focused case, run `python scripts/inference_case.py validate <case.json> --release`. For a multi-step project, complete the work packages, generate a research brief, attach required governance artifacts, set the stage to `RELEASED`, and run `python scripts/research_workspace.py validate <workspace.json> --release`. These checks verify structure, provenance, dependencies, receipt semantics, and evidence linkage. A human derivation still requires mathematical review; no schema can infer truth from prose alone.

A successful program run means the computation executed. It does not mean the hypothesis was supported. Negative and inconclusive results are legitimate releases when their evidence and scope pass the same gate.

Do not issue `SUPPORTED` while any falsifier targeting the same headline claim is triggered. Resolve the contradiction by narrowing the claim, correcting an artifact, or changing the verdict.

Report in this order:

1. verdict and exact scope;
2. claim and domain contract;
3. assumptions that carry the result;
4. decisive falsification attempts and evidence;
5. what remains unsupported;
6. reproducibility instructions.

Do not market a computation as a theorem, a fit statistic as identification, or a backtest as investable performance.
