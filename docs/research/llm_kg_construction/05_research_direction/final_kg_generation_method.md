# Final Method: KnowAct Knowledge Graph Generation

[中文版](./final_kg_generation_method.zh-CN.md)

Status: final consolidated description of the current implementation, aligned with the repository on 2026-08-01.

“Final” means this is the canonical method description for the current system. It does not mean the graph quality, psychometric validity, or EDGA research hypotheses have received final empirical confirmation.

## 1. Method Position

KnowAct does not generate a generic text-to-triples knowledge graph. It authors a small, source-grounded diagnostic graph that defines what knowledge the benchmark may diagnose.

The graph is user-independent. User mastery, misconceptions, evidence, and reconstructed state belong to a Knowledge Map and never to graph nodes or edges.

The implemented method is named `Graph Authoring Agent Workflow`. A precise descriptive name is **source-grounded, scope-conditioned, verification-gated diagnostic graph authoring**.

EDGA is a proposed research framing, not a synonym for every current implementation detail. Section 9 separates the implemented workflow from EDGA hypotheses.

## 2. Operational Contract

The workflow is designed around four invariants:

- Source claims must be traceable to a fixed, integrity-checked Markdown source.
- Node discovery, canonicalization, rubric authoring, and edge proposal are separate decisions.
- Model output remains candidate data until a benchmark author explicitly promotes it.
- Evaluation runtime may load only immutable reviewed graph versions.

The end-to-end path is:

```text
fixed source + versioned scope metadata
  -> deterministic segmentation
  -> local node drafts with exact excerpts
  -> global skeleton reconciliation
  -> role-separated skeleton verification
  -> L0-L5 diagnostic rubric authoring
  -> precision-first edge proposal
  -> structural validation and candidate export
  -> benchmark-author edit/review
  -> explicit immutable promotion
```

## 3. Fixed Inputs and Scope

### 3.1 Source catalog

The current research surface accepts exactly `Economy`, `ISLP`, and `OSTEP`. A benchmark author manually prepares UTF-8 Markdown outside the workflow and places it under `storage/source_materials/{source_id}/`.

The catalog resolves the file through `metadata.json`. Before generation, code checks the path boundary, recorded byte size, and SHA-256 digest. PDF-to-Markdown conversion is not part of KnowAct.

### 3.2 Metadata-owned scope

Each source owns a versioned `GraphAuthoringScope` containing:

- aspect name and description;
- at least 50 unique representative diagnostic tasks;
- explicit excluded topics;
- a soft target node count;
- a hard maximum node count.

The current three sources target about 20 nodes and cap output at 24. The target is not a quota: weak or duplicate nodes must not be added merely to reach it.

The API accepts only `source_id`, optional `run_id`, and `client_provider`. Domain, scope, tasks, exclusions, and node budget are loaded by the backend and cannot be overridden by the client.

## 4. Generation Pipeline

### Stage 0: Resolve and verify the source

The backend loads source metadata, requires `benchmark_domain == source_id`, verifies the source size and hash, and constructs one structured `SourceMaterial`.

Failure at this stage prevents any candidate run from starting. This makes the run refer to a fixed local source rather than an uploaded or prompt-embedded document.

### Stage 1: Deterministic segmentation

Local code parses Markdown headings, keeps a heading path of up to three levels, removes narrow structural noise, and packs adjacent sections into bounded windows.

Current defaults are 50,000 minimum, 100,000 target, and 150,000 maximum characters, with zero paragraph overlap. Oversized sections are split at paragraph boundaries when possible.

Segments receive deterministic run-local ids such as `seg_000001`, document-order assembly, a reviewer-facing location, a source locator, and `char_count`.

Segmentation is not an LLM decision. Its full text is retained only as a replay/debug intermediate artifact.

### Stage 2: Segment-level node extraction

Each segment and the frozen scope are sent to a Node Extraction Agent Step. Up to eight segment requests may run concurrently, but outputs are reassembled in original segment order.

The step returns thin drafts only: name, definition, source locator, grounding note, and a short `evidence_excerpt`. It must not write rubrics, edges, difficulty labels, or user state.

Each segment may return at most 12 drafts. A valid segment may return none when it contains no useful diagnostic concept, but the whole run fails when all segments yield zero drafts.

Code checks that each excerpt occurs in the supplied segment after narrow normalization for whitespace, line wrapping, hyphenation, and recognizable PDF margin intrusions.

A segment receives at most three contract attempts. Only excessive draft count or failed excerpt membership triggers a full local retry; parsing, schema, and later workflow failures remain fail-closed.

### Stage 3: Global skeleton reconciliation

One reconciliation step sees all thin drafts and the frozen scope. It deduplicates, merges, lightly splits, removes weak items, and selects a compact graph-wide concept set.

It reads structured drafts and their provenance, not the full source text. Every output must preserve supporting draft ids, segment ids, locators, unchanged excerpts, and a merge/split note.

The hard maximum is enforced without truncation. Final node ids are derived deterministically from canonical names; an id collision is an error rather than a request to add an arbitrary suffix.

### Stage 4: Skeleton verification

A separate verifier role audits every reconciled skeleton before rubric or edge authoring. It receives the scope, definition, locators, grounding notes, and evidence excerpts, but not the full source.

A skeleton may be kept only when its grounding is `supported`, its scope status is `in_scope`, and its diagnostic value is `high` or `medium`. Every input id must receive exactly one decision.

This is role and input separation, not guaranteed model independence. The current provider wiring may use the same model client for proposer and verifier.

### Stage 5: Diagnostic rubric authoring

Verified skeletons are processed in batches of eight. The Rubric Agent sees skeleton fields and the global Mastery Scale, but not full source text, unreviewed neighboring graph context, or candidate edges.

It writes only a rubric patch: `diagnostic_goal`, node-specific `L0`-`L5` descriptions, observable `diagnostic_signals`, and `simulator_behavior`.

Workflow code merges each patch with the source-grounded id, name, definition, type, and locators. The model does not recopy or control those grounded fields.

### Stage 6: Precision-first edge proposal

The Edge Proposal Agent runs after complete candidate nodes exist. It may use node rubrics and source-grounding context, but it cannot change nodes or encode user state.

Only four edge types are legal:

- `part_of`;
- `prerequisite_for`;
- `supports`;
- `contrasts_with`.

Weak, merely related, or directionally ambiguous pairs should be omitted. Empty edge output is valid. `curation_confidence` is a model suggestion, not an automatic acceptance threshold.

Code canonicalizes `contrasts_with` endpoint order and then validates the complete graph.

### Stage 7: Candidate validation and export

Blocking validation checks node-id uniqueness, source locators, complete diagnostic fields, exact `L0`-`L5` keys, nonblank signals, valid edge endpoints, legal edge types, and graph structure.

The final review payload contains only:

- `candidate_nodes.json`;
- `candidate_edges.json`.

`workflow_log.json`, `intermediate/`, and `agent_traces/` are audit and debugging sidecars. They do not change candidate lifecycle status and are not reviewed benchmark data.

### Stage 8: Benchmark-author review and promotion

The internal workbench can load and edit a candidate graph. Save overwrites the candidate node and edge lists only after structural validation.

Confirm first saves the current edits, revalidates the graph, assigns a new version, and publishes an immutable snapshot under `benchmark/domains/{domain}/graphs/{version}/`.

The reviewed snapshot contains `authored_nodes.json`, `authored_edges.json`, and `graph_manifest.json`. An existing version cannot be overwritten.

Only this explicit promotion changes the operational status from candidate to reviewed. Runtime loaders reject candidate run directories.

## 5. Traceability and Failure Semantics

Every successful boundary has a structured intermediate artifact. Every agent step records raw model output and parsed output, with per-segment or per-batch traces where applicable.

The workflow is fail-closed. It does not silently repair parser failures, over-budget reconciliation, incomplete rubrics, invalid endpoints, or graph validation failures.

Concurrency changes throughput, not assembly order. Segment ids, draft ids, rubric batch order, and exported lists remain stable relative to source order and accepted model output.

Candidate and reviewed data are deliberately separated by path and loader. Lifecycle state is not written into node or edge objects.

## 6. What Current Validation Establishes

The implementation currently establishes:

- source file identity and integrity at run start;
- mechanical occurrence of extraction excerpts in their segment;
- provenance consistency across drafts and reconciled skeletons;
- complete structured node rubrics and valid graph structure;
- explicit, non-overwriting promotion into a reviewed version;
- runtime exclusion of candidate graph directories.

These checks support auditability and schema reliability. They do not by themselves establish semantic correctness or scientific validity.

## 7. Current Snapshot

As inspected on 2026-08-01, the repository contains successful candidate runs for all three fixed scopes:

- `Economy`: 22 nodes and 20 edges;
- `ISLP`: 21 nodes and 29 edges;
- `OSTEP`: 24 nodes and 28 edges.

No `graphs/{version}/` reviewed snapshot was present for these three domains in the inspected workspace. These counts therefore describe candidates, not benchmark ground truth.

Experiment 01 provides frozen offline review pages, two-reviewer comparison, and adjudication exports. Those JSON submissions are scientific audit records; they do not perform operational graph promotion.

## 8. Known Limitations

### 8.1 Text occurrence is not semantic entailment

Exact excerpt membership shows that text occurred in the segment. It does not prove that the excerpt entails the node definition, the chosen granularity, or the diagnostic interpretation.

### 8.2 Verification is not fully independent

The verifier has a distinct role and restricted input, but current wiring can reuse the same provider and model. Independence must not be claimed without a separate model or human protocol.

### 8.3 Segmentation may lose boundary context

Zero overlap reduces duplicates and cost, but concepts spanning a segment boundary may be missed. Character count is only a coarse context proxy.

### 8.4 Rubrics are measurement artifacts

Source grounding of a concept does not validate its six mastery levels. Rubric clarity, expert agreement, and psychometric behavior require separate evaluation.

### 8.5 Edges have limited evidence semantics

Edge rationales, weights, and confidence are model-authored. Structural validation checks legality and endpoints, not source entailment or pedagogical validity.

### 8.6 Candidate edits can weaken provenance

The workbench permits human edits. Save and promotion validate the edited graph structurally, but do not re-link every edit to the original extraction and reconciliation evidence.

### 8.7 Recall is unknown

The workflow measures the quality of proposed items more easily than missing concepts. There is no locked independent reference subset that estimates concept or edge recall.

### 8.8 Downstream benefit is unmeasured

The current implementation does not prove that this workflow outperforms one-shot generation, reduces review cost, improves simulator validity, or stabilizes tested-agent rankings.

## 9. Implemented Method Versus EDGA

The present workflow already implements source integrity checks, local extraction, global canonicalization, a verifier role, structured rubrics, precision-first edges, audit artifacts, and human promotion.

The proposed EDGA direction adds stronger claims and mechanisms: genuinely independent verification, semantic entailment checks, typed repair, quarantine, risk-ranked expert review, and comparative evaluation.

Until those mechanisms and experiments exist, call the production path `Graph Authoring Agent Workflow`. Treat EDGA quality, cost, and downstream improvements as hypotheses.

## 10. Verifiable Next Improvements

The next work should be framed as tests, not assumed upgrades:

1. Compare zero-overlap segmentation with small boundary overlap and measure duplicate rate, recall, cost, and reconciliation burden.
2. Add blinded semantic-support judgments for sampled node-definition/excerpt pairs.
3. Compare same-model verification with cross-model and human verification under matched budgets.
4. Build a locked expert reference subset to estimate node, edge, and missing-concept recall.
5. Evaluate L0-L5 rubrics separately for expert agreement and response-level separability.
6. Require edit-level provenance or explicit review annotations before promotion.
7. Measure how graph variants change review effort, simulator fidelity, reconstruction scores, and tested-agent rankings.

## 11. Implementation Map

- Orchestration: [`workflow.py`](../../../../backend/knowact/authoring/workflow.py)
- Agent steps and batching: [`steps.py`](../../../../backend/knowact/authoring/steps.py)
- Deterministic segmentation: [`segments.py`](../../../../backend/knowact/authoring/segments.py)
- Authoring validation: [`validation.py`](../../../../backend/knowact/authoring/validation.py)
- Candidate artifacts: [`output.py`](../../../../backend/knowact/authoring/output.py)
- Source contract: [`source_configuration.py`](../../../../backend/knowact/authoring/source_configuration.py)
- Source integrity: [`source_material_catalog.py`](../../../../backend/knowact/storage/source_material_catalog.py)
- Promotion: [`review_promotion.py`](../../../../backend/knowact/authoring/review_promotion.py)
- Reviewed storage: [`reviewed_graphs.py`](../../../../backend/knowact/storage/reviewed_graphs.py)
- Operational workflow: [`01-graph-authoring.md`](../../../workflow/01-graph-authoring.md)
- Review and promotion: [`02-graph-review-promotion.md`](../../../workflow/02-graph-review-promotion.md)
- Research basis: [`method_map.md`](../04_maps/method_map.md) and [`gap_map.md`](../04_maps/gap_map.md)
- Expert-review experiment: [`experiments/01_kg_scientific_validity`](../../../../experiments/01_kg_scientific_validity/README.md)

## 12. Final Claim Boundary

The current method is a reproducible way to turn a fixed scoped source into an auditable candidate diagnostic graph and, after explicit human action, an immutable reviewed graph version.

It is not yet evidence that the resulting graph is semantically complete, psychometrically valid, or superior to alternative authoring methods. Those are experimental questions.
