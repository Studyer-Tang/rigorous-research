# Tool routing

Use the unified `rigorous-research` command after installing the project. Direct `python scripts/<tool>.py` execution remains supported for a cloned skill directory and for hosts that load resources without installing the Python package.

| Research need | Unified command | Direct script | Extra requirements |
|---|---|---|---|
| Multi-step investigation | `rigorous-research workspace` | `research_workspace.py` | none |
| Focused claim audit | `rigorous-research case` | `inference_case.py` | none |
| Literature candidates | `rigorous-research literature` | `literature_search.py` | network for live retrieval |
| Exact mathematics | `rigorous-research math` | `math_backend.py` | SymPy; Lean is optional |
| Statistical stress tests | `rigorous-research statistics` | `statistics_backend.py` | none for bundled methods |
| Financial-data vintage | `rigorous-research data` | `finance_data.py` | network for live retrieval |
| Release-gate benchmark | `rigorous-research eval` | `research_eval.py` | none |
| Plan and receipt sealing | `rigorous-research seal` | `research_seal.py` | none |
| Blind review | `rigorous-research review` | `review_protocol.py` | none |
| Repository quality | `rigorous-research quality` | `skill_quality.py` | none |

The unified command is a dispatcher, not a new trust layer. Each subcommand retains its original exit codes, evidence semantics, and authorization boundary. Run `rigorous-research <command> --help` before using an unfamiliar backend.
