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
- **Answer Policy** first decides answer content and produces a **Simulator Answer Intent**. The **Expression Context Builder** then converts that intent into a de-identified **Simulator Expression Context** before generation.
- **Profile Context** can only shape expression style and must preserve the content determined by the intent.
- LLM generation and LLM-backed validation are allowed, but both must sit behind interfaces and respect de-identified context boundaries.
- Unsafe or unvalidated answers fail closed into a **Simulator Safe Fallback**.
- Debug traces are hidden benchmark-author artifacts, separate from visible transcript and scoring outputs.
- Phase 5 preview is stateless per turn and must not become a parallel episode runtime.

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
Expression Context Builder
        |
        v
Answer Generator
  (LLM-backed or rule-based)
        |
        v
Content-Preserving Style Pass
        |
        v
Simulator Answer Validation
        |
        v
Simulator Answer
```

This diagram shows workflow components only. Intermediate artifacts such as **Simulator Answer Intent** and **Simulator Expression Context** are module outputs, not separate workflow steps.

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
  - Output: **Simulator Answer Intent**, the structured content stance for the answer.
- **Expression Context Builder**
  - Input: **Simulator Answer Intent**, de-identified evidence signals derived from grounded evidence, and visible dialogue needed for continuity.
  - Output: de-identified **Simulator Expression Context** for generation and validation.
- **Answer Generator**
  - Input: **Simulator Expression Context**.
  - Output: candidate natural-language answer.
- **Content-Preserving Style Pass**
  - Input: candidate answer, **Simulator Answer Intent** or expression context, and optional confirmed **Profile Context** for style only.
  - Output: styled candidate answer with the same content.
- **Simulator Answer Validation**
  - Input: styled candidate answer, de-identified expression context, intent-coverage expectations, grounding metadata, and leakage rules.
  - Output: pass/fail validation result with blocking reasons and fallback guidance.

## Question Grounding

**Question Grounding** interprets one received **Diagnostic Question** against the visible **Authored Knowledge Graph**. It does not choose the question for the **Tested Agent**.

Question Grounding must not use hidden **Reviewed Map** state or hidden **Ground-Truth Evidence**. Hidden map content enters only after grounding, when the context builder selects state and evidence for the grounded nodes.

The grounding contract should produce:

- grounded node ids
- optional grounding confidence for debug use
- whether the question is an **Integrated Diagnostic Question**
- whether the turn contains multiple independent diagnostic questions
- whether the question asks for hidden benchmark labels or other unsupported structured state
- whether no node could be grounded

Question Grounding is a contract, not a required implementation mechanism. It may start as rule-based matching, explicit node-id matching in development fixtures, or LLM-assisted classification.

Grounding confidence may be recorded for simulator debugging, but it must not be exposed to the **Tested Agent** or used as a scoring signal. Low confidence may lead the simulator to ask for clarification and should be reflected in hidden debug trace.

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

The answer policy reads grounded hidden state and evidence, then derives one **Simulator Answer Intent**.

Input:

- simulator-only context for the grounded turn, including directly grounded node rubrics, simulator behavior, hidden state, and grounded simulator-only evidence
- grounding result and diagnostic-question flags
- current diagnostic question text

Output:

- one **Simulator Answer Intent**

The policy is the simulator reasoning boundary. It may be rule-based, LLM-backed, or hybrid, but analysis, inference, judgement, and answer-content decisions belong here rather than in the expression or generation layers.

The policy is also the single owner of response-mode decisions. No-grounding, multiple-question, label-seeking, safe non-answer, and ordinary diagnostic answer modes should be represented in the **Simulator Answer Intent** and executed by service orchestration, rather than bypassing the policy with pre-policy fallback answers.

The simulator assumes reviewed map state and grounded evidence have already passed upstream map-authoring validation and benchmark-author review. It should not reconcile contradictions between a reviewed **User Knowledge State** and its **Ground-Truth Evidence** at answer time; that is a map-authoring quality issue, not a simulator policy responsibility.

The intent is a structured answer-content decision for this answer. A coarse stance may be one field inside the intent, but it is not the whole intent. The intent may represent:

- confident correct understanding
- partial or fragile understanding
- uncertainty or hesitation despite some exposure
- not knowing or being unable to answer
- a misconception
- an ability boundary
- whether a concrete example is appropriate based on grounded evidence

The structured intent should separate at least:

- response mode, such as answering, refusing a label request, asking for clarification, or using a safe non-answer
- grounded node answer decisions, including expressible capabilities, limitations, misconceptions, and unknown boundaries
- evidence selection, including which de-identified evidence signals may shape visible content
- rubric alignment, including which level-specific capabilities may be expressed without exposing mastery labels
- generation directives, including allowed answer form, example use, formula use, confidence, and first-person wording
- visibility guards, including hidden labels, evidence ids, state tables, map references, and unsupported facts that must not appear

LLM-backed policy output must be parsed into a strict schema. Freeform policy prose may appear only inside bounded content fields such as concise directives, capability summaries, limitations, and selected de-identified signals. The expression layer should compile the structured intent into generation material rather than forwarding a policy-authored prompt.

The policy may select, combine, compress, and paraphrase grounded node rubrics, simulator behavior, hidden map state, and grounded evidence signals. It must not author new user facts, new prior experiences, new worked examples, new evidence, or new abilities that are not supported by the grounded inputs.

The policy should not collapse mastery into a binary know/do-not-know stance. Intermediate states should remain diagnostically visible through uncertainty, fragile explanation, boundary statements, or misconception-led answers.

The intent may retain grounded evidence refs internally for audit and debug trace. Those refs must be removed before building the **Simulator Expression Context**.

The implementation should distinguish the downstream **Simulator Answer Intent** from a hidden **Simulator Policy Decision Trace**. The trace may record node ids, mastery labels, hidden evidence refs, selected rubric text, and policy reasoning metadata for benchmark-author audit. The intent consumed by expression and generation must not contain mastery labels, hidden evidence ids, map ids, user ids, or other hidden artifact identifiers.

For an **Integrated Diagnostic Question**, the policy should produce one integrated intent. It may preserve per-node stance internally, but the answer should not merely concatenate separate per-node answers.

The policy must not read hidden map state, hidden evidence, or mastery labels for nodes that were not directly grounded by the current question. Cross-node reasoning is allowed only for nodes grounded by one integrated diagnostic question.

## Expression Context Builder

The expression context builder converts the **Simulator Answer Intent** into a generator-safe **Simulator Expression Context**. The generator should receive this context, not the raw **Reviewed Map**.

Input:

- **Simulator Answer Intent**
- grounded evidence signals after removing hidden evidence ids
- visible dialogue needed for natural continuity

Output:

- one de-identified **Simulator Expression Context**

The expression context builder does not decide what the user knows, what misconception to express, or which evidence matters. It packages the policy's decisions into de-identified generation material.

The expression context may include:

- the **Simulator Answer Intent**
- de-identified evidence signals
- visible dialogue needed for natural continuity

It must not include:

- raw full map data
- mastery labels such as `L2`
- hidden evidence ids
- state-table language

Evidence refs used by policy may appear in hidden debug trace, but the generator should receive only evidence signals or paraphrased cues.

## Generators

The LLM generator is the naturalness-oriented path for simulator preview. A rule-based generator is useful as a soft fallback and for regression fixtures.

This is a soft implementation preference, not a permanent architectural ban. Any generator must respect the same **Simulator Expression Context** and validation contract.

LLM-backed answer prompt/message construction lives in step-specific simulator templates under `backend/knowact/simulator/templates/`. Answer generation uses `templates/answer_generation.py`, answer validation uses `templates/answer_validation.py`, and shared prompt sections live in `templates/common.py`. Do not introduce a catch-all simulator prompt module; each LLM step should keep its own prompt/message builder and output contract.

## Profile Context

During simulator answer generation, **Profile Context** may shape expression style only.

The answer content should first be determined from grounded **User Knowledge States**, **Ground-Truth Evidence**, and the **Simulator Answer Intent**. A Profile Context style pass may adjust tone, brevity, or wording, but it must preserve the content already determined by the intent.

The style pass must not add profile-derived facts, new examples, prior-experience claims, or ability claims. If profile-derived facts are needed as content, they must already exist as grounded **Ground-Truth Evidence** for the grounded nodes.

## Visible Dialogue Context

The simulator may read prior visible transcript data to understand follow-up wording and maintain conversational continuity.

Visible dialogue must not update the hidden **Static User Knowledge State**. It also must not become a second hidden memory channel for simulator-only reasoning.

## Label-Seeking Questions

If the tested agent asks for hidden benchmark labels, evidence ids, or a state table, the simulator must not reveal them.

It may answer with a natural self-report consistent with the **Simulator Answer Intent**. For example, instead of saying `L2`, it can say that the user has a rough idea but struggles to explain when to use the concept.

Label-seeking questions should still use the normal Answer Intent to generator to validator path, with generation instructions that forbid benchmark labels and structured hidden state. Use the label-seeking fallback only when generation or validation cannot produce a safe natural self-report.

## Answer Validation

**Simulator Answer Validation** checks both safety and usefulness.

The validation mechanism should be behind an explicit interface. The initial implementation may use an LLM-backed validator because semantic leakage and intent coverage are not reliably captured by simple string matching. Validator-specific prompt/message construction lives in `backend/knowact/simulator/templates/answer_validation.py`. The interface should allow later replacement with heuristic, rule-based, or hybrid validators without changing simulator policy.

Validator output should be structured, such as pass/fail decisions, blocking safety reasons, intent-coverage notes, and retry/fallback guidance. It should not become a benchmark score or primary evaluation signal.

The validator input should be de-identified. It may see the generated answer, **Simulator Answer Intent**, de-identified evidence signals, grounding metadata, and leakage rules. It must not receive raw full map data or hidden evidence ids.

If the validator service fails, times out, or is otherwise unavailable, the simulator should fail closed: do not expose the unvalidated generated answer, return a **Simulator Safe Fallback**, and record the validator failure in hidden debug trace.

If the validator is available and rejects a candidate answer, it must return structured rejection reasons. The simulator should use those reasons for a bounded regeneration loop before falling back. Regeneration must preserve the same **Simulator Answer Intent** unless the rejection shows that the intent itself is underspecified or unsafe.

Validation retry routing should preserve layer boundaries:

- expression leakage, unsupported wording, or weak intent coverage should retry answer generation with the same **Simulator Answer Intent**
- generator timeout, invalid JSON, or empty output may retry answer generation briefly before terminal fallback
- policy-schema failure, unsafe intent fields, contradictory intent, or an impossible intent should retry or fall back at the **Simulator Answer Policy** layer before answer generation
- validator unavailability should not trigger regeneration from an unvalidated answer; it should fail closed

Blocking safety checks include:

- mastery labels
- hidden evidence ids
- full map or state-table language
- benchmark scoring fields

Intent coverage checks are quality checks. The answer should carry the core stance of the **Simulator Answer Intent**, such as uncertainty, partial knowledge, misconception, or ability boundary. Weak coverage should be recorded in debug trace and may trigger regeneration or fallback.

A generated answer that violates the **Visibility Boundary** must not become visible to the **Tested Agent**.

Regeneration feedback may include concise blocking safety reasons, intent-coverage gaps, and retry guidance. It must not include hidden evidence ids, mastery labels, full hidden state, raw maps, or benchmark-author debug details in the material sent to the generator.

## Safe Fallback

When answer generation cannot safely produce a visible answer, the simulator should return a **Simulator Safe Fallback**.

Fallbacks should be natural and non-leaking. They should not expose validator internals, grounding internals, hidden node ids, hidden evidence ids, or benchmark labels.

Initial fallback categories should include:

- no grounding
- multiple independent questions in one turn
- hidden-label or structured-state request
- generator, validator, or system failure

If the LLM generator fails, times out, or returns no usable answer, the simulator should use a safe fallback rather than asking the validator to generate replacement content. The validator judges candidate answers; it does not serve as a backup generator.

Policy and answer fallback paths should still produce or consume the same **Simulator Answer Intent** schema where possible. Safe fallback is the terminal visible response after policy fallback, generation failure, validator unavailability, or bounded regeneration exhaustion.

## Debug Trace

The simulator may record a hidden **Simulator Debug Trace** for benchmark-author debugging.

This trace may include grounding, grounding confidence, grounded node ids, answer intent, validation results, fallback reason, and generator metadata. It must remain separate from visible transcript data, must not be shown to the tested agent, and must not be used as primary scoring input.

No-grounding and multiple-question flags belong in this hidden debug trace, not in the visible observation text.

**Simulator Answer Intent** may be retained in hidden debug artifacts for audit, but it should not be stored as part of the formal visible episode run artifacts. Formal run artifacts should center on visible transcript data, tested-agent outputs, and scoring reports.

The development preview writes a local **Simulator Debug Trace** for every
`POST /api/simulator/preview` request under:

```text
benchmark/domains/{benchmark_domain}/simulator/{map_id}/{question_id_or_auto}/
```

If the request supplies `question.question_id`, it must be filesystem-safe:
letters, numbers, dots, underscores, or dashes only. If no `question_id` is
supplied, preview generates `question_{timestamp}` as the trace directory key.
Repeating the same `question_id` overwrites the previous preview trace by
clearing that question directory first.

The preview trace directory contains `debug_trace.json` plus optional
`agent_traces/` raw/parser artifacts for LLM-backed steps:

- `agent_traces/answer_policy/model_raw_output.txt` and `parser_output.json`
- `agent_traces/answer_generation/attempt_{n}/model_raw_output.txt` and `parser_output.json`
- `agent_traces/answer_validation/attempt_{n}/model_raw_output.txt` and `parser_output.json`

Preview debug traces may store raw model outputs and parsed step outputs, but
they must not store full prompt/messages, full reviewed graph payloads, full
reviewed map payloads, or full confirmed profile-context payloads. The trace
stores artifact identities and directly grounded turn details instead.

## Runtime Logging

The simulator implementation should emit operator-facing logger `info` messages at
workflow boundaries so terminal output shows which step is running: reviewed
artifact loading, question grounding, simulator context construction, answer
intent derivation, expression-context construction, answer generation, answer
validation, fallback, and final preview completion.

Runtime logs are not **Simulator Debug Trace** artifacts and are not visible
transcript data. They should record only progress metadata such as artifact
identities, component names, counts, flags, result status, and output lengths.
They must not record full hidden map payloads, hidden evidence ids, hidden
evidence signals, profile-context prose, raw model output, prompt payloads, or
visible answer text.

## Preview Boundary

Phase 5 may expose a development-only simulator preview before formal **Evaluation Episode Manifests** exist. The preview should be stateless per turn so it does not become a parallel episode runtime.

Current initial route: `POST /api/simulator/preview`.

The current implementation supports visible-graph **Question Grounding**, direct-node-only simulator context construction, **Simulator Answer Intent** derivation, de-identified **Simulator Expression Context** construction, LLM-backed visible answer generation, LLM-backed answer validation, bounded answer regeneration, persistent local preview debug trace artifacts, and safe fallback behavior. It handles clearly grounded questions, no-grounding non-answers, multiple-question clarifications, and label-seeking requests without exposing hidden labels. It intentionally does not implement formal episode persistence yet.

The next simulator-policy implementation slice should stabilize the structured intent boundary before adding an LLM-backed policy. Recommended order: define the richer **Simulator Answer Intent** and hidden **Simulator Policy Decision Trace** schemas, make the rule-based policy emit that schema as deterministic fallback, make expression consume only downstream-safe intent, update generator prompts around structured intent, route no-grounding/multiple/label-seeking modes through policy, add bounded validation-regeneration, and then add an LLM-backed policy behind the same interface.

The preview should:

- select reviewed artifacts by identity, such as `benchmark_domain` and `map_id`
- accept request-level `client_provider`, using the same `openai` / `deepseek` provider vocabulary as authoring and defaulting to `openai`
- derive `graph_version` from the reviewed map's `map_manifest.json`
- derive `user_id` from the reviewed map's `map_manifest.json` and load the confirmed **Profile Context** when available
- use reviewed graphs and reviewed maps, not candidate artifacts
- reject inline or request-overridden profile context
- continue with a configuration warning when confirmed **Profile Context** is missing
- accept one primary diagnostic question per request
- accept optional request-carried **Visible Dialogue Context**
- write a local hidden debug trace artifact for every preview request
- accept optional `preview_options.include_debug_trace` and use it only to decide whether the response returns trace availability/reference metadata
- return only the visible simulator answer plus visible observation metadata
- keep visible observation metadata coarse, such as `answer`, `clarification`, or `non_answer`
- keep internal fallback categories and validation reasons out of visible metadata
- allow non-leaking configuration warnings in preview metadata, such as missing style context
- return only a `debug_trace_id` and `debug_trace_available` flag when debug trace metadata is requested
- keep the full **Simulator Debug Trace** behind a benchmark-author-only debug path or local artifact
- avoid server-managed preview session state

Formal episode routes come later through the runtime, where simulator answers become visible **Interaction Observations** inside an evaluation run. Formal tested-agent-visible observation metadata should be stricter than preview metadata and should not include benchmark-author configuration warnings.
