# Offline research-agent replay / 离线科研 Agent 回放

Run from the repository root after installing `.[agent,math]`:

```text
python examples/agent-research/reproduce.py --output build/agent-replay
```

Use a new output directory for each replay. The controller is a deterministic, explicitly synthetic
callback. Mathematics, statistical simulation and independent certificate checking execute for real.
No external model is contacted; this is a runtime regression demonstration, not evidence that any
model became more intelligent or produced novel research.

| Study | Initial route | Feedback-driven correction | Result |
|---|---|---|---|
| Mathematics | Omit the cross term in `(x+1)^2` | An exact counterexample triggers the corrected expansion | Corrected identity independently checked; explicit machine contract met |
| Statistics | Use HAC lag 60 with sample size 60 | The retained execution error triggers lag 5 | Seeded IID/HAC coverage diagnostics for one AR(1) design |

Both studies deliver reports while leaving original case acceptance and translation review open.
The database and `agent-export.json` preserve failed routes, arguments, tool hashes and results.

这两个示例检验“提出步骤 → 实际执行 → 保留失败 → 修正路线 → 如实报告”的闭环。
控制器是人工编写的测试回放，不是模型的真实研究输出；计算和独立校验则真实执行。
数学例子验证已知初等恒等式，统计例子完成指定模拟，不宣称解决未解猜想或得到新定理。
