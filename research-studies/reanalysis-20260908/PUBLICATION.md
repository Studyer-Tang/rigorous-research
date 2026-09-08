# 研究重做发布记录 / Research reanalysis archive

用户在研究报告交付后授权将本轮成果上传 GitHub。报告中“本地保存、尚未发布”的文字描述其交付时状态，原文及其证据哈希保持不变；本页记录随后的发布。

The user authorized publication after delivery. Statements that the reports were local and unpublished describe their original delivery state. The reports and their recorded hashes are preserved; this page records subsequent publication.

- [总报告 / Research overview (Chinese)](REPORT.zh-CN.md)
- [Erdős–Straus：判据及证明 / Criterion and written proof](erdos/REPORT.zh-CN.md)
- [统计：推导、模拟及不确定性 / Theory, simulation and uncertainty](statistics/REPORT.zh-CN.md)
- [哥德巴赫子任务：审计与细分 / Arithmetic audit and subdivision](goldbach/REPORT.zh-CN.md)
- [交付时核验记录 / Delivery verification](verification.json)

## 发布范围 / Contents

包含报告、脚本、JSON 行动及账本、工作区、执行日志和哈希清单。哥德巴赫部分同时发布本轮使用的 stage-1 输入、其 Python 导入依赖及相关证书；旧 workspace/case 仅作为来源快照，不代表发布了旧课题所有被引用的文件。未纳入无关旧草稿、临时目录、运行锁、缓存和 SQLite 数据库；可从每个 `ledger.json` 阅读已导出的完整行动及事件。

Reports, scripts, JSON actions and ledgers, workspaces, run logs and hash manifests are included. Selected Goldbach inputs, imported Python modules and certificates accompany the new probes. Legacy workspace/case files are provenance snapshots, not a complete release of that older investigation. Unrelated drafts, temporary files, locks, caches and SQLite databases are excluded. Each `ledger.json` contains the exported actions and events.

## 复算 / Reproduction

在仓库根目录安装依赖后，使用 Python 3.12（原运行版本 3.12.14）：

From the repository root, install dependencies and use Python 3.12 (original run: 3.12.14):

```sh
python -m pip install -e ".[agent,math]"
python research-studies/reanalysis-20260908/erdos/check_greedy.py
python research-studies/reanalysis-20260908/statistics/summarize.py
python research-studies/reanalysis-20260908/goldbach/audit_record.py
python research-studies/reanalysis-20260908/goldbach/probe_subdivision.py
```

这些命令会重写对应结果，建议在单独克隆中执行。统计 `summarize.py` 是对已保存模拟结果的后处理；十次模拟的具体参数及种子在 `statistics/actions/003.json` 至 `013.json` 中（009 为研究笔记），可在新 Agent study 中重新提交对应 coverage 动作。执行日志中的 Windows 绝对路径是历史记录，不能直接作为其他机器的命令。

These commands overwrite their result files; use a separate clone. Statistical summarization postprocesses saved simulations. To rerun simulations, submit the coverage arguments in actions 003–008 and 010–013 to a fresh Agent study. Historical Windows paths in logs are not portable commands.

`host.py` 和 `finalize.py` 保存了本轮本地交付流程，需要原研究数据库及目录环境；它们不是发布包的一键自主研究入口。复算产生的耗时字段可能变化，因此应比较科学结果，同时保留原始归档用于哈希核验。

The host/finalization helpers document the original delivery workflow and require its local study state. They are not one-command autonomous research entry points. Runtime fields can change on rerun; compare scientific results and retain the archive for hash verification.

## 结论边界 / Scope

数学的一般证明为文字证明；机器验证只覆盖具体代数和有限证据。哥德巴赫审计独立于生成器的部分是记录算术，细分实验仍共享旧解析实现。原始猜想没有被证明或证伪，也没有进行新颖性文献核查。

General mathematical arguments are written proofs, with machine checks limited to specified algebra and finite evidence. Goldbach record arithmetic was independently audited; subdivision shares the legacy analytic implementation. The original conjectures remain unresolved, and novelty has not been audited.
