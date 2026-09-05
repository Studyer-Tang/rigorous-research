# Research workspace workflow

Use a workspace when a question needs literature, several computations, dependent work packages, or a paper-quality output. Use the smaller inference case alone for a short audit.

## Stages and exit conditions

### SCOPING

- Separate the headline claim from nearby stronger claims.
- Fix the mathematical objects or empirical estimand.
- Identify authority, data, privacy, and compute constraints.
- Create work items with observable acceptance conditions and explicit dependencies.

Exit when the question has a stable truth condition and the first executable or literature tasks are ready. If no stable reading exists, open a `specification` check instead of silently repairing the question.

### DISCOVERY

- Search primary sources before surveys and summaries.
- Record citation, stable locator, access date, role, and the claim each source supports.
- Distinguish what a source proves, assumes, computes, or merely conjectures.
- Build competing solution routes and failure tests; do not select a route only because it confirms the initial guess.

Exit when definitions and known results are sourced well enough to avoid rediscovery or a false novelty claim.

### ANALYSIS

- Run exact or statistical computations through `research_workspace.py run` when provenance matters.
- Declare expected outputs and task acceptance conditions before execution.
- Keep raw outputs and hashes. Record data vintage, parameters, seeds, software, and the decision clock where relevant.
- Treat exit code zero as successful execution only. The scientific result is stored in the inference case and may still be `REFUTED` or `INCONCLUSIVE`.

Exit when there is an inspectable candidate derivation or empirical result.

### FALSIFICATION

- Attack types, boundaries, adversarial examples, alternate specifications, leakage, dependence, costs, and selection as appropriate.
- Use an independent route when the result is decisive and the cost is proportionate.
- If a test fails, narrow or change the claim before adding new confirmation exercises.

Exit when all decisive failures are resolved or explicitly reflected in the verdict.

### SYNTHESIS

- Generate the research brief and organize evidence by role.
- State the strongest supported claim and the strongest nearby unsupported claim.
- Check novelty wording against the actual literature search coverage.
- Ensure title, abstract, and public summary do not outrun the evidence.

Exit when another person can reproduce the decisive step without the conversation history.

### RELEASED

Set this stage only after every planned work item is complete and both the workspace and inference case pass release validation. An `INCONCLUSIVE`, `REFUTED`, or `MISSPECIFIED` result may be a valid research release when the negative result itself is correctly evidenced.

## Commands

For a continuation handoff, run `rigorous-research workspace next workspace.json`. Its JSON lists runnable tasks with acceptance conditions, unresolved dependencies, explicit blockers, the most recent failed run, and release-gate gaps. Repair integrity errors before resuming work. Review a failed run before retrying; after a successful run, check acceptance instead of repeating the computation automatically. The proposal is read-only and does not infer that a completed command proves a claim. It does not invent commands or run an unattended research loop.

Command launch failures are recorded with return code 127, the error message, and hashed captures. A retry receives a new run ID; prior failures remain visible and still block strict release under the existing release policy. Non-positive timeouts and invalid workspaces are rejected before execution. This continuation support does not provide process isolation or crash recovery for a forcibly killed parent process.

Initialize both layers:

```text
python scripts/research_workspace.py init cases question-slug \
  --domain mathematics \
  --question "..." \
  --claim "..."
```

Use `task`, `source`, `set-task`, and `set-source` to maintain the plan and literature map. Execute a reproducible local computation with:

```text
python scripts/research_workspace.py run cases/question-slug/workspace.json \
  --task W002 \
  --label "Exact verification" \
  --output artifacts/result.json \
  --complete \
  -- python verify.py --output artifacts/result.json
```

The command runner does not expand the user's authorization. Run only local or external operations already within the requested scope. It records commands and artifacts; it is not a sandbox.

If an artifact is intentionally regenerated, use `rehash-run` and `rehash-evidence` only after reviewing the substantive diff. These commands journal the accepted revision. Never use them merely to silence an unexplained integrity failure.

Resume or release with:

```text
python scripts/research_workspace.py status cases/question-slug/workspace.json
python scripts/research_workspace.py status cases/question-slug/workspace.json --release
python scripts/research_workspace.py brief cases/question-slug/workspace.json
python scripts/research_workspace.py validate cases/question-slug/workspace.json --release
```

When the ledger and conversation disagree after an interruption, trust the validated ledger and inspect the latest artifacts before continuing.
