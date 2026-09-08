# Rigorous Research

[English](README.md) | [简体中文](README.zh-CN.md)

**实际研究重做（2026-09-08）**：[报告与复算说明](research-studies/reanalysis-20260908/PUBLICATION.md) 包含 Erdős–Straus 贪心构造判据、AR(1) 固定带宽覆盖率推导与实验，以及哥德巴赫积分子任务的审计和局部细分实测。原始猜想仍未解决，不声称新颖性或完全自主发现。

**1.11 版加入可运行的科研 Agent 架构**：Codex 托管理解与推理、独立 API 自主运行共用一个持久化内核，接入数学证书校验、统计工具和本地研究工作台。失败尝试会保存并反馈到下一步，报告交付、数学证据与原始目标验收分别记录。模型仍是推理能力的主要来源；架构提供工具、记忆和执行约束，不能保证科研突破。

```text
python -m pip install -e ".[agent,math]"
rigorous-research agent init research-studies expansion --objective "推导并验证 (x+1)^2 的展开式。"
rigorous-research agent context research-studies/expansion
rigorous-research agent serve --root research-studies
```

打开 `http://127.0.0.1:8765` 使用本地研究工作台。Codex 可以通过 `agent submit` 或项目提供的 MCP 工具执行研究，无需另填模型 API 密钥。独立运行时配置环境变量 `RESEARCH_AI_MODEL` 和 `RESEARCH_AI_API_KEY`，再运行 `rigorous-research agent run research-studies/expansion --steps 12 --seconds 600`。支持 OpenAI Responses、兼容 Chat Completions 的接口和 Ollama，不自动替换用户选择的模型。

详见[中文 Agent 指南](references/research-agent.zh-CN.md)、[完整接口与架构](references/research-agent.md)和[数学／统计实跑示例](examples/agent-research/README.md)。运行 `python scripts/build_plugin.py --output build/codex/rigorous-research` 可构建 Codex 插件包；构建不等于安装。当前精确数学工具覆盖明确的子命题，通用证明草稿和统计适用条件仍需审查。本地协议测试与离线回放不代表已经验证外部模型的科研水平、创新性或实际服务兼容性。

**1.10 版加入真实未解猜想实测**：[Erdős–Straus 研究报告与复现流程](examples/erdos-straus/REPORT.md)。验证了 9,998 个互异正整数分母见证，严格证明一条自然的贪心证明路线在 `n=49` 时失败，同时把原猜想保留为 **INCONCLUSIVE（证据不足）**。这不是解决了原猜想，也不声称刷新了数学结果或计算纪录。实测推动项目补齐整数证书，并区分“科研结果不确定”与“程序运行失败”。

运行 `rigorous-research egyptian --start 3 --stop 10000 --distinct --output finite.json`，再用 `rigorous-research verify-certificate finite.json` 独立检查。整数搜索和检查只依赖标准库；示例中的符号恒等式另需 SymPy。预算不足时保留未解决输入，不将其冒充反例。范围和预算说明见[整数搜索指南](references/integer-search.md)。

**1.9 版增强数学证明与统计严谨性**：新增证明义务、独立精确证书检查、统计定理适用条件和对抗回归测试。报告会显示未完成的证明步骤；命题、假设或证明依赖改变后，已有复核失效。操作细节见[证明与统计保障流程](references/proof-assurance.md)。

独立检查器会重新计算有理恒等式和反例，从原始矩阵重算行列式，并重建 Bernstein 区间证书。统计契约区分有限样本保证与渐近结论，拒绝用模拟结果替代理论条件。Copilot 将未解决的证明义务提供给模型，并在同一时间预算内用第二个进程复核数学输出。

这些机制约束证据与结论之间的关系，不能保证任何模型达到前沿模型水平，也不能保证完全没有幻觉。人工复核是本地记录的声明；机器验证覆盖写出的数学子命题，原文是否被正确翻译仍须审查。Lean 编译记录只作诊断证据。旧 schema 3 示例保留原校验并显示警告；schema 4 启用新增发布要求。

面向数学、统计和量化金融的科研工具与 Codex 技能，用证据约束结论，让研究过程可追溯、可复核、可继续推进。

[![validate](https://github.com/Studyer-Tang/rigorous-research/actions/workflows/ci.yml/badge.svg)](https://github.com/Studyer-Tang/rigorous-research/actions/workflows/ci.yml)

项目的目标是让重要科研结论能够被检验和复现，同时如实保留不确定性。完成计算不等于证实假设：`SUPPORTED`（支持）、`REFUTED`（反驳）、`INCONCLUSIVE`（证据不足）和 `MISSPECIFIED`（命题设定有误）是不同的可发布结果。

| 使用入口 | 适合什么任务 | 从哪里开始 |
|---|---|---|
| PaperTrail | 检查报告中的结论是否得到来源支持 | [浏览器演示](https://studyer-tang.github.io/rigorous-research/)或 `rigorous-research audit` |
| 研究引擎 | 组织数学、统计、金融研究及其证据 | `rigorous-research workspace`、`rigorous-research case` |

PaperTrail 是公开的报告审计界面，研究引擎负责更深入的复现与发布约束。两者共享证据规则、哈希和审查记录，也可以独立使用。

研究流程通常是：明确命题 → 整理来源与任务依赖 → 执行并记录计算 → 检查假设与反例 → 校准结论 → 发布可复现证据包。

## 从 AI 辅助科研开始

**1.8 版新增 Research Copilot**：把当前问题、推断契约、来源和待办工作整理成研究包，让模型提出可证伪的下一步，再用本地精确运算检查模型提出的数学子命题。它支持普通 AI 聊天、OpenAI Responses、兼容 Chat Completions 的接口和本地 Ollama。模型由用户指定，不绑定某一代模型。

```text
python -m pip install -e ".[math]"
rigorous-research copilot prepare cases/my-research/workspace.json --output packet.json
rigorous-research copilot advise packet.json --response model-response.json --output advice.json
rigorous-research copilot verify cases/my-research/workspace.json --packet packet.json --advice advice.json --output verification.json
```

先创建研究工作区，再运行上述命令。将 `packet.json` 提供给所选聊天模型；研究包包含指令与返回格式，将模型的 JSON 回复保存为 `model-response.json` 即可导入。这条命令流程本身不发起网络请求。

使用 API 时，选择 `--provider openai-responses`、`openai-compatible` 或 `ollama`，并指定端点和模型。密钥默认从环境变量 `RESEARCH_AI_API_KEY` 读取。OpenAI Responses 使用严格 JSON Schema；模型返回格式正确，并不代表科学内容正确。接口适配已通过离线回放测试，实际兼容性取决于用户所选服务与模型。

验证器仅允许内置的恒等式、反例和区间多项式界检查，限制检查数量与单次运行时间，拒绝与当前工作区不匹配的旧研究包。结果不会自动修改科研结论、证据或任务状态。模型提出的表达式仍可能误解原问题，因此“原命题是否被正确翻译”始终是待审查事项。这是命令行和智能体工作流，当前没有新增浏览器聊天界面。

完整离线演示和 API 配置见 [Research Copilot 指南](references/research-copilot.md)，可直接回放的示例见 [模型回复样例](assets/copilot-model-response.json)。该样例是人工编写的测试输入，不冒充前沿模型的真实运行结果。

### 验证整个区间上的多项式不等式

```text
rigorous-research math sympy-bound --lhs "x*(1-x)" --rhs 0 --symbol x --lower 0 --upper 1 --output bound.json
```

这条命令利用精确有理数 Bernstein 系数，证明所有实数 `x ∈ [0,1]` 都满足 `x(1-x) >= 0`。初始系数不足以证明时，可以对区间作有限次细分。

负的 Bernstein 系数本身不是反例；只有在定义域内找到精确的负值，才能反驳所检查的不等式。算法对次数和细分深度有限制；超出能力或预算的结果会明确报告错误或 `INCONCLUSIVE`。它是充分判定方法，不能保证证明所有真实成立的不等式。

## 研究引擎

### 研究工作区

`scripts/research_workspace.py` 管理多阶段研究：

- 带有依赖、验收条件和交付物的工作任务；
- 与具体命题关联的论文、数据集和软件来源；
- 本地执行命令、输出、环境、产物及 SHA-256 哈希；
- 可持续更新的状态记录和下一步建议；
- 汇总计划、来源、结果与结论的研究简报；
- 对未完成任务、失败运行、变化产物及未关闭义务的发布拦截。

### 推断案例

`scripts/inference_case.py` 管理结论是否成立：

- 分别为数学、统计、金融定义推断契约；
- 记录显式假设、预先声明的证伪条件、测试覆盖和观察结果；
- 区分决定性证据、诊断性证据和提示性证据；
- 区分命题为假、命题设定不当以及无法识别；
- 对证明、统计推断和回测使用不同的发布标准。

每个工作区包含一个推断案例；简短审计也可以单独使用案例。模块划分见 [架构说明](docs/architecture.md)。

### 精确反例搜索与研究续接

```text
rigorous-research math sympy-counterexample --lhs "x**2" --rhs "x" --symbols x --values 0 1 1/2 --max-points 100 --output witness.json
rigorous-research workspace next cases/my-research/workspace.json
```

第一条命令会给出 `x = 1/2` 时左侧 `1/4`、右侧 `1/2` 的精确反例。搜索尊重声明的正数、整数假设，排除原始分母为零的点；有限网格内没有反例，仍然只是 `INCONCLUSIVE`。

第二条命令输出只读 JSON，包括可执行任务、依赖阻塞、失败运行、验收检查和发布缺口。命令启动失败也保留错误与哈希记录，重试使用新的运行编号。它帮助智能体决定下一步，但不会自动执行无约束科研循环。

数学表达式采用显式运算和精确分数，例如用 `1/10` 表达十分之一。约分后仍保留原始定义域限制：`x/x = 1` 不能抹去 `x != 0`，矩阵元素中的限制同样保留。

## 验证体系

| 层次 | 提供的能力 | 不会据此直接宣称 |
|---|---|---|
| 文献 | 搜索 Crossref、arXiv、OpenAlex、Semantic Scholar、PubMed，保守去重并导出 JSON、Markdown、BibTeX | 搜索命中就是证据，或多个平台收录就是独立确认 |
| 科研诚信 | 汇总更新、撤稿、关注声明、版本关系和检索缺口，记录响应哈希 | 没有查到问题就证明没有问题 |
| 精确数学 | SymPy 恒等式、行列式、有理数反例、区间多项式界，以及可选 Lean 编译记录 | 一般符号化简就是完整证明，或有限样本证明普遍命题 |
| 统计推断 | IID、Newey–West、循环块 bootstrap、Holm/BH、多种数据生成过程的覆盖率检查 | 使用常见估计量就保证有限样本有效性 |
| 金融数据 | 冻结 Kenneth French、FRED 原始响应及版本、单位、日历、许可和哈希 | 最新修订数据就是历史时点当时可见的信息 |
| 治理 | 预注册计划封存、计算凭据、盲审材料和独立审查 | 自写“决定性证据”标签或过期审查就能通过严格发布 |
| AI 辅助 | 候选结论、范围问题、研究建议与内置子命题检查 | AI 自行确认来源支持、完成审查或认定研究结论 |
| PaperTrail | 关联报告结论、来源原文、定位信息和人工判断 | 附近出现引用就意味着支持 |

修改已绑定的命题输入、依赖锁、证书、原始数据、案例或审查包，会使对应凭据失效。本地审查身份是自行声明的；高风险应用仍需外部身份认证或与凭据哈希绑定的数字签名。

## 用 PaperTrail 审计报告

```text
rigorous-research audit report.md --manifest evidence.json --output-dir papertrail-site
```

输出为可独立打开的 `index.html` 和机器可读的 `audit.json`，不需要后端、数据库、账户或 API 密钥。决定性判断要求来源原文、定位信息和承担责任的人工审查者。详见 [PaperTrail 指南](docs/papertrail.md) 与 [Cartea-Jin-Shi 实验](examples/papertrail-cartea/README.md)。

构建浏览器演示：

```text
rigorous-research papertrail --output-dir build/papertrail-site --demo-report examples/papertrail-cartea/report.md --demo-manifest examples/papertrail-cartea/evidence.json
```

浏览器接受粘贴文本和本地 `.md`、`.json`、`.pdf` 文件，提供中英切换，导出 JSON 或独立 HTML。PDF 工作区可以渲染页面、提取文字、计算文件哈希，并将选中文段连同页码作为 `UNREVIEWED` 证据。人工审查台记录创建、修改、撤销历史，也显示人工判断与 AI 草稿的差异。

页面没有上传端点、分析脚本、账户要求或内置密钥。选取 PDF 后才加载固定版本的 PDF.js；主动选择 OCR 后才加载固定版本 Tesseract.js 及语言数据。普通 Markdown/JSON 路径不加载这两项依赖，PDF 和渲染页保留在浏览器内。

### 导入 PDF、网页和 DOI

```text
rigorous-research import pdf paper.pdf --output paper-draft.md
rigorous-research import url https://example.org/article --output article-draft.md
rigorous-research import doi 10.1234/example --output source.json
rigorous-research import assist report.md --output assistance.json
```

PDF 导入需要 `python -m pip install -e ".[papertrail]"`；扫描件先做 OCR。网页导入限制响应大小，并拦截回环、私网、链路本地和保留地址。导入的是待审查材料，不自动确认证据关系。

## 科研诚信与版本历史

```text
rigorous-research integrity check 10.1234/example --output-dir build/integrity
```

输出 JSON、带关系图的 Markdown 和 HTML。每项服务检查记录时间、URL、响应哈希、状态与局限。Crossmark 标为需要人工检查，不将其面向人的对话框冒充稳定公共 API。浏览器只有在用户主动查询 DOI 后才联系 Crossref、OpenAlex、PubMed。见 [科研诚信指南](docs/research-integrity.md)。

## 受治理的 AI 审稿

```text
rigorous-research ai-review draft report.md --manifest evidence.json --output ai-review-draft.json
```

默认使用本地确定性规则，不调用模型。可选 Ollama 和用户提供的兼容接口只补充理由、范围问题和搜索建议，模型返回的正式判断会被丢弃。确认证据必须另行提供人工身份、来源原文和定位信息。详见 [AI 审查指南](docs/governed-ai-reviewer.md)。

[Cartea-Jin-Shi 实验](examples/papertrail-cartea/README.md) 使用真实 119 页金融预印本，保留 PDF 哈希、简短页码摘录及固定的服务回放输入，不再分发原始 PDF。它包含一个故意扩大适用范围的结论，并保留待人工确认状态。

## 为什么需要这些限制

- 有限个符号样例不能悄悄变成对所有参数成立的定理。
- 无法识别因果效应，不意味着相反的因果结论成立。
- 程序执行成功，不会把正的样本均值变成已确定的长期溢价。
- 回测盈利仍须检查时点、成本、基准与按时间顺序的评价。
- 违反假设会阻止支持，却不自动反驳条件定理。
- 自己的证伪条件已经触发时，不能同时发布“支持”结论。

## 已有研究示例

### 参数化 Toeplitz 行列式：`SUPPORTED`

[完整工作区](examples/toeplitz-determinant/research-brief.md) 研究矩阵 `T_n(rho) = (rho^|i-j|)`，并给出在整数多项式环上对所有正整数 `n` 成立、无除法的证明：`det T_n(rho) = (1-rho^2)^(n-1)`。

示例还包含到 `n=7` 的精确 Leibniz 展开、覆盖到 `n=12` 的 84 个精确有理数消元样例，以及 `n=6` 的 SymPy 行列式证书与环境绑定凭据。它检查 `n=1`、`rho=±1`、隐藏除法和行操作顺序。普遍证明与有限计算的证据角色保持区分。

### 美国动量因子：`INCONCLUSIVE`

[完整工作区](examples/momentum-factor/research-brief.md) 冻结 Kenneth French 1993-01 至 2024-12 的月度动量因子数据，记录版本哈希，执行六阶 Newey–West、10,000 次十二个月循环块 bootstrap、分时期分析、对称截尾、极端月份排除和逐年剔除。

样本均值为每月 **0.408%**，但这不足以稳定支持预注册的结论，因此保留 `INCONCLUSIVE`。估计目标、时间窗口、方法、敏感性检验族和决策规则均有封存记录，具体统计量以示例报告为准。

### 依赖与厚尾：30,000 个模拟样本

[覆盖率研究](examples/dependence-coverage/report.md) 使用六种预先声明的 AR(1) 过程。当 `phi=0.8` 时，名义 95% 的 IID 区间在高斯与 Student-t3 情况下实际覆盖率仅为 **48.58%** 和 **46.36%**；八阶 Newey–West 改善至 **82.08%** 和 **81.22%**，仍未达到目标。

示例如实记录文献检索去重与 arXiv 限流缺口。较小的 [数学反例](examples/math-counterexample/report.md) 和 [前视偏差审计](examples/lookahead-audit/report.md) 可用于快速理解发布规则。

## 创建并推进研究工作区

```text
rigorous-research workspace init cases toeplitz-question --domain mathematics --question "What is the determinant of the parameterized matrix?" --claim "The proposed closed form holds for every n."
rigorous-research workspace task cases/toeplitz-question/workspace.json --title "Verify exact small cases" --kind computation --acceptance "Coefficient-by-coefficient equality through n=7" --deliverable artifacts/check.json
rigorous-research workspace run cases/toeplitz-question/workspace.json --task W001 --label "Exact verification" --output artifacts/check.json --complete -- python verify.py --output artifacts/check.json
rigorous-research workspace status cases/toeplitz-question/workspace.json
rigorous-research workspace brief cases/toeplitz-question/workspace.json
```

其中 `verify.py` 是研究者为具体问题编写并检查的程序。运行器记录执行过程，本身不是安全沙箱，也不扩张用户授权。单独的短审计可用 `rigorous-research case init`；每条命令均支持 `--help`。

其他常用入口：`literature` 搜索文献，`math sympy-identity` 验证恒等式，`seal seal-plan` 封存预注册计划，`statistics coverage` 检查有限样本覆盖率，`data fetch` 冻结数据，`review prepare` 生成盲审材料。

## 输出与能力边界

项目可以生成有来源的研究计划、证据矩阵、定理审计、精确计算或反例材料、统计设计、时点一致的金融审计、哈希关联运行记录、PaperTrail 报告，以及明确最强支持结论与未支持结论的研究简报。

它不能制造创新性、把未经检查的自然语言证明当作真理、自动取得专有数据，或让弱研究设计自动获得可识别性。目前也不是无人干预的通用数学证明系统。

## 安装、验证与目录

Python 工具需要 Python 3.10+，核心使用标准库。精确数学额外使用 SymPy；Lean 4 可选，不存在时不会生成模拟编译结果。

```text
git clone https://github.com/Studyer-Tang/rigorous-research.git
cd rigorous-research
python -m pip install -e ".[math]"
rigorous-research quality
rigorous-research eval
python -m unittest discover -s tests -v
```

可将仓库作为一个完整目录安装到宿主配置的技能目录，也可只用 Python CLI。实时文献、金融数据和外部模型调用需要网络；验证、工作区管理、封存及大部分测试可以离线运行。PyYAML 用于技能验证，不是运行时核心依赖。

| 路径 | 内容 |
|---|---|
| `SKILL.md`、`agents/` | 技能路由、行为约束和宿主界面元数据 |
| `references/` | 数学、统计、金融、证据契约和 Copilot 详细规则 |
| `scripts/research_workspace.py`、`scripts/inference_case.py` | 研究任务与科学结论治理 |
| `scripts/research_copilot.py` | 模型研究包、受限建议和数学子命题检查 |
| `scripts/math_backend.py`、`scripts/statistics_backend.py` | 数学与统计验证后端 |
| `scripts/literature_search.py`、`scripts/finance_data.py` | 文献检索和金融数据冻结 |
| `scripts/research_seal.py`、`scripts/review_protocol.py` | 封存、凭据、盲审和裁决 |
| `scripts/papertrail_*`、`scripts/governed_ai_reviewer.py` | 报告导入、审计、浏览器界面与 AI 审查 |
| `assets/`、`examples/` | 可复用样例、模板和已有研究案例 |
| `tests/`、`evals/` | 行为测试与发布规则反例评估 |

`quality` 检查技能元数据、版本一致性、本地文档链接、Python 语法、不安全动态执行、疑似密钥和本机绝对路径；`eval` 检查已发布样例通过、已知破坏被拒绝。

构建 Agent Plugin：

```text
python scripts/build_plugin.py --output build/agent-plugin --archive dist/rigorous-research-agent-plugin
```

带标签的 GitHub 发布流程会附加 wheel、源码包、插件 ZIP、依赖 SBOM 和构建来源证明。插件根目录包含 `plugin.json` 与 `skills/rigorous-research/SKILL.md`，安装方式取决于宿主。

更多信息：[快速入门](docs/quickstart.md) · [路线图](ROADMAP.md) · [更新记录](CHANGELOG.md) · [贡献指南](CONTRIBUTING.md) · [安全说明](SECURITY.md) · [引用信息](CITATION.cff)。部分深入文档目前使用英文。

## 设计来源与许可证

项目借鉴 [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) 的仓库维护思路，包括标准元数据、按需展开的文档、结构验证和脚本测试。实现独立编写，围绕本项目的推断契约设计，不复制其技能目录。

采用 MIT 许可证，见 [LICENSE](LICENSE)。
