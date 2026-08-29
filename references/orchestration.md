# Orchestration and independent review

Use additional roles only when separation changes the evidence quality or reduces context contamination.

## Topology selection

### Direct audit

Suitable when the target is bounded, source material is small, the decisive calculation is inspectable, and no substantial implementation is required. The same agent may execute and verify, but must still run an adversarial pass and disclose that review was not independent.

### Execute + review

Default for substantive work. The executor owns edits, calculations, and artifacts. A separate reviewer receives the frozen objective, acceptance criteria, relevant source definitions, diff or proof, raw outputs, and case ledger. The reviewer should not receive a proposed verdict or a persuasive narrative before inspecting the evidence.

### Research cell

Use for multiple independent workstreams or broad source discovery:

- **Scout:** find primary sources, equivalent formulations, prior work, and cheap discriminating tests. It does not decide the theorem or implement the final artifact.
- **Executor:** construct the proof, code, experiment, or reproduction and attach evidence to obligations.
- **Adversarial reviewer:** search for counterexamples, omitted hypotheses, scope drift, test failures, and invalid evidence linkage.
- **Integrator:** reconcile conflicts against primary evidence, update the ledger, and choose the next smallest decisive action.

Bound every role by a concrete deliverable and stopping condition. Parallel roles should investigate separable questions; do not ask several agents the same vague question and count agreement as verification.

## Reviewer packet

Provide:

1. exact objective and non-goals;
2. branch or interpretation under review;
3. acceptance criteria and critical obligations;
4. source locators and frozen inputs;
5. proof, diff, or artifact under review;
6. raw commands, return codes, test counts, and output locators;
7. evidence ledger and unresolved items;
8. requested verdict schema.

Withhold the executor's desired verdict until after the reviewer forms an assessment. A useful reviewer response contains:

- verdict: `accept`, `revise`, or `reject`;
- exact failed obligation or acceptance criterion;
- evidence examined;
- strongest counterexample or failure attempt;
- minimum next action that could change the verdict;
- confidence separately for correctness, scope match, and reproducibility.

## Independence is structural

Review is weak when it reuses the same derivation, code path, cached output, assumptions, or summary. Improve independence through a different representation, implementation, specialization, proof technique, source query, or test generator. A new conversation with the same evidence and reasoning path is not automatically independent.

## Round protocol

Each round should change at least one of:

- an obligation status;
- the evidence set;
- the interpretation map;
- the implementation or proof artifact;
- the method being attempted;
- a verified blocker.

If two rounds have the same goal, action class, output, and unresolved obligations, diagnose the stall before continuing. Change the method, reduce the target, obtain missing evidence, or stop. Do not spend rounds rephrasing the same request.

## User interventions

Treat a new instruction as one of:

- **scope override:** changes objective, non-goals, authority, or acceptance criteria;
- **new workstream:** adds a separable obligation;
- **tactical guidance:** changes only the next action;
- **question/status request:** answer it without corrupting the active objective.

Record scope overrides in the ledger before continuing. Preserve superseded targets instead of editing them out of history.

