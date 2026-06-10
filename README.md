# KnowAct

[中文版本](README.zh-CN.md)

**KnowAct: Evaluating Functional Theory of Mind in Knowledge-Grounded Human-AI Interaction**

KnowAct is a research-oriented benchmark and evaluation framework for studying how AI agents use Theory of Mind-like abilities during knowledge-grounded human-AI interaction.

Instead of only asking whether a model can describe a user's mental state, KnowAct focuses on a more functional question:

> Can an agent use its model of the user to make better interaction decisions?

The project explores how an agent infers, updates, and acts upon a user's knowledge state during multi-turn interaction.

---

## Motivation

Large language model agents are increasingly expected to collaborate with users in open-ended tasks such as learning, research, writing, and decision-making. In these scenarios, a useful agent should not only understand the external task, but also reason about the user's internal state:

- What does the user already know?
- What concepts are missing or misunderstood?
- What should the agent ask next?
- When should the agent explain, challenge, summarize, or move forward?
- How should the agent adapt its behavior based on the user's knowledge profile?

This ability is related to **Theory of Mind**, but KnowAct emphasizes its practical role in interaction. We call this direction **Functional Theory of Mind**: the ability to use user-state reasoning to guide actions in a dialogue.

---

## Core Research Question

KnowAct investigates the following question:

> How can we evaluate whether an AI agent can use Theory of Mind-like user modeling to guide interaction decisions in knowledge-grounded tasks?

More specifically, the project asks:

1. Can an agent infer a user's hidden knowledge profile through limited interaction?
2. Can the agent choose useful conversational actions based on that inferred profile?
3. Can we quantitatively compare the agent's reconstructed user profile with a ground-truth profile?
4. Does a ToM-aware agent loop outperform simpler baselines in profile reconstruction and interaction quality?

---

## Key Idea

KnowAct constructs controlled user profiles and tests whether an agent can recover and use them through dialogue.

The basic evaluation pipeline is:

```text
Ground-truth Knowledge Profile
        ↓
User Simulator
        ↓
Multi-turn Interaction
        ↓
Tested Agent infers User Profile
        ↓
Profile Comparison / Scoring
```

The ground-truth user profile is hidden from the tested agent. The agent must interact with a simulated user, ask questions, interpret responses, and gradually reconstruct the user's knowledge state.

---

## Benchmark Design

KnowAct uses a semi-synthetic benchmark construction process:

V1 starts with a single benchmark domain, `classical_supervised_ml_algorithms`, so the first implementation can validate data authoring, simulation, active diagnosis, final reconstruction, and scoring before adding cross-domain calibration. The current V1 working graph is the reviewed generated graph version promoted for that domain under `benchmark/domains/classical_supervised_ml_algorithms/graphs/{version}/`; the earlier 30-50 node target is no longer a hard constraint. Scope follows the reviewed graph artifact and can be narrowed later by publishing a new graph version.

1. **Benchmark Data Authoring**

   A project-owned graph authoring agent workflow will use model API calls to generate candidate knowledge graphs and candidate knowledge maps. One step reads the Parsed Source Markdown and extracts source-grounded node skeletons with source locators and concise source grounding notes; later node rubric and edge proposal steps consume those structured intermediate artifacts rather than the full source text. The node rubric step completes diagnostic goals, L0-L5 rubrics, diagnostic signals, and simulator behavior; the edge step uses complete candidate nodes, rubrics, locators, and source grounding notes to propose candidate edges. The graph authoring workflow's final review output is two JSON list files, one for nodes and one for edges; candidate status belongs to filenames or review state, not to the node or edge objects themselves. After review, authored graph data remains split into separate node and edge JSON list files. Candidate nodes must be extracted from selected authoritative sources and carry source locators; they should not be brainstormed from model memory. Persona, background, preferences, and task goals can guide map generation, but v1 evaluation uses only benchmark-author reviewed authored knowledge graphs and ground-truth knowledge maps for scoring.

   Each v1 evaluation episode is declared by an explicit manifest that binds the authored graph, hidden map, optional profile context, `max_turns`, interaction rule, and the fixed `squared_mastery_distance_v1` scoring profile.

2. **Human Verification**

   Generated profiles are manually checked and revised to ensure consistency, plausibility, and evaluability.

3. **User Simulation**

   An LLM-based user simulator is conditioned on the hidden knowledge map and evidence, then answers diagnostic questions naturally without revealing mastery labels, hidden evidence ids, or the full map. It may be uncertain, partially correct, or reveal misconceptions, but its answers should remain consistent with the hidden map and evidence.
   See `docs/UserSimulator.md` for the Phase 5 simulator workflow, grounding, validation, fallback, and single-turn boundaries.

4. **Agent Interaction**

   The tested agent interacts with the simulated user without access to the hidden profile.

5. **Profile Reconstruction**

   After the conversation, the tested agent submits a final reconstructed knowledge map. Per-turn reconstruction traces are optional analysis artifacts.

6. **Evaluation**

   The final reconstructed knowledge map is compared against the hidden ground-truth knowledge map using structured map comparison.

---

## Knowledge Graph and Knowledge Map

KnowAct separates the user-independent **Knowledge Graph** from the user-specific **Knowledge Map**.

The **Knowledge Graph** contains stable domain knowledge:

- `nodes`: diagnosable knowledge units.
- `edges`: objective relationships between nodes.

The **Knowledge Map** represents a user's or tested agent's knowledge state over that graph. User state is tracked at the node level; edges guide exploration and diagnosis but do not describe user state.

A possible graph structure is:

```json
{
  "nodes": [
    {
      "id": "epistemic_uncertainty",
      "name": "Epistemic Uncertainty",
      "type": "concept"
    },
    {
      "id": "active_learning",
      "name": "Active Learning",
      "type": "concept"
    }
  ],
  "edges": [
    {
      "id": "edge_epistemic_uncertainty_prerequisite_for_active_learning",
      "source": "epistemic_uncertainty",
      "target": "active_learning",
      "type": "prerequisite_for",
      "rationale": "Understanding reducible model uncertainty helps explain why active learning queries informative samples.",
      "weight": 0.85,
      "curation_confidence": 0.95
    }
  ]
}
```

A possible user map structure is:

```json
{
  "user_id": "u_001",
  "states": [
    {
      "node_id": "active_learning",
      "mastery_level": "L2",
      "evidence_refs": ["ev_104"],
      "misconceptions": [],
      "unknowns": []
    }
  ]
}
```

The graph and map can support both evaluation and agent decision-making.

---

## Evaluation

KnowAct v1 keeps evaluation focused on automatic comparison between the hidden ground-truth knowledge map and the tested agent's reconstructed knowledge map.

### 1. Profile Reconstruction Accuracy

The agent's reconstructed map is compared with the hidden map over structured user-state fields. The primary v1 result is `episode_mastery_distance`: the mean squared distance between inferred and hidden `mastery_level` values across all nodes in the episode's authored knowledge graph. Lower is better.

Possible supporting metrics include:

* Misconception detection accuracy
* Missing prediction rate
* Unsupported inference rate, based on missing visible evidence references

V1 does not require a separate evaluator agent or LLM judge for primary scoring. Evidence records are used to make reconstruction more grounded and auditable, not to add another subjective evaluation layer. Unsupported inference is reported separately from mastery-level distance.

### 2. Interaction Efficiency

The agent should recover useful information within an explicit turn budget. V1 episodes configure `max_turns` directly instead of deriving it from the number of graph nodes. One turn contains one primary diagnostic question and one simulator answer.

Possible metrics include:

* Number of turns used
* Information gain per turn
* Redundant question rate
* Coverage of important profile dimensions
* Early-stage reconstruction quality

### 3. Action Quality

Later versions may evaluate whether the agent uses the inferred profile to make better teaching or recommendation decisions. In v1, the interaction is limited to active knowledge-state diagnosis.

The main v1 action type is:

* Ask a diagnostic question

The goal is to infer the user's state efficiently and with evidence-backed reconstruction.

---

## Agent Loop

KnowAct includes a planned ToM-aware agent loop.

A simplified version:

```text
Observe user response
        ↓
Update inferred knowledge map
        ↓
Estimate uncertainty
        ↓
Select next interaction action
        ↓
Generate response
        ↓
Continue interaction
```

The agent loop explicitly separates:

* user-state inference
* uncertainty estimation
* action selection
* response generation
* profile reconstruction

This makes it possible to compare different agent designs and analyze where failures occur.

---

## Baselines

KnowAct is designed to compare a ToM-aware agent with simpler baselines, such as:

### Direct Chat Baseline

Out of scope for v1. It may be revisited after the active diagnosis loop is stable.

### Passive Summarization Baseline

Out of scope for v1. Passive reconstruction may be useful later, but v1 focuses on diagnostic question selection.

### Fixed-Question Baseline

The agent follows a predefined diagnostic question order and does not adapt its questions based on previous answers.

### Random-Question Baseline

The agent randomly selects diagnostic questions within the episode constraints.

### Simple LLM Agent

The agent sees the authored knowledge graph and dialogue history, uses a simple prompt to choose the next diagnostic question, and submits a final reconstructed knowledge map.

### Oracle Profile Baseline

Out of scope for v1. An oracle may be useful later as an upper bound, but it is not needed to validate the first benchmark loop.

---

## Research Hypothesis

KnowAct is based on the hypothesis that:

> Agents with explicit user modeling and ToM-like action selection should infer user knowledge states more accurately and interact more efficiently than agents without such mechanisms.

This project tests whether that hypothesis holds under controlled knowledge-grounded interaction settings.

---

## Current Status

KnowAct is currently in the design and prototyping stage.

The V1 implementation has started with the schema and validation spine:

- `backend/knowact/core/`: Pydantic schemas for knowledge graphs, evidence records, knowledge maps, visible interaction contracts, episode manifests, and scoring reports.
- `backend/knowact/validation/`: cross-object validators for graph references, map coverage/evidence support, and episode manifest constraints.
- `backend/knowact/authoring/`: the Phase 2 graph authoring workflow spine, with node extraction, node rubric authoring, edge proposal, candidate file export boundaries, and separate `templates/` and `parsers/` modules for agent prompts and raw model outputs.
- `backend/knowact/simulator/`: Phase 5 user simulator contracts with a usable stateless single-turn API that keeps request and response fields tested-agent-visible.
- `backend/knowact/llm/`: a model-client interface plus OpenAI and DeepSeek SDK-backed clients for text-based authoring steps and LLM-backed simulator turns.
- `backend/knowact/storage/`: local artifact, material path, and reviewed graph/map promotion helpers. Test-stage book PDFs can be placed under the repository-level `storage/` directory, which is git-ignored except for `.gitkeep`.
- `backend/knowact/api/` and `backend/main.py`: a FastAPI entrypoint with an authoring API that can run the real graph authoring workflow from a local textbook PDF.
- `frontend/`: a React/Vite research workbench with top-level Knowledge Graph and User Profile modules. It supports candidate graph review and the Profile Context generation, editing, save, and immutable-confirmation gate.
- `benchmark/fixtures/dev_classical_supervised_ml_algorithms/`: a 5-node development fixture for schema and validator checks, not the formal reviewed v1 graph.
- `test/`: `unittest` coverage for the public schema and validation APIs.

Configure local OpenAI API access by copying `.env.example` to `.env` and filling in:

```bash
OPENAI_API_KEY=...
KNOWACT_OPENAI_MODEL=gpt-4.1-mini
```

DeepSeek can be selected per authoring or simulator turn request with `client_provider="deepseek"` and is configured through environment variables rather than request-body secrets:

```bash
DEEPSEEK_API_KEY=...
KNOWACT_DEEPSEEK_MODEL=deepseek-v4-flash
KNOWACT_DEEPSEEK_BASE_URL=https://api.deepseek.com
KNOWACT_DEEPSEEK_TIMEOUT_SECONDS=120
```

The simulator turn endpoint `/api/simulator/turn` accepts request-level `client_provider`, defaulting to `openai`, and uses the selected provider for both answer generation and answer validation. If the selected provider is not configured, the turn endpoint returns a non-leaking configuration error rather than falling back to unvalidated model text. `/api/simulator/preview` remains a deprecated compatibility alias.

The current tests use deterministic fixtures and fake clients; they do not call the OpenAI or DeepSeek APIs.

Run the current Python checks with:

```bash
uv run python -m unittest
```

Manually smoke-test Aliyun OSS signed URL access with:

```bash
uv run python scripts/manual_aliyun_oss_smoke.py
```

Start the backend development API with:

```bash
uv run fastapi dev backend/main.py
```

Start the frontend workbench in a second terminal with:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Run the Candidate Graph Review Workbench model checks with:

```bash
npm --prefix frontend run test:candidate-graph-workbench
```

The frontend currently exposes authoring modules for Knowledge Graph review, Profile Context confirmation, and User Map generation/review/promotion, plus a Simulator entry that runs reviewed-map-grounded single-turn answers without starting simulator episodes.

If the backend is running on a non-default port, set `VITE_API_PROXY_TARGET`, for example:

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8001 npm --prefix frontend run dev
```

Then open the frontend URL printed by Vite, or open the local Swagger UI at `http://127.0.0.1:8000/docs`. The current API includes:

- `POST /api/authoring/source-materials` and `GET /api/authoring/source-materials`, which upload PDF source materials into `storage/source_materials/{source_id}/original.pdf`, write `metadata.json`, and list registered source materials for the workbench.
- `GET /api/authoring/benchmark-domains`, which lists existing benchmark-domain directories for workbench selectors without creating or mutating benchmark data.
- `GET /api/authoring/graphs/{benchmark_domain}` and `GET /api/authoring/graphs/{benchmark_domain}/{version}`, which list and read reviewed authored graph snapshots for map-authoring selectors and visualization.
- `POST /api/authoring/graph-candidates`, which reads one PDF by relative path under `storage/`, resolves same-directory same-stem Parsed Source Markdown, calls MinerU to create or regenerate that Markdown when needed, sends the Markdown text only to the node extraction step, returns source-grounded skeletons, candidate nodes, candidate edges, Markdown cache metadata, and a compact run log summary, and writes `candidate_nodes.json`, `candidate_edges.json`, validation-passed `intermediate/` artifacts, and sidecar `workflow_log.json` by default. The workflow log records step status and links to `agent_traces/{step}/model_raw_output.txt`, `agent_traces/{step}/parser_output.json`, and batch trace artifacts where applicable, while still avoiding full prompt/source-material text. MinerU standard mode publishes the local PDF through a private Aliyun OSS staging object and short-lived signed URL before submitting the URL to MinerU; PDFs above `KNOWACT_MINERU_MAX_PAGES_PER_TASK` are split into chunks and their Markdown results are joined in page order. Only the node and edge files are candidate graph review artifacts. Example request:
- `GET /api/authoring/candidate-graphs/{benchmark_domain}/{run_id}` and `PUT /api/authoring/candidate-graphs/{benchmark_domain}/{run_id}`, which read and validate-save candidate graph review artifacts. The save endpoint overwrites `candidate_nodes.json` and `candidate_edges.json` only after schema and graph validation pass.
- `POST /api/authoring/candidate-graphs/{benchmark_domain}/{run_id}/promotion`, which revalidates saved candidate artifacts, copies them into `benchmark/domains/{benchmark_domain}/graphs/{version}/` as `authored_nodes.json` and `authored_edges.json`, and generates `graph_manifest.json`. Reviewed graph versions are immutable: an existing version returns `409 Conflict`, and corrections must publish a new version.
- `GET /api/authoring/users/{benchmark_domain}` and `GET /api/authoring/users/{benchmark_domain}/{user_id}`, which list and read confirmed Profile Context snapshots for map-authoring selectors and read-only preview.
- `POST /api/authoring/profile-context-candidates`, which generates one reviewable synthetic-user Profile Context draft and writes the minimal candidate run artifacts.
- `GET /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}` and `PUT /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}`, which read and validate-save the current Profile Context draft. The save endpoint edits persona fields only; run identity and benchmark domain remain fixed.
- `POST /api/authoring/candidate-profile-contexts/{benchmark_domain}/{run_id}/confirmation`, which publishes one validated draft as immutable `benchmark/domains/{benchmark_domain}/users/{user_id}/profile_context.json`. Confirmed user ids cannot be overwritten, and each candidate run can be confirmed at most once.
- `POST /api/authoring/map-candidates`, which loads one reviewed graph version and one confirmed Profile Context by identity, runs one full-graph knowledge-state outline call, partitions evidence authoring into contiguous reviewed-node windows, and writes `candidate_map.json`, `consistency_warnings.json`, `workflow_log.json`, outline/evidence intermediates, and per-batch step traces. Evidence batches default to `5` nodes and accept an optional positive `evidence_batch_size` override. One optional `sampling_temperature` value, defaulting to `0.7`, applies to the outline call and every evidence batch. Candidate-map run ids cannot overwrite existing runs; retry with a new run id.
- `GET /api/authoring/candidate-maps/{benchmark_domain}`, which lists candidate-map runs, including failed runs that retained workflow logs but did not write a promotable `candidate_map.json`.
- `GET /api/authoring/candidate-maps/{benchmark_domain}/{run_id}`, which returns one saved Candidate Knowledge Map and its artifact references for inspection.
- `GET /api/authoring/candidate-maps/{benchmark_domain}/{run_id}/warnings`, which returns generation-time edge-consistency warnings for candidate-map review.
- `POST /api/authoring/candidate-maps/{benchmark_domain}/{run_id}/promotion`, which revalidates one saved Candidate Knowledge Map with its reviewed graph and confirmed Profile Context, converts `kind` to `ground_truth`, and publishes immutable `maps/{map_id}/map.json` plus `map_manifest.json`. Existing `map_id` values return `409 Conflict`, generation-time `consistency_warnings.json` is not copied into reviewed data, and a successfully published run is removed from `candidate_maps/`.
- `GET /api/authoring/maps/{benchmark_domain}` and `GET /api/authoring/maps/{benchmark_domain}/{map_id}`, which list and read reviewed Knowledge Map snapshots for read-only workbench inspection.
- `POST /api/simulator/turn`, which returns one reviewed-map-grounded simulator answer. It accepts `benchmark_domain`, reviewed `map_id`, request-level `client_provider` (`openai` or `deepseek`, default `openai`), one diagnostic `question`, optional visible dialogue context, and optional debug-trace availability request metadata. Every turn writes a hidden local debug trace under `benchmark/domains/{benchmark_domain}/simulator/{map_id}/{question_id_or_auto}/`; `turn_options.include_debug_trace` only controls whether the response returns `debug_trace_id` and `debug_trace_available`. `/api/simulator/preview` remains a deprecated compatibility alias.

```json
{
  "pdf_path": "books/isl_python.pdf",
  "client_provider": "openai",
  "run_id": "dev_run_001",
  "force_reparse": false
}
```

PDF source material requests are constrained to `storage/` and reject absolute paths or `..` traversal. For `storage/books/isl_python.pdf`, the default Markdown cache path is `storage/books/isl_python.md`; existing Markdown is reused unless `force_reparse=true`. The LLM path uses Markdown text, not PDF base64 `input_file` or OpenAI `file_id`, and `client_provider` currently accepts `openai` or `deepseek` with `openai` as the default. OSS staging objects are temporary, private-bucket transport for MinerU URL parsing; signed URLs are not returned in API responses or workflow logs. Candidate generation never auto-promotes its outputs; reviewed graph and map publication are separate explicit promotion actions.

Implemented / planned components include:

- [x] V1 core schema and validation spine
- [x] Knowledge map representation
- [x] Phase 2 graph authoring workflow spine
- [x] OpenAI and DeepSeek SDK client boundaries for LLM-backed steps
- [x] FastAPI authoring API for real source-backed graph candidate runs
- [x] Candidate Graph Review Workbench frontend
- [x] User Map Authoring Workbench frontend
- [x] Simulator reviewed-map turn API and workbench entry
- [x] Phase 3 review-gated authored graph promotion with generated manifests
- [x] LLM-based Profile Context generation and immutable confirmation gate
- [x] Single-batch Candidate Knowledge Map generation tracer bullet
- [x] Reviewed map promotion with map manifests
- [ ] Ground-truth map authoring
- [ ] Human verification protocol
- [x] User simulator
- [ ] Tested agent interface
- [ ] ToM-aware agent loop
- [ ] Baseline agents
- [ ] Structured map comparison metrics
- [ ] Evaluation scripts
- [ ] Experiment reports

---

## Example Task Setting

A possible benchmark scenario:

```text
Domain: Research paper reading

Ground-truth user profile:
- Understands basic LLM concepts
- Has partial knowledge of RAG
- Does not fully understand Theory of Mind
- Confuses user modeling with personalization
- Wants to design a research project around AI-assisted paper reading

Agent goal:
- Interact with the user
- Infer the user's knowledge state
- Identify missing concepts and misconceptions
- Build a reconstructed knowledge map
- Choose helpful next actions
```

The agent is evaluated by how closely its reconstructed profile matches the hidden ground-truth profile and how effectively it uses that profile during the conversation.

---

## Why KnowAct?

Existing evaluations often test whether a model can answer questions about beliefs, intentions, or hidden states. KnowAct instead focuses on whether a model can use such reasoning in interaction.

The project shifts the evaluation focus from:

```text
Can the model describe the user's mental state?
```

to:

```text
Can the model act better because it models the user's mental state?
```

This makes KnowAct especially relevant for educational agents, research assistants, personalized AI systems, and knowledge-grounded collaborative agents.

---

## Roadmap

Future directions include:

- Designing richer knowledge map structures
- Creating multiple domains beyond paper reading
- Adding controlled misconceptions to user profiles
- Measuring active information-seeking behavior
- Comparing different agent architectures
- Studying failure modes in user simulation
- Reducing circularity between profile generation, simulation, and evaluation
- Testing with real human users after synthetic validation

---

## Citation

This project is under active development. Citation information will be added later.
