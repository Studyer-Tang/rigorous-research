# Proof and statistical assurance

Version 1.9 adds explicit proof obligations and independently checked mathematical content. These are bounded checks of recorded artifacts, not a general proof of scientific truth or an authenticated review system.

## Proof obligations

New inference cases use schema 4 and initialize translation `P001` and proof `P002`. To edit or migrate a case, save an object with an `obligations` array and run:

```text
rigorous-research case set-proof cases/my-research/case.json --file proof.json
```

Each node has a unique `P001`-style ID, `target_claim`, `kind`, explicit `statement`, `coverage` (`full` or `partial`), `depends_on`, `assumption_ids`, `operation`, and `side_conditions`. Kinds are `translation`, `domain`, `proof`, `counterexample`, `theorem-application`, and `finite-check`. For a refutation, replace the goal's kind with `counterexample`; a failed identification assumption alone does not refute an effect.

Declare sensitive steps explicitly:

| Operation | Required side-condition key | Targeted falsification |
|---|---|---|
| `division` | `nonzero` | Zero denominator, including before cancellation |
| `matrix-inverse` | `invertible` | Singular or rank-deficient case |
| `limit-interchange` | `interchange_justified` | Failure of domination, uniformity, or the cited theorem |
| `generalization` | `exhaustive_argument` | Untested boundary, dimension, parameter, or quantifier |

The side-condition value names a `domain` node in `depends_on`. These tags are declarations: the software does not discover hidden divisions or quantify prose automatically. Check operation coverage during translation review. Finite-check and partial-coverage nodes cannot close a general proof. For a finite theorem, use a full proof node and explicitly establish exhaustiveness.

For certificate resolution, copy the exact certificate `claim` into `certificate_claim` and its `assumptions` into `certificate_assumptions` (use `{}` when absent). Register the certificate as case evidence, then run `case resolve-proof ... --id P002 --evidence E001 --method certificate`. The checker recomputes its content and checks that its formula and assumptions match the obligation. A valid subclaim still depends on the translation and domain steps.

Translation requires an actual human review of types, quantifiers, original domains, assumptions, scope, and the connection from the proposed subclaim to the headline result. Record that review using `case resolve-proof ... --method review --reviewer ... --note ...` only after it occurs, referencing its evidence file. The reviewer name and note are required values supplied by the reviewer. An AI must never invent them or use another person's identity to close a gate. Review may also resolve a derivation outside the supported machine fragment.

Derived states are `OPEN`, `BLOCKED`, `PARTIAL`, `INVALID`, `REVIEWED`, and `MACHINE_VERIFIED`. The binding includes the claim, domain contract, assumptions, proof graph, and selected evidence record. Changed scope, assumptions, proof steps, or evidence invalidate old resolutions. Dependencies must close before dependent conclusions can close. `REVIEWED` is a self-declared local attestation; it is not an authenticated signature, a checked derivation, or proof of reviewer independence.

## Independent mathematical checking

```text
rigorous-research math sympy-bound --lhs "x**2" --symbol x --lower=-1 --upper 1 --max-depth 1 --output build/bound.json
rigorous-research verify-certificate build/bound.json
```

The second command reconstructs the polynomial from exact nonnegative Bernstein coefficients and requires complete interval coverage without gaps or overlaps. It never calls the producer's certificate routines. Rational identities are recomputed with retained original denominator exclusions. Matrix certificates additionally require `--input matrix.json` with the original matching checksum and use a different determinant algorithm. Counterexamples must reproduce exact values, respect declared assumptions and domains, and, for bounds, lie inside the claimed interval with a negative difference.

Independent results are `ESTABLISHED`, `REFUTED`, `INCONCLUSIVE`, or `INVALID`. Both conclusive mathematical outcomes return exit code 0: callers must inspect the status and its direction. No witness does not prove the original claim. General nonrational symbolic diagnostics are outside this independent checker's supported fragment. Both producer and checker share SymPy and the restricted parser; this is separate verification logic, not a formally verified kernel or fully independent software stack.

Strict SymPy receipts reopen and check mathematical content, including established interval bounds. A fresh checksum cannot make an incorrect certificate valid. A counterexample establishes a refutation, so it cannot pass an `ESTABLISHED` identity receipt by relabeling. Use a counterexample obligation for that direction. Lean compilation remains diagnostic until a named target, its transitive axioms, and pinned imports can be audited; clean source scanning is insufficient.

Copilot runs producer and checker in separate child processes sharing the same per-test deadline. Case and workspace validation recompute locally; direct certificate/receipt checking has size limits but no process timeout. Use Copilot's bounded checks for model-proposed expressions. Neither route proves that the expression represents the research question.

## Statistical applicability

```text
rigorous-research statistical-contract init --method newey-west-mean --claim C001 --output build/contract.json
rigorous-research statistical-contract audit build/contract.json
rigorous-research case set-statistical-contract cases/my-research/case.json --file build/contract.json
```

The initial audit is deliberately `CONDITIONAL`. Fill the estimand/testing `target` and each required condition. `JUSTIFIED` requires a precise statement, a basis (`theorem`, `design`, `implementation`, or `derivation`), an existing `evidence_file` relative to the contract, and `evidence_sha256`. Quote the applicable theorem and explain how the actual design and estimator meet it. Diagnostics and simulations cannot establish universal assumptions. The validator checks declarations and evidence bindings; it does not prove the prose in those files.

| Method | Recorded guarantee | Conditions needing explicit justification |
|---|---|---|
| `student-t-mean` | Finite sample | IID normal sampling, positive variance, fixed sample size, no outcome selection, exact Student-t implementation (including sample size and degrees of freedom) |
| `iid-mean-clt` | Asymptotic | IID sampling, finite positive variance, no outcome selection, valid CLT implementation |
| `newey-west-mean` | Asymptotic | Stationarity, applicable CLT and moment assumptions, valid bandwidth sequence and HAC implementation, no outcome selection |
| `holm` | Finite sample | Valid marginal p-values, prespecified family, Holm implementation; arbitrary dependence allowed |
| `bh` | Finite sample | Valid marginal p-values, prespecified family, independence or appropriate PRDS conditions, BH implementation |

HAC conditions must identify a concrete theorem; “stationary” alone is insufficient. A fixed-lag computation is not evidence for a consistent bandwidth sequence. The built-in IID normal interval estimates its standard error and is not an exact Student-t interval. Installing a contract does not implement a new estimator.

Missing conditions yield `CONDITIONAL`; violations, unsupported guarantee substitutions, or bad evidence bindings yield `INAPPLICABLE` (binding-load errors yield `INVALID`). A successful audit is only `APPLICABLE_UNDER_RECORDED_CONDITIONS`. None of these failures proves an opposite sign, no effect, or a causal effect. Report sensitivity and unresolved conditions explicitly.

Schema 4 `SUPPORTED` statistics and finance releases currently require one of these registered applicable contracts targeting the decision claim. This conservative gate does not yet cover every descriptive, causal, pricing, or statistical method. Keep unsupported work inconclusive or scope a claim to a supported method; do not mislabel a different theorem merely to pass. Schema 3 cases remain readable and retain their older release checks with a warning. `set-proof` explicitly migrates to schema 4; legacy examples are not evidence of passing the new assurance requirements.

## Regression scope

`rigorous-research eval` includes frozen exact proofs and adversarial mutations of coefficients, domains, interval coverage, witnesses, theorem guarantees, and selection assumptions. Statistical fixtures are labeled synthetic and test contract handling, not a real study. Unit tests also check stale dependency graphs, circular proofs, invalid certificate receipts, and the distinction between compilation and formal assurance. Passing these tests demonstrates those bounded behaviors; research quality or model-level improvement requires separate held-out evaluation.
