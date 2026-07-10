# Workflow 1: Graph Authoring

## 目标与位置

本流程将权威教材来源转成可供人工审核的 `candidate_nodes.json` 和 `candidate_edges.json`。它位于 benchmark 构造链路，输出仍是 candidate，不能被 evaluation runtime 读取。

```text
PDF/source -> Parsed Source Markdown -> Parsed Source Segments
-> segment node extraction -> skeleton reconciliation
-> node rubric authoring -> edge proposal -> candidate graph files
```

## 设计亮点

### 先切分来源，再让 agent 提取

来源 Markdown 被确定性地切分成带 heading path、`char_count` 和 source locator 的大窗口。Node Extraction Agent 只读取一个已验证 segment，而不是整本书或模型记忆，令每个候选节点都有可审计的来源锚点，也控制长上下文成本。

### 分离“发现概念”与“写诊断 rubric”

提取步骤只产出薄的 `Segment Node Extraction Draft`：名称、定义、定位和 grounding note。Reconciliation 将跨段重复概念合并为干净的 `Source-Grounded Node Skeleton`；之后 Rubric Agent 才补全诊断目标、L0–L5 levels、signals 和 simulator behavior。这样避免在早期把不稳定的边、难度判断或相邻未审核节点混入概念发现。

### 边以精确性优先

Edge Proposal Agent 在完整 node rubric 完成后才运行。它应省略“可能有关”的弱关系，而不是追求稠密图；候选边的置信度只是 agent 建议，不是自动准入条件。

### 可重放和可定位失败

segment 可有限并发，但 draft id、输出和 trace 仍按源 segment 顺序装配。每一步都有解析与阻断校验；某个 segment、reconciliation 或 rubric 失败就停止下游，保留中间产物和 trace 供修复提示或 prompt 后重跑。

## 关键边界

- source preparation、segmentation 和 artifact export 在 LLM 之外；模型只处理受限的结构化输入。
- `KnowledgeNode.id` 由 reconciled canonical name 确定性派生；重复 id 是校验错误，不能偷偷加后缀。
- candidate 状态属于路径和 review 生命周期，不写入 node/edge 对象字段。
- 最终 review artifact 只有两个 JSON list；中间段、draft、reconciliation provenance 和 trace 是调试材料。
