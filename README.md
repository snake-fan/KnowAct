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

## Running the Project Locally

Prerequisites:

- `make` for the repository-level development commands
- Python 3.12, matching `.python-version`
- `uv` for Python dependency management
- Node.js and `npm` for the React workbench

From the repository root, prepare `.env` and install backend/frontend dependencies:

```bash
make setup
```

Fill in `.env` only for workflows that call an external model provider, such as LLM-backed graph authoring or simulator turns. The backend can still be started for health checks and local UI/API wiring without real secrets. Graph authoring uses exactly three filesystem-managed sources: `Economy`, `ISLP`, and `OSTEP`. Place each manually prepared UTF-8 Markdown file under `storage/source_materials/{source_id}/`; its versioned `metadata.json` supplies the matching domain, a user-facing domain summary, aspect, at least 50 reference-grounded representative questions, exclusions, and node budget. The User Profile workbench displays that summary read-only before rough-description entry, while the graph generation form asks only for Source, Run ID, and Provider.

Episode registration reads provider-scoped model dropdowns from `KNOWACT_OPENAI_MODELS` and `KNOWACT_DEEPSEEK_MODELS` (comma-separated), with `KNOWACT_OPENAI_MODEL` and `KNOWACT_DEEPSEEK_MODEL` as defaults. A provider is available only when its API key is configured. The initial persistent Episode Run Queue is single-process; do not start the backend with multiple Uvicorn workers.

Start the FastAPI backend and React workbench together:

```bash
make dev
```

The backend listens on `http://127.0.0.1:8000` and the frontend on `http://127.0.0.1:5173` by default. Useful development URLs include `http://127.0.0.1:8000/health` and `http://127.0.0.1:8000/docs`. The frontend proxies `/api` and `/health` to the configured backend URL.

Start the backend and standalone participant app together:

```bash
make simulator-test
```

The participant app listens on `http://127.0.0.1:5174` by default.

Use separate terminals when only one service is needed:

```bash
make backend
make frontend
make simulator-test-frontend
```

The standalone participant app reads compatible domains, reviewed graphs, and
bilingual question banks from [`benchmark/question_banks/`](benchmark/question_banks/)
directly through the backend. Its optional
`simulator-test-frontend/.env.local` is needed only for API-origin, title,
provider, or language overrides.

The catalog currently contains 80 atomic bilingual items for each of Economy,
ISLP, and OSTEP. Each bank is accepted only with a source audit, per-item roleplay
screen, and content-hash-bound quality review; expert and psychometric validation
remain pending.

Startup settings are non-secret Make variables. Inspect them with `make config` and override them from the command line or process environment without editing source files:

```bash
make dev BACKEND_PORT=8001 FRONTEND_PORT=5174
make frontend VITE_API_PROXY_TARGET=http://127.0.0.1:8001
make simulator-test-frontend VITE_API_PROXY_TARGET=http://127.0.0.1:8001
```

Application credentials and model/service settings remain in the root `.env`; Make does not print or parse those secrets. `make env` creates `.env` from `.env.example` only when it is missing and never overwrites an existing file. Run `make help` for the complete command list.

Basic verification commands:

```bash
make test
make build
# or run both
make check
```

The three executable research packages are indexed in
[`experiments/README.md`](experiments/README.md). Study protocols, materials,
result templates, and generated artifacts live there; literature evidence and
method synthesis remain under `docs/research/`.

---

## Benchmark Design

KnowAct uses a semi-synthetic benchmark construction process:

V1 benchmark construction uses three fixed source/domain identities: `Economy`, `ISLP`, and `OSTEP`. This is intentionally a small research configuration rather than a general document-ingestion product. Every evaluation episode remains single-domain and binds one reviewed graph and one reviewed map; cross-domain calibration is an experimental concern rather than a frontend configuration feature. Existing artifacts or code paths that use `statistical_learning_with_python` or `classical_supervised_ml_algorithms` should be treated as migration/compatibility state.

1. **Benchmark Data Authoring**

   A project-owned graph authoring agent workflow uses model API calls to generate candidate knowledge graphs and candidate knowledge maps. For graph generation, the request contains only the selected fixed source, optional run id, and provider; the backend validates the source's local Markdown and loads its stable research scope from metadata. Graph authoring then derives Parsed Source Segments, extracts segment-level node drafts with bounded internal parallelism, and reconciles them into source-grounded node skeletons with source locators and concise grounding notes. Later rubric and edge steps consume structured intermediates rather than full source text. The final review output remains two JSON list files, one for nodes and one for edges. Candidate nodes must be extracted from the selected authoritative source and carry source locators; they should not be brainstormed from model memory. Persona, background, preferences, and task goals can guide map generation, but v1 evaluation uses only benchmark-author reviewed authored knowledge graphs and ground-truth knowledge maps for scoring.

   The Knowledge Graph workbench can reload a saved candidate by domain and run id for continued editing. An explicit Confirm saves and revalidates that candidate, publishes a new immutable reviewed graph version, and switches the page to the published read-only snapshot. Reviewed graphs can also be loaded directly by domain and version; evaluation runtime continues to accept reviewed artifacts only.

   Each v1 evaluation episode is declared by an explicit immutable manifest that binds the authored graph, hidden map, optional profile context, `max_turns`, interaction rule, fixed `squared_mastery_distance_v1` scoring profile, and pinned agent/provider/model/temperature/retry configuration. The runtime workbench loads eligible episodes into one persistent FIFO run queue for bounded parallel execution, turn-level checkpoint recovery, individual cancellation, and per-episode result inspection; it does not create batch resources.

2. **Human Verification**

   Generated profiles are manually checked and revised to ensure consistency, plausibility, and evaluability. The current `Economy`, `ISLP`, and `OSTEP` candidate-graph content-validity study uses frozen offline HTML packages under [`experiments/01_kg_scientific_validity/`](experiments/01_kg_scientific_validity/README.md): independent reviewers export hash-bound JSON, and a separate page compares two complete submissions and exports confirmation JSON before structural validation and explicit promotion.

3. **User Simulation**

   An LLM-based user simulator is conditioned on the hidden knowledge map and evidence, then answers diagnostic questions naturally without revealing mastery labels, hidden evidence ids, or the full map. It may be uncertain, partially correct, or reveal misconceptions, but its answers should remain consistent with the hidden map and evidence.
   See `docs/UserSimulator.md` for the Phase 5 SAGE simulator workflow, grounding, blueprint boundary, fallback, and single-turn boundaries; the human-validity protocol and materials are in [`experiments/02_simulator_human_validity/`](experiments/02_simulator_human_validity/README.md).

   The standalone React app under
   [`simulator-test-frontend/`](simulator-test-frontend/README.md) automates the
   initial personal-fidelity study without exposing the internal research
   workbench. A participant revises and confirms their Profile and node-level
   Knowledge Map, receives 20 sampled items from an independent bilingual bank,
   answers before SAGE answers the same item, and rates the two answers side by
   side. The frontend discovers compatible domain, graph, and bank data from
   the backend; the backend freezes the selected identities in each resumable
   private session. Expert blind rating is deferred to a later stage.

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

KnowAct v1 keeps evaluation focused on automatic comparison between the hidden ground-truth knowledge map and the tested agent's final reconstruction submission.

### 1. Profile Reconstruction Accuracy

The agent submits a full-graph final reconstruction with one `unknown|L0|...|L5` mastery prediction for every node. The primary v1 result is `episode_mastery_distance`: the mean squared distance between inferred and hidden `mastery_level` values across all nodes in the episode's authored knowledge graph. Submitted `unknown` values are missing predictions with distance `36`. Lower is better.

Possible supporting metrics include:

* Missing prediction rate
* Unsupported inference rate, based on missing visible evidence references
* Exact mastery match rate
* Per-node signed mastery error

V1 does not require a separate evaluator agent or LLM judge for primary scoring. Evidence records are used to make reconstruction more grounded and auditable, not to add another subjective evaluation layer. Unsupported inference is reported separately from mastery-level distance, and misconception/unknown text is not part of the initial automatic score.

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

### Experimental Evidence-Calibrated Agent

The `evidence_calibrated_agent` interprets visible answers as per-level likelihoods, persists an optional L0-L5 belief in the working map, and deterministically selects among multiple LLM-proposed questions using an inspectable risk-aware utility. It uses the same visibility, checkpoint, finalization, and scoring paths as the Simple LLM baseline. Method evidence is documented in [`docs/research/tested_agent_knowledge_map_reconstruction/`](docs/research/tested_agent_knowledge_map_reconstruction/README.md), and the executable comparison design is in [`experiments/03_agent_reconstruction/`](experiments/03_agent_reconstruction/README.md). It is a research candidate, not a validated replacement for the baseline.

### Oracle Profile Baseline

Out of scope for v1. An oracle may be useful later as an upper bound, but it is not needed to validate the first benchmark loop.

---

## Research Hypothesis

KnowAct is based on the hypothesis that:

> Agents with explicit user modeling and ToM-like action selection should infer user knowledge states more accurately and interact more efficiently than agents without such mechanisms.

This project tests whether that hypothesis holds under controlled knowledge-grounded interaction settings.

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
