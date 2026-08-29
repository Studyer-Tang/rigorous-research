# Rigorous Research

An evidence-gated Codex skill for difficult research, mathematical proof, technical investigation, reproduction, and long-horizon implementation.

The skill combines a concise operating protocol with a durable research ledger. It can work as a quick proof auditor, an executor-plus-reviewer loop, or a bounded multi-role research cell. Completion requires evidence, deterministic acceptance checks, and independent review—not a confident final message.

## Why it is different

- The original target is frozen before exploration begins.
- Ambiguous or repaired statements become separate branches.
- Claims and deliverables are decomposed into explicit obligations.
- Evidence is checksummed and linked to the obligations it supports.
- Failed branches and scope changes remain in the journal.
- Test collection, test count, exclusions, and return codes are audited.
- Independent review operates on raw artifacts, not only an executor summary.
- Repeated rounds must produce new evidence or change method.
- Public claims pass a separate scope, novelty, and reproducibility gate.
- Reusable lessons retain triggers, scope boundaries, and supporting evidence instead of silently rewriting the workflow.

This is not an automatic scientist. It is a compact control plane for making AI-assisted work inspectable and hard to overclaim.

## Install

Copy this folder to your Codex skills directory and invoke `$rigorous-research`. Python 3.10 or newer is needed only for the optional ledger tool; the skill instructions themselves have no package dependencies.

## Start a managed case

```text
python scripts/research_loop.py init cases zipper-question \
  --mode proof \
  --objective "Determine whether the exact source-defined element is nonzero"
```

Add an obligation and evidence:

```text
python scripts/research_loop.py obligation cases/zipper-question/case.json \
  --branch LITERAL --statement "The proposed representation descends to the exact quotient"

python scripts/research_loop.py evidence cases/zipper-question/case.json \
  --kind computation --summary "All defining relations verified over the stated ring" \
  --file artifacts/verify_relations.txt --independent
```

Render a readable report and run the release gate:

```text
python scripts/research_loop.py render cases/zipper-question/case.json
python scripts/research_loop.py validate cases/zipper-question/case.json --release
```

The release gate checks record consistency and evidence linkage. It does not certify that a proof is true or that a result is novel.

## Repository layout

```text
SKILL.md                    concise routing and invariants
references/                 guidance loaded only for relevant modes
scripts/research_loop.py    durable case ledger and release gate
assets/                     paper, case-file, and author-email templates
tests/                      standard-library behavioral tests
agents/openai.yaml          Codex interface metadata
```

## Security and privacy

Do not put secrets, private correspondence, unpublished personal data, or proprietary datasets into a public case ledger. Store a description and controlled locator instead. Never expose a local dashboard, service, or remote command channel as part of this skill.

## License

MIT. See [LICENSE](LICENSE).
