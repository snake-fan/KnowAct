# Workflow 4: Knowledge Map Authoring and Promotion

## 目标与位置

本流程以一个 reviewed graph 和一个 confirmed Profile Context 为输入，生成覆盖全图、带隐藏 Ground-Truth Evidence 的 candidate map；审核后发布为 runtime 使用的 reviewed hidden map。

```text
reviewed graph + confirmed profile context
-> full-graph knowledge-state outline
-> outline validation -> batched evidence authoring
-> candidate map + consistency warnings -> review/revalidation
-> immutable reviewed map
```

## 设计亮点

### 先全局状态，后局部证据

Outline Agent 一次性看到完整 reviewed nodes/rubrics，先为每个节点产生 `mastery_level`、`misconceptions` 和 `unknowns`，但不看 edges。全局视图使用户画像在整个图上连贯；其后 Evidence Agent 仅接收一个连续 node batch 的 state、rubric 和 profile context，限制证据生成的上下文和泄漏面。

### 确定性 checkpoint 与稳定排序

outline 必须和图 node id 集合完全相等，拒绝缺失、重复和未知节点。evidence batch 按 `authored_nodes.json` 的稳定顺序连续切分，输出也按此顺序装配；evidence id 与 ordinal 由代码分配，而非由模型决定。

### 证据支撑而非裸标签

每个状态引用 `simulator_only` Ground-Truth Evidence，并满足按 mastery 的最低记录数。模型只写 `node_id`、evidence kind、signal；workflow 固定 `visibility`、type 和 id。这让 Simulator 有充足依据自然表达不确定、误解或能力边界，同时不给模型机会伪造生命周期字段。

### warning 与准入分离

edge consistency 是生成时的人工 review hint，不是 promotion 时重算的 truth。promotion 的硬门槛是覆盖、state 唯一性、evidence、profile existence 和 graph version existence；避免把启发式 warning 误做成不可解释的发布规则。

## 关键边界

- candidate map 不能人工逐项 patch；质量问题应改善输入或 workflow 后生成新 run。
- `map_id` 只在 promotion 分配，且不覆盖；同一 `(user_id, graph_version)` 可有多个独立 map sample。
- promotion 将 `kind` 从 `candidate` 确定性改为 `ground_truth`，并保存最小 `map_manifest.json`；成功后移除 candidate run。
