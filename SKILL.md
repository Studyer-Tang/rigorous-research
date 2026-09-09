---
name: rigorous-research
description: Plan, execute, audit, and package mathematical, statistical, or quantitative-finance research with sourced work plans, reproducible computations, explicit assumptions, falsification tests, and domain release gates. Use for multi-step research, literature-grounded theorem work, counterexamples, estimand design, simulations, empirical studies, factor research, or backtest validation; do not use for ordinary summaries or generic project management.
license: MIT
metadata:
  version: "1.14"
  skill-author: Rigorous Research contributors
---

# Rigorous Research

Treat every research result as an **inference contract**: a scoped claim joined to the objects or estimand, assumptions, falsifiers, and evidence that make the conclusion valid. Build the surrounding investigation as a recoverable research workspace. Do not let mathematical proof, statistical estimation, and financial backtesting borrow standards from one another without an explicit bridge.

## Choose the operating layer

For persistent autonomous mathematics or statistics research, read [references/research-agent.md](references/research-agent.md).
Use the shared Agent kernel through `research_context` / `research_submit` MCP tools when connected,
or `rigorous-research agent context` / `agent submit` from the CLI. Codex supplies the reasoning;
no separate model key is required in hosted mode. For unattended operation, the user-selected API
model uses the same kernel through `agent run`. Follow the returned action schema and current revision.
Inspect failed results before choosing the next route; keep proof drafts, assumptions and remaining
obligations in notes with references to prior actions. For statistics, record the estimand, sampling
design, identification conditions, multiplicity family and exploratory status before interpreting results.
Use `finish` for an honest current report, never as evidence that the original objective was achieved.
Export exact artifacts and apply the existing case/release gates before closing proof obligations.

- For a focused claim audit, use `scripts/inference_case.py` and read [references/evidence-contracts.md](references/evidence-contracts.md).
- For research spanning literature, dependent tasks, computations, revisions, or a paper-quality output, use `scripts/research_workspace.py` and read [references/research-workflow.md](references/research-workflow.md). The workspace initializes and validates an inference case inside it.

After installation, the same tools are available through `rigorous-research case ...` and `rigorous-research workspace ...`. For command selection, optional dependencies, and direct-script fallbacks, read [references/tool-routing.md](references/tool-routing.md).

When resuming an investigation, use `rigorous-research workspace next workspace.json` to inspect dependency-ready work, failed runs, acceptance conditions, and release gaps. Carry out the applicable next step within the user's scope; the generated proposal does not satisfy acceptance conditions or set a verdict. For rational identities, use `rigorous-research math sympy-counterexample` to search a bounded exact grid before investing in a proof. Preserve the original domain restrictions; a search with no witness remains inconclusive.

For model-assisted research planning, use `rigorous-research copilot prepare` to export a bounded research packet, `copilot advise` to import a chat response or call a user-selected model, and `copilot verify` to check the proposed mathematical subclaims. Read [references/research-copilot.md](references/research-copilot.md) for the response contract, provider setup, and replay workflow. For one-variable polynomial bounds on closed rational intervals, use `math sympy-bound`. Check that the tested expression and interval represent the original claim before promoting any result; a model's translation is an open obligation.

Do not create a managed workspace for a short explanation or an answer that has no persistent artifacts.

For integer existence problems involving three unit fractions, use `rigorous-research egyptian` and read [references/integer-search.md](references/integer-search.md). Declare distinctness and the exact finite input interval, independently check every witness, and keep budget exhaustion inconclusive. When investigating an open conjecture, record its sourced statement and public status, distinguish a failed proof route from a conjecture counterexample, and make no novelty claim without an appropriate literature review.

In Agent mode, use `egyptian`, `egyptian_window`, and `egyptian_scan` for native integer experiments.
Use `egyptian_family` to check explicit integer-polynomial constructions for all nonnegative integer
parameters, including identity, integrality, positivity and ordering. Its coefficient method is sufficient,
not complete. A collection of valid families still requires a separate coverage argument.
For competing routes, record each auxiliary hypothesis, observed failure and next discriminating test;
keep the original conjecture visible when strengthening or abandoning a route. The returned
`research_memory` includes legacy tasks and proof obligations as untrusted context, not accepted evidence.
Use the native `route` action for persistent competing hypotheses, blockers and next tests; its latest
revisions remain visible beyond the recent-action window. `supported` is a planning label, not proof acceptance.

For real polynomial inequalities, read [references/polynomial-proofs.md](references/polynomial-proofs.md).
Use `inequality_search` for feasible rational counterexamples, `polynomial_sos` for automatic quadratic
discovery or supplied weighted-square proofs, and `polynomial_amgm` for supplied AM-GM proofs when a
square decomposition is unavailable. Declare every nonnegative polynomial assumption explicitly.
Failure to find a decomposition does not disprove nonnegativity; finite grids cannot establish it.

For information-theoretic proof routes, read [references/entropy-proofs.md](references/entropy-proofs.md).
`entropy_inequality` checks a rational linear combination of Shannon entropies on one recorded finite
distribution. Its exact integer comparison ignores floating diagnostics; universal quantifiers and
the required coupling marginals must be justified separately. A failed literature request is not an
empty search result. Preserve fielded arXiv queries and inspect primary text before accepting a proof claim.

For proof obligations, independently checked certificates, or statistical theorem applicability, read [references/proof-assurance.md](references/proof-assurance.md). New cases use schema 4: separate translation, domain conditions, and the proof or counterexample; derive closure from evidence rather than model confidence. Declare division, inversion, limit interchange, and generalization operations explicitly. Never invent a human reviewer or record an AI review as human. Leave unproved steps open and continue independently useful research.

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
- Use `math_backend.py` for exact polynomial or rational identities and optional Lean compilation; recheck certificates with `certificate_verifier.py`. SymPy simplification of a general transcendental expression is diagnostic. Lean compilation remains diagnostic until target-theorem identity, transitive axiom dependencies, and the imported environment are verified.
- Bind decisive machine evidence to its inputs, outputs, backend version, command, environment locks, semantic domain, and return code with `research_seal.py`. Changed inputs invalidate the receipt.
- Use `statistics_backend.py` to compare IID and dependence-aware uncertainty, run circular block bootstrap, control Holm or BH multiplicity, and test empirical coverage under prespecified data-generating processes.
- Fetch financial series through `finance_data.py` when an adapter exists. Preserve the raw response, retrieval time, as-of meaning, revision policy, units, calendar, identifiers, adjustments, license, and SHA-256. A latest-revised FRED series is not point-in-time data.
- Use `review_protocol.py` to prepare a blinded packet before requesting independent review. Do not expose the author verdict, check outcomes, or evidence roles. Any author-side artifact change invalidates the review receipt.

## Verdicts

Use one verdict per headline claim:

- `SUPPORTED`: the exact claim passes every required domain gate.
- `REFUTED`: a valid contradiction or counterexample defeats the exact claim; failed identification alone does not refute an effect.
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
