# KnowAct V1 Project Architecture

Status: Draft for review

本文基于 `CONTEXT.md`、v1 ADRs 和 `docs/V1ProjectBreakdown.md`，提出 KnowAct v1 的项目架构建议。它不是新的 ADR；如果本文与已接受 ADR 冲突，以 ADR 和 `CONTEXT.md` 为准。

## Architecture Goals

KnowAct v1 的架构目标是先跑通一个可审计、可复现的 active knowledge-state diagnosis benchmark 闭环：

```text
Authoritative Source
  -> Graph Authoring Agent Workflow
  -> benchmark-author review
  -> Authored Knowledge Graph
  -> Map authoring and review
  -> Evaluation Episode Manifest
  -> User Simulator + Tested Agent interaction
  -> Final Reconstruction Submission
  -> Structured Map Comparison
  -> Evaluation Report
```

核心约束：

- `Knowledge Graph` 和 `Knowledge Map` 必须分离。
- graph/map/schema/scoring 优先结构化，不把核心对象藏在 prompt 字符串里。
- candidate authoring data 与 reviewed benchmark data 必须分离。
- evaluation runtime 只能使用 reviewed graph 和 reviewed maps。
- `Visibility Boundary` 必须由 runtime 和数据访问层共同保证，而不是只靠 prompt 约束。
- v1 的正式 benchmark graph 以已经 promotion 的 reviewed graph version 为准；小图只能作为 development fixture。

## Recommended Repository Layout

建议保持三条主线：文档与决策、后端 benchmark core、前端 research workbench。

```text
/
├── AGENTS.md
├── CONTEXT.md
├── README.md
├── README.zh-CN.md
├── pyproject.toml
├── docs/
│   ├── KnowledgeGraph.md
│   ├── V1ProjectBreakdown.md
│   ├── V1ProjectArchitecture.md
│   └── adr/
├── backend/
│   ├── main.py
│   └── knowact/
│       ├── api/
│       ├── core/
│       ├── validation/
│       ├── storage/
│       ├── authoring/
│       ├── simulator/
│       ├── agents/
│       ├── runtime/
│       ├── scoring/
│       ├── reports/
│       └── llm/
├── frontend/
│   └── src/
│       ├── app/
│       ├── features/
│       ├── components/
│       └── api/
├── benchmark/
│   ├── domains/
│   ├── fixtures/
│   └── runtime/
├── experiments/
│   ├── runs/
│   └── reports/
└── test/
```

说明：

- `backend/knowact/` 是 benchmark 的 Python package 主体。
- `benchmark/` 存放 benchmark artifacts，包括 development fixtures、candidate review data、reviewed graph/map data 和 runtime episode manifests。`benchmark/runtime/episodes/` 是跨 domain 的 `Runtime Episode Registry`。`benchmark/domains/` 可以继续被默认 ignore；只有明确要发布或保留的 reviewed artifacts 才应有意加入版本库。
- `experiments/` 存放 episode run outputs、agent outputs、scoring reports 和分析结果。是否全部提交到版本库后续再定；默认应避免提交大体积或敏感实验输出。
- `Reference/` 中的 PDF 或源材料可以作为本地工作资料，但正式 benchmark data 应通过 `Source Locator` 和 source metadata 保持可审计，不依赖把大型原始 PDF 强绑定进 runtime。

## Backend Architecture

后端按依赖方向分层。下层不依赖上层；runtime 负责组合 simulator、agents 和 scoring。

```text
api
  -> runtime, storage, reports

runtime
  -> core, validation, storage, simulator, agents, scoring

authoring
  -> core, validation, storage, llm

simulator / agents
  -> core, storage, llm

scoring / reports
  -> core, validation, storage

validation / storage
  -> core

core
  -> no KnowAct application imports
```

### `core/`

职责：定义纯 domain schemas、枚举和轻量 domain helpers。

建议文件：

- `graph.py`: `KnowledgeNode`, `KnowledgeEdge`, edge types, source locators.
- `map.py`: `KnowledgeMap`, `UserKnowledgeState`, `GroundTruthKnowledgeMap`, `ReconstructedKnowledgeMap`.
- `evidence.py`: `EvidenceRecord`, evidence type/kind/visibility.
- `episode.py`: `EvaluationEpisodeManifest`, turn budget, interaction rules.
- `interaction.py`: `DiagnosticQuestion`, simulator answer, transcript turn, interaction observation.
- `scoring.py`: scoring profile name, mastery levels, score report schemas.
- `agent.py`: tested-agent protocol input/output schemas.

原则：

- `core/` 不读取文件、不调用模型、不知道 FastAPI。
- `Knowledge Node` 不包含用户状态。
- `Knowledge Edge` 不包含用户状态或 evidence。
- `Knowledge Map` 只引用 graph node ids。

### `validation/`

职责：跨对象校验，比 Pydantic 字段校验更高一层。

建议能力：

- graph validation: node id 唯一、edge endpoint 存在、edge type 合法、`contrasts_with` 存储方向规范。
- map validation: 满足 `Map Coverage Requirement`、每个 node 最多一个 current state、evidence refs 有效。
- manifest validation: graph/map/profile/scoring binding 完整，拒绝 per-episode scoring overrides。
- visibility validation: hidden evidence 不进入 tested-agent-visible context。
- reconstruction validation: final reconstructed map 引用 visible evidence，缺失项标记为 `Missing Prediction`。

### `storage/`

职责：读取和写入 benchmark artifacts，不包含业务决策。

建议能力：

- `GraphRepository`: 读取 candidate/reviewed node 和 edge JSON list files。
- `MapRepository`: 读取 candidate/reviewed knowledge maps 和 evidence。
- `EpisodeRepository`: 读取 episode manifests。
- `RunRepository`: 写入 transcripts、agent outputs、scoring reports。
- `ArtifactPathResolver`: 统一处理 development fixture、reviewed benchmark、experiment run output 的路径。

原则：

- storage 不决定 candidate 能否进入 evaluation runtime；只提供读取和写入。
- runtime 只能通过 reviewed artifact loader 加载正式 episode。
- 路径策略集中在一个地方，避免模块里硬编码 graph directory paths。

### `authoring/`

职责：辅助 benchmark author 生成 reviewable candidate graph/map data。它不属于 evaluation runtime。

建议模块：

- `schemas.py`: authoring-only schemas, including `SourceMaterial`, `Parsed Source Segment`, `Segment Node Extraction Draft`, `Source-Grounded Node Skeleton` with concise source grounding notes, step input/result DTOs, list wrappers, and workflow result objects.
- `workflow.py`: `GraphAuthoringAgentWorkflow` orchestration, including step order, dependency direction, and validation checkpoints.
- `steps.py`: graph authoring step protocols and concrete step implementations. `Node Extraction Agent Step`, `Node Skeleton Reconciliation Agent Step`, `Node Rubric Authoring Agent Step`, and `Edge Proposal Agent Step` can live in this single module; they are workflow responsibilities, not required one-file-per-step modules.
- `templates/common.py`: shared graph-authoring prompt components such as source-grounding rules, node design rules, MasteryScale guidance, edge type definitions, schema/output contracts, and JSON serialization helpers.
- `templates/node_extraction.py`, `templates/node_skeleton_reconciliation.py`, `templates/node_rubric_authoring.py`, `templates/edge_proposal.py`: prompt/message builders for each Graph Authoring Agent Workflow step. Step-specific prompt content should live in the step-specific template file; do not add compatibility re-export modules for old aggregate template names.
- `parsers/graph_authoring.py`: raw model-output parsers that turn JSON text into segment node drafts, reconciled source skeletons, candidate nodes, and candidate edges.
- `validation.py`: authoring-specific validation around parsed source segments, segment grounding, skeleton reconciliation provenance, complete candidate node rubrics, and candidate edge graph validity.
- `logging.py`: authoring run log schemas and helpers for structured, redacted `Graph Authoring Run Log` records, including links to external agent-step raw model outputs and parser outputs for local debugging.
- `output.py`: candidate graph file export, especially `candidate_nodes.json` and `candidate_edges.json`, plus sidecar `workflow_log.json` export.
- `sources.py`: authoring source preparation, including resolving cached `Parsed Source Markdown`, splitting PDFs that exceed MinerU's per-task page limit into local chunks, temporarily publishing local PDFs or PDF chunks through private Aliyun OSS signed URLs for MinerU standard-mode parsing, joining chunk Markdown in page order, and calling MinerU when a same-directory same-stem Markdown file is missing or explicitly regenerated.
- `segments.py`: deterministic `Parsed Source Markdown` to `Parsed Source Segments` derivation, including shallow heading-path parsing, adjacent-section packing into large context windows, paragraph-level splitting for oversized sections, `char_count`, and source locator preservation. Source parsing and segmentation both stay outside the `llm/` completion boundary.
- `openai_workflow.py`: shared graph authoring workflow wiring behind the `ModelClient` interface, with provider selection for OpenAI and DeepSeek clients.
- `map_authoring.py` and `map_authoring_output.py`: initial Candidate Knowledge Map generation workflow, deterministic assembly, blocking validation, and debug artifact export. Reviewed-map promotion support lives with the shared `review_promotion.py` promotion orchestration and reviewed-map storage helpers. The initial map-authoring contract is intentionally single-map: one generation run receives `benchmark_domain`, one reviewed `graph_version`, one confirmed `user_id`, optional `run_id`, and `client_provider`. `map_id` is assigned only during reviewed-map promotion. The normal orchestration starts from a benchmark-author supplied rough user description, generates a reviewable `Profile Context`, and applies separate `Profile Context Validation` and explicit benchmark-author `Profile Context Confirmation` gates before invoking candidate-map generation. Candidate-map generation remains an independently callable authoring capability for focused debugging. Cohort generation remains an outer orchestration concern that can repeat the single-map contract.
- Candidate Knowledge Map generation now supports reviewed-graph scale through contiguous evidence-authoring batches in stable reviewed-node order. It exposes identity-based generation, artifact inspection, and explicit promotion, defaults to `evidence_batch_size = 5` with a positive request-level override, applies one request-level `sampling_temperature` to the outline step and every evidence batch, and writes generation-time edge-consistency warnings. Candidate-map run ids do not overwrite existing run directories; retry creates a new run id.
- `Profile Context` is a structured JSON artifact with `user_id`, `benchmark_domain`, readable `summary`, `background`, `prior_experience`, `goals`, and `preferences`. It carries coherence inputs for map authoring and later simulation, not node-level mastery values.
- Initial profile-context validation is deterministic structural validation: nonblank summary, at least one nonblank background item, present optionally empty prior-experience list, at least one nonblank goal, present optionally empty preferences list, benchmark-domain equality with the artifact path, and forbidden extra fields. It does not call an LLM validator or use brittle text blacklists.
- Profile-context authoring receives the rough user description, benchmark-domain identity, and optional domain summary only. It does not receive graph nodes, node rubrics, or edges. Candidate-map generation is the first map-authoring step that receives the confirmed `Profile Context` together with the complete reviewed `Authored Knowledge Graph`.
- Candidate-map generation identifies its graph input by `benchmark_domain` and `graph_version`, then loads the reviewed snapshot from `benchmark/domains/{benchmark_domain}/graphs/{graph_version}/`. Standalone debugging uses the same reviewed-graph lookup path and must not accept uploaded or inline node and edge JSON payloads.
- Candidate-map generation identifies profile input by `user_id`, then loads a saved and confirmed `Profile Context` artifact. Standalone debugging uses the same lookup and confirmation boundary and must not accept inline profile-context JSON payloads.
- `Profile Context Confirmation` publishes an immutable snapshot under `benchmark/domains/{benchmark_domain}/users/{user_id}/profile_context.json`. Any later edit must publish a new domain-unique `user_id`; map generation and episodes keep referring to their original snapshot.
- Profile-context confirmation never overwrites an existing `user_id` and does not expose `overwrite=true`.
- One candidate profile-context run may be confirmed at most once. Another synthetic user requires a new candidate profile-context run so distinct user ids do not alias one draft.
- Keep confirmed profile-context storage lightweight in the initial slice: `profile_context.json` is the immutable snapshot and no separate profile-context manifest is required. Candidate profile-context runs retain debugging artifacts.
- Candidate profile-context generation uses a run id only. `Profile Context Confirmation` is where the benchmark author assigns formal `user_id`, so discarded persona drafts do not create synthetic-user identities.
- Candidate profile-context artifacts do not contain `user_id` before confirmation. Their `PUT` endpoint edits persona content only: `summary`, `background`, `prior_experience`, `goals`, and `preferences`. Run identity and benchmark domain remain fixed.
- Candidate profile-context `PUT` overwrites the current draft file in place. Do not retain candidate-profile revisions in the initial slice; immutability starts when confirmation publishes `users/{user_id}/profile_context.json`.
- Confirmed profile-context snapshots bind `benchmark_domain` but remain independent of `graph_version`, allowing the same synthetic user profile to drive map generation against later reviewed graph versions in the same domain.
- Candidate profile-context runs live under `benchmark/domains/{benchmark_domain}/candidate_profile_contexts/{run_id}/`. Candidate-map runs live under `benchmark/domains/{benchmark_domain}/candidate_maps/{run_id}/` with `candidate_map.json`, `consistency_warnings.json`, `workflow_log.json`, optional `intermediate/`, and optional `agent_traces/` while they await review. They are discardable synthetic samples: benchmark-author review accepts a generated candidate unchanged for promotion or rejects it. Poor candidates should be regenerated after improving profile input or workflow behavior rather than manually patched. Explicit benchmark-author promotion assigns a domain-unique `map_id`, publishes immutable reviewed snapshots under `benchmark/domains/{benchmark_domain}/maps/{map_id}/` with `map.json` and `map_manifest.json`, and removes the originating run from `candidate_maps/`.
- Reviewed-map promotion never overwrites an existing `map_id` and does not expose `overwrite=true`. A replacement synthetic sample must use a new map id so existing episode references remain reproducible.
- Successful promotion removes the originating candidate-map run from `candidate_maps/`. Another reviewed sample requires a new generation run so distinct map ids represent distinct synthetic samples rather than aliases of identical output.
- Candidate profile-context runs use a minimal artifact set: `candidate_profile_context.json`, `workflow_log.json`, `agent_traces/model_raw_output.txt`, and `agent_traces/parser_output.json`. Do not add `intermediate/` or a redundant `profile_context_authoring/` trace subdirectory for this single-step workflow.
- Candidate-map runs retain step-specific structure because generation has two real agent steps. `intermediate/` stores `state_outline.json` and `ground_truth_evidence.json`. `agent_traces/` stores `knowledge_state_outline/model_raw_output.txt`, `knowledge_state_outline/parser_output.json`, and per-batch `ground_truth_evidence/{batch_name}/model_raw_output.txt` plus `parser_output.json`. Do not copy confirmed profile-context or reviewed-graph payloads into the run directory; `workflow_log.json` records `user_id`, `benchmark_domain`, and `graph_version` references.
- One confirmed `user_id` may produce multiple candidate-map runs for retry and debugging. One `(user_id, graph_version)` pair may also promote multiple independent ground-truth-map samples with distinct `map_id` values; episode manifests select the map sample they use.
- Reviewed-map promotion allows multiple accepted samples for one `(user_id, graph_version)` pair as long as every published sample uses a new domain-unique `map_id`.
- `map_manifest.json` binds `map_id`, `user_id`, `benchmark_domain`, `graph_version`, and `promoted_from_candidate_run`. Promotion revalidates graph coverage, one current state per node, evidence refs, mastery-sensitive simulator-support minimums, confirmed user-profile existence, and reviewed graph-version existence. It does not read or recompute edge-consistency warnings.
- `consistency_warnings.json` is a generation-time review hint that stays in the originating candidate-map run only. Reviewed-map snapshots do not copy warnings, and Phase 6 runtime loaders do not read them.
- `user_id` identifies the confirmed synthetic-user profile basis; `map_id` identifies one promoted synthetic knowledge-map sample generated from that basis.
- Keep `map_manifest.json` minimal in the initial slice: do not add timestamps, model configuration, or copied warning payloads. Candidate-map run artifacts retain debugging metadata.
- Candidate-map generation has two agent steps. `Knowledge-State Outline Agent Step` drafts full-graph node-level `mastery_level`, `misconceptions`, and `unknowns` from confirmed `Profile Context` and reviewed nodes with rubrics; it does not receive reviewed edges. `Ground-Truth Evidence Authoring Agent Step` then drafts hidden evidence from that outline, confirmed `Profile Context`, and reviewed node rubrics; it may batch nodes internally.
- Each evidence-authoring batch receives confirmed `Profile Context`, reviewed rubrics for its batch nodes, and state outlines for its batch nodes only. It does not receive other node states, reviewed edges, or the complete graph. Deterministically reject batch output that references nodes outside the batch or fails mastery-sensitive evidence minimums for batch nodes.
- Partition evidence-authoring batches as contiguous windows in stable reviewed `authored_nodes.json` order. Do not shuffle nodes or cluster batches by graph edges.
- Initial knowledge-state outline authoring uses one full-graph model call for the current reviewed graph scale. Do not batch this step until larger graphs justify a separate global reconciliation design.
- Knowledge-state-outline model output contains `node_id`, `mastery_level`, `misconceptions`, and `unknowns` only. It does not output `evidence_refs`, `user_id`, or lifecycle `kind`; workflow code supplies those during deterministic candidate-map assembly.
- Outline output and assembled maps explicitly include `misconceptions` and `unknowns` arrays for every node state, even when empty. Missing arrays are invalid rather than defaulted.
- Prompt outline authoring to avoid exact duplicate misconception or unknown items within one state. Validation rejects exact duplicates rather than silently rewriting generated samples. Do not add semantic-similarity merging.
- Do not enforce mastery-specific item counts for misconceptions or unknowns. Prompt for plausible content without forcing generated filler.
- Keep `evidence_refs` optional with schema-level default `[]`; context-specific ground-truth authoring, reconstruction, and scoring validation decide whether empty evidence is allowed.
- Before evidence authoring starts, a blocking validation checkpoint requires the outline node-id set to exactly match the reviewed graph node-id set. Reject duplicate, unknown, or missing node ids, invalid mastery values, and blank misconception or unknown items.
- After outline validation, normalize assembled states into stable reviewed `authored_nodes.json` order. Normalize generated evidence into the same node order; within one node preserve model-output order and assign deterministic evidence ordinals from that order.
- Ground-truth evidence authoring defaults to `evidence_batch_size = 5`. `POST /api/authoring/map-candidates` accepts an optional positive-integer request-level override for provider or prompt tuning.
- `POST /api/authoring/map-candidates` also accepts optional request-level `sampling_temperature`, defaulting to `0.7`, for synthetic-map sampling. It applies to map generation only; graph authoring and profile-context authoring keep their existing model configuration. Record effective temperature in the map workflow log. Do not add seed support initially. Provider adapters must reject unsupported temperature requests explicitly rather than silently ignore them.
- One map-generation run uses the same effective sampling temperature for its outline step and every evidence-authoring batch. Do not expose separate outline and evidence temperature controls initially.
- Initial evidence batching is fail-fast without partial resume. Any failed batch marks the candidate-map run failed; traces remain for debugging and retry creates a new run id. Defer resume semantics until model-call cost justifies immutable-outline replay design.
- Workflow-authored ground-truth evidence uses `simulator_only`. Every reviewed ground-truth node state must cite at least one `simulator_only` evidence record so Phase 5 simulation has an actionable basis.
- Evidence authoring uses a mastery-sensitive minimum-count policy: L0-L1 states receive at least one `simulator_only` record, L2-L3 states receive at least two records, and L4-L5 states receive at least one record. Prompt guidance suggests suitable evidence kinds and capability/boundary coverage, but validation does not require mastery-specific kinds.
- Ground-truth-evidence model output contains `node_id`, `evidence_kind`, and `signal` only. Workflow code assigns deterministic `ev_{run_id}_{node_id}_{ordinal}` ids and fixed `evidence_type = ground_truth_profile`, `visibility = simulator_only`, and `turn_id = null`. Promotion preserves these run-scoped evidence ids unchanged.
- Prompt evidence authoring to avoid exact duplicate `(evidence_kind, signal)` pairs within one node. Validation rejects exact duplicates rather than counting them toward mastery-sensitive minimums. Do not add semantic-similarity merging.
- Keep initial evidence-kind validation lightweight. `background_fact` remains valid under the shared minimum rules; defer kind-specific restrictions until generated artifacts reveal a concrete failure mode.
- Workflow code deterministically merges hidden evidence references into node-level states. Model output does not maintain cross-object `evidence_refs`.
- Workflow output writes `candidate_map.json` with `kind = candidate`. Only reviewed-map promotion code converts it to `kind = ground_truth` when publishing `map.json`; model output does not control lifecycle kind.
- Candidate-map output is written only after blocking validation passes. Reject missing, duplicate, or unknown node states; invalid mastery; missing or cross-node evidence refs; evidence counts below mastery-sensitive minimums; workflow evidence that is not `simulator_only`; `kind != candidate`; and `user_id` mismatch. On failure retain traces and intermediates but do not write a promotable `candidate_map.json`. Edge-aware consistency remains a separate non-blocking warning step.
- Profile-map semantic coherence remains a benchmark-author accept-or-reject review concern. Do not add an LLM coherence judge or treat semantic persona alignment as blocking structural validation in the initial slice.
- Reviewed `Knowledge Edges` act as soft consistency signals for candidate-map review. Deterministic edge-aware checks receive the drafted outline and reviewed edges, then produce review warnings for suspicious node-state combinations but do not automatically rewrite or reject uneven maps.
- The initial deterministic warning rule is intentionally narrow: for a reviewed `prerequisite_for` edge, emit a warning when target mastery exceeds source mastery by at least two levels. Do not infer mastery ordering from `part_of`, `supports`, or `contrasts_with` edges. Warning records include edge id, endpoint node ids and mastery values, and the triggering rule.

边界：

- graph authoring final output 只能是 `candidate_nodes.json` 和 `candidate_edges.json` 两个 JSON list files。
- `workflow_log.json` 可以作为 run directory 中的 sidecar artifact 存在，并记录 agent step 状态、counts、错误和 trace artifact URI；LLM raw output 与 parser output 分别写入 `agent_traces/{step}/model_raw_output.txt` 与 `agent_traces/{step}/parser_output.json`。这些都不是 candidate graph final review output，也不改变 node/edge JSON list schema。
- Segment-level node extraction traces should be keyed by segment id, for example `agent_traces/node_extraction/{segment_id}/model_raw_output.txt` and `parser_output.json`, or an equivalent per-segment batch trace.
- Parsed source segment ids are run-local sequential ids in document order, for example `seg_000001`; they are used for trace, debug, and replay, while reviewer-facing location remains the `Source Locator`.
- Initial segmentation thresholds stay as internal code defaults; `POST /api/authoring/graph-candidates` does not expose request parameters for segment maximum character length, target size, minimum size, or overlap.
- Segment sizing uses simple character length as the context-size proxy, and segment artifacts should record `char_count`; do not add a tokenizer dependency or provider-specific token counting for the initial slice. Current graph-authoring defaults target coarse source windows around `100_000` characters, prefer not to emit non-final segments below `50_000` characters, cap segment chunks at `150_000` characters where paragraph boundaries permit, and avoid paragraph overlap to reduce duplicate node drafts.
- Segment-level node extraction may issue bounded parallel model requests internally for throughput, defaulting to 8 concurrent requests. Workflow outputs, draft ids, and batch traces must be assembled in original segment order for deterministic replay, and progress logs should expose completed and remaining segment counts during long runs.
- Node Skeleton Reconciliation keeps one global step trace, for example `agent_traces/node_skeleton_reconciliation/model_raw_output.txt` and `parser_output.json`; merge and split provenance belongs in `intermediate/node_skeleton_reconciliation.json`.
- `intermediate/` 可以作为 run directory 中的 structured replay/debug artifact directory 存在，保存通过相邻 validation checkpoint 的 workflow intermediate artifacts，例如 `parsed_source_segments.json`、`segment_node_extraction_drafts.json`、`node_skeleton_reconciliation.json`、`source_grounded_node_skeletons.json`、`node_rubric_patches.json`、`candidate_nodes_pre_edge.json` 和 canonicalized candidate edge snapshots；这些不是 candidate graph final review output。
- `parsed_source_segments.json` stores each segment's full `text` for replay/debug. Downstream draft, reconciliation, rubric, and edge intermediate artifacts reference segment ids, source locators, notes, and provenance, but do not copy segment text or full source text.
- `segment_node_extraction_drafts.json` stores intentionally thin drafts with only `draft_id`, `segment_id`, `name`, `definition`, `source_locator`, and `grounding_note`. Segment-level extraction must not generate rubrics, edges, type taxonomy, difficulty labels, prerequisite claims, or other downstream judgments.
- A valid parsed source segment may have an empty draft list when it contains no diagnosable concept; this is distinct from a failed, unparseable, or ungrounded segment output.
- The whole graph-authoring run fails if all valid segments together produce zero drafts; reconciliation needs at least one draft input and downstream skeleton/candidate artifacts must not be written in that case.
- `source_grounded_node_skeletons.json` stores clean rubric-step input only: `id`, `name`, `definition`, `source_locators`, and `source_grounding_notes`. Workflow code derives `id` deterministically from the reconciled canonical `name`, and that `id` is the final `KnowledgeNode.id`; do not add a separate `skeleton_id` to `node_id` mapping. Duplicate derived ids are reconciliation failures and should fail validation rather than being silently suffixed. Reconciliation provenance such as supporting draft ids, supporting segment ids, and merge or split notes stays in `node_skeleton_reconciliation.json` and is not passed to the rubric prompt.
- `candidate` 状态不写进 node/edge object。
- Full `Parsed Source Markdown` 会先被切成 `Parsed Source Segments`；Node Extraction Agent Step 只接收 segment-level `Source`、`Location` 和 `Text`，不接收整本文本。
- Node Skeleton Reconciliation Agent Step 读取结构化 `Segment Node Extraction Drafts` 和 source-grounding metadata，不回读 segment text 或 full source text。
- rubric authoring 只读取 source-grounded skeletons、source locators、source grounding notes 和 MasteryScale，不读取 unreviewed candidate edges。
- edge proposal 可以读取 complete candidate nodes、rubrics、source locators 和 source grounding notes，但仍然只产生 candidate edges。
- `workflow.py` 负责编排 step 顺序和每步后的 validation；具体 step 只负责把自己的 template、model client 和 parser 连接起来。
- `workflow.py` 判定 intermediate artifact 何时可信并调用 `output.py` helper 写盘；step implementation 不直接写 candidate graph 或 intermediate artifact files。
- `steps.py` 可以统一承载多个 step 接口和 LLM step 实现；只有在职责真正膨胀时才拆出 `node_extraction.py`、`node_skeleton_reconciliation.py`、`rubric_authoring.py` 或 `edge_proposal.py`。
- template 与 parser 不混写在 step class 中。每个 step 的 prompt 差异通过 `templates/node_extraction.py`、`templates/node_skeleton_reconciliation.py`、`templates/node_rubric_authoring.py`、`templates/edge_proposal.py` 表达，共享约束放在 `templates/common.py`；parser 仍可通过 `parsers/graph_authoring.py` 统一表达 raw model output 到 structured objects 的转换。
- rubric authoring 的 LLM output 只包含 node-level rubric patch；`id`、`name`、`type`、`definition` 和 `source_locators` 由 workflow 按 source-grounded skeleton `id` 确定性合并，避免让模型重复拷贝 source-grounded 字段。
- Large node-rubric authoring can be batched inside the concrete step implementation. The workflow still records one `node_rubric_authoring` entry, while the step trace may contain per-batch raw/parser artifacts.

### `llm/`

职责：隔离模型调用，避免 authoring、simulator、agents 各自散落 SDK 调用。

建议模块：

- `client.py`: `ModelClient` protocol。
- `messages.py`: prompt/message data structures。
- `openai_client.py`: Chat Completions-backed raw text adapter for current JSON authoring steps.
- Later, `adapters.py` can collect or split concrete provider adapters if provider support broadens.
- `tracing.py`: request/response metadata, redaction, replay hooks。

原则：

- domain schemas 不依赖 LLM SDK。
- prompt templates 输入输出尽量结构化，并优先放在调用方所属 workflow 的 `templates/` 目录中。
- model client 返回原始模型文本；workflow-specific parser 负责把输出解析成 domain schema。
- hidden map、hidden evidence、visible transcript 的边界在调用前显式构造。
- Phase 2 初始实现使用 OpenAI Python SDK-compatible adapters，通过 `.env.example` 中记录的环境变量配置 OpenAI 或 DeepSeek API key、model、base URL 和 timeout；`POST /api/authoring/graph-candidates`、`POST /api/simulator/turn` 和 `POST /api/tested-agents/simple-llm/turn-test` 通过 `client_provider` 在请求级选择 provider，默认 `openai`。
- 测试阶段的 PDF source material 可以放在仓库根目录 `storage/` 下，由 `/api/authoring` 按相对路径选择；authoring source preparation 先复用或生成同目录同 stem 的 `Parsed Source Markdown`，再派生 `Parsed Source Segments`，由后续 LLM steps 通过普通 text `ModelClient` 消费 segment 或结构化 intermediate artifacts。
- v1 graph authoring 不使用 PDF base64 `input_file`、OpenAI Files API `file_id` 或 PDF-specific LLM client path；MinerU 解析属于 `authoring/sources.py` 的 source preparation，Markdown segmentation 属于 `authoring/segments.py`。
- MinerU standard mode 通过私有阿里云 OSS bucket 的临时 staging object 生成短期 signed URL，再将 URL 提交给 MinerU v4；超过 `KNOWACT_MINERU_MAX_PAGES_PER_TASK` 的 PDF 会先在本地拆分为多个 chunk，逐块解析后按页码顺序拼接为一个 `Parsed Source Markdown`；OSS object 默认 best-effort 删除，signed URL 不进入 API response、workflow log 或 candidate graph artifacts。
- 测试和 development fixture 默认使用 fake 或 deterministic model clients，不应在普通 validation checks 中调用真实 OpenAI API。

### `simulator/`

职责：根据 hidden map 和 hidden evidence 生成自然但受约束的 simulator answer。

设计引用：`docs/UserSimulator.md` 定义 Phase 5 的 simulator workflow 和信息边界。该 workflow 是行为契约；实现可以合并或拆分步骤，但模块边界必须保留同样的可见性约束。

建议模块：

- `grounding.py`: Question Grounding over the visible `Authored Knowledge Graph` and `Visible Dialogue Context` only; produces grounded node ids, integrated-question flags, multiple-question flags, label-seeking flags, and no-grounding status without reading hidden map or hidden evidence.
- `context_builder.py`: after grounding, constructs simulator-only context for directly grounded nodes, including grounded rubrics, hidden `User Knowledge States`, grounded `Ground-Truth Evidence`, and visible dialogue needed for follow-up wording. It must not pull hidden neighboring-node state merely because of graph edges.
- `policy.py`: Answer Policy component. It consumes the grounded simulator-only context, grounding result, and current diagnostic question, then outputs one `Simulator Answer Blueprint` with the structured content blueprint for the answer.
- `generators.py`: Answer Generator interfaces and LLM/rule-based implementations. Generators consume the de-identified `Simulator Answer Blueprint`, visible dialogue, optional style hint, and optional regeneration guidance, then output candidate natural-language answers; LLM-backed answer prompt/message helpers must not consume raw reviewed maps.
- `style.py`: optional content-preserving style pass using confirmed `Profile Context` for tone, brevity, and wording only. It must not introduce profile-derived facts, examples, prior-experience claims, or ability claims unless those are already present as grounded evidence.
- `checks.py`: `Simulator Answer Validation`, including leakage checks, blueprint-coverage checks, consistency checks, fallback guidance, and validator-specific prompt/message helpers when using an LLM-backed validator. Validator inputs should be de-identified and should not become scoring signals.
- `fallbacks.py`: natural non-leaking safe fallback construction for no grounding, multiple independent questions, hidden-label requests, generator failure, validator failure, and system failure.
- `debug_trace.py`: local hidden turn trace writing, filesystem-safe trace ids, repeated question-directory overwrite behavior, and request-scoped raw/parser artifact capture for LLM-backed simulator steps.
- `service.py`: simulator turn orchestration; wires grounding, context building, answer policy, generation, validation, fallback, and hidden debug trace production.
- `turn.py`: stateless single-turn DTO/API boundary. The formal turn response selects reviewed artifacts by identity and exposes only visible answer data, coarse turn metadata, non-leaking warnings, and optional debug trace handles. A separate workbench/test response may add only directly grounded node ids for map highlighting.

边界：

- simulator 可以看到 hidden reviewed map。
- simulator 不把 mastery labels、hidden evidence ids、full state table 暴露给 tested agent。
- simulator answer 进入 transcript 后成为 tested-agent-visible `Interaction Observation`。
- simulator 可以在 formal episode manifest 存在前，通过 stateless single-turn flow 直接绑定 reviewed graph、reviewed map 和 optional confirmed profile context 来进行人工对话测试。
- simulator single-turn API 不是 benchmark run，也不产生 scoring report；它用于检查回答自然度、泄漏风险和 hidden-map 一致性。
- simulator single-turn API 通过 request-level `client_provider` 选择 LLM provider，使用与 authoring 相同的 `openai` / `deepseek` provider vocabulary，默认 `openai`。
- simulator single-turn API 每次请求都会写出隐藏的本地 **Simulator Debug Trace** 到 `benchmark/domains/{benchmark_domain}/simulator/{map_id}/{question_id_or_auto}/`；重复的 `question_id` 会清空并覆盖该 question 目录，只保留最后一次 turn trace。
- simulator turn debug trace 可以保存 LLM-backed simulator steps 的 raw model output 和 parser output，但不保存完整 prompt/messages、完整 reviewed graph、完整 reviewed map 或完整 confirmed profile context payload。
- `Question Grounding` 只解释被测 agent 已提出的问题；它不是 tested-agent question selection policy。
- hidden map state 和 hidden evidence 只能在 grounding 之后、针对 directly grounded nodes 进入 simulator-only context。
- `Simulator Answer Blueprint` 可以进入 hidden debug trace，但正式 visible transcript 和 scoring artifacts 不应存储 blueprint、grounded node ids、hidden evidence ids 或 validator internals。
- simulator workbench/test route 可以返回 minimal `grounded_node_ids` 供 benchmark author 高亮 inspected nodes；它不应返回 mastery labels、hidden evidence ids、raw debug trace、profile context 或其他 hidden payload。
- `Profile Context` 在 simulator runtime 中只用于 content-preserving wording style；回答内容必须先由 grounded user state、ground-truth evidence 和 answer blueprint 决定。

### `agents/`

职责：实现 tested agent 协议和 v1 baselines。

Decision reference: `docs/adr/0051-v1-tested-agents-use-working-map-semantic-tools.md`.

建议模块：

- `protocol.py`: tested-agent interface。
- `base.py`: phase-aware base class shared by fixed, random, and LLM tested agents.
- `agents/fixed_question.py`: `Fixed-Question Baseline`。
- `agents/random_question.py`: `Random-Question Baseline`。
- `agents/simple_llm.py`: `Simple LLM Agent`。
- `templates/`: prompt/message builders for tested-agent implementations.
- `providers.py`: tested-agent LLM provider vocabulary.
- `llm_agent.py`: provider-backed simple LLM tested-agent wiring.
- `working_map.py`: agent-owned full-graph working map schemas and update helpers for assessed mastery, diagnostic confidence, and assessment notes.
- `tools.py`: semantic tested-agent tool boundary for reading visible context, updating the working map, asking diagnostic questions, and finalizing reconstruction.
- `question_bank.py`: fixed baseline 的问题来源。
- `reconstruction.py`: final reconstructed map assembly helpers。

边界：

- tested agents 只能看到 authored graph、episode rules、visible transcript 和 visible observations。
- tested agents start each episode with an `Agent Working Knowledge Map` shell covering every node in the episode graph; node and edge identities come from the visible authored graph and are not agent-created.
- The initial working-map state per node contains `node_id`, `assessed_mastery_level`, `diagnostic_confidence`, `assessment_note`, and `supporting_turn_ids` only. Defer structured misconception and unknown reconstruction until after the mastery-focused active diagnosis loop works.
- tested-agent map mutation uses semantic operations such as `read_working_map`, `update_node_assessments`, and `finalize_reconstructed_map`; do not expose generic JSON patch or CRUD tools over graph/map artifacts.
- `update_node_assessments` accepts a batch of node-level assessment updates. Each item changes only one node's assessed mastery, diagnostic confidence, assessment note, and `supporting_turn_ids`; it must not add, delete, or mutate authored nodes or edges.
- Non-unknown assessment updates require a nonblank assessment note and at least one visible `supporting_turn_id`. Unknown assessments may leave both fields empty.
- `update_node_assessments` is atomic: if any item is invalid, the whole batch is rejected and the working map remains unchanged.
- A rejected working-map tool call does not consume an interaction turn. The tested agent may inspect the validation error, reorganize its update batch, and call the tool again within the same agent decision phase.
- Each agent decision phase should cap rejected working-map update retries, initially `max_tool_retries = 3`. When exhausted, mark the run or trace with `tool_retry_exhausted = true` and continue the phase without applying that update batch.
- `finalize_reconstructed_map` exports a full-graph `FinalReconstructionSubmission`; working-map nodes that still have unknown assessed mastery remain `unknown` so scoring can report them as missing predictions without coercing unknown to L0.
- If finalization sees a non-unknown working-map judgment without valid `supporting_turn_ids`, keep that non-unknown prediction in the `FinalReconstructionSubmission`, omit it from the evidence-backed `Final Reconstructed Knowledge Map` view, and emit a warning so scoring can report it as an unsupported inference.
- Initial `finalize_reconstructed_map` exports empty `misconceptions` and `unknowns` arrays for submitted states because Phase 7 working maps do not yet track those fields.
- Initial `finalize_reconstructed_map` mechanically wraps agent-selected `supporting_turn_ids` into reconstructed-map `EvidenceRecord` objects with `evidence_type = interaction_observation`, `visibility = tested_agent`, `turn_id` set to the cited visible turn, and `evidence_kind = prior_answer` by default. This is schema assembly, not runtime inference.
- Rejected finalization attempts may be retried with the same `max_tool_retries = 3` limit. If early finalization retry is exhausted while turns remain, the agent returns to the normal question/update loop; if forced-finalization retry is exhausted, the runner uses forced finalization fallback.
- The tested agent is responsible for constructing the full-graph final reconstruction submission and choosing tested-agent-visible support for its reconstructed states. Runtime may validate references, but it must not infer mastery or auto-fill reconstructed states on the agent's behalf.
- Runtime validation of `supporting_turn_ids` is visibility and existence checking only; it does not judge whether the cited turns semantically prove the assessment.
- The runner follows an answer-driven update cycle: after the first question, the tested agent updates its working map only after receiving the latest visible simulator answer, then asks the next question or finalizes.
- The tested agent should not update its working map while waiting for a simulator answer.
- A tested agent may finalize before exhausting `max_turns`; the runner ends the episode once a valid final reconstruction submission is submitted.
- If `max_turns` is exhausted without a final submission, the runner enters forced finalization: the tested agent may read visible context and submit the final map, but it may not ask another diagnostic question.
- If forced finalization fails or times out, the runner may mechanically export the current working map into a fallback full-graph final reconstruction submission. Mark the run output with `forced_finalization_fallback = true`.
- Fixed, random, and simple LLM baselines all use the same working-map and finalization tool path; fixed-question exists as a deterministic floor for regression and smoke testing.
- Simple LLM agents may update multiple node assessments after a turn, including indirectly inferred nodes, but they must still use the semantic working-map tools rather than producing final reconstructed-map JSON directly from the transcript.
- v1 baseline set 不包含 oracle、passive summarization、teaching agent 或复杂 ToM agent。

Run output policy:

- Persist the latest agent working map as `working_map.json` for inspection and forced-finalization fallback.
- Persist append-only tested-agent tool calls and validation outcomes as `agent_tool_trace.json`.
- Do not persist full per-turn working-map snapshots by default in Phase 7; the append-only tool trace should be sufficient for replay/debug unless a later failure mode justifies snapshot artifacts.

### `runtime/`

职责：执行 `Evaluation Episode`。

建议模块：

- `episode_repository.py`: 读取 `Runtime Episode Registry` 中的 episode manifest。
- `episode_loader.py`: 加载 identity-first manifest、reviewed graph、reviewed map、derived profile context。
- `visibility.py`: 构造 tested-agent-visible context 和 simulator-only context reference，并验证 hidden data 不进入 tested-agent-visible payload。
- `turn_loop.py`: one diagnostic question + one simulator answer。
- `runner.py`: orchestrate episode start/end。
- `transcript.py`: transcript and interaction observation recording。

Phase 6 的初始 runtime scope 是 contract skeleton：episode registry、manifest loading、artifact binding、visibility context construction 和 read-only runtime API。它不启动 formal run，不调用 tested agent 或 simulator，不产生 transcript、agent output 或 scoring report；`turn_loop.py`、`runner.py` 和 `transcript.py` 在 Phase 7-9 接入。

`Evaluation Episode Manifest` 在 Phase 6 采用 identity-first binding，而不是自由 artifact URI：

- `episode_id`
- `benchmark_domain`
- `graph_version`
- `hidden_map_id`
- `max_turns`
- `interaction_rule = single_diagnostic_question_per_turn`
- `scoring_profile = squared_mastery_distance_v1`

runtime 的核心 flow：

```text
load Evaluation Episode Manifest from Runtime Episode Registry
  -> load reviewed Authored Knowledge Graph
  -> load reviewed Map and derive profile context from the map manifest user_id
  -> build simulator-only context
  -> build tested-agent-visible context
  -> Phase 6 stops here for read-only inspection
  -> Phase 7-9 continue:
  -> initialize Agent Working Knowledge Map over the episode graph
  -> first turn:
       agent asks one Diagnostic Question from the visible graph and empty working-map evidence
       simulator answers naturally
       runtime records visible Interaction Observation
  -> repeat until max_turns or finalization:
       agent updates its working map from the latest visible answer
       agent either asks one next Diagnostic Question or finalizes
       if a question is asked, simulator answers naturally
       runtime records visible Interaction Observation
  -> agent submits Final Reconstruction Submission
  -> scoring compares final submission with hidden map
  -> report is written
```

### `scoring/`

职责：实现 `Structured Map Comparison` 和 fixed scoring profile。

建议模块：

- `profiles.py`: `squared_mastery_distance_v1` definition。
- `distance.py`: L0-L5 to 0-5, squared distance, missing prediction penalty 36。
- `compare.py`: per-node comparison between a full-graph `FinalReconstructionSubmission` and the hidden reviewed map。
- `unsupported.py`: unsupported inference detection。
- `aggregate.py`: episode-level metrics。

边界：

- scoring 不调用 LLM。
- scoring 不读取 profile context 作为主分数。
- unsupported inference 单独报告，不覆盖 mastery distance。

### `reports/`

职责：把 scoring output 组织成研究可读结果。

建议输出：

- per-node comparison table。
- per-node signed mastery error。
- episode mastery distance。
- exact mastery match rate。
- missing prediction rate。
- unsupported inference rate。
- optional misconception diagnostics。
- run metadata and scoring profile version。

### `api/`

职责：FastAPI 入口，主要服务 research workbench 和人工 review。

建议路由：

- `GET /health`
- `GET /api/authoring/benchmark-domains`
- `GET /api/authoring/graphs/{benchmark_domain}`
- `GET /api/authoring/graphs/{benchmark_domain}/{version}`
- `POST /api/authoring/graph-candidates`
- `GET /api/authoring/users/{benchmark_domain}`
- `GET /api/authoring/users/{benchmark_domain}/{user_id}`
- `POST /api/authoring/profile-context-candidates`
- `GET /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}`
- `PUT /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}`
- `POST /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}/confirmation`
- `POST /api/authoring/map-candidates`
- `GET /api/authoring/candidate-maps/{benchmark_domain}`
- `GET /api/authoring/candidate-maps/{benchmark_domain}/{run_id}`
- `POST /api/authoring/candidate-maps/{benchmark_domain}/{run_id}/promotion`
- `GET /api/authoring/maps/{benchmark_domain}`
- `GET /api/authoring/maps/{benchmark_domain}/{map_id}`
- `GET /graphs`
- `GET /graphs/{graph_id}`
- `GET /maps/{map_id}`
- `POST /api/runtime/episodes`
- `GET /api/runtime/episodes`
- `GET /api/runtime/episodes/{episode_id}`
- `POST /api/runtime/episodes/{episode_id}/runs`
- `GET /api/runtime/runs/{run_id}/transcript`
- `POST /api/tested-agents/simple-llm/turn-test`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/report`

Phase 4 的初始 authoring surface 保持 narrow and functional：profile-context candidate 支持生成、读取、编辑和显式 confirmation；candidate map 支持生成、读取、列出 runs 和显式 promotion，但不提供 map `PUT`，因为 poor candidate maps 应重新生成而不是手工 patch。为支持 workbench selectors 和 simulator 前端入口，允许只读 `GET /api/authoring/benchmark-domains`、reviewed graph/profile list/read、candidate-map run list，以及 reviewed-map list/read；这些接口不创建或修改 benchmark data，也不启动 simulator runtime。调用方显式串联窄接口，使 profile-context editing、confirmation、candidate-map inspection 和 promotion 保持可见 gate；待闭环调通后再考虑更宽的 orchestration 产品形态。

Phase 6 的 runtime surface 开放 `POST /api/runtime/episodes`、`GET /api/runtime/episodes` 和 `GET /api/runtime/episodes/{episode_id}`。`POST /api/runtime/episodes` 执行 `Episode Manifest Registration`，request 只暴露 `episode_id`、`benchmark_domain`、`graph_version`、`hidden_map_id` 和 `max_turns`；runtime service 固定写入 `interaction_rule = single_diagnostic_question_per_turn` 与 `scoring_profile = squared_mastery_distance_v1`，同步加载并校验 reviewed graph 与 reviewed hidden map binding，只有 binding 通过且 `episode_id` 尚不存在时才把 `Evaluation Episode Manifest` 发布到 `Runtime Episode Registry`，不启动 run。Successful registration 返回 `201 Created` 和 runtime management detail envelope；重复 `episode_id` 或 graph/map identity mismatch 返回 `409 Conflict`，reviewed artifact loading failure 返回 `424 Failed Dependency`。Missing confirmed Profile Context 不阻塞 registration；它只作为 runtime management status/warning 返回。Episode registration 不支持 overwrite；修改 graph、map 或 budget 必须注册新的 `episode_id`。Runtime management detail response 面向 benchmark author，可返回 `hidden_map_id`、reviewed map `user_id`、profile-context load status 和 non-leaking missing-profile warning 供前端展示，但不返回 hidden states、hidden evidence、profile context payload、debug traces、simulator answer blueprint、transcript 或 scoring report；profile context 正文应通过 profile/user inspection surface 查看。其中的 tested-agent-visible context preview 是同一 response 中唯一可交付给 tested agent 的子对象，必须排除 `hidden_map_id`、`map_id`、`user_id`、profile-context status、warnings 和任何 hidden payload。不要为了 frontend management 和 tested-agent delivery 拆出两套 Phase 6 HTTP routes；边界靠 response 分层和 runtime 交付选择来保证。

Phase 7-9 的初始 run surface 开放 `POST /api/runtime/episodes/{episode_id}/runs`。它从已注册 episode 启动一个 Episode Run，request 使用 `agent_kind` 选择 tested-agent implementation（首版仅 `simple_llm_agent`），并分离 `tested_agent_client_provider` 与 `simulator_client_provider`，可选 `run_id` 不覆盖已有 run。成功 response 返回 run metadata、artifact paths 和 scoring report；正式 artifacts 写入 `experiments/runs/{run_id}/`。该 response 不内联 transcript、working map、agent tool trace、hidden map identity、profile context、simulator debug trace、answer blueprint 或 hidden evidence。`GET /api/runtime/runs/{run_id}/transcript` 是 benchmark-author-facing run artifact read endpoint，只返回 visible `VisibleDialogueContext` turns，仍不得返回 simulator debug trace ids、grounded node ids、answer blueprints、hidden evidence ids、profile context 或 validation internals。

Phase 7 的 development/test surface 允许 `POST /api/tested-agents/simple-llm/turn-test` 直接调用 `Simple LLM Agent` 做人工调试。该 route stateless 地加载 reviewed graph，接收 tested-agent-visible `VisibleDialogueContext` 和可选 `AgentWorkingKnowledgeMap`，必要时初始化 working map，应用本轮 working-map updates，然后返回下一步 tested-agent decision。它不读取 hidden map、不调用 simulator、不写 transcript、不注册 runtime run，也不产生 scoring report。

`POST /api/authoring/profile-context-candidates` 接收 required `benchmark_domain`、required `rough_description`、optional limited `domain_summary`、optional `run_id` 和 request-level `client_provider`。首版允许 inline `domain_summary`，但其中不得包含 node 或 rubric 明细；后续可由 domain manifest 提供稳定 summary。

## Benchmark Data Layout

建议把 benchmark data 分为 fixtures、candidate、reviewed、runtime registry 和 runs。

```text
benchmark/
├── fixtures/
│   └── statistical_learning_with_python_dev/
│       ├── graph_manifest.json
│       ├── authored_nodes.json
│       ├── authored_edges.json
│       ├── maps/
│       └── episodes/
├── domains/
│   └── statistical_learning_with_python/
│       ├── sources/
│       │   └── isl_python.md
│       ├── candidate_graphs/
│       │   └── run_001/
│       │       ├── candidate_nodes.json
│       │       ├── candidate_edges.json
│       │       ├── workflow_log.json
│       │       ├── intermediate/
│       │       │   ├── parsed_source_segments.json
│       │       │   ├── segment_node_extraction_drafts.json
│       │       │   ├── node_skeleton_reconciliation.json
│       │       │   └── source_grounded_node_skeletons.json
│       │       └── agent_traces/
│       ├── graphs/
│       │   └── v1/
│       │       ├── graph_manifest.json
│       │       ├── authored_nodes.json
│       │       └── authored_edges.json
│       ├── candidate_profile_contexts/
│       │   └── run_001/
│       │       ├── candidate_profile_context.json
│       │       ├── workflow_log.json
│       │       └── agent_traces/
│       │           ├── model_raw_output.txt
│       │           └── parser_output.json
│       ├── users/
│       ├── candidate_maps/
│       │   └── run_001/
│       │       ├── candidate_map.json
│       │       ├── consistency_warnings.json
│       │       ├── workflow_log.json
│       │       ├── intermediate/
│       │       │   ├── state_outline.json
│       │       │   └── ground_truth_evidence.json
│       │       └── agent_traces/
│       │           ├── knowledge_state_outline/
│       │           │   ├── model_raw_output.txt
│       │           │   └── parser_output.json
│       │           └── ground_truth_evidence/
│       │               └── batch_001/
│       │                   ├── model_raw_output.txt
│       │                   └── parser_output.json
│       └── maps/
└── runtime/
    └── episodes/
        └── episode_001/
            └── episode_manifest.json
```

```text
experiments/
├── runs/
│   └── run_2026_...
│       ├── episode_manifest_snapshot.json
│       ├── transcript.json
│       ├── working_map.json
│       ├── agent_tool_trace.json
│       ├── agent_output.json
│       └── scoring_report.json
└── reports/
    └── v1_baseline_report.md
```

Artifact policy:

- `fixtures/` 可以小而稳定，用于 tests 和 local development。
- `candidate_graphs/` 和 `candidate_maps/` 是 review input，不进入 formal evaluation。
- `graphs/{version}/` 和 `maps/` 是 reviewed benchmark data；只有明确要发布或保留时才应加入版本库。
- `runtime/episodes/` 是 `Runtime Episode Registry`；它可以收集跨 benchmark domain 的 runnable episodes，但每个 manifest 仍只绑定一个 benchmark domain、一个 reviewed graph version 和一个 hidden reviewed map。
- Phase 3 graph promotion 将重新校验后的 candidate snapshot 复制到 `graphs/{version}/`，保留原 candidate run，并生成只绑定 metadata 与 node/edge 文件引用的 `graph_manifest.json`。Reviewed graph version 不允许覆盖；修订必须发布新的 version。
- `experiments/runs/` 是 generated output，应避免混入人工 authored ground truth。
- 大型 source PDFs 可以本地保存，正式数据只引用 source metadata 和 `Source Locator`。

## Frontend Architecture

frontend 是 research tooling，不是营销首页。建议在 M8 后扩展，早期只做必要 inspection。

```text
frontend/src/
├── app/
│   ├── routes.tsx
│   └── shell.tsx
├── api/
│   ├── client.ts
│   └── types.ts
├── features/
│   ├── graphs/
│   ├── maps/
│   ├── episodes/
│   ├── runs/
│   └── reports/
└── components/
    ├── layout/
    ├── tables/
    └── visualization/
```

核心视图：

- Graph inspector: 展示 nodes、edges、source locators、edge rationale、weight、curation confidence。
- Map inspector: 展示 node-level `User Knowledge State`、mastery、evidence refs。
- Episode runner: 展示 manifest、turn budget、visible context、transcript。
- Report viewer: 展示 per-node distances、missing prediction、unsupported inference、episode mastery distance。
- Review helper: 辅助 benchmark author 检查 candidate nodes/edges/maps，但不自动 promote。

当前 `Episodes` frontend module 属于 Runtime navigation，排在 `Simulator` 之后。Create Episode 入口执行 **Episode Manifest Registration**：用户选择 `benchmark_domain` 和一个 reviewed `map_id`，前端从 reviewed map manifest 派生 `graph_version`，再向 `POST /api/runtime/episodes` 提交 `episode_id`、`benchmark_domain`、`graph_version`、`hidden_map_id` 和 `max_turns`。`interaction_rule = single_diagnostic_question_per_turn` 与 `scoring_profile = squared_mastery_distance_v1` 是固定 v1 runtime contract，不作为可编辑表单字段。

Run Episode backend route 已经开放为 `POST /api/runtime/episodes/{episode_id}/runs`，`frontend/src/api/runtime.ts` 与 `Episodes` workbench 保持与该 request/response contract 对齐。Workbench 中的 Run Episode UI 调用初始 `simple_llm_agent` runner slice，允许 benchmark author 选择 tested-agent/simulator provider、提交可选 `run_id`，并查看 run metadata、visible transcript、score summary、per-node comparison 与 artifact paths。Run transcript 通过 `GET /api/runtime/runs/{run_id}/transcript` 读取；Run trigger 必须继续与 Episode Manifest Registration 分离。

UI 边界：

- graph view 不展示 user state。
- map view 不把 edge 当成 user state。
- tested-agent-visible view 不显示 hidden evidence、hidden map 或 simulator-only context。
- formal v1 run 应明确标记 reviewed artifacts；development fixture run 应明确标记 fixture。

## Milestone-To-Module Map

| Milestone | Primary modules | Notes |
| --- | --- | --- |
| M1 schema and validation | `core/`, `validation/`, `storage/`, `test/` | 先建立对象与校验主干 |
| M2 graph authoring | `authoring/`, `llm/`, `storage/` | 产出 candidate node/edge JSON lists |
| M3 graph review promotion | `storage/`, `validation/`, optional review UI | reviewed graph 才能进入 runtime |
| M4 maps | `authoring/`, `core/`, `validation/`, `storage/` | map coverage 和 evidence visibility 是重点 |
| M5 simulator | `simulator/`, `llm/`, `storage/`, `validation/` | reviewed-map grounded turns 和 leakage guard 是关键风险 |
| M6 episode contract | `core/episode.py`, `storage/`, `runtime/episode_repository.py`, `runtime/episode_loader.py`, `runtime/visibility.py`, `api/`, `validation/` | runtime registry、identity-first manifest、reviewed artifact binding、visible context inspection |
| M7 baselines | `agents/`, `runtime/turn_loop.py` | fixed/random/simple LLM 共用协议 |
| M8 scoring reports | `scoring/`, `reports/`, `storage/` | 不调用 LLM，不读取 persona 作主分数 |
| M9 end-to-end v1 | `runtime/`, `agents/`, `simulator/`, `scoring/` | 第一份可解释 experiment report |
| M10 workbench | `api/`, `frontend/` | 支持检查、运行、报告浏览 |

## Test Strategy

测试应先覆盖结构化约束，再覆盖 LLM-adjacent behavior。

建议测试层级：

- schema tests: Pydantic object parsing and serialization。
- validation tests: graph references、map coverage、evidence visibility、manifest scoring profile。
- scoring tests: squared mastery distance、missing penalty 36、unsupported inference rate。
- runtime tests: registry loading、manifest artifact binding、max_turns、visibility context construction。
- simulator guard tests: 不泄露 mastery labels、hidden evidence ids、full map。
- end-to-end fixture tests: 5-8 node development fixture 跑完整 episode。

首个推荐命令仍可保持简单：

```text
uv run python -m unittest
```

## Open Review Questions

1. 是否接受 `backend/knowact/` 作为 Python package 根目录？
   - 推荐：接受。它保留 `backend/` 边界，也让 FastAPI 和 benchmark core 不散落在仓库根目录。

2. 是否接受 `benchmark/` 作为 reviewed benchmark data 和 development fixtures 的根目录？
   - 推荐：接受。它比 `data/` 更明确表达这些文件是 benchmark artifacts，不是普通应用数据。

3. 是否接受 `experiments/` 作为 run output 和 report 的根目录？
   - 推荐：接受，但默认不要提交大体积 run outputs；只提交精选 reports 或小型 fixture outputs。

4. authoring workflow 是否应该通过 API 暴露？
   - 推荐：暴露一条窄的 source-backed candidate graph run API，用于真实运行和人工检查生成质量；它以本地 PDF 为入口，先解析或复用同目录 Markdown，再派生 Parsed Source Segments，并让 LLM steps 只消费 bounded segment text 或 structured intermediate artifacts。它只能写 candidate artifacts，不能 promote reviewed graph data。review workflow 稳定后再扩展 UI/API。

5. frontend 是否进入 v1 必需路径？
   - 推荐：不是 M1-M8 的必需路径。M10 再扩展 research workbench；早期可只做最小 inspection。
