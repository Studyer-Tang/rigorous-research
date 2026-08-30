# Quick start

## Choose how to run it

Use the repository directly when installing it as an Agent Skill. Install the Python toolkit when you want the `rigorous-research` command in a terminal.

```text
git clone https://github.com/Studyer-Tang/rigorous-research.git
cd rigorous-research
python -m pip install -e ".[math]"
rigorous-research --help
```

Without installation, replace `rigorous-research workspace` with `python scripts/research_workspace.py`, and similarly for the other tools.

## Create the smallest useful artifact

For one claim, initialize an inference case:

```text
rigorous-research case init cases nonvanishing \
  --domain mathematics \
  --question "Is the specified element nonzero?" \
  --claim "The element is nonzero over K(q)."
```

For a multi-step investigation, initialize a workspace:

```text
rigorous-research workspace init cases factor-audit \
  --domain finance \
  --question "Does the proposed factor survive chronological evaluation?" \
  --claim "The prespecified factor has positive net out-of-sample performance."
```

Run the subcommand with `--help`, add work packages and evidence, and do not set a supported verdict until the relevant release obligations are closed.

## Verify the installation

```text
rigorous-research quality
rigorous-research eval
python -m unittest discover -s tests -v
```

The benchmark includes deliberately corrupted research packets. Passing means the validators accepted the released fixtures and rejected the specified corruptions; it does not establish that arbitrary research claims are true.
