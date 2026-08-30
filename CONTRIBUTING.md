# Contributing

Contributions should make research conclusions more reproducible, falsifiable, or easier to audit without weakening an existing release gate.

## Development setup

Python 3.10 or newer is required. The core tools use the standard library; exact-mathematics tests additionally use SymPy.

```text
python -m venv .venv
python -m pip install -e ".[math,dev]"
rigorous-research quality
rigorous-research eval
python -m unittest discover -s tests -v
ruff format --check scripts tests
ruff check scripts tests
```

Run a command with `--help` before changing its behavior. Keep generated research outputs out of the skill directories unless they are intentional, reviewed examples.

## Pull-request expectations

- State the research failure mode or usability problem being addressed.
- Add a regression test for changed executable behavior.
- Preserve negative and inconclusive outcomes; a successful command is not evidence that a claim is supported.
- Keep `SKILL.md` focused on routing and move detailed domain guidance into `references/`.
- Use relative, portable paths. Do not commit credentials, private datasets, user names, or local machine paths.
- Increment `metadata.version` in `SKILL.md` when skill behavior or instructions change.
- Keep `pyproject.toml`, `SKILL.md`, `CITATION.cff`, and the changelog release heading version-aligned.
- Record new optional dependencies and whether they require network access in the README; keep frontmatter within the fields accepted by the bundled Codex validator.

New domain release gates need both a documented inference contract and adversarial tests showing what the gate rejects. Changes to hashing, sealing, blind review, or path containment deserve special review because they affect previously released evidence packets.

## Design provenance

The repository-level validation approach is inspired by the structural contracts used in [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills). This project implements its own smaller, standard-library validator for a single portable skill and retains its independent inference-contract architecture.
