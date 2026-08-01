# Final Method: SAGE User Simulator

[简体中文](04_final_method.zh-CN.md)

> Status: final consolidated method contract for the current implementation.
> SAGE is implemented; human fidelity and proxy validity remain unverified.
> Last updated: 2026-08-01.

## 1. Method Position

SAGE means **Scoped Answer Generation from Epistemic State**. It converts one reviewed hidden Knowledge Map into a bounded, natural-language answer to one diagnostic question.

SAGE is an information-flow method, not a cognitive model. Its contribution is the separation of public grounding, local hidden-state access, answer-content reasoning, and surface realization.

The method must support knowledge-state diagnosis without turning the Simulator into a queryable benchmark oracle. The Tested Agent infers user state from visible answers; it never receives the hidden map.

This document consolidates the executable method.

The literature audit remains in [`02_reviewed_paper_pool.md`](02_reviewed_paper_pool.md). The evidence argument remains in [`03_evidence_synthesis_and_sage.md`](03_evidence_synthesis_and_sage.md).

## 2. Claim Boundary

The method separates three claim types.

- **Implemented fact:** the current service enforces staged access, strict structured intermediates, bounded generation retry, safe fallback, and visible/hidden artifact separation.
- **Literature-supported motivation:** prior simulator, grounded-dialogue, student-modeling, and plan-to-text evidence motivates the decomposition.
- **Research hypothesis:** SAGE answers are faithful to people and preserve conclusions about Tested Agents. This requires human experiments.

“Final method” means that this is the canonical current method description. It does not mean that SAGE has passed human-validity, adversarial leakage, or proxy-validity evaluation.

## 3. Inputs and Invariants

One turn is bound to the following artifacts and inputs.

| Symbol | Input | Visibility and role |
| --- | --- | --- |
| \(\mathcal{G}\) | Reviewed Authored Knowledge Graph | Public structure used for grounding |
| \(\mathcal{M}^{\star}\) | Reviewed hidden Knowledge Map | Simulator-only node state |
| \(Z\) | Ground-Truth Evidence | Simulator-only support for reviewed states |
| \(q_t\) | Current Diagnostic Question | Visible turn input |
| \(\mathcal{H}^{vis}_{t-1}\) | Visible Dialogue Context | Optional visible continuity context |
| \(\eta\) | Confirmed Profile Context style hint | Optional wording control only |

The request selects `benchmark_domain` and reviewed `map_id`. The service derives `graph_version` and `user_id` from the immutable map manifest.

Candidate graphs and candidate maps are not valid Simulator inputs. Missing Profile Context does not block the turn; the service uses neutral wording and records a non-leaking warning.

Each turn contains one ordinary diagnostic question or one integrated multi-node question. Multiple independent questions are rejected as a clarification response.

## 4. End-to-End Method

```text
reviewed graph + diagnostic question + visible dialogue
  -> public-scope question grounding
  -> direct-node hidden context retrieval
  -> structured Simulator Answer Blueprint
  -> natural-language surface realization
  -> visible answer or safe fallback
  -> hidden audit trace
```

Formally:

\[
S_t = g(q_t,\mathcal{G},\mathcal{H}^{vis}_{t-1}),
\]

\[
C_t = R(\mathcal{M}^{\star},Z;S_t),
\]

\[
B_t = \pi(C_t,q_t),
\]

\[
a_t \sim p_{\phi}(\cdot\mid B_t,\mathcal{H}^{vis}_{t-1},\eta).
\]

Here, \(S_t\) is public grounding scope, \(C_t\) is permitted local hidden context, \(B_t\) is the de-identified blueprint, and \(a_t\) is the visible answer.

The order is the method's main control: hidden state is unavailable when scope is chosen, and raw hidden state is unavailable when answer wording is generated.

## 5. Stage 1: Public-Scope Question Grounding

The grounder interprets the question against the reviewed public graph before any hidden map data is loaded.

Its structured result contains:

- directly grounded node ids;
- an integrated-question flag;
- a multiple-question flag;
- a label-seeking flag;
- implicit no-grounding status when no node is returned.

The provider-backed grounder receives visible node identity, name, and definition. It may receive only the latest visible dialogue turn to resolve a follow-up reference.

It does not receive mastery, misconceptions, unknowns, simulator-only evidence, graph edges, scoring data, or the full hidden map.

Unknown node ids, provider failures, timeouts, malformed JSON, or schema failures trigger rule-based grounding fallback. A valid model-produced no-grounding result remains no-grounding.

This stage decides scope and flags. It does not decide what the user knows or how the final answer should sound.

## 6. Stage 2: Minimal Hidden-Context Retrieval

When grounding succeeds, the context builder retrieves state only for directly grounded nodes.

For each grounded node, it loads:

- the visible node rubric and simulator behavior;
- the reviewed `UserKnowledgeState`;
- evidence referenced by that state whose visibility is `simulator_only` and whose `node_id` matches.

Graph neighbors do not widen the hidden context. Edges do not authorize access to additional states.

If the turn has no grounding or contains multiple independent questions, the service builds an empty context. It does not load the reviewed map for answer-content generation.

Visible dialogue supports follow-up wording only. It does not update the static hidden Knowledge Map or become hidden long-term memory.

## 7. Stage 3: Epistemic Answer Policy

The Answer Policy is the reasoning boundary. It turns local reviewed state into a strict, de-identified `Simulator Answer Blueprint`.

The runtime fixes response mode from grounding:

| Grounding condition | Response mode |
| --- | --- |
| Multiple independent questions | `clarification` |
| No grounded node | `non_answer` |
| Hidden-label or state-table request | `label_refusal` |
| Valid grounded question | `answer` |

The rule-based fallback maps local state to one of five answer stances: correct, partial, uncertain, not knowing, or misconception.

Low mastery with an explicit misconception yields a misconception stance. L4–L5 yields correct understanding; L2–L3 yields partial understanding; L1 or an unresolved unknown yields uncertainty; the remaining case yields not knowing.

The blueprint contains:

- runtime-owned question text and response mode;
- primary stance;
- first-person answer shape and sentence budget;
- answer strategy;
- one content unit per grounded node;
- supported claim, boundary, misconception, uncertainty, cues, and overclaim limits.

The blueprint excludes mastery labels, node ids, evidence refs, map ids, user ids, ground-truth labels, and scoring fields.

An LLM-backed policy may select, compress, or paraphrase grounded rubrics and evidence. Its output must parse into the strict schema and preserve the expected node order and response mode.

Unsafe fields, unknown nodes, invalid integration mode, malformed output, timeout, or provider failure cause a deterministic rule-based policy fallback.

The hidden `Simulator Policy Decision Trace` may retain mastery and evidence references for benchmark-author audit. That trace is never generator or Tested-Agent input.

## 8. Stage 4: Surface Answer Generation

The generator receives only the blueprint, visible dialogue, an optional style hint, and retry guidance. It does not receive the raw graph, map, mastery labels, evidence ids, or Profile Context payload.

The generator renders one concise first-person answer. Integrated questions receive one integrated response, not a concatenation of independent mini-answers.

Profile Context may adjust tone, brevity, or phrasing after content has been fixed. It must not add facts, prior experience, examples, or abilities absent from the blueprint.

Model output must be one JSON object with a nonblank `answer`. The service makes at most two generation attempts.

Provider failure, timeout, invalid JSON, or an empty answer triggers retry. Exhaustion returns the fixed safe response: “I am not confident I can answer that cleanly right now.”

There is no independent post-generation semantic validator in the current method. Parsing proves contract conformance, not semantic fidelity or adversarial non-leakage.

## 9. Visible Output and Hidden Audit

The formal turn response exposes only:

- the natural-language answer;
- coarse observation kind: `answer`, `clarification`, or `non_answer`;
- non-leaking configuration warnings;
- an optional debug-trace reference and availability flag.

The workbench-only `turn-test` route may additionally expose directly grounded node ids for map highlighting. Formal episode transcripts exclude those ids.

Every turn writes a benchmark-author-only debug trace. It may contain artifact bindings, grounding decisions, local hidden-state summaries, blueprint data, model/parser artifacts, attempts, and fallback cause.

The visible transcript never contains the hidden trace, blueprint, mastery, evidence refs, Profile Context, scoring state, or raw model output.

## 10. Runtime Boundary

`POST /api/simulator/turn` is a stateless Phase 5 inspection boundary. It accepts request-carried visible dialogue but does not create a server-side conversation or an Evaluation Episode.

Formal evaluation uses the Episode Runtime. There, the same Simulator answer becomes a Tested-Agent-visible `Interaction Observation`; the hidden state and debug artifacts remain outside the visibility boundary.

Experiment 02 is a separate participant-facing orchestration. It reuses SAGE and reviewed artifacts, but it is not an Episode Runtime and does not invoke Tested Agents or scoring.

## 11. Human-Validity Protocol

The implemented participant path is deliberately narrow:

```text
participant Profile revision and confirmation
  -> node-by-node Knowledge Map revision and confirmation
  -> sample 20 unique items from a versioned bilingual bank
  -> save the participant answer
  -> generate the SAGE answer to the same item
  -> collect five 1-5 self-ratings
  -> persist a resumable private session
  -> retain answer pairs for later blind review
```

The human answer is saved before the Simulator answer is generated or shown. Questions are independent; one item's dialogue is not carried into the next item.

The five ratings cover core content, expressed knowledge, capability boundary, expression style, and overall representativeness. Completed pairs remain `blind_review_status = pending` for later expert rating.

This protocol establishes a data-collection path, not a result. Ethics review, domain-expert question review, bilingual-equivalence review, cognitive interviews, pilot work, and a frozen analysis plan remain formal-collection gates.

## 12. Evaluation Logic

SAGE must be evaluated on separate levels.

| Level | Question | Required evidence |
| --- | --- | --- |
| Structural access | Did each component receive only licensed fields? | Code inspection, contracts, tests, canaries |
| Output safety | Does the answer avoid direct and semantic leakage? | Adversarial leakage suite and blinded review |
| State fidelity | Does the answer express the intended mastery and boundary? | Matched human answers and state ratings |
| Personal fidelity | Does the participant recognize the answer as representative? | Participant self-ratings and comments |
| Proxy validity | Are agent effects preserved under simulation? | Matched human/Simulator agent comparisons |

Naturalness is secondary. A fluent answer can still leak hidden state, overstate ability, erase misconceptions, or change an agent ranking.

## 13. Baselines and Ablations

The full validation design should compare:

- monolithic role prompt;
- persona-only prompt;
- SAGE without the blueprint;
- SAGE without reviewed evidence;
- SAGE without style context;
- SAGE with rule-based realization;
- isolated full-map-context safety ablation;
- full SAGE.

The full-map and raw-state conditions are unsafe for routine benchmark execution. They belong only in an isolated validation harness whose output is never shown to Tested Agents.

The primary hypotheses are lower leakage, lower mastery overstatement, better preservation of uncertainty and misconceptions, style without content drift, and agreement with human-based agent comparisons.

Each hypothesis may fail independently. No single naturalness or self-fidelity score can validate the whole method.

## 14. Implementation Map

| Method component | Current implementation |
| --- | --- |
| Grounding | `backend/knowact/simulator/grounding.py` |
| Local hidden context | `backend/knowact/simulator/context_builder.py` |
| Answer policy and blueprint | `backend/knowact/simulator/policy.py` |
| Surface realization | `backend/knowact/simulator/generators.py` |
| Retry and fallback | `backend/knowact/simulator/service.py`, `fallbacks.py` |
| Prompt contracts | `backend/knowact/simulator/templates/` |
| Hidden trace | `backend/knowact/simulator/debug_trace.py` |
| Single-turn API contract | `backend/knowact/simulator/turn.py`, `api/simulator.py` |
| Participant validation | `backend/knowact/runtime/simulator_experiment.py` |

The canonical implementation detail remains [`../../UserSimulator.md`](../../UserSimulator.md).

The canonical participant protocol remains [`../../../experiments/02_simulator_human_validity/design/experimental_design.md`](../../../experiments/02_simulator_human_validity/design/experimental_design.md).

## 15. Current Limitations and Validation Priorities

The current implementation has explicit limits.

- Structural isolation cannot prevent every paraphrased leak or unsupported semantic implication.
- Grounding can under-scope or over-scope a question. The rule fallback is lexical, and the method has no grounding-confidence contract.
- The reviewed Knowledge Map is static during a turn sequence. SAGE does not model learning, fatigue, memory change, or state drift.
- The current style hint is coarse and has not been shown to preserve personal expression.
- The fixed safe fallback is English, which may reduce naturalness in Chinese sessions.
- The five participant ratings have not completed cognitive interviews or psychometric validation.
- No human dataset currently supports state-fidelity, personal-fidelity, or proxy-validity claims.

Validation should proceed in this order:

1. adversarial leakage probes and hidden-field canaries;
2. held-out human answer pairs with blinded state and boundary ratings;
3. blueprint, evidence, style, and generator ablations;
4. matched human/Simulator comparisons of agent effect direction and ranking.

## 16. Final Method Statement

SAGE answers a diagnostic question by first fixing its public graph scope.

It then retrieves only directly licensed hidden state, abstracts that state into a de-identified answer blueprint, and realizes the blueprint as a visible answer.

Its strongest current claim is structural: the implementation reduces direct raw-state exposure through staged contracts and failure closure.

Human fidelity, semantic non-leakage, and proxy validity remain falsifiable empirical claims. They must be reported only after the corresponding validation level is completed.
