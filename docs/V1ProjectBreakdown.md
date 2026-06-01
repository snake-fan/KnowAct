# KnowAct V1 Project Breakdown

Status: Draft for review

This document turns the current `CONTEXT.md` glossary and v1 ADRs into an execution breakdown. It is not a new ADR. If this plan conflicts with `CONTEXT.md` or an accepted ADR, the glossary and ADRs take precedence.

## V1 Anchor Decisions

KnowAct v1 is an active knowledge-state diagnosis benchmark. The tested agent asks diagnostic questions to infer a fixed hidden `Ground-Truth Knowledge Map` over a visible `Authored Knowledge Graph`; it does not teach, tutor, or update the user's hidden state during an episode.

The first benchmark domain is `classical_supervised_ml_algorithms`, grounded primarily in *An Introduction to Statistical Learning with Applications in Python*. The formal v1 graph targets 30-50 reviewed `Knowledge Nodes`, with reviewed `Knowledge Edges`, reviewed `Ground-Truth Knowledge Maps`, explicit `Evaluation Episode Manifests`, and one fixed scoring profile: `squared_mastery_distance_v1`.

The implementation should prioritize a narrow vertical slice first, but any small graph used before the 30-50 node graph must be treated as a development fixture, not as the formal v1 benchmark graph.

## Phase Overview

| Phase | Milestone | Completion Signal |
| --- | --- | --- |
| 0. Domain decision baseline | M0: v1 design baseline accepted | Existing glossary and ADRs are consistent enough to guide implementation |
| 1. Schema and validation spine | M1: core structured objects validate | JSON fixtures for graph, maps, evidence, manifests, and scoring config pass schema checks |
| 2. Graph authoring workflow | M2: source-grounded candidate graph workflow runs | Workflow produces `candidate_nodes.json` and `candidate_edges.json` from authoritative source material |
| 3. Authored graph review and promotion | M3: reviewed v1 graph exists | Reviewed `authored_nodes.json`, `authored_edges.json`, and `graph_manifest.json` are available |
| 4. Ground-truth map authoring | M4: reviewed hidden maps exist | Each map covers every node in the episode graph and cites hidden evidence |
| 5. Episode runtime contract | M5: evaluation episode manifests validate | Manifests bind graph, hidden map, profile context, turn budget, interaction rule, and scoring profile |
| 6. User simulator | M6: simulator can answer bounded diagnostic turns | Simulator answers naturally without leaking mastery labels, hidden evidence ids, or full maps |
| 7. Tested agent interface and baselines | M7: baseline agents complete episodes | Fixed-question, random-question, and simple LLM agents submit final reconstructed maps |
| 8. Scoring and reports | M8: structured reports are reproducible | Reports include episode mastery distance, missing prediction rate, and unsupported inference rate |
| 9. End-to-end v1 benchmark run | M9: first v1 experiment report | Reviewed episodes run across v1 baselines with interpretable results and failure notes |
| 10. Research workbench | M10: reviewable UI/API surface | A minimal research interface supports graph/map inspection, episode review, and report browsing |
| 11. Post-v1 expansion | M11: next benchmark question selected | Multi-domain, teaching actions, real users, or richer agents are considered after v1 evidence |

## Graph Authoring API Surface

Before the formal research workbench is complete, the backend exposes narrow authoring and review endpoints for manually exercising the real graph authoring workflow and explicitly promoting reviewed candidate snapshots. This surface is separate from formal evaluation runtime.

Current opened endpoint:

- `GET /health`: backend process health.
- `POST /api/authoring/graph-candidates`: reads one local textbook PDF by relative path under repository-level `storage/`, resolves same-directory same-stem `Parsed Source Markdown`, calls MinerU to create or regenerate that Markdown when needed, sends the Markdown text only to the Node Extraction Agent Step using the request-level `client_provider`, and returns `Source-Grounded Node Skeletons`, candidate `Knowledge Nodes`, candidate `Knowledge Edges`, Markdown cache metadata, and a compact run log summary. Later workflow steps consume structured intermediate artifacts rather than `SourceMaterial.text`. MinerU standard mode publishes the local PDF through a private Aliyun OSS staging object and short-lived signed URL, submits that URL to MinerU v4, then best-effort deletes the staging object. PDFs above `KNOWACT_MINERU_MAX_PAGES_PER_TASK` are split locally into chunks, parsed through separate MinerU tasks, and joined back into one Parsed Source Markdown. When `write_artifacts=true`, it writes `candidate_nodes.json`, `candidate_edges.json`, the sidecar `workflow_log.json`, validation-passed `intermediate/` artifacts, and per-step `agent_traces/{step}/` raw/parser artifacts under a candidate graph run directory by default; only the node and edge files are candidate graph review artifacts.
- `POST /api/authoring/candidate-graphs/{benchmark_domain}/{run_id}/promotion`: revalidates one saved candidate graph run, copies its node and edge lists into `graphs/{version}/` as reviewed authored graph artifacts, and generates `graph_manifest.json`. Publishing over an existing version requires an explicit `overwrite=true` retry after user confirmation.

Guardrails:

- Candidate generation must not automatically promote artifacts into reviewed benchmark data; Phase 3 promotion requires an explicit benchmark-author confirmation action.
- The authoring API must stay visibly separate from future evaluation runtime routes.
- Evaluation runtime endpoints must continue to load only reviewed `Authored Knowledge Graphs` and reviewed `Ground-Truth Knowledge Maps`.
- PDF material requests must remain constrained to `storage/`, reject path traversal, and treat local books and generated Markdown as authoring inputs rather than reviewed benchmark artifacts.
- OSS staging URLs are temporary source-preparation transport for MinerU and must not be returned in API responses, written into workflow logs, or treated as reviewed benchmark data.

## Phase 0: Domain Decision Baseline

Goal: keep implementation aligned with the domain language already established in `CONTEXT.md`.

Milestone M0:

- `Knowledge Graph`, `Knowledge Map`, `Ground-Truth Knowledge Map`, `Reconstructed Knowledge Map`, `Evidence Record`, `Evaluation Episode`, and `Scoring Profile` have stable meanings.
- The v1 scope is explicitly active diagnosis with a static user knowledge state.
- The formal v1 domain, source basis, graph size target, visibility boundary, turn definition, and scoring profile are already captured in ADRs.

Exit criteria:

- New implementation work can cite existing terms instead of inventing parallel names such as "user graph", "node state", or "profile score".
- Remaining open questions are execution details, not unresolved domain boundaries.

Implementation note:

- Structures to maintain: `CONTEXT.md` for glossary-only terminology, `docs/adr/` for hard-to-reverse decisions, and this breakdown for implementation sequencing.
- Opened interfaces: none. API names introduced later should reuse glossary terms such as `Knowledge Graph`, `Knowledge Map`, `Evaluation Episode Manifest`, and `Graph Authoring Agent Workflow`.

## Phase 1: Schema and Validation Spine

Goal: define the structured contracts before building generators, simulators, or scorers.

Milestone M1:

- Pydantic schemas exist for `Knowledge Node`, `Knowledge Edge`, `Evidence Record`, `Knowledge Map`, `Evaluation Episode Manifest`, final reconstructed map output, and scoring reports.
- Fixture files cover at least one small development graph and one map pair.
- Validation catches missing node coverage, invalid edge references, missing evidence references, malformed mastery levels, and unsupported scoring profile overrides.

Recommended implementation order:

1. Start with graph and map schemas.
2. Add evidence records and visibility boundaries.
3. Add episode manifests.
4. Add scoring report schemas.

Do not include yet:

- Fixed graph directory layout beyond what the fixtures need.
- Per-episode custom scoring rules.
- User state on edges.

Implementation note:

- Structures to implement: `backend/knowact/core/` schemas, `backend/knowact/validation/` validators, `benchmark/fixtures/` development artifacts, and `test/` schema/validation checks.
- Opened interfaces: no HTTP API required. The public interface is the Python schema and validation API used by later authoring, runtime, scoring, and API endpoints.

## Phase 2: Graph Authoring Workflow

Goal: build the project-owned authoring workflow that turns authoritative source material into reviewable candidate graph files.

Milestone M2:

- The `Node Extraction Agent Step` reads ISL Python source material and produces `Source-Grounded Node Skeletons` with simple `Source Locators` and concise source grounding notes.
- The `Node Rubric Authoring Agent Step` turns node skeletons into complete candidate `Knowledge Nodes` with `diagnostic_goal`, L0-L5 `levels`, diagnostic signals, and `simulator_behavior`.
- The `Edge Proposal Agent Step` uses complete candidate nodes and rubrics to propose precision-first candidate `Knowledge Edges`.
- The final workflow output is exactly two JSON list files: `candidate_nodes.json` and `candidate_edges.json`.

Recommended milestone split:

- M2a: run the workflow on a small development fixture of roughly 5-8 nodes.
- M2b: run the workflow on the formal candidate graph target of 30-50 nodes.

Guardrails:

- Candidate nodes must be source-grounded, not brainstormed from model memory.
- Only node extraction receives full Parsed Source Markdown; later LLM-backed workflow steps receive structured intermediate artifacts, not source-material text.
- Rubric authoring must not use unreviewed neighboring nodes or candidate edges.
- Edge proposal should omit weak, speculative, or merely related pairs.
- Candidate status belongs to filenames, directories, or review state, not inside node or edge objects.

Implementation note:

- Phase 2 keeps LLM calls behind a `ModelClient` interface. The initial concrete adapters use OpenAI Python SDK-compatible chat completions for OpenAI and DeepSeek, read local API settings from environment variables documented in `.env.example`, and choose the provider per graph-authoring API request through `client_provider`.
- PDF source-material graph authoring runs use MinerU to prepare same-directory same-stem Markdown under local `storage/`; MinerU standard mode receives a short-lived signed URL for a private Aliyun OSS staging object rather than a base64 payload or public-read bucket object. Large PDFs are split by page count before MinerU submission and their Markdown chunks are concatenated in source page order. The LLM receives Markdown text through the ordinary text `ModelClient` path, not PDF base64 `input_file` or OpenAI `file_id`.
- Development and test runs should use deterministic or fake model clients unless the author explicitly chooses to run a provider-backed workflow.
- Structures to implement: `backend/knowact/authoring/schemas.py`, `workflow.py`, `steps.py`, `templates/graph_authoring.py`, `parsers/graph_authoring.py`, `validation.py`, `output.py`, `sources.py`, and `openai_workflow.py`; `backend/knowact/llm/` supplies the model completion boundary.
- Opened authoring interface: `POST /api/authoring/graph-candidates`. It accepts `pdf_path`, optional `benchmark_domain`, optional `source_id`, optional `source_title`, optional `run_id`, `client_provider`, `force_reparse`, and `write_artifacts`; it returns workflow outputs plus Markdown cache metadata and compact run log summary and, by default, writes `candidate_nodes.json`, `candidate_edges.json`, sidecar `workflow_log.json`, validation-passed `intermediate/` artifacts, and agent traces under `benchmark/domains/{benchmark_domain}/candidate_graphs/api/{run_id}/`.
- Stable workbench interface: defer formal authoring write APIs until candidate review and promotion semantics are clearer.

## Phase 3: Authored Graph Review and Promotion

Goal: separate generated candidate graph data from reviewed benchmark graph data.

Milestone M3:

- Benchmark author review accepts, edits, or rejects candidate nodes and edges.
- Reviewed graph data is stored as separate `authored_nodes.json` and `authored_edges.json` JSON list files.
- `graph_manifest.json` references graph id, version, originating candidate run, optional source metadata, and the separate node/edge files.
- Edge `curation_confidence` values are accepted or revised by the benchmark author.

Review checklist:

- Every node is stable, diagnosable, and source-grounded.
- Every formal node has complete L0-L5 rubrics.
- Every edge has a canonical edge type and a clear `Knowledge Edge Rationale`.
- `contrasts_with` edges are not duplicated in both directions.
- `part_of`, `prerequisite_for`, and `supports` are not used as generic relatedness labels.

Resolved `Graph File Layout`:

- Reviewed graph versions are published under `benchmark/domains/{benchmark_domain}/graphs/{version}/`.
- Each reviewed graph version directory contains `graph_manifest.json`, `authored_nodes.json`, and `authored_edges.json`.
- The benchmark author supplies the graph version during promotion; the implementation derives the graph id from the benchmark domain and version.
- Promoting to an existing graph version requires an explicit overwrite confirmation; a normal promotion request must not silently replace reviewed graph artifacts.
- Promotion copies the validated candidate node and edge files into the reviewed graph version directory as a published snapshot; the originating candidate graph run remains available for audit and later inspection.
- `graph_manifest.json` records the originating candidate graph run. When the candidate run has a readable `workflow_log.json`, promotion also copies its source metadata into the manifest; missing optional audit metadata does not block Phase 3 promotion.

Implementation note:

- Implemented promotion slice: `backend/knowact/authoring/review_promotion.py` revalidates saved candidate node/edge files and builds `graph_manifest.json`; `backend/knowact/storage/reviewed_graphs.py` reads and publishes artifact snapshots.
- Opened review-gated interface: `POST /api/authoring/candidate-graphs/{benchmark_domain}/{run_id}/promotion`. Read-only inspection of reviewed graphs remains a future stable API addition.
- Authoring API boundary: the Phase 2 candidate endpoint may create candidate files for review, but it must not create reviewed `authored_nodes.json` or `authored_edges.json`.

## Phase 4: Ground-Truth Map Authoring

Goal: create reviewed hidden user knowledge maps that can drive simulation and scoring.

Milestone M4:

- Candidate maps are generated over the reviewed `Authored Knowledge Graph`.
- Each `Ground-Truth Knowledge Map` covers every node in the episode graph.
- Each `User Knowledge State` has one or more hidden `Ground-Truth Evidence` records.
- Optional `Profile Context` can guide coherence, but it is not part of primary scoring.
- Benchmark author review promotes candidate maps into reviewed ground-truth maps.

Validation should catch:

- Missing states for graph nodes.
- Multiple current states for the same user and node.
- Evidence that points to an unknown node.
- Evidence with the wrong visibility.
- Profile context that contradicts the structured map.

Do not include yet:

- Scored persona similarity.
- Real user data.
- User-specific edge state.

Implementation note:

- Structures to implement: map authoring helpers under `backend/knowact/authoring/`, map/evidence loaders under `backend/knowact/storage/`, reviewed `ground_truth_maps/`, optional profile context artifacts, and validation checks for coverage and hidden evidence visibility.
- Interfaces to open: read-only map inspection can be exposed after hidden/visible redaction rules are implemented; write or generation APIs should stay gated because generated maps are `Candidate Knowledge Maps` until reviewed.
- Authoring API boundary: any future map authoring endpoint must clearly return candidate maps and must not make them evaluation-ready.

## Phase 5: Episode Runtime Contract

Goal: make each evaluation run reproducible and explicit.

Milestone M5:

- Each `Evaluation Episode Manifest` binds the episode graph, hidden map, optional profile context, `max_turns`, interaction rule, and `squared_mastery_distance_v1`.
- The manifest validator rejects custom scoring overrides.
- Runtime loading enforces the visibility boundary: the tested agent sees the authored graph and visible interaction history, but not hidden map data or simulator-only evidence.
- One `Interaction Turn` means one primary `Diagnostic Question` followed by one simulator answer.

Recommended development fixture:

- One small development episode can be used to test runtime wiring.
- Formal v1 episodes must use reviewed graph and reviewed ground-truth maps.

Implementation note:

- Structures to implement: `backend/knowact/runtime/episode_loader.py`, `runtime/visibility.py`, storage repositories for manifests/graphs/maps, and manifest validation tests.
- Interfaces to open: stable read-only endpoints for `GET /episodes` and `GET /episodes/{episode_id}` once repositories exist; run-trigger endpoints should wait until simulator, agent, and scoring wiring can preserve the visibility boundary.
- Development API boundary: runtime smoke endpoints may use development fixtures, but formal runtime paths must reject candidate graph/map artifacts.

## Phase 6: User Simulator

Goal: answer diagnostic questions naturally while staying faithful to the hidden map.

Milestone M6:

- The simulator is conditioned on hidden map state, hidden evidence, and optional profile context.
- It answers only the primary diagnostic question for each turn.
- It can express grounded ambiguity: uncertainty, partial correctness, self-correction, not knowing, or misconceptions.
- It does not reveal mastery labels, hidden evidence ids, or the full ground-truth map.
- Simulator transcripts are recorded as visible `Interaction Observations` for the tested agent.

Validation focus:

- Leakage tests for labels, evidence ids, and state-table language.
- Consistency checks against hidden mastery levels and evidence.
- Regression fixtures for ambiguous but grounded answers.

Implementation note:

- Structures to implement: `backend/knowact/simulator/context_builder.py`, `prompting.py`, `policy.py`, `service.py`, and `checks.py`, with LLM calls behind `backend/knowact/llm/`.
- Interfaces to open: no standalone public simulator oracle endpoint for formal evaluation. A development-only endpoint may be added later for single-turn simulator checks after leakage guards exist.
- Stable API exposure should happen through episode run endpoints, where simulator answers become visible `Interaction Observations` rather than hidden state dumps.

## Phase 7: Tested Agent Interface and Baselines

Goal: make agent comparison possible through a shared protocol.

Milestone M7:

- A tested agent can receive the visible graph, episode rules, and dialogue history.
- A tested agent can produce one diagnostic question per turn.
- A tested agent submits one `Final Reconstructed Knowledge Map` after the episode ends.
- Reconstructed user states cite tested-agent-visible evidence records.
- The fixed-question, random-question, and simple LLM baselines can complete the same episode contract.

Baseline boundaries:

- Fixed-question baseline uses a predefined question order.
- Random-question baseline selects diagnostic questions randomly within episode constraints.
- Simple LLM agent sees the authored graph and dialogue history, then chooses questions and submits a final map.
- Oracle, passive summarization, teaching, and complex ToM agents stay out of the v1 baseline set.

Implementation note:

- Structures to implement: `backend/knowact/agents/protocol.py`, fixed/random/simple LLM baseline modules, question-bank support, and reconstructed-map assembly helpers.
- Interfaces to open: no direct agent-control API is required at first; agents should be selected through episode run requests after the runtime contract exists.
- Development API boundary: future baseline smoke-test endpoints may exist, but they must expose only tested-agent-visible context.

## Phase 8: Scoring and Reports

Goal: compute reproducible structured comparison results.

Milestone M8:

- Scoring compares the final reconstructed map against the hidden ground-truth map over every node in the episode graph.
- `mastery_level` values map L0-L5 to 0-5 and use squared distance.
- Missing predictions receive distance penalty 36 and are reported separately.
- Unsupported inference does not override mastery distance, but is reported as a separate rate.
- Episode-level primary result is mean `Episode Mastery Distance`, where lower is better.

Report contents:

- Episode metadata and scoring profile version.
- Per-node predicted vs ground-truth mastery distance.
- Mean episode mastery distance.
- Missing prediction rate.
- Unsupported inference rate.
- Optional confidence calibration and misconception diagnostics.

Implementation note:

- Structures to implement: `backend/knowact/scoring/` for profile definition, distance, comparison, unsupported inference, and aggregation; `backend/knowact/reports/` for report shaping; `RunRepository` for persisted scoring reports.
- Interfaces to open: `GET /runs/{run_id}/report` after run storage exists; an optional fixture-only scoring comparison endpoint can be added if it never leaks hidden maps from formal episodes.
- Scoring APIs must report `Episode Mastery Distance`, missing prediction rate, and unsupported inference rate without using an LLM judge for the primary score.

## Phase 9: End-to-End V1 Benchmark Run

Goal: produce the first interpretable research result from the full reviewed v1 loop.

Milestone M9:

- At least one reviewed v1 graph, multiple reviewed ground-truth maps, and their episode manifests run end to end.
- Fixed-question, random-question, and simple LLM baselines are evaluated on the same episodes.
- Reports identify where agents fail: question selection, evidence collection, final reconstruction, confidence, or unsupported inference.
- A first experiment report states what v1 does and does not claim.

Minimum review questions for the report:

- Does adaptive question selection outperform fixed and random baselines?
- Does the simple LLM agent reconstruct maps with fewer missing predictions?
- Are unsupported inferences common enough to require stronger output constraints?
- Are simulator answers diagnostic without becoming oracle-like?

Implementation note:

- Structures to implement: `backend/knowact/runtime/runner.py`, `runtime/turn_loop.py`, `runtime/transcript.py`, `experiments/runs/` output snapshots, and experiment-level report documents.
- Interfaces to open: `POST /episodes/{episode_id}/runs`, `GET /runs/{run_id}`, and `GET /runs/{run_id}/report` once reviewed artifacts, simulator, agents, and scoring are wired.
- Development API boundary: end-to-end fixture runs can appear in development-only routes first, but formal v1 runs should use stable routes and reviewed artifacts only.

## Phase 10: Research Workbench

Goal: make authoring, review, and result inspection easier without blocking the benchmark core.

Milestone M10:

- Backend APIs expose graphs, maps, episode manifests, simulator runs, agent outputs, and reports.
- A React research interface supports graph inspection, knowledge-map comparison, episode transcript review, and report browsing.
- Knowledge graph views distinguish user-independent nodes/edges from user-specific map state.
- Review screens make evidence, confidence, mastery level, and visibility boundaries easy to inspect.

Recommended timing:

- Build only minimal tooling before M8.
- Expand the workbench after the first end-to-end scoring path is stable.

Implementation note:

- Structures to implement: `backend/knowact/api/` stable routers, frontend `src/app/`, `src/api/`, and feature modules for graphs, maps, episodes, runs, and reports.
- Interfaces to open: stable `/api` routes for graph inspection, map inspection with visibility-aware redaction, episode manifests, run triggers, run status, and report browsing.
- Development-only endpoints should either be retired or kept explicitly marked after equivalent stable workbench routes exist.

## Phase 11: Post-V1 Expansion

Goal: choose the next research claim after v1 proves or disproves the core loop.

Candidate directions:

- Add multiple benchmark domains and cross-domain calibration.
- Add teaching, recommendation, or next-action quality after active diagnosis stabilizes.
- Add real human users after synthetic validation.
- Compare richer ToM-aware agent architectures.
- Introduce alternative scoring profile versions.
- Study simulator failure modes and reduce circularity between generation, simulation, and evaluation.

Do not start these before v1:

- Multi-domain benchmark claims.
- Real-user evaluation claims.
- Teaching-quality claims.
- Complex agent architecture comparisons as primary results.

Implementation note:

- Structures to implement: new benchmark domain directories, additional scoring profile versions only when justified, richer agent modules, and post-v1 ADRs for any irreversible expansion.
- Interfaces to open: versioned stable APIs if multi-domain, real-user, or teaching workflows introduce incompatible contracts.
- Development-only endpoints should remain narrow smoke-test windows, not a parallel product API.

## Dependency Map

```text
M0 Domain decisions
  -> M1 Schemas and validators
    -> M2 Graph authoring workflow
      -> M3 Reviewed authored graph
        -> M4 Reviewed ground-truth maps
          -> M5 Episode manifests and runtime contract
            -> M6 User simulator
            -> M7 Tested agent interface and baselines
              -> M8 Scoring and reports
                -> M9 End-to-end v1 benchmark report
                  -> M10 Research workbench expansion
                  -> M11 Post-v1 research expansion
```

## Review Points

1. Should the first runnable implementation use a 5-8 node development fixture before the formal 30-50 node v1 graph?
   - Recommended answer: yes. It protects implementation speed while keeping the fixture clearly outside formal v1 evaluation.

2. Resolved: `Graph File Layout` is lightweight and versioned under `benchmark/domains/{benchmark_domain}/graphs/{version}/`.
   - Promotion copies validated candidate snapshots into reviewed graph data files and requires explicit confirmation before overwriting an existing version.

3. Should the frontend wait until after the first scorer and report path exists?
   - Recommended answer: mostly yes. A minimal review helper is fine, but the core benchmark validity depends on schemas, authored data, simulator, agents, and scoring first.

4. Should v1 include a custom ToM-aware agent beyond the simple LLM baseline?
   - Recommended answer: not as a required v1 milestone. First prove that the benchmark loop and baseline comparisons are stable; then add richer agents as post-v1 or v1.1 work.
