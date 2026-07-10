# KnowAct Agent Workflows

本目录记录 KnowAct 中由 agent、确定性校验与 benchmark-author review 共同完成的工作流设计。阅读顺序是先本文件，再进入具体流程；这里的说明服务于既有 ADR、`CONTEXT.md`、`docs/V1ProjectArchitecture.md` 和 `docs/V1ProjectBreakdown.md`，不替代它们。

## 全局流程与设计原因

KnowAct v1 评估的是 Tested Agent 能否通过有限对话诊断一个固定但隐藏的用户知识状态。因此系统把“构造可审计 benchmark”和“执行不泄漏的评估”分成两条受控链路：前者允许 authoring agent 生成候选数据，但必须经 benchmark author 显式审核并 promotion；后者只读取 immutable reviewed artifacts，并将 hidden map、evidence 和 simulator internals 隔离在 Tested Agent 之外。

```text
Authoritative source
  -> [1 Graph authoring] -> candidate graph -> [2 Graph promotion] -> reviewed graph
Rough user description
  -> [3 Profile context] -> confirmed profile context
reviewed graph + confirmed profile context
  -> [4 Map authoring] -> candidate map -> [5 Map promotion] -> reviewed hidden map
reviewed graph + hidden map
  -> [6 Simulator turn] <-> [7 Episode runtime / tested agent]
  -> final reconstructed map -> [8 Scoring and report]
```

这种顺序解决四个核心问题：

- 可追溯性：每个 reviewed artifact 都能追溯到候选 run、来源或输入身份。
- 可复现性：reviewed graph、profile context、map 和 episode binding 都不可覆盖；修正以新 identity 发布。
- 可诊断性：LLM 输出被解析为结构化中间产物，并在关键边界进行阻断校验和保留 trace。
- 公平性：Tested Agent 可见 graph 和对话，但不能访问 hidden map、Ground-Truth Evidence、Profile Context、simulator blueprint 或 scoring internals。

## 流程索引

1. [Graph authoring](01-graph-authoring.md)：从权威来源生成可审核候选知识图谱。
2. [Graph review and promotion](02-graph-review-promotion.md)：将审核通过的候选图谱发布为 immutable reviewed version。
3. [Profile context authoring and confirmation](03-profile-context.md)：从粗略 persona 形成确认后的合成用户上下文。
4. [Knowledge map authoring and promotion](04-map-authoring-promotion.md)：生成带隐藏证据的候选知识地图并发布。
5. [Single-turn user simulation](05-user-simulation.md)：在严格可见性边界内生成自然用户回答。
6. [Evaluation episode runtime](06-episode-runtime.md)：将 reviewed artifacts 绑定为可执行评估 episode。
7. [Tested-agent decision and reconstruction](07-tested-agent.md)：让被测 agent 诊断、维护 working map 并提交最终重建。
8. [Structured scoring and reporting](08-scoring-reporting.md)：比较最终重建和隐藏地图，产出可复现报告。

## 共同设计约束

- `Knowledge Graph` 描述客观节点和边；用户状态仅属于 `Knowledge Map` 的 node-level state。
- LLM 负责受限的生成或判断，身份分配、排序、跨对象装配、验证与发布由确定性代码负责。
- candidate artifact 不能自动进入 runtime；任何 promotion 都需要显式 benchmark-author 操作。
- agent workflow 的 trace 仅供 benchmark author 调试；不能成为 Tested Agent 的上下文或主评分依据。
- v1 是 static-state active diagnosis：交互不教学，也不更新隐藏用户知识状态。
