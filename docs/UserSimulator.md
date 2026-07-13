# User Simulator

Status: Draft for Phase 5 design

This document defines the v1 user simulator workflow. It follows `CONTEXT.md`, the v1 ADRs, and `docs/V1ProjectBreakdown.md`. If this document conflicts with `CONTEXT.md` or an accepted ADR, the glossary and ADR take precedence.

## Goal

The v1 **User Simulator** answers **Diagnostic Questions** naturally while staying faithful to a hidden **Reviewed Map** and hidden **Ground-Truth Evidence**.

It is not a state-query API, a scoring component, or a tested-agent question-selection policy. The tested agent must infer the user's state from visible answers.

## Design Summary

- The simulator answers one **Diagnostic Question** per turn, including one **Integrated Diagnostic Question** when the question is genuinely a single multi-node probe.
- **Question Grounding** is a replaceable contract over the visible graph and dialogue context; it does not use hidden map state or select questions for the tested agent.
- Hidden map state and evidence enter only after grounding, and only for directly grounded nodes.
- **Answer Policy** first decides answer content and produces a de-identified **Simulator Answer Blueprint** that generation consumes directly.
- **Profile Context** can only shape wording style and must preserve the content determined by the blueprint.
- LLM generation sits behind an interface and receives only de-identified context.
- Leakage prevention is enforced by the policy-to-generator data boundary rather than a second model review; failed or malformed generation falls back safely.
- Debug traces are hidden benchmark-author artifacts, separate from visible transcript and scoring outputs.
- The Phase 5 single-turn endpoint is stateless per turn and must not become a parallel episode runtime.

## Workflow

```text
Diagnostic Question
  + Authored Knowledge Graph
  + Visible Dialogue Context
        |
        v
Question Grounding
        |
        v
Simulator Context Builder
        |
        v
Answer Policy
        |
        v
Answer Generator
  (LLM-backed or rule-based)
        |
Simulator Answer
```

This diagram shows workflow components only. **Simulator Answer Blueprint** is the structured intermediate artifact between policy and generation.

The implementation may collapse or split these components, but it should preserve their information boundaries.

Component contracts:

- **Question Grounding**
  - Input: **Diagnostic Question**, visible **Authored Knowledge Graph**, and **Visible Dialogue Context**.
  - Output: grounding result with grounded node ids, integrated-question flag, multiple-question flag, label-seeking flag, and no-grounding status.
- **Simulator Context Builder**
  - Input: grounding result, visible graph data for grounded nodes, hidden reviewed map data for directly grounded nodes, grounded **Ground-Truth Evidence**, and needed visible dialogue.
  - Output: simulator-only context for the grounded turn.
- **Answer Policy**
  - Input: simulator-only context, grounding result, and the current diagnostic question.
  - Output: **Simulator Answer Blueprint**, the structured content blueprint for the answer.
- **Answer Generator**
  - Input: **Simulator Answer Blueprint**, visible dialogue needed for continuity, optional style hint, and optional regeneration guidance.
  - Output: natural-language answer.

## Question Grounding

**Question Grounding** interprets one received **Diagnostic Question** against the visible **Authored Knowledge Graph**. It does not choose the question for the **Tested Agent**.

Question Grounding must not use hidden **Reviewed Map** state or hidden **Ground-Truth Evidence**. Hidden map content enters only after grounding, when the context builder selects state and evidence for the grounded nodes.

The grounding contract should produce:

- grounded node ids
- whether the question is an **Integrated Diagnostic Question**
- whether the turn contains multiple independent diagnostic questions
- whether the question asks for hidden benchmark labels or other unsupported structured state
- whether no node could be grounded

Question Grounding is a contract, not a required implementation mechanism. It may start as rule-based matching, explicit node-id matching in development fixtures, or LLM-assisted classification.

Provider-backed simulator construction may use LLM-assisted semantic grounding,
while direct deterministic service construction used by tests and fixtures may
keep the rule-based grounder. The API should not expose a separate grounding
strategy switch in the initial slice; provider-backed grounding is part of
simulator service wiring.

LLM-assisted grounding should stay simple: it maps the question to reviewed graph
nodes by intended concept meaning and does not introduce a grounding-confidence
contract. Its initial node payload should include only `node_id`, `name`, and
`definition`; it should not receive diagnostic goals, diagnostic signals,
rubrics, simulator behavior, edges, hidden user state, or hidden evidence. Its
structured output should cover `grounded_node_ids`, `is_multiple_question`, and
`is_label_seeking`; service code can continue deriving the integrated-question
flag from multiple grounded nodes that are not a multiple-question violation.
If the model-backed grounding step fails, times out, returns malformed JSON,
returns unknown node ids, or fails schema validation, the simulator may fall
back to rule-based grounding so local behavior remains non-oracular and the
hidden map loading boundary is preserved. A valid model-backed no-grounding
result should remain no-grounding rather than being overridden by rule-based
matching.

For follow-up wording, LLM-assisted grounding may receive at most the latest
visible dialogue turn's question and answer text. That context is only for
resolving references such as "say that again" or "can you expand on that"; it
should not become long-term simulator memory or widen grounding beyond the
current turn's intended concept.

Question Grounding should not introduce a grounding-confidence field or
threshold in the initial slice. Ambiguous or unsupported grounding should be
represented through the existing grounded node ids, integrated-question flag,
multiple-question flag, label-seeking flag, and no-grounding behavior.

Grounding identifies no-grounding, multiple-question, label-seeking, and integrated-question conditions, but it does not decide the final response mode. The **Simulator Answer Policy** decides how the simulator should respond to those grounded conditions.

## Turn Boundary

A turn may contain one ordinary **Diagnostic Question** or one **Integrated Diagnostic Question**.

An integrated question can ground to multiple nodes when it asks for one comparison, explanation, or application across concepts. It should not be treated as multiple independent turns.

A turn must not pack multiple independent diagnostic questions. When that happens, the simulator should not answer the knowledge content. It should ask for one specific question.

## Context Builder

The context builder uses only directly grounded nodes for hidden knowledge content.

It should include:

- grounded node rubrics and simulator behavior
- grounded **User Knowledge States**
- grounded node **Ground-Truth Evidence**
- **Visible Dialogue Context** needed for follow-up wording

It should not include hidden mastery or evidence from neighboring nodes merely because of graph edges.

If a question grounds to no nodes, the **Simulator Answer Policy** should choose a natural clarification or non-answer without using hidden map content.

No-grounding answers and multiple-question clarifications are still visible simulator answers. They should be recorded as visible observations when used inside an episode, because the tested agent spent a turn.

## Answer Policy

The answer policy reads grounded hidden state and evidence, then derives one **Simulator Answer Blueprint**.

Input:

- simulator-only context for the grounded turn, including directly grounded node rubrics, simulator behavior, hidden state, and grounded simulator-only evidence
- grounding result and diagnostic-question flags
- current diagnostic question text

Output:

- one **Simulator Answer Blueprint**

The policy is the simulator reasoning boundary. It may be rule-based, LLM-backed, or hybrid, but analysis, inference, judgement, and answer-content decisions belong here rather than in generation.

The policy is also the single owner of response-mode decisions. No-grounding, multiple-question, label-seeking, safe non-answer, and ordinary diagnostic answer modes should be represented in the **Simulator Answer Blueprint** and executed by service orchestration, rather than bypassing the policy with pre-policy fallback answers.

The simulator assumes reviewed map state and grounded evidence have already passed upstream map-authoring validation and benchmark-author review. It should not reconcile contradictions between a reviewed **User Knowledge State** and its **Ground-Truth Evidence** at answer time; that is a map-authoring quality issue, not a simulator policy responsibility.

The blueprint is a structured answer-content decision for this answer. A coarse stance may be one field inside the blueprint, but it is not the whole blueprint. The blueprint may represent:

- confident correct understanding
- partial or fragile understanding
- uncertainty or hesitation despite some exposure
- not knowing or being unable to answer
- a misconception
- an ability boundary
- whether a concrete example is appropriate based on grounded evidence

The structured blueprint should separate at least:

- `schema_version`, current diagnostic-question text, and response mode supplied by runtime
- `primary_stance` for the coarse answer posture across the turn
- `answer_shape` with first-person voice, single-node/integrated/clarification/non-answer mode, and a sentence budget
- `answer_strategy` that tells generation how to preserve the policy decision without restating fixed runtime rules
- `content_units` for each directly grounded node, including node name, stance, `core_claim`, optional `boundary`, optional `mistaken_belief`, optional `uncertainty`, selected de-identified `supporting_cues`, and `avoid_overclaiming` limits

Current generator-facing blueprint shape:

```json
{
  "schema_version": "simulator_answer_blueprint.v1",
  "question_text": "current diagnostic question",
  "response_mode": "answer",
  "primary_stance": "partial_understanding",
  "answer_shape": {
    "voice": "first_person",
    "integration_mode": "single_node",
    "max_sentences": 2
  },
  "answer_strategy": "concise policy-derived instruction for generation",
  "content_units": [
    {
      "node_name": "visible node name",
      "stance": "partial_understanding",
      "core_claim": "what the user can express",
      "boundary": "what remains weak or incomplete",
      "mistaken_belief": null,
      "uncertainty": "what the user is unsure about",
      "supporting_cues": ["de-identified supporting signal"],
      "avoid_overclaiming": ["claim the generator must not imply"]
    }
  ]
}
```

Fixed generation rules and visibility guards, such as first-person wording, benchmark-label refusal, hidden-id blocking, state-table blocking, and unsupported-fact blocking, belong in the generator runtime contract. They should not be repeated as LLM-authored policy output fields.

LLM-backed policy output must be parsed into a strict schema. Freeform policy prose may appear only inside bounded blueprint fields such as `answer_strategy`, `core_claim`, `boundary`, `mistaken_belief`, `uncertainty`, selected de-identified `supporting_cues`, and `avoid_overclaiming`. Generation should receive the structured blueprint directly rather than raw graph/map information or a policy-authored prompt.

The policy may select, combine, compress, and paraphrase grounded node rubrics, simulator behavior, hidden map state, and grounded evidence signals. It must not author new user facts, new prior experiences, new worked examples, new evidence, or new abilities that are not supported by the grounded inputs.

The policy should not collapse mastery into a binary know/do-not-know stance. Intermediate states should remain diagnostically visible through uncertainty, fragile explanation, boundary statements, or misconception-led answers.

The blueprint must not contain grounded evidence refs. Those refs may appear only in hidden audit trace.

The implementation should distinguish the downstream **Simulator Answer Blueprint** from a hidden **Simulator Policy Decision Trace**. The trace may record node ids, mastery labels, hidden evidence refs, selected rubric text, and policy reasoning metadata for benchmark-author audit. The blueprint consumed by generation must not contain mastery labels, hidden evidence ids, map ids, user ids, or other hidden artifact identifiers.

For an **Integrated Diagnostic Question**, the policy should produce one integrated blueprint. It may preserve per-node stance inside `content_units`, but the answer should not merely concatenate separate per-node answers.

The policy must not read hidden map state, hidden evidence, or mastery labels for nodes that were not directly grounded by the current question. Cross-node reasoning is allowed only for nodes grounded by one integrated diagnostic question.

## Generators

The LLM generator is the naturalness-oriented path for simulator turns. A rule-based generator is useful as a soft fallback and for regression fixtures.

This is a soft implementation preference, not a permanent architectural ban. Any generator must respect the same **Simulator Answer Blueprint** contract.

LLM-backed answer prompt/message construction lives in `backend/knowact/simulator/templates/answer_generation.py`, with shared prompt sections in `templates/common.py`. Do not introduce a catch-all simulator prompt module.

## Profile Context

During simulator answer generation, **Profile Context** may shape wording style only.

The answer content should first be determined from grounded **User Knowledge States**, **Ground-Truth Evidence**, and the **Simulator Answer Blueprint**. Profile Context may adjust tone, brevity, or wording, but it must preserve the content already determined by the blueprint.

The style pass must not add profile-derived facts, new examples, prior-experience claims, or ability claims. If profile-derived facts are needed as content, they must already exist as grounded **Ground-Truth Evidence** for the grounded nodes.

## Visible Dialogue Context

The simulator may read prior visible transcript data to understand follow-up wording and maintain conversational continuity.

Visible dialogue must not update the hidden **Static User Knowledge State**. It also must not become a second hidden memory channel for simulator-only reasoning.

## Label-Seeking Questions

If the tested agent asks for hidden benchmark labels, evidence ids, or a state table, the simulator must not reveal them.

It may answer with a natural self-report consistent with the **Simulator Answer Blueprint**. For example, instead of saying `L2`, it can say that the user has a rough idea but struggles to explain when to use the concept.

Label-seeking questions still use the normal Answer Blueprint-to-generator path, with generation instructions that forbid benchmark labels and structured hidden state. Use the label-seeking fallback when policy or generation cannot produce a natural self-report.

## Leakage Boundary

The simulator does not run a separate Answer Validation agent after generation. Leakage prevention is structural: policy converts grounded hidden state into a de-identified **Simulator Answer Blueprint**, and the generator receives only that blueprint, visible dialogue, and an optional style hint. It never receives raw maps, mastery labels, hidden evidence ids, map ids, user ids, scoring fields, or debug details.

Generator instructions still forbid benchmark labels, hidden ids, state-table wording, map dumps, scores, debug references, and schema language. Failed, timed-out, empty, or malformed model output may be retried briefly with the same blueprint before terminal fallback.

## Safe Fallback

When answer generation cannot safely produce a visible answer, the simulator should return a **Simulator Safe Fallback**.

Fallbacks should be natural and non-leaking. They should not expose grounding internals, hidden node ids, hidden evidence ids, or benchmark labels.

Initial fallback categories should include:

- no grounding
- multiple independent questions in one turn
- hidden-label or structured-state request
- generator or system failure

If the LLM generator fails, times out, or returns no usable answer, the simulator should use a safe fallback.

Policy and answer fallback paths should still produce or consume the same **Simulator Answer Blueprint** schema where possible. Safe fallback is the terminal visible response after policy fallback or bounded generation failure.

## Debug Trace

The simulator may record a hidden **Simulator Debug Trace** for benchmark-author debugging.

This trace may include grounding source, grounded node ids, answer blueprint, fallback reason, and generator metadata. It must remain separate from visible transcript data, must not be shown to the tested agent, and must not be used as primary scoring input.

No-grounding and multiple-question flags belong in this hidden debug trace, not in the visible observation text.

**Simulator Answer Blueprint** may be retained in hidden debug artifacts for audit, but it should not be stored as part of the formal visible episode run artifacts. Formal run artifacts should center on visible transcript data, tested-agent outputs, and scoring reports.

The single-turn simulator endpoint writes a local **Simulator Debug Trace** for every
`POST /api/simulator/turn` request under:

```text
benchmark/domains/{benchmark_domain}/simulator/{map_id}/{question_id_or_auto}/
```

If the request supplies `question.question_id`, it must be filesystem-safe:
letters, numbers, dots, underscores, or dashes only. If no `question_id` is
supplied, the simulator generates `question_{timestamp}` as the trace directory key.
Repeating the same `question_id` overwrites the previous turn trace by
clearing that question directory first.

The turn trace directory contains `debug_trace.json` plus optional
`agent_traces/` raw/parser artifacts for LLM-backed steps:

- `agent_traces/answer_policy/model_raw_output.txt` and `parser_output.json`
- `agent_traces/answer_generation/attempt_{n}/model_raw_output.txt` and `parser_output.json`

Turn debug traces may store raw model outputs and parsed step outputs, but
they must not store full prompt/messages, full reviewed graph payloads, full
reviewed map payloads, or full confirmed profile-context payloads. The trace
stores artifact identities and directly grounded turn details instead.

## Runtime Logging

The simulator implementation should emit operator-facing logger `info` messages at
workflow boundaries so terminal output shows which step is running: reviewed
artifact loading, question grounding, simulator context construction, answer
blueprint derivation, answer generation, fallback, and final turn completion.

Runtime logs are not **Simulator Debug Trace** artifacts and are not visible
transcript data. They should record only progress metadata such as artifact
identities, component names, counts, flags, result status, and output lengths.
They must not record full hidden map payloads, hidden evidence ids, hidden
evidence signals, profile-context prose, raw model output, prompt payloads, or
visible answer text.

## Single-Turn Boundary

Phase 5 exposes a usable single-turn simulator before formal **Evaluation Episode Manifests** exist. The endpoint is stateless per turn so it does not become a parallel episode runtime.

Current formal single-turn route: `POST /api/simulator/turn`. The workbench/test route `POST /api/simulator/turn-test` uses the same request contract and visible answer fields, but may add only `grounded_node_ids` so the benchmark-author UI can highlight the latest directly grounded **Knowledge Nodes**.

The current implementation supports visible-graph **Question Grounding**, direct-node-only simulator context construction, **Simulator Answer Blueprint** derivation, LLM-backed visible answer generation, bounded malformed-output retry, persistent local turn debug trace artifacts, and safe fallback behavior. It handles clearly grounded questions, no-grounding non-answers, multiple-question clarifications, and label-seeking requests without passing hidden labels to generation. It intentionally does not implement formal episode persistence yet.

The next simulator-policy implementation slice should keep hardening the structured blueprint boundary before broadening episode runtime integration. The rule-based policy and LLM-backed policy should emit the same **Simulator Answer Blueprint**, and generator prompts should consume that blueprint rather than raw map information.

The single-turn endpoint should:

- select reviewed artifacts by identity, such as `benchmark_domain` and `map_id`
- accept request-level `client_provider`, using the same `openai` / `deepseek` provider vocabulary as authoring and defaulting to `openai`
- derive `graph_version` from the reviewed map's `map_manifest.json`
- derive `user_id` from the reviewed map's `map_manifest.json` and load the confirmed **Profile Context** when available
- use reviewed graphs and reviewed maps, not candidate artifacts
- reject inline or request-overridden profile context
- continue with a configuration warning when confirmed **Profile Context** is missing
- accept one primary diagnostic question per request
- accept optional request-carried **Visible Dialogue Context**
- write a local hidden debug trace artifact for every turn request
- accept optional `turn_options.include_debug_trace` and use it only to decide whether the response returns trace availability/reference metadata
- return only the visible simulator answer plus visible observation metadata
- keep visible observation metadata coarse, such as `answer`, `clarification`, or `non_answer`
- keep internal fallback categories out of visible metadata
- allow non-leaking configuration warnings in turn metadata, such as missing style context
- return only a `debug_trace_id` and `debug_trace_available` flag when debug trace metadata is requested
- keep the full **Simulator Debug Trace** behind a benchmark-author-only debug path or local artifact
- avoid server-managed simulator session state

The `turn-test` endpoint is benchmark-author/workbench-oriented. It must not expose hidden map state, mastery labels, evidence refs, raw debug trace payloads, raw model outputs, or profile context. Its only field beyond the formal turn response is `grounded_node_ids`, a minimal **Question Grounding** signal for local UI highlighting. Formal episode transcripts and tested-agent-visible turn artifacts should still exclude `grounded_node_ids`.

Formal episode routes come later through the runtime, where simulator answers become visible **Interaction Observations** inside an evaluation run. Formal tested-agent-visible observation metadata should be stricter than single-turn metadata and should not include benchmark-author configuration warnings.

## Phase 5 Preview Verification

The Phase 5 simulator route set is a development and workbench preview of one reviewed-map-grounded turn. It is not a formal **Evaluation Episode** runtime, does not create or read **Evaluation Episode Manifests**, and does not persist server-side simulator sessions.

Regression tests use temporary, development-only reviewed graph/map/profile fixtures. They select simulator inputs by `benchmark_domain` and reviewed `map_id`, derive graph and user bindings from reviewed artifacts, and keep candidate graph/map runs out of the simulator input boundary.

The focused grounded-ambiguity regression module covers multiple mastery levels and evidence kinds. It checks uncertainty, partial correctness, self-correction, not knowing, ability boundaries, misconceptions, visible-dialogue follow-up wording without hidden state mutation, no-grounding preview non-answers, and multiple-question preview clarifications.

Run the focused simulator verification with:

```bash
uv run python -m unittest test/test_v1_simulator_grounded_ambiguity.py test/test_v1_simulator_service.py test/test_v1_simulator_turn_contracts.py
```

Run the full Python regression suite with:

```bash
uv run python -m unittest
```
