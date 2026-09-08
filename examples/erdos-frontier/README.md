# Live Erdős–Straus investigation / 多路线实战研究

[中文完整报告](REPORT.zh-CN.md) · [Research brief and open obligations](research-brief.md)

**The original conjecture remains inconclusive.** This archive records 93 actions chosen by a live
Codex host, with actual computations and research-driven changes to Agent 1.12. It is not a synthetic
model replay, proof of the original conjecture, novelty claim, or demonstration of autonomous discovery.

- Refuted short-window auxiliary hypotheses: n=1129 needs the third possible first denominator;
  n=1201 needs the sixth; n=246241 needs the tenth. Each excluded prefix has complete divisor evidence.
- Checked 4,166 consecutive inputs n=1 mod24 below 100,000 for the eight-step hypothesis before a
  targeted later search found its counterexample. Finite success did not justify generalization.
- Independently certified 55 explicit polynomial families for every nonnegative integer parameter.
  Fifty-two combine to cover 834 residues modulo840, leaving exactly 1,121,169,289,361,529. This
  reproduces classical partial coverage, not a new coverage record.
- Derived a written lifting lemma and checked three concrete infinite families through the observed
  difficult inputs. Lifting assumes an existing solution; it supplies no all-integer descent argument.

本轮使用项目 skill 和同一个 Agent 内核，实际改变了证明路线，并补入整数窗口、共享预算扫描、
完整参数族证书和持续可见的证明义务。原猜想始终未决，未制造人工评审。具体证据和一般提升引理见中文报告。

## Reproduce / 复算

From the repository root, using Python 3.12 (originally 3.12.14):

```sh
python -m pip install -e ".[agent,math]"
python examples/erdos-frontier/reproduce.py
```

This verifies archive hashes, every stored integer certificate, polynomial coverage, the finite
prefix and the inconclusive release gates, then reruns nine representative tool actions with exact
certificate comparison. It does not rerun literature retrieval or simulate model choices.

`discover_families.py`, `expand_families.py` and `summarize.py` preserve deterministic experiments selected
by the live host. They overwrite generated outputs; use a separate copy if rerunning them. Historical
workspace commands reference the original local study directory. Use `reproduce.py` as the portable entry.
Runtime locks, SQLite state and downloaded paper HTML are excluded; `ledger.json` exports the live record.
The literature URL and downloaded-content hash are retained, without bundling the full paper.

Native Agent actions now share the same adapters and independent checks across hosted/API/MCP modes.
General proof discovery and the choice of mathematical ideas still depend on the model. No controlled
model-capability comparison was performed.
