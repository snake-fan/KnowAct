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
- `POST /api/authoring/candidate-graphs/{benchmark_domain}/{run_id}/promotion`: revalidates one saved candidate graph run, copies its node and edge lists into `graphs/{version}/` as reviewed authored graph artifacts, and generates `graph_manifest.json`. Reviewed graph versions are immutable; corrections publish a new version.
- `POST /api/authoring/map-candidates`: loads one reviewed graph version and one confirmed Profile Context snapshot by identity and generates one evidence-backed Candidate Knowledge Map. It runs one full-graph outline call, partitions evidence authoring into contiguous reviewed-node windows with optional request-level batch-size control, applies one shared sampling temperature, and writes generation-time edge-consistency warnings. Candidate-map run ids cannot overwrite an existing run directory; retry with a new run id.
- `GET /api/authoring/candidate-maps/{benchmark_domain}/{run_id}`: returns one saved Candidate Knowledge Map and its debug artifact references for benchmark-author inspection.

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
- Promotion never overwrites an existing graph version and does not expose `overwrite=true`; corrections publish a new version so maps and episodes keep a reproducible graph basis.
- Promotion copies the validated candidate node and edge files into the reviewed graph version directory as a published snapshot; the originating candidate graph run remains available for audit and later inspection.
- `graph_manifest.json` records the originating candidate graph run. When the candidate run has a readable `workflow_log.json`, promotion also copies its source metadata into the manifest; missing optional audit metadata does not block Phase 3 promotion.

Implementation note:

- Implemented promotion slice: `backend/knowact/authoring/review_promotion.py` revalidates saved candidate node/edge files and builds `graph_manifest.json`; `backend/knowact/storage/reviewed_graphs.py` reads and publishes artifact snapshots.
- Opened review-gated interface: `POST /api/authoring/candidate-graphs/{benchmark_domain}/{run_id}/promotion`. Read-only inspection of reviewed graphs remains a future stable API addition.
- Authoring API boundary: the Phase 2 candidate endpoint may create candidate files for review, but it must not create reviewed `authored_nodes.json` or `authored_edges.json`.

## Phase 4: Ground-Truth Map Authoring

Goal: create reviewed hidden user knowledge maps that can drive simulation and scoring.

Resolved initial workflow boundary:

- One ground-truth map authoring run produces exactly one `Candidate Knowledge Map` for one synthetic benchmark user over one reviewed `Authored Knowledge Graph` version.
- The workflow starts from a benchmark-author supplied rough user description and expands it into a reviewable `Profile Context`.
- The benchmark author may edit the generated `Profile Context`.
- `Profile Context Validation` is a separate structural-validation step. `Profile Context Confirmation` is the separate explicit benchmark-author acceptance of one validated context snapshot.
- Initial `Profile Context Validation` is deterministic: require a nonblank `summary`, at least one nonblank `background` item, a present but optionally empty `prior_experience` list, at least one nonblank `goals` item, a present but optionally empty `preferences` list, path-domain equality for `benchmark_domain`, and no extra fields. Do not call an LLM validator or apply brittle text blacklists.
- The normal authoring flow runs validation and confirmation before invoking candidate-map generation.
- Candidate-map generation remains independently callable as an authoring capability for focused debugging instead of being fused into the normal workflow gate.
- `Profile Context` is a structured JSON artifact with `user_id`, `benchmark_domain`, readable `summary`, `background`, `prior_experience`, `goals`, and `preferences`.
- `Profile Context` must not contain node-level mastery values; those belong to the generated `Candidate Knowledge Map`.
- Profile-context authoring receives only the rough user description, benchmark-domain identity, and optional domain summary. It must not receive graph nodes, node rubrics, or edges.
- The confirmed `Profile Context` then guides generation of node-level `User Knowledge State` values and hidden `Ground-Truth Evidence`.
- Candidate-map generation receives the confirmed `Profile Context` and the complete reviewed `Authored Knowledge Graph`.
- Candidate-map generation identifies graph input with `benchmark_domain` and `graph_version`, then loads the reviewed snapshot from `benchmark/domains/{benchmark_domain}/graphs/{graph_version}/`. It must not accept uploaded or inline node and edge JSON payloads.
- Candidate-map generation identifies profile input with `user_id`, then loads a saved and confirmed `Profile Context` artifact. It must not accept inline profile-context JSON payloads.
- Normal and standalone-debug calls share the same generation boundary: both require a reviewed graph snapshot and a confirmed `Profile Context`.
- `Profile Context Confirmation` publishes an immutable snapshot under `benchmark/domains/{benchmark_domain}/users/{user_id}/profile_context.json`.
- Keep confirmed profile-context storage lightweight: do not add a separate profile-context manifest in the initial slice. Candidate-run artifacts remain available for profile-generation debugging.
- Candidate profile-context generation uses `run_id` only. During confirmation, the benchmark author supplies the formal `user_id`.
- Candidate profile-context artifacts do not contain `user_id` before confirmation. Their `PUT` endpoint edits `summary`, `background`, `prior_experience`, `goals`, and `preferences` only; `run_id` and `benchmark_domain` remain fixed.
- Candidate profile-context `PUT` overwrites the current draft file in place. Do not add candidate-profile revision history in the initial slice; immutability begins at confirmation.
- Changing a confirmed `Profile Context` requires publishing a new `user_id`; confirmed snapshots must not be silently overwritten.
- `Profile Context Confirmation` never overwrites an existing `user_id` and does not expose `overwrite=true`.
- One candidate profile-context run may be confirmed at most once. Publishing another synthetic user requires a new candidate profile-context run so distinct `user_id` values do not alias one draft.
- A confirmed `Profile Context` binds `benchmark_domain` but does not bind `graph_version`. The same synthetic user profile may be reused when generating maps against later reviewed graph versions within the same domain.
- Candidate profile-context runs are saved under `benchmark/domains/{benchmark_domain}/candidate_profile_contexts/{run_id}/`.
- Each candidate profile-context run contains `candidate_profile_context.json`, a minimal `workflow_log.json`, and `agent_traces/model_raw_output.txt` plus `agent_traces/parser_output.json`. Do not add an `intermediate/` directory or a redundant single-step trace subdirectory.
- Candidate-map runs are saved under `benchmark/domains/{benchmark_domain}/candidate_maps/{run_id}/` with `candidate_map.json`, `consistency_warnings.json`, `workflow_log.json`, optional `intermediate/`, and optional `agent_traces/`.
- Candidate-map `intermediate/` stores `state_outline.json` and `ground_truth_evidence.json`.
- Candidate-map `agent_traces/` stores `knowledge_state_outline/model_raw_output.txt`, `knowledge_state_outline/parser_output.json`, and per-batch `ground_truth_evidence/{batch_name}/model_raw_output.txt` plus `parser_output.json`.
- Candidate-map runs do not copy confirmed profile-context or reviewed-graph payloads. Their `workflow_log.json` records `user_id`, `benchmark_domain`, and `graph_version` references.
- A candidate map is a discardable synthetic sample. Benchmark-author review accepts it unchanged for promotion or rejects it. Poor state or evidence quality should be fixed by improving profile input or workflow behavior and generating a new candidate run, not by manually patching one map.
- One confirmed `user_id` may produce multiple candidate-map runs for retry and debugging.
- One `(user_id, graph_version)` pair may produce and promote multiple independent `Ground-Truth Knowledge Maps`, each with a distinct `map_id`. The benchmark author selects which promoted map sample an episode uses.
- Promotion accepts multiple reviewed map samples for the same `(user_id, graph_version)` pair as long as every published sample uses a new domain-unique `map_id`.
- Explicit benchmark-author promotion assigns a domain-unique `map_id` and publishes an immutable reviewed snapshot under `benchmark/domains/{benchmark_domain}/ground_truth_maps/{map_id}/` with `ground_truth_map.json` and `map_manifest.json`.
- Reviewed-map promotion never overwrites an existing `map_id` and does not expose `overwrite=true`. Replacing a reviewed synthetic sample requires a new `map_id`; old snapshots remain available for episode reproducibility.
- One successful candidate-map run may be promoted at most once. Publishing another reviewed sample requires a new candidate-map generation run so distinct `map_id` values do not alias identical run output.
- `map_manifest.json` binds `map_id`, `user_id`, `benchmark_domain`, `graph_version`, and `promoted_from_candidate_run`.
- `user_id` identifies the confirmed synthetic-user profile basis; `map_id` identifies one promoted synthetic knowledge-map sample generated from that basis.
- Keep `map_manifest.json` minimal in the initial slice. Do not add timestamps, model configuration, or copied warning payloads; candidate-map run artifacts retain debugging metadata.
- Promotion revalidates graph coverage, unique current state per node, evidence references, simulator-support evidence minimums, confirmed profile-context existence, and reviewed graph-version existence.
- Edge-consistency warnings are generation-time review hints only. Promotion does not read, validate, recompute, or copy them.
- Keep `consistency_warnings.json` in the originating candidate-map run only.
- `Knowledge-State Outline Agent Step` first drafts full-graph node-level `mastery_level`, `misconceptions`, and `unknowns` from the confirmed `Profile Context` and reviewed nodes with rubrics. It must not receive reviewed edges.
- Initial outline authoring runs as one full-graph model call for the reviewed 30-50 node target. Do not split outline generation into node batches; defer batching and global reconciliation until graph scale requires them.
- Knowledge-state-outline model output contains `node_id`, `mastery_level`, `misconceptions`, and `unknowns` only. It must not output `evidence_refs`, `user_id`, or lifecycle `kind`; workflow code supplies those during deterministic candidate-map assembly.
- Outline output and assembled candidate maps must explicitly include `misconceptions` and `unknowns` arrays for every node state, even when empty. Missing arrays are invalid rather than interpreted as defaults.
- Prompt outline authoring to avoid exact duplicate items within each state's `misconceptions` and `unknowns`. Validation rejects exact duplicates instead of silently deduplicating them. Do not add semantic-similarity merging.
- Do not enforce mastery-specific item counts for `misconceptions` or `unknowns`. Prompt for plausible content, but do not force low-mastery misconceptions or high-mastery empty arrays.
- Keep `evidence_refs` optional with schema-level default `[]`. Context-specific ground-truth authoring, reconstruction, and scoring validation decide whether empty references are allowed.
- Before evidence authoring starts, a blocking outline-validation checkpoint requires `outline node ids == reviewed graph node ids`. Reject duplicate, unknown, or missing node ids, invalid `mastery_level`, and blank `misconceptions` or `unknowns`.
- After outline validation, normalize assembled `states` into reviewed `authored_nodes.json` order. Normalize generated `evidence` into the same node order; within one node preserve model-output order and assign evidence ordinals from that stable order.
- `Ground-Truth Evidence Authoring Agent Step` then drafts hidden `Ground-Truth Evidence` from the state outline, confirmed `Profile Context`, and reviewed node rubrics. It may batch nodes internally.
- Each evidence-authoring batch receives the confirmed `Profile Context`, reviewed rubrics for its batch nodes, and state outlines for its batch nodes only. It must not receive other node states, reviewed edges, or the complete graph.
- Partition evidence-authoring batches as contiguous windows in reviewed `authored_nodes.json` order. Do not shuffle nodes or cluster batches by edges.
- After each evidence-authoring batch, deterministically reject output that references nodes outside the batch or fails mastery-sensitive evidence minimums for batch nodes.
- `Ground-Truth Evidence Authoring Agent Step` uses an evidence batch size of `5` by default. `POST /api/authoring/map-candidates` may override it with optional positive-integer `evidence_batch_size`.
- Initial evidence batching is fail-fast without partial resume. If any batch fails, mark the candidate-map run failed, retain traces for debugging, and retry with a new `run_id`.
- Workflow-authored `Ground-Truth Evidence` uses `simulator_only`.
- Each reviewed ground-truth node state must cite at least one `simulator_only` evidence record.
- Minimum workflow-authored `simulator_only` evidence-count policy: L0-L1 states receive at least one record; L2-L3 states receive at least two records; L4-L5 states receive at least one record. Prompt guidance should favor `misconception_trace` or weak `prior_answer` for L0-L1, capability and boundary evidence for L2-L3, and `worked_example` or strong `prior_answer` for L4-L5, but validation must not require mastery-specific evidence kinds.
- Ground-truth-evidence model output contains `node_id`, `evidence_kind`, and `signal` only. Workflow code assigns deterministic `ev_{run_id}_{node_id}_{ordinal}` ids and fixed `evidence_type = ground_truth_profile`, `visibility = simulator_only`, and `turn_id = null`. Promotion preserves these run-scoped evidence ids unchanged.
- Prompt evidence authoring to avoid exact duplicate `(evidence_kind, signal)` pairs within one node. Validation rejects exact duplicates rather than counting them toward mastery-sensitive minimums. Do not add semantic-similarity merging.
- Keep evidence-kind validation lightweight in the initial slice. `background_fact` remains a valid workflow-authored evidence kind under the same minimum rules; do not add kind-specific exclusion or uniqueness constraints until generated artifacts show a concrete quality problem.
- Workflow code deterministically merges generated evidence references into node-level states; model output must not maintain cross-object `evidence_refs`.
- Workflow output writes `candidate_map.json` with `kind = candidate`. Only promotion code may deterministically replace it with `kind = ground_truth` when writing `ground_truth_map.json`; model output must not set lifecycle kind.
- Write a successful `candidate_map.json` only after blocking candidate-map validation passes. Reject missing, duplicate, or unknown node states; invalid mastery; missing or cross-node evidence refs; evidence counts below mastery-sensitive minimums; workflow evidence that is not `simulator_only`; `kind != candidate`; and `user_id` mismatch.
- On blocking-validation failure, mark the run failed and retain traces plus intermediate artifacts, but do not write a promotable `candidate_map.json`. Edge-consistency findings remain non-blocking warnings.
- Reviewed `Knowledge Edges` are soft diagnostic signals for candidate-map consistency. Deterministic edge-aware checks receive the drafted state outline and reviewed edges, then emit review warnings for suspicious state combinations; they must not automatically rewrite or reject uneven maps.
- Candidate-map generation identifies `benchmark_domain`, `graph_version`, `user_id`, optional `run_id`, `client_provider`, optional positive-integer `evidence_batch_size` defaulting to `5`, and optional `sampling_temperature` defaulting to `0.7`. It does not assign `map_id`.
- `sampling_temperature` applies to candidate-map generation only, not graph authoring or profile-context authoring. Record the effective temperature in `workflow_log.json`. Do not add seed support in the initial slice. A provider adapter that cannot apply temperature must reject the request explicitly rather than silently ignoring it.
- One map-generation run applies the same effective `sampling_temperature` to the outline step and every evidence-authoring batch. Do not split outline and evidence temperature controls in the initial slice.
- Cohort or batch generation is deferred. A later batch layer may orchestrate repeated single-map runs without changing the single-map authoring contract.

Milestone M4:

- Candidate maps are generated over the reviewed `Authored Knowledge Graph`.
- Each `Ground-Truth Knowledge Map` covers every node in the episode graph.
- Each `User Knowledge State` has one or more hidden `Ground-Truth Evidence` records.
- Phase 4 synthetic map authoring requires a confirmed `Profile Context`; the general runtime schema may still keep profile context optional for future manually imported or historical maps. Profile context is not part of primary scoring.
- Generated `Profile Context` is reviewable and explicitly confirmed before it guides candidate-map generation.
- Benchmark-author accept-or-reject review promotes acceptable candidate maps unchanged into reviewed ground-truth maps.

Validation should catch:

- Missing states for graph nodes.
- Multiple current states for the same user and node.
- Evidence that points to an unknown node.
- Evidence with the wrong visibility.
- Ground-truth states without at least one `simulator_only` evidence reference.

Review warnings should surface:

- Suspicious mastery combinations across reviewed `prerequisite_for` edges when target mastery exceeds source mastery by at least two levels.
- Candidate-map inconsistencies that may be realistic but require benchmark-author attention rather than automatic rejection.

Initial warning boundary:

- Check reviewed `prerequisite_for` edges only.
- Do not infer mastery ordering from `part_of`, `supports`, or `contrasts_with` edges.
- Each warning records the edge id, source node id and mastery, target node id and mastery, and triggering rule.

Benchmark-author review should inspect:

- Semantic coherence between the confirmed `Profile Context` and generated candidate map. Do not add an LLM coherence judge or treat this as blocking structural validation in the initial slice; reject and regenerate incoherent samples.

Do not include yet:

- Scored persona similarity.
- Real user data.
- User-specific edge state.

Implementation note:

- Structures to implement: map authoring helpers under `backend/knowact/authoring/`, map/evidence loaders under `backend/knowact/storage/`, candidate and confirmed profile-context artifacts, reviewed `ground_truth_maps/`, and validation checks for coverage and hidden evidence visibility.
- Implemented reviewed-graph slice: `POST /api/authoring/map-candidates` and `GET /api/authoring/candidate-maps/{benchmark_domain}/{run_id}` cover identity-based reviewed graph/profile loading, one full-graph outline call, contiguous multi-batch evidence authoring, request-level batch-size and sampling-temperature controls, deterministic evidence-backed candidate assembly, blocking validation, fail-fast retained debug artifacts, edge-consistency warnings, and non-overwriting candidate-map run ids. Reviewed-map promotion remains follow-up work.
- Interfaces to open for the initial functional slice:
  - `GET /api/authoring/benchmark-domains`
  - `POST /api/authoring/profile-context-candidates`
  - `GET /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}`
  - `PUT /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}`
  - `POST /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}/confirmation`
  - `POST /api/authoring/map-candidates`
  - `GET /api/authoring/candidate-maps/{benchmark_domain}/{run_id}`
  - `POST /api/authoring/candidate-maps/{benchmark_domain}/{run_id}/promotion`
- Do not add candidate-profile or candidate-map browsing list endpoints in the initial Phase 4 slice. `GET /api/authoring/benchmark-domains` is a narrow read-only discovery exception for workbench selectors: it lists existing safe domain ids without creating or mutating benchmark data. Add wider browsing surfaces after the functional workflow is exercised end to end.
- Do not add a one-shot orchestration endpoint in the initial Phase 4 slice. Callers explicitly sequence the narrow endpoints so profile-context editing, confirmation, candidate-map inspection, and promotion remain visible gates.
- Authoring API boundary: profile-context candidates may be edited before confirmation; candidate maps may be inspected and either promoted unchanged or rejected, but not edited through a map `PUT` endpoint.
- `POST /api/authoring/profile-context-candidates` accepts required `benchmark_domain` and `rough_description`, optional limited `domain_summary`, optional `run_id`, and request-level `client_provider`. `domain_summary` may be supplied inline in the initial slice but must not contain node or rubric details; a later domain manifest may replace this temporary input.

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
- Optional misconception diagnostics.

Implementation note:

- Structures to implement: `backend/knowact/scoring/` for profile definition, distance, comparison, unsupported inference, and aggregation; `backend/knowact/reports/` for report shaping; `RunRepository` for persisted scoring reports.
- Interfaces to open: `GET /runs/{run_id}/report` after run storage exists; an optional fixture-only scoring comparison endpoint can be added if it never leaks hidden maps from formal episodes.
- Scoring APIs must report `Episode Mastery Distance`, missing prediction rate, and unsupported inference rate without using an LLM judge for the primary score.

## Phase 9: End-to-End V1 Benchmark Run

Goal: produce the first interpretable research result from the full reviewed v1 loop.

Milestone M9:

- At least one reviewed v1 graph, multiple reviewed ground-truth maps, and their episode manifests run end to end.
- Fixed-question, random-question, and simple LLM baselines are evaluated on the same episodes.
- Reports identify where agents fail: question selection, evidence collection, final reconstruction, or unsupported inference.
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
- Review screens make evidence, mastery level, and visibility boundaries easy to inspect.

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
   - Promotion copies validated candidate snapshots into reviewed graph data files. Reviewed graph versions are immutable; corrections publish a new version.

3. Should the frontend wait until after the first scorer and report path exists?
   - Recommended answer: mostly yes. A minimal review helper is fine, but the core benchmark validity depends on schemas, authored data, simulator, agents, and scoring first.

4. Should v1 include a custom ToM-aware agent beyond the simple LLM baseline?
   - Recommended answer: not as a required v1 milestone. First prove that the benchmark loop and baseline comparisons are stable; then add richer agents as post-v1 or v1.1 work.
