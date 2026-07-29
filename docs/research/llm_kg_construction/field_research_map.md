# Reliable KG Authoring for KnowAct: Research and Method Map

## Executive conclusion

KnowAct should not adopt a free-form autonomous multi-agent system. It should use a deterministic, staged authoring workflow with logically independent proposal and verification roles.

There is no universal best LLM-KG agent. The defensible synthesis of prior work is: define the target schema and guidelines, retain exact evidence, extract locally for recall, normalize globally, verify independently, repair with bounded actions, and escalate uncertainty to humans.

The design is called **Evidence-Grounded Diagnostic Graph Authoring (EDGA)**. Its novelty is intentionally modest: it adapts reliable components from KGC, ontology engineering, and educational assessment to the special graph KnowAct needs.

## Why KnowAct is a special KGC problem

Generic KGC asks whether text supports triples such as `(entity, relation, entity)`. KnowAct needs:

- a concept inventory at a stable diagnostic granularity;
- relations useful for reasoning about learning and diagnosis;
- L0--L5 mastery rubrics, observable signals, and plausible misconceptions;
- source provenance and an explicit boundary between extraction and expert assessment design.

A concept can be factually correct yet unusable as a benchmark node. Conversely, a useful mastery rubric may be valid expert operationalization without appearing verbatim in the textbook.

## Current KnowAct workflow and its limitations

The implemented reusable workflow is:

`PDF/Markdown → deterministic non-overlapping segments → local node extraction → global reconciliation → batched rubric authoring → one global edge call → structural validation → manual promotion`.

This is already better than a single prompt because it separates local extraction, reconciliation, and enrichment. It is not demonstrably the best method.

Key limitations are:

1. segments have no overlap, so cross-boundary concepts can be omitted;
2. downstream steps receive compressed grounding notes rather than exact source spans;
3. validation is mainly structural and does not establish semantic entailment;
4. there is no independent verifier, typed semantic repair, or calibrated abstention;
5. canonicalization and edge proposal each create a global context bottleneck;
6. the review gate lacks item-level reviewer identity, rationale, agreement, and edit history;
7. source checksums and complete inference configuration are not always bound to artifacts.

The three current reviewed v1.2 graphs require a separate caveat. Their manifests identify a direct prompt-guided authoring run rather than the reusable four-stage workflow, and candidate/reviewed snapshots are byte-identical. They must be treated as development artifacts until complete extraction and expert-review evidence is recorded.

## The EDGA workflow

### Stage 0 — Freeze the graph specification

Authors define:

- source scope and exclusions;
- competency questions the graph must support;
- node eligibility and granularity rules;
- relation definitions, direction, positive examples, and near misses;
- allowed provenance classes;
- hard validation constraints and expert escalation rules.

A candidate node must pass three gates: it is supported by the source, stable enough to name independently, and diagnosable by roughly one to three targeted questions.

### Stage 1 — Establish source integrity

Record source hash, parser and OCR versions, page coverage, section hierarchy, figures/tables handled, and extraction configuration. Invalidate cached parsing whenever the source hash changes.

Create structure-aware segments with modest overlap. Keep page, section, character offsets, and a short evidence quotation in a provenance sidecar; do not force long quotations into the public graph.

### Stage 2 — Extract local candidates for recall

An extractor sees one segment, the graph specification, and examples. It emits thin candidates: preferred name, aliases, concise definition, exact evidence, candidate type, and uncertainty.

The first pass is intentionally recall-oriented. A second coverage pass checks headings, definitions, formulas, examples, and salient terms that produced no node.

### Stage 3 — Verify grounding and eligibility

A fresh-context verifier sees each candidate and its original evidence. It separately labels:

- source support: explicit, entailed, unsupported, or insufficient context;
- eligibility: stable concept or incidental mention;
- granularity: acceptable, too broad, too narrow, or mixed;
- diagnostic value: observable or not operationalizable.

Unsupported items are not silently rewritten. They are sent to a bounded repair pass with source context, then deleted or quarantined if unresolved.

### Stage 4 — Canonicalize globally without a global prompt

Lexical and embedding retrieval generate high-recall duplicate candidates. A canonicalizer then makes explicit `keep`, `alias`, `merge`, or `split` decisions with rationales and retained provenance.

Reconciliation is hierarchical: within section, across neighboring sections, then across the domain. Retrieval narrows comparisons but never makes the semantic decision.

### Stage 5 — Author and validate diagnostic rubrics

For each canonical node, an authoring role creates the diagnostic goal, L0--L5 rubric, observable signals, misconceptions, and simulator guidance.

This stage follows evidence-centered design:

- **student/claim model:** what increasing knowledge of the node means;
- **evidence model:** what answer features support each level;
- **task model:** what question can elicit those features.

A separate validator checks ordinal monotonicity, adjacent-level distinguishability, observability, single-construct focus, and consistency with the definition. Rubrics are labeled `expert_pedagogical_extension` unless the source explicitly states them.

### Stage 6 — Propose relation candidates locally

Avoid one all-pairs or one full-graph prompt. Candidate pairs are the union of:

- co-occurrence and section adjacency;
- discourse cues such as “requires,” “part of,” and contrasts;
- semantic retrieval top-k;
- cross-references, equations, examples, and the LLM proposer's suggestions.

This stage optimizes candidate-pair recall; the next stage controls precision.

### Stage 7 — Apply type-specific edge tests

Each candidate pair is classified against every relation's decision test while viewing source evidence and node rubrics.

- `prerequisite_for(A,B)`: lacking A should normally block stable higher-level performance on B. Store direct dependencies only.
- `part_of(A,B)`: A is a structural component of B, not merely useful for it.
- `supports(A,B)`: A helps explain, transfer, or reason about B but is not necessary.
- `contrasts_with(A,B)`: comparing A and B clarifies a meaningful distinction; store a canonical symmetric form.

Record whether the edge is source-explicit, source-entailed, or an expert pedagogical extension. Direction/type disagreements abstain to human review.

### Stage 8 — Audit and repair the graph

Deterministic validation checks IDs, endpoints, schemas, self-loops, duplicates, source manifests, relation conflicts, and missing provenance. Prerequisite and part-of cycles are review warnings rather than automatically deleted errors.

Semantic repair uses `KEEP`, `FIX`, `REWRITE`, `DELETE`, or `QUARANTINE`, adapting GraphRefine's richer repair idea. The verifier that requests a rewrite cannot approve the rewritten item.

### Stage 9 — Conduct risk-ranked expert review

Prioritize low-confidence items, proposer--verifier disagreement, inferred/pedagogical edges, ambiguous merge/split decisions, cycles, and schema extensions.

Two experts review independently and a third adjudicates. Promotion stores reviewer identity/qualification, item decision, rationale, before/after diff, time, and agreement. A graph version is immutable after promotion.

## Recommended agent structure

The “agents” are bounded roles behind a deterministic orchestrator:

1. source-integrity checker;
2. local concept extractor;
3. grounding/eligibility verifier;
4. canonicalization adjudicator;
5. rubric author and rubric validator;
6. relation proposer and relation verifier;
7. deterministic graph auditor;
8. human review gate.

The same model may fill multiple roles, but proposer and verifier should use fresh contexts and independent instructions. A different verifier model is a useful ablation, not a prerequisite.

## Failure and boundary policy

| Failure | Handling | Terminal state |
|---|---|---|
| Timeout, 429, or 5xx | Idempotent request, exponential backoff with jitter, checkpoint resume | Retry or failed batch |
| Malformed JSON | Safe deterministic parser, exact schema feedback, maximum two retries | Valid item or failed batch |
| Unsupported definition | Recheck original span, typed repair | Fixed, deleted, or quarantined |
| Missing concept | Coverage pass and targeted re-extraction | Candidate or documented omission |
| Ambiguous merge/split | Preserve both candidates and provenance | Human adjudication |
| Edge type/direction conflict | Do not force a label | Human adjudication |
| Cycle | Inspect weakest-supported edge and node granularity | Reviewed resolution |
| Context overflow | Recursive/hierarchical reconciliation and retrieval | Resumed sub-batches |
| Partial artifact or bad manifest | Fail promotion | No reviewed snapshot |

The system is fail-closed: exceeding the repair budget never produces a silently “successful” graph.

## Expert validation

Recruit two subject-matter experts who can teach or assess the target material, plus one independent adjudicator. Suitable pools include course instructors, experienced teaching assistants, textbook-area researchers, and professional teaching networks.

Screen reviewers with teaching/research history and a short calibration task on held-out material. Record conflicts of interest and compensate review time. A KG/NLP expert may audit the schema but should not replace domain expertise.

Experts first annotate a locked subset from source text without seeing model candidates. They then review randomized, blinded candidate outputs. This produces both a recall-sensitive reference and realistic edit-time measurements.

Report agreement for node inclusion, node alignment, relation type/direction, rubric ratings, and provenance class. Use an appropriate categorical agreement statistic and ICC for ordinal/continuous rubric ratings.

## Experimental validation

### Baselines

1. human-only reference authoring;
2. one-shot full-document or chapter-level LLM;
3. segment extraction plus deterministic deduplication;
4. the current staged workflow without semantic verifier;
5. EDGA.

### Metrics

- **Nodes:** equivalent-only precision/recall/F1, duplicate rate, unsupported rate, over/under-splitting, source coverage.
- **Edges:** endpoint/type/direction F1, oracle-node edge F1, evidence support, conflict and cycle rates.
- **Canonicalization:** pairwise and cluster scores, over-merge and under-merge rates.
- **Rubrics:** fidelity, diagnostic relevance, monotonicity, adjacent distinguishability, observability, misconception plausibility.
- **Reliability:** first-pass/final schema validity, recovery, silent corruption, checkpoint-resume correctness.
- **Efficiency:** latency, tokens, retries, expert review time, accepted without edit.

Use chapter-stratified locked splits and paired cluster bootstrap intervals. Compare equal model/token budgets. Run fault injection and repeated stochastic extractions; do not report a single lucky graph.

## Paper positioning

The paper should say that EDGA is a source-grounded benchmark-construction protocol informed by EDC, PiVe, SAC-KG, KGGen, GraphJudge, GraphRefine, competency questions, ECD, and ACE.

It should not claim that EDGA is “the best,” that multi-agent systems are inherently superior, or that reviewed graphs were produced by EDGA until provenance confirms this.

The paper contribution is credible if experiments show a better quality--review-cost frontier and complete auditability. If quality is tied, reduced expert effort and lower silent-corruption risk remain meaningful results.
