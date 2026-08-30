## Purpose

Describe the research failure mode, usability problem, or compatibility issue addressed.

## Evidence and tests

- [ ] Changed executable behavior has a regression test.
- [ ] `python scripts/skill_quality.py` passes.
- [ ] `python scripts/research_eval.py` passes.
- [ ] `python -m unittest discover -s tests -v` passes.
- [ ] Ruff format and lint checks pass.

## Research and publication safety

- [ ] No credentials, private data, user-specific paths, or unlicensed datasets are included.
- [ ] Negative and inconclusive outcomes remain representable.
- [ ] Changes to hashes, seals, review packets, or release gates include adversarial tests.
- [ ] New dependencies, network access, licenses, and trust assumptions are documented.
- [ ] `SKILL.md` and package versions were updated if behavior changed.
