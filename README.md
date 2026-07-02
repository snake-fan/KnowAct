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

- Python 3.12, matching `.python-version`
- `uv` for Python dependency management
- Node.js and `npm` for the React workbench

From the repository root, install backend dependencies and prepare local environment variables:

```bash
uv sync
test -f .env || cp .env.example .env
```

Fill in `.env` only for workflows that call external services, such as LLM-backed graph authoring, simulator turns, MinerU parsing, or Aliyun OSS staging. The backend can still be started for health checks and local UI/API wiring without real secrets.

Start the FastAPI backend:

```bash
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The backend listens on `http://127.0.0.1:8000` by default. Useful development URLs include `http://127.0.0.1:8000/health` and `http://127.0.0.1:8000/docs`.

In a second terminal, install and start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL printed by the command, usually `http://localhost:5173`. The Vite dev server proxies `/api` and `/health` to `http://127.0.0.1:8000`; if the backend runs elsewhere, start the frontend with `VITE_API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev`.

Basic verification commands:

```bash
uv run python -m unittest
cd frontend && npm run build
```

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
