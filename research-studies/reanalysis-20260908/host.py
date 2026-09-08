"""Record proposals authored by the live Codex host; no model replay or decision loop."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from research_agent import Study
from research_io import sha256, write_json


def submit(topic, tool, arguments, rationale, falsifier, evidence=None, timeout=120):
    study = Study(HERE / topic)
    context = study.context()
    proposal = {"action": {"tool": tool, "arguments": arguments}, "rationale": rationale,
                "falsifier": falsifier, "evidence": evidence or []}
    study.event("host_proposal", {"controller": "live Codex host", "external_model_api": False,
                                  "revision": context["state"]["revision"], "tool": tool})
    result = study.submit(proposal, context["state"]["revision"], timeout)
    write_json(HERE / topic / "actions" / f"{result['id']:03d}.json", result)
    body=result['result']
    print(json.dumps({"topic": topic, "id": result["id"], "execution": result["execution"],
                      "status":body.get('status'),"result":body.get('result'),
                      "check":body.get('independent_check'),"error":body.get('error')}, ensure_ascii=False))
    return result


def initialize():
    topics = {
        "erdos": ("mathematics", "Reinvestigate the distinct-denominator Erdos-Straus conjecture for all n>=3; determine exactly when the greedy first denominator works on n=1 mod 24, without confusing a failed route with a counterexample to the conjecture."),
        "statistics": ("statistics", "Reproduce the previous AR(1) mean-interval coverage study and determine whether increasing sample size with eight fixed Newey-West lags restores nominal coverage, under the stated Gaussian and Student-t3 designs."),
        "goldbach": ("mathematics", "Resume the existing strong Goldbach investigation. Audit the unresolved Li equation (14) positive-weight certificate and determine which error component must be reduced. This subtask must not be substituted for proving the strong Goldbach conjecture."),
    }
    sources = ["examples/erdos-straus/REPORT.md", "examples/erdos-straus/artifacts/finite-search.json",
               "examples/dependence-coverage/plan.json", "examples/dependence-coverage/coverage-grid.json",
               "examples/dependence-coverage/run_grid.py", "scripts/statistics_backend.py",
               "cases/goldbach-conjecture/workspace.json", "cases/goldbach-conjecture/case.json",
               "cases/goldbach-conjecture/agent-drafts/li-equation14-d-free-positive-weight-stage1-report.md",
               "cases/goldbach-conjecture/agent-drafts/li-equation14-d-free-positive-weight-stage1-local-smoke.json",
               "cases/goldbach-conjecture/artifacts/certify_li_equation14_d_free_positive_weight_stage1.py"]
    write_json(HERE / "source-manifest.json", {"sources": [{"path": path, "sha256": sha256(ROOT / path)} for path in sources],
               "mode": "live-codex-hosted", "old_files_modified": False, "public_novelty_audit": "not undertaken in this reanalysis"})
    for topic, (domain, objective) in topics.items():
        study = Study.create(HERE, topic, objective, domain)
        print(json.dumps({"topic": topic, "state": study.state()}))


if __name__ == "__main__":
    if sys.argv[1] == "init":
        initialize()
    elif sys.argv[1] == "submit":
        request = json.loads(sys.stdin.read())
        submit(**request)
    elif sys.argv[1] == "export":
        for topic in ("erdos", "statistics", "goldbach"):
            write_json(HERE / topic / "ledger.json", Study(HERE / topic).export())
