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
  -> Ground-Truth Knowledge Map authoring and review
  -> Evaluation Episode Manifest
  -> User Simulator + Tested Agent interaction
  -> Final Reconstructed Knowledge Map
  -> Structured Map Comparison
  -> Evaluation Report
```

核心约束：

- `Knowledge Graph` 和 `Knowledge Map` 必须分离。
- graph/map/schema/scoring 优先结构化，不把核心对象藏在 prompt 字符串里。
- candidate authoring data 与 reviewed benchmark data 必须分离。
- evaluation runtime 只能使用 reviewed graph 和 reviewed ground-truth maps。
- `Visibility Boundary` 必须由 runtime 和数据访问层共同保证，而不是只靠 prompt 约束。
- v1 的正式 benchmark graph 目标是 30-50 nodes；小图只能作为 development fixture。

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
│   └── fixtures/
├── experiments/
│   ├── runs/
│   └── reports/
└── test/
```

说明：

- `backend/knowact/` 是 benchmark 的 Python package 主体。
- `benchmark/` 存放可版本化的 benchmark data，包括 development fixtures、candidate review data、reviewed graph/map/episode manifests。
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

- `schemas.py`: authoring-only schemas, including `SourceMaterial`, `Source-Grounded Node Skeleton`, list wrappers, and workflow result objects.
- `workflow.py`: `GraphAuthoringAgentWorkflow` orchestration, including step order, dependency direction, and validation checkpoints.
- `steps.py`: graph authoring step protocols and concrete step implementations. `Node Extraction Agent Step`, `Node Rubric Authoring Agent Step`, and `Edge Proposal Agent Step` can live in this single module; they are workflow responsibilities, not required one-file-per-step modules.
- `templates/common.py`: shared graph-authoring prompt components such as source-grounding rules, node design rules, MasteryScale guidance, edge type definitions, schema/output contracts, and JSON serialization helpers.
- `templates/node_extraction.py`, `templates/node_rubric_authoring.py`, `templates/edge_proposal.py`: prompt/message builders for each Graph Authoring Agent Workflow step. `templates/graph_authoring.py` can remain as a compatibility re-export only; step-specific prompt content should live in the step-specific template file.
- `parsers/graph_authoring.py`: raw model-output parsers that turn JSON text into source skeletons, candidate nodes, and candidate edges.
- `validation.py`: authoring-specific validation around skeleton grounding, complete candidate node rubrics, and candidate edge graph validity.
- `logging.py`: authoring run log schemas and helpers for structured, redacted `Graph Authoring Run Log` records, including links to external agent-step raw model outputs and parser outputs for local debugging.
- `output.py`: candidate graph file export, especially `candidate_nodes.json` and `candidate_edges.json`, plus sidecar `workflow_log.json` export.
- `sources.py`: authoring source preparation, including resolving cached `Parsed Source Markdown`, splitting PDFs that exceed MinerU's per-task page limit into local chunks, temporarily publishing local PDFs or PDF chunks through private Aliyun OSS signed URLs for MinerU standard-mode parsing, joining chunk Markdown in page order, calling MinerU when a same-directory same-stem Markdown file is missing or explicitly regenerated, and keeping source parsing outside the `llm/` completion boundary.
- `openai_workflow.py`: shared graph authoring workflow wiring behind the `ModelClient` interface, with provider selection for OpenAI and DeepSeek clients.
- Later, add `map_authoring.py` and `review_export.py` when ground-truth map generation and human review promotion need concrete workflow support.

边界：

- graph authoring final output 只能是 `candidate_nodes.json` 和 `candidate_edges.json` 两个 JSON list files。
- `workflow_log.json` 可以作为 run directory 中的 sidecar artifact 存在，并记录 agent step 状态、counts、错误和 trace artifact URI；LLM raw output 与 parser output 分别写入 `agent_traces/{step}/model_raw_output.txt` 与 `agent_traces/{step}/parser_output.json`。这些都不是 candidate graph final review output，也不改变 node/edge JSON list schema。
- `candidate` 状态不写进 node/edge object。
- rubric authoring 不读取 unreviewed candidate edges。
- edge proposal 可以读取 complete candidate nodes 和 rubrics，但仍然只产生 candidate edges。
- `workflow.py` 负责编排 step 顺序和每步后的 validation；具体 step 只负责把自己的 template、model client 和 parser 连接起来。
- `steps.py` 可以统一承载多个 step 接口和 LLM step 实现；只有在职责真正膨胀时才拆出 `node_extraction.py`、`rubric_authoring.py` 或 `edge_proposal.py`。
- template 与 parser 不混写在 step class 中。每个 step 的 prompt 差异通过 `templates/node_extraction.py`、`templates/node_rubric_authoring.py`、`templates/edge_proposal.py` 表达，共享约束放在 `templates/common.py`；parser 仍可通过 `parsers/graph_authoring.py` 统一表达 raw model output 到 structured objects 的转换。
- rubric authoring 的 LLM output 只包含 node-level rubric patch；`id`、`name`、`type`、`definition` 和 `source_locators` 由 workflow 按 skeleton id 确定性合并，避免让模型重复拷贝 source-grounded 字段。

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
- Phase 2 初始实现使用 OpenAI Python SDK-compatible adapters，通过 `.env.example` 中记录的环境变量配置 OpenAI 或 DeepSeek API key、model、base URL 和 timeout；`POST /api/authoring/graph-candidates` 通过 `client_provider` 在请求级选择 provider，默认 `openai`。
- 测试阶段的 PDF source material 可以放在仓库根目录 `storage/` 下，由 `/api/authoring` 按相对路径选择；authoring source preparation 先复用或生成同目录同 stem 的 `Parsed Source Markdown`，再通过普通 text `ModelClient` 发送给 LLM。
- v1 graph authoring 不使用 PDF base64 `input_file`、OpenAI Files API `file_id` 或 PDF-specific LLM client path；MinerU 解析属于 `authoring/sources.py` 的 source preparation。
- MinerU standard mode 通过私有阿里云 OSS bucket 的临时 staging object 生成短期 signed URL，再将 URL 提交给 MinerU v4；超过 `KNOWACT_MINERU_MAX_PAGES_PER_TASK` 的 PDF 会先在本地拆分为多个 chunk，逐块解析后按页码顺序拼接为一个 `Parsed Source Markdown`；OSS object 默认 best-effort 删除，signed URL 不进入 API response、workflow log 或 candidate graph artifacts。
- 测试和 development fixture 默认使用 fake 或 deterministic model clients，不应在普通 validation checks 中调用真实 OpenAI API。

### `simulator/`

职责：根据 hidden map 和 hidden evidence 生成自然但受约束的 simulator answer。

建议模块：

- `context_builder.py`: 构造 simulator-only context。
- `prompting.py`: simulator prompt。
- `policy.py`: leakage guard 和 grounded ambiguity policy。
- `service.py`: simulator turn service。
- `checks.py`: answer leakage and consistency checks。

边界：

- simulator 可以看到 hidden ground-truth map。
- simulator 不把 mastery labels、hidden evidence ids、full state table 暴露给 tested agent。
- simulator answer 进入 transcript 后成为 tested-agent-visible `Interaction Observation`。

### `agents/`

职责：实现 tested agent 协议和 v1 baselines。

建议模块：

- `protocol.py`: tested-agent interface。
- `fixed_question.py`: `Fixed-Question Baseline`。
- `random_question.py`: `Random-Question Baseline`。
- `simple_llm.py`: `Simple LLM Agent`。
- `question_bank.py`: fixed baseline 的问题来源。
- `reconstruction.py`: final reconstructed map assembly helpers。

边界：

- tested agents 只能看到 authored graph、episode rules、visible transcript 和 visible observations。
- v1 baseline set 不包含 oracle、passive summarization、teaching agent 或复杂 ToM agent。

### `runtime/`

职责：执行 `Evaluation Episode`。

建议模块：

- `episode_loader.py`: 加载 manifest、reviewed graph、reviewed map、profile context。
- `visibility.py`: 构造 tested-agent-visible context 和 simulator-only context。
- `turn_loop.py`: one diagnostic question + one simulator answer。
- `runner.py`: orchestrate episode start/end。
- `transcript.py`: transcript and interaction observation recording。

runtime 的核心 flow：

```text
load Evaluation Episode Manifest
  -> load reviewed Authored Knowledge Graph
  -> load reviewed Ground-Truth Knowledge Map
  -> build simulator-only context
  -> build tested-agent-visible context
  -> repeat until max_turns:
       agent asks one Diagnostic Question
       simulator answers naturally
       runtime records visible Interaction Observation
  -> agent submits Final Reconstructed Knowledge Map
  -> scoring compares final map with hidden map
  -> report is written
```

### `scoring/`

职责：实现 `Structured Map Comparison` 和 fixed scoring profile。

建议模块：

- `profiles.py`: `squared_mastery_distance_v1` definition。
- `distance.py`: L0-L5 to 0-5, squared distance, missing prediction penalty 36。
- `compare.py`: per-node map comparison。
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
- episode mastery distance。
- missing prediction rate。
- unsupported inference rate。
- optional confidence calibration。
- optional misconception diagnostics。
- run metadata and scoring profile version。

### `api/`

职责：FastAPI 入口，主要服务 research workbench 和人工 review。

建议路由：

- `GET /health`
- `POST /api/authoring/graph-candidates`
- `GET /graphs`
- `GET /graphs/{graph_id}`
- `GET /maps/{map_id}`
- `GET /episodes`
- `GET /episodes/{episode_id}`
- `POST /episodes/{episode_id}/runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/report`

早期可以先只做 authoring candidate run trigger、read-only inspection 和 evaluation run trigger。authoring API 只能生成 reviewable candidate graph artifacts；promotion/review 写操作等核心闭环稳定后再开放。

## Benchmark Data Layout

建议把 benchmark data 分为 fixtures、candidate、reviewed、episodes 和 runs。

```text
benchmark/
├── fixtures/
│   └── classical_supervised_ml_algorithms_dev/
│       ├── graph_manifest.json
│       ├── authored_nodes.json
│       ├── authored_edges.json
│       ├── ground_truth_maps/
│       └── episodes/
└── domains/
    └── classical_supervised_ml_algorithms/
        ├── sources/
        │   └── isl_python.source.json
        ├── candidate_graphs/
        │   └── run_001/
        │       ├── candidate_nodes.json
        │       ├── candidate_edges.json
        │       ├── workflow_log.json
        │       └── agent_traces/
        ├── graphs/
        │   └── v1/
        │       ├── graph_manifest.json
        │       ├── authored_nodes.json
        │       └── authored_edges.json
        ├── candidate_maps/
        ├── ground_truth_maps/
        └── episodes/
            └── v1/
                └── episode_001.json
```

```text
experiments/
├── runs/
│   └── run_2026_...
│       ├── episode_manifest_snapshot.json
│       ├── transcript.json
│       ├── agent_output.json
│       └── scoring_report.json
└── reports/
    └── v1_baseline_report.md
```

Artifact policy:

- `fixtures/` 可以小而稳定，用于 tests 和 local development。
- `candidate_graphs/` 和 `candidate_maps/` 是 review input，不进入 formal evaluation。
- `graphs/v1/` 和 `ground_truth_maps/` 是 reviewed benchmark data。
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
- Map inspector: 展示 node-level `User Knowledge State`、mastery、confidence、evidence refs。
- Episode runner: 展示 manifest、turn budget、visible context、transcript。
- Report viewer: 展示 per-node distances、missing prediction、unsupported inference、episode mastery distance。
- Review helper: 辅助 benchmark author 检查 candidate nodes/edges/maps，但不自动 promote。

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
| M4 ground-truth maps | `authoring/`, `core/`, `validation/`, `storage/` | map coverage 和 evidence visibility 是重点 |
| M5 episode contract | `core/episode.py`, `runtime/episode_loader.py`, `validation/` | manifest 绑定 graph/map/rules/scoring |
| M6 simulator | `simulator/`, `llm/`, `runtime/visibility.py` | leakage guard 是关键风险 |
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
- runtime tests: one-turn contract、max_turns、visibility context construction。
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
   - 推荐：暴露一条窄的 source-backed candidate graph run API，用于真实运行和人工检查生成质量；它以本地 PDF 为入口，先解析或复用同目录 Markdown，再把 Markdown 作为 LLM text input。它只能写 candidate artifacts，不能 promote reviewed graph data。review workflow 稳定后再扩展 UI/API。

5. frontend 是否进入 v1 必需路径？
   - 推荐：不是 M1-M8 的必需路径。M10 再扩展 research workbench；早期可只做最小 inspection。
