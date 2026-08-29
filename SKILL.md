---
name: rigorous-research
description: Run evidence-gated research, mathematical proof, technical investigation, reproduction, or long-horizon implementation from exact objective through independent review and release. Use when a claim or artifact must be checked, iterated, resumed, or published with traceable evidence; do not use for a quick factual answer or ordinary summary.
---

# Rigorous Research

Operate a resumable evidence loop. Optimize for a correct, inspectable outcome rather than activity, persuasive prose, or model agreement.

## Non-negotiable invariants

- Freeze the exact objective, acceptance criteria, scope, and user constraints before expanding the task.
- Treat primary sources, repository state, commands, raw outputs, and reproducible artifacts as evidence. Treat model assertions as hypotheses.
- Separate literal statements from corrections, stable variants, approximations, and inferred author intent. Never transfer a result between them without proof.
- Give each critical claim or deliverable an obligation and attach evidence to that obligation.
- A completion verdict requires all three: critical obligations closed, deterministic checks passed, and independent review accepted.
- Failed tests, zero collected tests, collection errors, timeouts, excluded cases, and unverifiable citations are failures, not partial passes.
- Preserve failed branches and scope changes. Do not rewrite history to make the final route look inevitable.
- Stop safely on missing authority, destructive risk, secrets, external approvals, or exhausted evidence; do not convert these into invented results.

## Choose the smallest sufficient topology

1. **Direct audit:** use one agent for a bounded claim with inspectable evidence.
2. **Execute + review:** use a separate reviewer for substantive proofs, code changes, reproductions, or publication claims.
3. **Research cell:** for broad or long-horizon work, separate scout, executor, adversarial reviewer, and integrator roles. Give each a bounded task and isolated context when subagents are available and authorized.

Do not spawn roles merely to simulate rigor. Independent roles must receive different evidence packets or attack surfaces. For topology, handoffs, and reviewer blindness, read [references/orchestration.md](references/orchestration.md).

## Evidence loop

1. **Frame:** record the exact target, success tests, non-goals, authority boundaries, sources, assumptions, and material interpretations.
2. **Decompose:** create critical obligations and acceptance criteria. Mark dependencies and a concrete falsifier or check for each.
3. **Explore:** search primary sources and run cheap discriminating tests. Record negative results and eliminate weak branches early.
4. **Execute:** perform the next smallest action that can close an obligation or materially change the plan.
5. **Verify:** run deterministic checks; verify that they actually executed the intended cases. Recompute decisive mathematical or computational steps independently when feasible.
6. **Review:** provide the reviewer the frozen target, diff or proof, raw evidence, check results, and unresolved obligations. Do not ask it to validate only the executor's summary.
7. **Decide:** continue, revise, branch, refute, declare ill-posed, or complete. Repeated rounds require new evidence or a changed method.
8. **Distill:** produce a conservative result, reproducibility instructions, limitations, and reusable lessons. Never publish internal chain-of-thought; preserve evidence and decision summaries instead.

For work spanning several actions or turns, initialize a case with `scripts/research_loop.py init`. The case ledger is the source of truth after context compaction. Read [references/state-and-evidence.md](references/state-and-evidence.md) before maintaining a case.

## Domain routing

- Mathematical claims, constructions, quotients, representations, or counterexamples: read [references/mathematical-audit.md](references/mathematical-audit.md).
- Code, experiments, CAS, numerical output, benchmarks, or reproductions: read [references/computational-evidence.md](references/computational-evidence.md) and [references/acceptance-gates.md](references/acceptance-gates.md).
- Openness, novelty, priority, related work, or source interpretation: read [references/literature-and-novelty.md](references/literature-and-novelty.md).
- Papers, abstracts, announcements, expert emails, or public claims: read [references/claim-and-publication.md](references/claim-and-publication.md).
- Full research investigations with several interpretations: also read [references/research-protocol.md](references/research-protocol.md).

## Review verdicts

Use one per interpretation or deliverable:

- `VERIFIED`: all critical obligations and acceptance criteria are supported.
- `REFUTED`: valid evidence defeats the exact target.
- `INCOMPLETE`: meaningful progress exists but a critical obligation remains open.
- `ILL-POSED`: the target lacks a truth condition without additional choices.
- `BLOCKED`: required authority or external input is unavailable after safe alternatives are exhausted.

`BLOCKED` is operational; it does not establish anything about the research claim.

## Completion and reporting

Before declaring completion, run `scripts/research_loop.py validate <case.json> --release` for a managed case. Passing confirms ledger consistency, not truth; the independent reviewer still owns the truth-oriented verdict.

Lead the final response with verdict and exact scope. Then give the decisive evidence, checks actually run, files or artifacts, unresolved limits, and the strongest unsupported nearby claim. Do not advertise an open-problem resolution unless source identity, mathematical correctness, current openness, and novelty are independently supported.

