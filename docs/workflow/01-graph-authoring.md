# Workflow 1: Graph Authoring

## 目标与位置

本流程把人工预处理的权威教材 Markdown 中一个明确方面的知识，转成可供人工审核的 `candidate_nodes.json` 和 `candidate_edges.json`。它位于 benchmark 构造链路，输出仍是 candidate，不能被 evaluation runtime 读取。

```text
Selected fixed Source
-> local Markdown + validated metadata-owned Graph Authoring Scope
-> deterministic source segments
-> scope-aware node extraction + exact evidence check
-> global reconciliation and representative-node selection
-> independent skeleton verification
-> node rubric authoring -> precision-first edge proposal
-> candidate graph files -> human review
```

## 设计亮点

### 先切分来源，再让 agent 提取

来源 Markdown 被确定性地切分成带 heading path、`char_count` 和 source locator 的大窗口。Node Extraction Agent 只读取一个已验证 segment 和同一个显式 scope，而不是整本书或模型记忆。每个 draft 必须携带能在该 segment 中进行空白归一化后精确匹配的短 `evidence_excerpt`；代码先验证 excerpt membership，再允许进入全局合并。

### 先限定方面，再控制代表性节点数

`Economy`、`ISLP`、`OSTEP` 的方面名称、方面描述、至少 50 道 representative diagnostic questions、领域排除主题和节点预算保存在各自的 `metadata.json`。每次 run 只选择 Source，不重复填写这些稳定研究配置。Reconciliation 在全局视角下合并重复、调整粒度，并选择接近 `target_node_count` 的代表性节点；默认目标约 20、上限 24。目标是软目标而不是配额：来源不足时允许少于 20 个，绝不通过弱相关、偶然细节或重复节点凑数。

### 分离“发现概念”与“写诊断 rubric”

提取步骤只产出薄的 `Segment Node Extraction Draft`：名称、定义、定位、grounding note 和 evidence excerpt。Reconciliation 将跨段重复概念合并为干净的 `Source-Grounded Node Skeleton`，并保留 supporting draft/segment 与 evidence provenance。独立 Verification Agent 随后逐项判断 source support、scope fit 和 diagnostic value，只保留满足全部条件的 skeleton；之后 Rubric Agent 才补全诊断目标、L0–L5 levels、signals 和 simulator behavior。这样避免在早期把不稳定的边、难度判断或相邻未审核节点混入概念发现，也避免 proposer 直接批准自己的候选。

### 边以精确性优先

Edge Proposal Agent 在完整 node rubric 完成后才运行。它应省略“可能有关”的弱关系，而不是追求稠密图；候选边的置信度只是 agent 建议，不是自动准入条件。

### 可重放和可定位失败

segment 可有限并发，但 draft id、输出和 trace 仍按源 segment 顺序装配。单段 extraction 允许最多 3 次局部机械契约尝试：只有“超过 12 个 drafts”或 `evidence_excerpt` 不能在该 segment 中精确匹配时，才把确定性校验错误反馈给同一 extraction step 并要求重生成该段的完整 JSON；所有尝试都保存在该 segment 的 raw trace 中。JSON 解析、schema、全局 reconciliation、verification、rubric 和 edge validation 仍然 fail closed，不触发该重试，也不会自动修复或批准语义结果。

## 关键边界

- 三本书到 Markdown 的转换在 KnowAct 之外由 benchmark author 手工完成，并直接放入 `storage/source_materials/{source_id}/`；前端与 API 不承担上传。
- 生成 API 只暴露 `source_id`、可选 `run_id` 和 `client_provider`。`benchmark_domain` 与 source id 相同，scope、题库、排除项和节点预算全部从 metadata 加载。
- source catalog、metadata validation、segmentation、evidence excerpt membership check 和 artifact export 在 LLM 之外；模型只处理受限的结构化输入。
- `KnowledgeNode.id` 由 reconciled canonical name 确定性派生；重复 id 是校验错误，不能偷偷加后缀。
- candidate 状态属于路径和 review 生命周期，不写入 node/edge 对象字段。
- verifier 的 `remove` 决策保留在 intermediate artifact 中，但不会进入 rubric/edge authoring；它不是人工 review 的替代品。
- 最终 review artifact 只有两个 JSON list；scope、segments、drafts、reconciliation provenance、verification decisions 和 traces 是审计与调试材料。
