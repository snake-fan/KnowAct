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
| 3. Authored graph review and promotion | M3: reviewed v1 graph exists | Reviewed `authored_nodes.json`, `authored_edges.json`, and optional `graph_manifest.json` are available |
| 4. Ground-truth map authoring | M4: reviewed hidden maps exist | Each map covers every node in the episode graph and cites hidden evidence |
| 5. Episode runtime contract | M5: evaluation episode manifests validate | Manifests bind graph, hidden map, profile context, turn budget, interaction rule, and scoring profile |
| 6. User simulator | M6: simulator can answer bounded diagnostic turns | Simulator answers naturally without leaking mastery labels, hidden evidence ids, or full maps |
| 7. Tested agent interface and baselines | M7: baseline agents complete episodes | Fixed-question, random-question, and simple LLM agents submit final reconstructed maps |
| 8. Scoring and reports | M8: structured reports are reproducible | Reports include episode mastery distance, missing prediction rate, and unsupported inference rate |
| 9. End-to-end v1 benchmark run | M9: first v1 experiment report | Reviewed episodes run across v1 baselines with interpretable results and failure notes |
| 10. Research workbench | M10: reviewable UI/API surface | A minimal research interface supports graph/map inspection, episode review, and report browsing |
| 11. Post-v1 expansion | M11: next benchmark question selected | Multi-domain, teaching actions, real users, or richer agents are considered after v1 evidence |

## Phase 0: Domain Decision Baseline

Goal: keep implementation aligned with the domain language already established in `CONTEXT.md`.

Milestone M0:

- `Knowledge Graph`, `Knowledge Map`, `Ground-Truth Knowledge Map`, `Reconstructed Knowledge Map`, `Evidence Record`, `Evaluation Episode`, and `Scoring Profile` have stable meanings.
- The v1 scope is explicitly active diagnosis with a static user knowledge state.
- The formal v1 domain, source basis, graph size target, visibility boundary, turn definition, and scoring profile are already captured in ADRs.

Exit criteria:

- New implementation work can cite existing terms instead of inventing parallel names such as "user graph", "node state", or "profile score".
- Remaining open questions are execution details, not unresolved domain boundaries.

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

## Phase 2: Graph Authoring Workflow

Goal: build the project-owned authoring workflow that turns authoritative source material into reviewable candidate graph files.

Milestone M2:

- The `Node Extraction Agent Step` reads ISL Python source material and produces `Source-Grounded Node Skeletons` with simple `Source Locators`.
- The `Node Rubric Authoring Agent Step` turns node skeletons into complete candidate `Knowledge Nodes` with `diagnostic_goal`, L0-L5 `levels`, diagnostic signals, and `simulator_behavior`.
- The `Edge Proposal Agent Step` uses complete candidate nodes and rubrics to propose precision-first candidate `Knowledge Edges`.
- The final workflow output is exactly two JSON list files: `candidate_nodes.json` and `candidate_edges.json`.

Recommended milestone split:

- M2a: run the workflow on a small development fixture of roughly 5-8 nodes.
- M2b: run the workflow on the formal candidate graph target of 30-50 nodes.

Guardrails:

- Candidate nodes must be source-grounded, not brainstormed from model memory.
- Rubric authoring must not use unreviewed neighboring nodes or candidate edges.
- Edge proposal should omit weak, speculative, or merely related pairs.
- Candidate status belongs to filenames, directories, or review state, not inside node or edge objects.

## Phase 3: Authored Graph Review and Promotion

Goal: separate generated candidate graph data from reviewed benchmark graph data.

Milestone M3:

- Benchmark author review accepts, edits, or rejects candidate nodes and edges.
- Reviewed graph data is stored as separate `authored_nodes.json` and `authored_edges.json` JSON list files.
- Optional `graph_manifest.json` references graph id, version, source metadata, and the separate node/edge files.
- Edge `curation_confidence` values are accepted or revised by the benchmark author.

Review checklist:

- Every node is stable, diagnosable, and source-grounded.
- Every formal node has complete L0-L5 rubrics.
- Every edge has a canonical edge type and a clear `Knowledge Edge Rationale`.
- `contrasts_with` edges are not duplicated in both directions.
- `part_of`, `prerequisite_for`, and `supports` are not used as generic relatedness labels.

Decision point:

- Resolve a lightweight `Graph File Layout` before promoting the first reviewed graph, because ADRs intentionally deferred directory paths.

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

2. Should `Graph File Layout` be resolved before the first reviewed graph is promoted?
   - Recommended answer: yes, but keep it lightweight. ADRs already fixed file contents and split storage; only directory placement remains.

3. Should the frontend wait until after the first scorer and report path exists?
   - Recommended answer: mostly yes. A minimal review helper is fine, but the core benchmark validity depends on schemas, authored data, simulator, agents, and scoring first.

4. Should v1 include a custom ToM-aware agent beyond the simple LLM baseline?
   - Recommended answer: not as a required v1 milestone. First prove that the benchmark loop and baseline comparisons are stable; then add richer agents as post-v1 or v1.1 work.
