# 计划：为 Graph Authoring Workflow 增加执行过程日志

## Issue 概要

- 标题：为 Phase 1 / Graph Authoring Workflow 增加执行过程日志
- 涉及范围：`backend/knowact/authoring/`、`backend/knowact/api/authoring.py`、authoring artifacts
- Issue 阶段标记：Phase 1
- V1 拆解对齐：`docs/V1ProjectBreakdown.md` 当前把 `Graph Authoring Workflow` 放在 Phase 2 / M2。本文按现有 Phase 2 authoring workflow 边界设计，不改变 reviewed graph、runtime 或 scoring 边界。

## 目标

为每次 graph authoring candidate run 生成结构化、可审计、可复盘的 run log。日志用于定位每个 agent step、validation checkpoint、artifact 写出与失败位置，同时保持 `candidate_nodes.json` 和 `candidate_edges.json` 的现有输出契约不变。

## 当前状态

- `GraphAuthoringAgentWorkflow.run()` 当前按顺序执行：
  - `NodeExtractionStep`
  - `validate_source_grounded_node_skeletons`
  - `NodeRubricAuthoringStep`
  - `validate_complete_candidate_nodes`
  - `EdgeProposalStep`
  - `validate_candidate_edges`
- `GraphAuthoringWorkflowResult` 只包含 skeletons、candidate nodes、candidate edges。
- `write_graph_authoring_output()` 只写出 `candidate_nodes.json` 和 `candidate_edges.json`。
- `POST /api/authoring/graph-candidates` 在 `write_artifacts=true` 时把两个 candidate JSON 写入 run directory，并在 API response 中返回 artifact paths。
- 现有 ADR 明确允许 validation notes / intermediate debug information 作为 workflow logs 存在，但它们不属于最终 graph-authoring answer contract。

## 设计原则

- 不修改 `KnowledgeNode` / `KnowledgeEdge` schema。
- 不把 log metadata 写入 candidate node 或 edge object。
- `workflow_log.json` 是 sidecar run artifact，不是 candidate graph final review output。
- `candidate_nodes.json` 和 `candidate_edges.json` 仍然是两个 plain JSON list files。
- 日志只保存结构化 metadata、counts、status、错误类型和 artifact path；不保存完整 PDF 文本、完整 prompt、raw model output 或 secret。
- 成功 run 必须记录完整 step 和 validation checkpoint；失败 run 尽量记录失败前已完成的 entries 和失败 entry。

## 建议日志 Schema

新增 authoring-only Pydantic schema，建议放在 `backend/knowact/authoring/logging.py`。

建议对象：

- `GraphAuthoringRunLog`
  - `run_id: str`
  - `workflow_name: str`
  - `started_at: datetime`
  - `completed_at: datetime | None`
  - `status: Literal["running", "succeeded", "failed"]`
  - `source_materials: tuple[RunLogSourceMaterial, ...]`
  - `entries: tuple[WorkflowRunLogEntry, ...]`
  - `artifact_paths: GraphAuthoringLogArtifactPaths | None`
  - `error: WorkflowRunError | None`
- `RunLogSourceMaterial`
  - `source_id`
  - `title`
  - `citation`
  - 可选 API 补充字段，例如 `storage_uri`、`filename`、`size_bytes`
  - 不包含 `SourceMaterial.text`
- `WorkflowRunLogEntry`
  - `entry_name`
  - `entry_type: Literal["agent_step", "validation_checkpoint", "artifact_write"]`
  - `started_at`
  - `completed_at`
  - `status: Literal["succeeded", "failed"]`
  - `input_counts: dict[str, int]`
  - `output_counts: dict[str, int]`
  - `validation_result: Literal["passed", "failed"] | None`
  - `error: WorkflowRunError | None`
- `WorkflowRunError`
  - `error_type`
  - `message`
  - 可选 `checkpoint` / `step_name`

成功 run 至少需要包含这些 entries：

1. `node_extraction`
2. `validate_source_grounded_node_skeletons`
3. `node_rubric_authoring`
4. `validate_complete_candidate_nodes`
5. `edge_proposal`
6. `validate_candidate_edges`
7. optional `write_candidate_graph_artifacts`
8. optional `write_workflow_log_artifact`

计数规则：

- `node_extraction`: input `source_materials`, output `skeletons`
- skeleton validation：input `skeletons`，记录 validation result
- rubric authoring：input `skeletons` 和 `source_materials`，output `candidate_nodes`
- node validation：input `candidate_nodes` 和 `skeletons`，记录 validation result
- edge proposal：input `candidate_nodes` 和 `source_materials`，output `candidate_edges`
- edge validation：input `candidate_nodes` 和 `candidate_edges`，记录 validation result

## 实施计划

1. 增加 run-log schemas 和常量。
   - 增加 `WORKFLOW_LOG_FILENAME = "workflow_log.json"`。
   - 保持 graph artifact 常量不变：`candidate_nodes.json`、`candidate_edges.json`。
   - 使用 `model_dump(mode="json", exclude_none=True)` 做 JSON 序列化。

2. 增加一个小型 run-log builder。
   - 建议模块：`backend/knowact/authoring/logging.py`。
   - builder 负责创建 timestamp、记录 entry start/finish、维护 success/failure status、记录 counts，并通过结构设计避免敏感内容进入日志。
   - builder 只接收 counts 和 source metadata，不接收 prompt 或 raw model output。
   - workflow core 不知道 PDF storage 细节；默认只从 `SourceMaterial` 记录 `source_id`、`title`、`citation`，永不记录 `text`。
   - API 层调用 `run_with_log()` 时通过 `source_metadata` 补充 `storage_uri`、`filename`、`size_bytes`。

3. 在保留现有 `run()` 契约的同时增加带日志的 workflow 执行路径。
   - 保持 `GraphAuthoringAgentWorkflow.run(source_materials)` 返回 `GraphAuthoringWorkflowResult`。
   - 增加 `run_with_log(source_materials, *, run_id, source_metadata=None)`，返回类似 `GraphAuthoringWorkflowRunResult(workflow_result, run_log)` 的 wrapper。
   - issue 完成后，`run_with_log()` 应成为默认 workflow execution path；`run()` 通过调用 `run_with_log()` 并只返回 `workflow_result` 来保持旧调用方兼容。
   - `run()` 不暴露成功 run log，也不在 workflow object 上维护 `last_run_log` 之类的可变状态；需要成功日志的调用方应显式使用 `run_with_log()`。
   - 如果某个 step 或 validation 失败，先把当前 entry 和 top-level log 标记为 failed，再抛出 `GraphAuthoringWorkflowRunError`。该异常携带 partial `run_log` 和原始 `cause`，API 仍按 `cause` 类型映射 HTTP status。

4. 显式记录每个 validation checkpoint。
   - 包装 `validate_source_grounded_node_skeletons`。
   - 包装 `validate_complete_candidate_nodes`。
   - 包装 `validate_candidate_edges`。
   - validation 失败时设置 `validation_result="failed"`，记录 `error_type`，但不把被校验对象的完整 payload 写入日志。

5. 增加 sidecar log artifact 写出能力。
   - 保持 `write_graph_authoring_output()` 只写两个文件。
   - 增加 `write_graph_authoring_run_log(run_log, output_dir) -> Path`。
   - API 在成功 run 中先写 candidate artifacts，再更新 log artifact paths，最后写 `workflow_log.json`。
   - 对于 `write_artifacts=true` 的失败 run，应只在 run directory 中写出 `workflow_log.json`，并在 `HTTPException.detail` 中返回 `workflow_log_uri`，方便本地调试和后续前端定位。

6. 以向后兼容方式扩展 API response。
   - 在 `GraphCandidateAuthoringResponse` 中增加 `run_log_summary`。
   - 在 `GraphCandidateArtifactPaths` 中增加 `workflow_log_uri`。
   - 保留现有 response fields 和 candidate node/edge payloads。
   - 在调用 workflow 前计算 `run_id`，确保 execution metadata 和 output directory 使用同一个 id。
   - 成功 response 只返回 compact summary 和 artifact path，不返回完整 in-memory run log。
   - `run_log_summary` 只保留运行身份、状态和顶层 output counts，例如 `run_id`、`workflow_name`、`status`、`started_at`、`completed_at`、`output_counts`。不加入 `step_count`、`validation_count` 或 `artifact_count`；这些细节以 `workflow_log.json` 为准。

7. 确保敏感内容不进入日志。
   - Source material log entries 可以包含 `source_id`、`title`、`citation`、`storage_uri`、`filename`、`size_bytes`。
   - 不包含 `SourceMaterial.text`。
   - 不包含 rendered prompts、raw LLM responses、API keys、environment variables 或完整 PDF 内容。
   - `WorkflowRunError.error_type` 记录异常类名；`message` 只保存截断后的 `str(exc)`，建议上限 500 字符。
   - `message` 需要做保守脱敏，例如替换疑似 API key；不记录 traceback、exception repr 或对象 payload。
   - 增加测试，断言代表性的 forbidden strings 不会出现在 `workflow_log.json` 中。

## 测试计划

增加聚焦的 `unittest` 覆盖：

- Workflow success log structure：
  - run status 为 `succeeded`
  - entries 包含三个 agent steps 和三个 validation checkpoints
  - counts 与 fixture output 匹配，例如 `skeletons=5`、`candidate_nodes=5`、`candidate_edges=4`
  - workflow core 直接调用时，source metadata 只包含 `source_id`、`title`、`citation`，不包含 `text`
  - 序列化后的 log 中不出现 source text、prompt text 或 raw model output
- Artifact write behavior：
  - 直接调用 `write_graph_authoring_output()` 时仍然只写 `candidate_nodes.json` 和 `candidate_edges.json`
  - API run 在 `write_artifacts=true` 时写出 `candidate_nodes.json`、`candidate_edges.json` 和 sidecar `workflow_log.json`
  - API response 包含 `artifact_paths.workflow_log_uri`
- API no-write behavior：
  - 当 `write_artifacts=false` 时，不要求创建 output directory
  - response 包含 compact `run_log_summary.output_counts`，但不包含 log artifact path
- Failure behavior：
  - fake failing step 或 validation 会把 top-level status 标记为 `failed`
  - failed entry 记录 `entry_name`、`entry_type`、`error_type` 和脱敏后的 message
  - 除非 workflow 成功，否则不写出 partial candidate node/edge files
  - 当 `write_artifacts=true` 时，失败 response 的 `HTTPException.detail` 包含本地 `workflow_log_uri`
  - API 对 `GraphAuthoringWorkflowRunError.cause` 保持现有 HTTP status mapping，例如 validation 为 422，parse/model errors 为 502
  - serialized log 不包含 traceback、exception repr、raw output 片段或疑似 API key

推荐命令：

```bash
uv run python -m unittest test/test_v1_graph_authoring_workflow.py test/test_v1_authoring_api.py
```

## 验收标准映射

- 成功的 graph authoring run 会生成结构化 run log：`GraphAuthoringRunLog`。
- API 返回 compact `run_log_summary`；当 `write_artifacts=true` 时同时返回 `artifact_paths.workflow_log_uri`。
- `write_artifacts=true` 时，run directory 下会写出 `workflow_log.json`。
- log 覆盖 node extraction、node rubric authoring、edge proposal，以及所有 validation checkpoints。
- 通过 schema 设计和回归测试排除敏感内容。
- 现有 `candidate_nodes.json` 和 `candidate_edges.json` 契约保持不变。
- 测试覆盖成功 run 的 log 结构和 artifact 写出行为。

## 已决定事项

- 当 `write_artifacts=true` 且 API 调用失败时，`HTTPException.detail` 应返回 `workflow_log_uri`。这里的 URI 是相对项目根目录的本地 artifact path，不是外网 URL。
- 成功 API response 只返回 compact `run_log_summary` 加 artifact path，不返回完整 in-memory run log；完整日志以 `workflow_log.json` 为准。
- `run_log_summary` 只保留运行身份、状态和 `output_counts`；step、validation、artifact 明细不进入 summary。
- issue 完成后，`run_with_log()` 成为默认 workflow execution path；`run()` 保留旧返回类型，但内部复用带日志执行。
- `run()` 不暴露成功 run log，也不维护 `last_run_log`；API 等需要日志的调用方显式调用 `run_with_log()`。
- step 或 validation 失败时抛出 `GraphAuthoringWorkflowRunError`，其中携带 partial `run_log` 和原始 `cause`；API 根据 `cause` 保持现有 HTTP status mapping。
- 失败日志只记录异常类名和截断、脱敏后的 `str(exc)`；不记录 traceback、exception repr、raw model output、prompt 或 source text。
- workflow core 只记录 `SourceMaterial` 的 `source_id`、`title`、`citation`；API 层通过 `source_metadata` 补充 `storage_uri`、`filename`、`size_bytes`。

## 待决问题

- 暂无。
