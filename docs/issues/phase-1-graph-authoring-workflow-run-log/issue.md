## Title

为 Phase 1 / Graph Authoring Workflow 增加执行过程日志

## Background

当前 authoring workflow 可以从本地 PDF 生成 candidate graph artifacts，例如 `candidate_nodes.json` 和 `candidate_edges.json`。但一次 workflow run 的执行过程缺少可审计记录，后续如果生成结果质量不稳定、某个 step 失败、或需要复盘 LLM 输出链路，难以判断问题发生在哪一步。

## Problem

目前缺少结构化 run log，无法回答这些问题：

- 本次 run 使用了哪些 source material？
- workflow 执行了哪些 step？
- 每个 step 是否成功完成？
- 每个 validation checkpoint 是否通过？
- 每一步产出了多少 skeletons / nodes / edges？
- 如果失败，失败发生在哪一步，错误类型是什么？
- 本次 run 的 artifact 路径和 run metadata 是什么？

## Goal

为当前 Phase 1 / authoring workflow 增加执行过程日志，使每次 candidate graph run 都可以被复盘、调试和人工 review。

## Non-goals

- 不改变 `KnowledgeNode` / `KnowledgeEdge` schema。
- 不把 log metadata 写进 candidate node 或 edge object。
- 不自动 promote candidate artifacts 为 reviewed graph。
- 不在日志中保存敏感内容，例如完整 PDF 文本、完整 prompt、raw model output 或 API key。

## Proposed Scope

新增一个结构化 workflow run log，建议记录：

- `run_id`
- `workflow_name`
- `started_at`
- `completed_at`
- `status`
- `source_materials`
- step entries:
  - `step_name`
  - `step_type`
  - `started_at`
  - `completed_at`
  - `status`
  - `input_counts`
  - `output_counts`
  - `validation_result`
  - `error`, if failed
- artifact paths:
  - `candidate_nodes.json`
  - `candidate_edges.json`
  - optional `workflow_log.json`

## Acceptance Criteria

- 每次成功的 graph authoring run 都能生成一份结构化 run log。
- API response 中可以返回 run log summary 或 log artifact path。
- 如果 `write_artifacts=true`，run directory 中应保存 `workflow_log.json`。
- log 至少覆盖：
  - node extraction step
  - node rubric authoring step
  - edge proposal step
  - 每个 validation checkpoint
- log 不包含 PDF 原文、完整 prompt、raw model output 或 secret。
- 现有 `candidate_nodes.json` 和 `candidate_edges.json` 输出契约不被破坏。
- 添加测试覆盖成功 run 的 log 结构和 artifact 写出行为。

## Notes

这个 issue 的核心价值是让 early phase 的真实 authoring run 可追踪、可复盘、可调试，同时保持 candidate graph artifact 和执行日志的边界清晰。