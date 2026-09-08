# 科研 Agent 使用指南

这个版本把 Skill 的研究规范连接到真正的执行内核。模型负责提出论证和选择下一步，
内核负责保存过程、执行限定工具、校验证据、反馈失败，以及限制运行预算。
它不会让普通模型凭空获得前沿模型的数学能力，也不保证自动产出新定理或论文。

1.12 版把整数搜索接入同一个执行内核：`egyptian` 查有限解，`egyptian_window` 精确检查
某个首分母窗口，`egyptian_scan` 在共享预算内搜索等差数列中的窗口反例。
`egyptian_family` 接收 n、x、y、z 关于非负整数参数 t 的整系数多项式，系数按常数项到高次项排列，
分别检查恒等式、整性、正性和分母顺序。后两项采用非负系数这一充分条件，方法不适用时保持未决。
窗口反例只否定相应路线；无限参数族仍需要单独证明其覆盖范围，不能直接升级为原猜想的证明。

`research_memory` 将旧工作区任务、假设和证明义务连同文件哈希放入模型上下文，限制每份文档的
列表数量与长度并说明截断。它们仍是未经接受的研究记录；读取记录不会自动关闭任何证明义务。
具体接口和检查原理见 [整数研究指南](integer-search.md#native-agent-research-tools)。

## 安装与两种运行方式

在项目目录使用 Python 3.10 或更新版本：

```text
python -m pip install -e ".[agent,math]"
rigorous-research agent init research-studies my-study --domain mathematics --objective "写出你的原始研究目标"
rigorous-research agent context research-studies/my-study
```

统计项目将领域设为 `statistics`。`agent` 扩展安装 JSON Schema 校验器和官方 Python MCP SDK，
`math` 安装 SymPy；原有工作区、证明契约、整数工具依然可独立使用。

**Codex 托管方式**：把项目及 Skill 提供给 Codex，让它读取 `agent context` 的研究记录与行动格式，
提出一步研究操作，再调用 `agent submit STUDY proposal.json --revision 当前版本号`。
已连接 MCP 时，对应工具是 `research_context`、`research_submit` 和 `research_inspect`。
推理由当前 Codex 提供，无需另配 API 密钥；项目本身不会自行启动无人值守的 Codex 会话。

**独立自主方式**：在运行环境或密钥管理器配置 `RESEARCH_AI_MODEL` 与 `RESEARCH_AI_API_KEY`：

```text
rigorous-research agent run research-studies/my-study --steps 12 --seconds 600
```

默认使用 OpenAI Responses。可通过 `--provider`、`--endpoint`、`--model`、`--api-key-env`
指定服务、模型和密钥变量。兼容接口使用 `openai-compatible`；Ollama 使用 `ollama`，
并显式配置 `--endpoint http://127.0.0.1:11434` 及已安装模型名称，无需密钥。
网络请求失败时保存状态并停止，不自动重复付费请求或偷偷更换模型。

API 模式会向所选端点发送研究目标、最近的提案与结果、数据标签和运行事件。
原始数值数组保存在本地，其派生统计结果会进入后续上下文。不要把密钥写入研究文本。
记录保存模型名称、响应哈希和调用次数；调用次数不是完整费用统计。

## 本地工作台与 Codex 插件

```text
rigorous-research agent serve --root research-studies
```

打开 `http://127.0.0.1:8765`，可以创建、查看研究项目，导入 JSON 数值数组，查看证据与失败，
暂停、恢复并导出记录。启动时指定 `--model` 或配置模型环境变量后，可以点击“运行 12 步”，
每次最多运行 600 秒。未配置模型时，由 Codex 或命令行提供行动。
服务只监听本机地址，验证请求来源与会话令牌，当前不作为互联网多用户服务。

MCP 服务启动方式：

```text
rigorous-research agent mcp --root research-studies
python scripts/build_plugin.py --output build/codex/rigorous-research
```

插件包同时包含 Codex 清单、MCP 配置和 Skill。先安装相同版本的 Python 包，
再按 Codex 的插件流程导入构建目录。MCP 默认通过 PATH 中的 `rigorous-research` 启动；
找不到时在 `.mcp.json` 中配置其绝对路径。建议在 MCP 服务环境中将 `RESEARCH_AGENT_ROOT`
设置为可写研究目录的绝对路径。构建不会修改全局配置或自动安装插件。

## 数学、统计和严谨性的边界

| 能力 | 目前实现 | 不能据此宣称 |
|---|---|---|
| 数学恒等式与反例 | 精确有理表达式、限定网格反例、独立证书复核 | 有限搜索证明无限命题，或表达式自动等同原问题 |
| 区间多项式不等式 | 一元有理区间上的 Bernstein 证书复核 | 任意分析学或高维不等式已形式化 |
| 统计计算 | IID/HAC/区组自助法、AR(1) 覆盖率模拟、Holm/BH | 自动满足独立性、矩条件、识别条件或总体覆盖保证 |
| 文献 | 建项时通过 `--network` 开启的元数据检索 | 搜索命中就等于核实了论文或原创性 |
| 论证与引理 | 带前序行动引用的草稿与待证明条件 | 模型自评通过就等于严格证明 |

统计研究应先写明估计目标、抽样单位、识别条件、多重检验族和探索性状态。
预注册、统计适用性契约与正式发布继续使用项目原有工具；这个运行器不把事后模拟包装成预注册证据。
一般 Lean 定理搜索、任意 Python/R 实验和全文定理核实尚未接入自主工具集。

研究状态分开记录：工具成功执行、精确子命题检查结果、报告已交付、机器验收契约是否匹配、
原始目标是否完成，以及原文到数学命题的翻译是否经过审查。
`finish` 只表示报告交付。模型没有把原始目标直接设置为“已证明”的接口。
可通过 `init --contract` 声明精确工具、参数和预期状态；匹配成功仅完成这份机器契约。

## 恢复、证据与发布

研究记录存入 `agent.sqlite3`。每次行动先持久化再执行，进程锁避免两个控制器同时推进同一项目。
中断后，下次获取控制权时把未完成操作标为 `INTERRUPTED`；不会悄悄算作成功或自动重跑昂贵步骤。
数值数据与结果均记录内容哈希，旧版本提案、重复成功行动和不存在的证据引用会被拒绝。
这是本地复现记录，不是对抗可同时修改数据库与代码的攻击者的签名系统。

`agent pause STUDY` 阻止下一步执行，已经开始的限时操作可以完成并保存。
`agent resume STUDY` 清除暂停标志，停止的循环需要再次 `agent run`。
`need_input` 或 `finish` 后提交一条包含补充信息的 `note`，即可保留原目标并重新推进。
默认三次连续失败或提案拒绝后停止；不同的不确定尝试可以继续，直到达到显式预算。
模型调用、工具生成与独立检查都有时间限制。子进程不是操作系统安全沙箱，也没有硬内存配额。

上下文保留最近 20 步和 10 条事件，大结果会截断预览；可按行动编号查看完整历史。
`agent export STUDY --output ledger.json` 导出全部记录。
Agent 不静默修改原有 `case.json` 的证明图或科研结论：检查导出的证据，按
[证明保障流程](proof-assurance.md)登记对应制品，处理翻译、定义域和真实审查义务后再正式发布。

## 如何判断它是否真的有用

[双领域示例](../examples/agent-research/README.md)实际执行数学与统计工具，并演示失败后的修正。
控制器是明确标注的人工测试回放，不是前沿模型输出，也不是新科研成果。
接口测试另外覆盖本地模型协议和真实 MCP 通信；未调用外部模型的测试不能证明其线上服务兼容性。

要评估科研增益，应固定模型版本、问题集、可用工具和预算，与直接使用模型比较：
原始证明目标完成率、错误完成声明、未解决比例、成本和复现质量。
不能拿生成报告数量、程序测试通过率或一个简单恒等式代替科研能力提升的证据。
完整接口与状态语义见[英文架构指南](research-agent.md)。
