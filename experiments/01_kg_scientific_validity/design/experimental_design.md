# Three-Domain Candidate Knowledge Graph Expert Review Study

[中文](experimental_design.zh-CN.md)

> Status: protocol, three independent-review HTML pages, and the JSON
> comparison/confirmation page are prepared. No expert-review result has been
> recorded.

## Purpose and claim boundary

This study performs a content-validity check for the fixed `Economy`, `ISLP`,
and `OSTEP` candidate graphs:

> Do qualified domain experts judge the nodes to be source-supported, in scope,
> diagnostically useful, and equipped with distinguishable L0--L5 rubrics, and
> judge the edges to have valid relation types, directions, and provenance?

The study does not compare graph-authoring methods, estimate extraction recall
against a reference ontology, or treat a candidate graph as benchmark ground
truth. Results must be reported separately by domain; a shared workflow alone
does not establish cross-domain validity.

## Frozen review packages

| Domain | Candidate run | Nodes | Edges | Tasks |
| --- | --- | ---: | ---: | ---: |
| Economy | `kg_metadata_v1_economy_20260730_contract_retry_v6` | 22 | 20 | 50 |
| ISLP | `kg_metadata_v1_islp_20260730_evidence_v2` | 21 | 29 | 50 |
| OSTEP | `kg_metadata_v1_ostep_20260730_robust_v2` | 24 | 28 | 50 |

Each HTML package embeds:

- its `candidate_nodes.json` and `candidate_edges.json`;
- source title, citation, scope, 50 representative tasks, and excluded topics;
- SHA-256 values for candidate nodes, candidate edges, source metadata, and
  source content;
- a deterministic `graph_fingerprint` derived from that binding.

The inputs remain candidate artifacts. A reviewed graph can be published only
after independent review, JSON adjudication, required edits, refreezing,
structural validation, and explicit benchmark-author promotion.

## Reviewers

Recruit two independent reviewers per domain. Each reviewer must satisfy at
least one criterion:

- taught or assisted a university course directly covering the declared scope;
- conducted research or professional practice in that scope;
- holds an advanced degree with directly relevant coursework and assessment
  experience.

A reviewer must not have generated, edited, verified, or promoted the assigned
candidate graph. Project staff screen other project relationships before
assignment without adding another reviewer-data field. Export only
`reviewer_id`, `role`, `experience_band`, and `introduction`; use IDs such as
`R1` and `R2`, not names.

One person may review multiple domains only when separately qualified for each.
Every domain still requires two independent complete submissions. A third
qualified reviewer is needed only when R1 and R2 cannot resolve an item after
both independent submissions are complete.

## Independent review procedure

### 1. Open the domain HTML

Use one of:

- `../materials/review_pages/economy_kg_review.html`
- `../materials/review_pages/islp_kg_review.html`
- `../materials/review_pages/ostep_kg_review.html`

The page works offline, saves a browser-local draft, and can export draft JSON.
Reviewers must not discuss items or inspect each other's JSON before both
independent submissions are complete.

### 2. Review every node

Inspect the name, definition, source locators, diagnostic goal, L0--L5 levels,
diagnostic signals, and simulator behavior.

| Field | Allowed values |
| --- | --- |
| `scope_fit` | `in_scope`, `boundary`, `out_of_scope` |
| `granularity` | `appropriate`, `too_broad`, `too_narrow`, `mixed` |
| `diagnostic_usefulness` | `adequate`, `minor_issue`, `major_issue` |
| `rubric_quality` | `adequate`, `minor_issue`, `major_issue` |
| `decision` | `accept`, `edit`, `reject` |

`edit` requires the smallest necessary change and a rationale. `reject`
requires a rationale.

### 3. Review every edge

| Field | Allowed values |
| --- | --- |
| `relation_validity` | `valid`, `uncertain`, `invalid` |
| `type_correct` | `yes`, `no`, `uncertain` |
| `replacement_type` | blank or `part_of`, `prerequisite_for`, `supports`, `contrasts_with` |
| `direction_correct` | `yes`, `no`, `not_applicable`, `uncertain` |
| `provenance_class` | `source_explicit`, `source_entailed`, `expert_pedagogical_extension`, `unsupported` |
| `decision` | `accept`, `edit`, `delete` |

`type_correct=no` requires a replacement type. `contrasts_with` requires
`direction_correct=not_applicable`; other edge types cannot use that value.
`edit` requires an exact change and rationale; `delete` requires a rationale.
A merely related pair is not enough to retain an edge.

### 4. Check all 50 representative tasks

Rate every metadata-frozen task as:

- `sufficient`
- `partial`
- `insufficient`

`partial` or `insufficient` requires the missing/redundant content and a
rationale. This is a bounded scope check, not a formal ontology-recall estimate.

Then record one overall decision:

- `approve`
- `approve_after_edits`
- `do_not_approve`

### 5. Export complete review JSON

The page enables `status=complete` only after it validates:

- the four reviewer fields: ID, role, experience band, and introduction;
- controlled and conditional fields for every node and edge;
- all 50 coverage reviews;
- the overall graph decision.

The output schema is `knowact.kg_review_submission.v3`. It carries the complete
graph binding and fingerprint; filenames alone never establish the reviewed
input.

## JSON comparison and adjudication

After the two independent submissions, open
`../materials/review_pages/compare_and_confirm.html` and import both JSON files.
The page rejects:

- drafts or submissions that failed completeness validation;
- fingerprints outside the three frozen packages;
- two different graph fingerprints;
- identical reviewer IDs;
- mismatched node, edge, or task item sets/order.

It reports:

- raw agreement and Cohen's kappa for node `decision`;
- raw agreement and Cohen's kappa for edge `decision`;
- exact task-coverage agreement count;
- disagreement counts for each controlled field;
- total items requiring adjudication.

An item requires explicit resolution when either reviewer records:

- any controlled-field disagreement;
- `unsupported`, `out_of_scope`, `major_issue`, or `invalid`;
- `edit`, `reject`, or `delete`;
- `partial` or `insufficient` coverage;
- `approve_after_edits` or `do_not_approve`.

Each triggered item records a final decision, exact edit/action, and
adjudication rationale. The page exports
`knowact.kg_review_confirmation.v3` and stores SHA-256 values for both imported
review JSON files.

## Acceptance and promotion boundary

The confirmation JSON uses:

1. `not_approved` when the final overall decision is `do_not_approve`;
2. `edits_required` when any edit, deletion, rejection, coverage problem, or
   conditional approval remains;
3. `ready_for_structural_validation` only when all nodes and edges are accepted
   unchanged, all tasks are sufficient, and the overall decision is `approve`.

The page does not perform promotion and always emits `promotion_ready=false`.

- For `edits_required`, update candidate artifacts, regenerate a newly hashed
  package, and perform the protocol-required follow-up. The old confirmation
  does not establish that the new files were reviewed.
- For `ready_for_structural_validation`, run repository graph validation before
  the benchmark author explicitly invokes the non-overwriting promotion flow.
- Any later correction to a reviewed graph publishes a new version rather than
  overwriting the old one.

There is no arbitrary minimum kappa threshold. Raw agreement and kappa describe
review reliability; continuation depends on resolved validity defects,
unchanged artifact binding, completed adjudication, and structural validation.

## Study outputs

Archive separately per domain:

- two de-identified complete review JSON files;
- one complete confirmation JSON;
- input and final candidate/reviewed artifact hashes;
- structural-validation command and result;
- a new graph version when applicable;
- one completed result summary.

Blank pages, schemas, drafts, or passing generator tests are not expert-review
results.
