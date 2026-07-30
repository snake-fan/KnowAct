# Statistical Learning Graph Expert Review Study

## Purpose and claim boundary

This study provides a proportionate content-validity check for the fixed KnowAct
`statistical_learning_foundations` graph. It asks whether qualified domain
experts judge the graph to be source-supported, in scope, diagnostically useful,
and relationally coherent.

It is deliberately **not** a comparison of graph-authoring methods. It does not
compare one-shot and staged generation, estimate extraction recall against a
reference ontology, or claim that the graph is the unique or complete ontology
of statistical learning.

The supported paper claim is limited to:

> The graph was completely reviewed by two independent statistical-learning
> experts using a prespecified item-level form, with all disagreements and
> requested edits resolved before the graph was used in reported experiments.

## Frozen review package

- Benchmark domain: `statistical_learning_foundations`
- Review input graph: `v2.0`
- Nodes: 21
- Edges: 30
- Declared representative tasks: 5
- Source: manually prepared ISLP Markdown snapshot
- Candidate run: `scoped_evidence_gpt55_20260730_v3`

Frozen artifact hashes:

| Artifact | SHA-256 |
| --- | --- |
| `authored_nodes.json` | `ba6efb98140cc93e9166c89a2ea038566be7a79c027a821ec1cc629544b4fda0` |
| `authored_edges.json` | `eaf665e1c88f476cdd702ce0456183337ae1422eb3067e1f5b17182b5be9152f` |
| `graph_manifest.json` | `201ad674ad4a908b4dd8980fbc46edc6a3a731d41e1243a13f54791051ca4b85` |
| source Markdown | `f41927934e0f921654013caeffe29430bf5aae2d6cf4a2216bd54e94d4daf374` |

Repository inputs:

- `benchmark/domains/statistical_learning_foundations/graphs/v2.0/authored_nodes.json`
- `benchmark/domains/statistical_learning_foundations/graphs/v2.0/authored_edges.json`
- `benchmark/domains/statistical_learning_foundations/graphs/v2.0/graph_manifest.json`
- `storage/source_materials/islp_statistical_learning_foundations_md_v1/source.md`

Reviewers receive the frozen graph files, the source Markdown, the declared
scope, and their own copies of the forms in this directory. They do not receive
agent traces, verifier decisions, or the previous internal AI review until
their independent reviews are complete.

## Reviewers

Recruit two reviewers who satisfy at least one of the following:

- taught or assisted a university course covering statistical learning or
  regression;
- conducted research using statistical learning or regression methodology;
- hold an advanced degree with directly relevant coursework and assessment
  experience.

Reviewers must not have generated, edited, verified, or promoted the candidate
graph. Any other relationship to the project is disclosed in the conflict-of-
interest field before review begins.

Use reviewer codes such as `R1` and `R2` in study data. Record qualifications
in `reviewer_metadata_form.csv`; do not store unnecessary personal data.

A third qualified reviewer is needed only if R1 and R2 cannot resolve an item
after seeing each other's completed judgments.

## Procedure

### 1. Prepare independent copies

Create one copy of each of these files for each reviewer:

- `reviewer_metadata_form.csv`
- `node_review_form.csv`
- `edge_review_form.csv`
- `global_coverage_review_form.csv`

Do not let reviewers discuss items or see each other's responses before both
copies are submitted. Each reviewer completes one independent pass; it may be
split across sittings, but actual active review time must be recorded.

### 2. Review all nodes

For every node, the reviewer inspects the name, definition, source locator,
diagnostic goal, L0--L5 rubric, diagnostic signals, and simulator behavior.
The reviewer fills the following controlled fields:

| Field | Allowed values | Meaning |
| --- | --- | --- |
| `source_support` | `supported`, `partial`, `unsupported`, `uncertain` | Whether the source supports the node name and definition. |
| `scope_fit` | `in_scope`, `boundary`, `out_of_scope` | Whether the node belongs to the declared aspect and tasks. |
| `granularity` | `appropriate`, `too_broad`, `too_narrow`, `mixed` | Whether one node is a stable diagnostic unit. |
| `diagnostic_usefulness` | `adequate`, `minor_issue`, `major_issue` | Whether answers can reveal meaningful knowledge differences. |
| `rubric_quality` | `adequate`, `minor_issue`, `major_issue` | Whether L0--L5 is ordered, observable, and distinguishable enough for the benchmark. |
| `decision` | `accept`, `edit`, `reject` | Overall item decision. |

`edit` and `reject` require a short rationale. `edit` should also state the
smallest proposed correction. Reviewers may consult the cited source section;
string occurrence alone is not treated as semantic support.

### 3. Review all edges

For every edge, the reviewer inspects the endpoint nodes, proposed relation
type, direction, and rationale.

| Field | Allowed values | Meaning |
| --- | --- | --- |
| `relation_validity` | `valid`, `uncertain`, `invalid` | Whether a meaningful graph relation holds. |
| `type_correct` | `yes`, `no`, `uncertain` | Whether the proposed canonical type is correct. |
| `replacement_type` | blank or one canonical type | Required when a different type is proposed. |
| `direction_correct` | `yes`, `no`, `not_applicable`, `uncertain` | Direction check; `not_applicable` is for `contrasts_with`. |
| `provenance_class` | `source_explicit`, `source_entailed`, `expert_pedagogical_extension`, `unsupported` | Basis for the relationship. |
| `decision` | `accept`, `edit`, `delete` | Overall edge decision. |

The four canonical types remain `part_of`, `prerequisite_for`, `supports`, and
`contrasts_with`. A merely related pair is not enough to retain an edge.

### 4. Check graph-level coverage

Each reviewer rates all five representative tasks as `sufficient`, `partial`,
or `insufficient` and identifies any essential missing or redundant concept.
This is a bounded scope check, not a formal recall estimate against a reference
ontology.

The reviewer then records one overall decision:

- `approve`
- `approve_after_edits`
- `do_not_approve`

### 5. Compute descriptive agreement

Report separately for nodes and edges:

- counts and percentages for `accept`, `edit`, and `reject/delete`;
- raw agreement on the overall item decision;
- Cohen's kappa on the overall item decision;
- the number of disagreements in each controlled review field;
- total reviewer time.

Because every item in the fixed graph is reviewed, no sampling-based hypothesis
test is required. Raw agreement must always be reported alongside kappa because
a high prevalence of accepted items can depress kappa.

### 6. Adjudicate and version

Copy R1 and R2 node decisions, edge decisions, task-coverage ratings, and
overall graph decisions into the corresponding prefilled rows of
`adjudication_form.csv`. Adjudication is required for:

- different overall decisions;
- any `unsupported`, `out_of_scope`, `major_issue`, `invalid`, or
  `provenance_class=unsupported` judgment;
- every requested edit or deletion;
- every task rated `partial` or `insufficient` by either reviewer.

Record the final decision, exact edit, and rationale. R1 and R2 may resolve an
item by discussion; use a third reviewer only when disagreement remains.

Do not overwrite `v2.0`. If adjudication changes graph content, publish a new
graph version such as `v2.1`. If the graph is accepted unchanged, retain the
frozen version and archive the completed review forms and result summary with
the hashes above.

## Acceptance rule

The graph is eligible for reported benchmark experiments only when:

1. both reviewers completed every node, edge, and coverage item;
2. no unresolved disagreement remains;
3. no final item is `unsupported`, `out_of_scope`, `major_issue`, or `invalid`;
4. every requested edit/delete decision is implemented or rejected with a
   recorded adjudication rationale;
5. each representative task is finally judged sufficiently covered or has a
   documented scope justification;
6. the final graph passes the repository's structural graph validation.

There is intentionally no arbitrary minimum kappa threshold. Agreement is
reported as evidence about review reliability; adjudication and zero unresolved
validity defects determine promotion eligibility.

## Study outputs

Archive the following without embedding reviewer names in public artifacts:

- two reviewer metadata forms;
- two completed node forms;
- two completed edge forms;
- two completed coverage forms;
- one completed adjudication form;
- one completed `results_summary_template.md`;
- final graph hashes and, when applicable, the new graph version.
