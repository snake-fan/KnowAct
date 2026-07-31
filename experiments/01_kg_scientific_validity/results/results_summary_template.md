# Knowledge Graph Expert Review Results

[中文模板](results_summary_template.zh-CN.md)

> Status: unfilled template. No expert-review result is claimed. Copy and
> complete this template separately for each domain.

## Frozen input

- Domain: `[Economy | ISLP | OSTEP]`
- Candidate run: `[run_id]`
- Graph fingerprint: `[sha256:...]`
- Candidate nodes SHA-256: `[hash]`
- Candidate edges SHA-256: `[hash]`
- Source metadata SHA-256: `[hash]`
- Source content SHA-256: `[hash]`
- Nodes / edges / representative tasks: `[N] / [E] / 50`
- Complete review JSON: `[R1 file + SHA-256]`, `[R2 file + SHA-256]`
- Confirmation JSON: `[file + SHA-256]`

## Reviewer profiles

| Reviewer ID | Role | Experience band | Introduction |
| --- | --- | --- | --- |
| R1 |  |  |  |
| R2 |  |  |  |

## Node review

| Metric | R1 | R2 | Final confirmation |
| --- | ---: | ---: | ---: |
| Accept, n (%) |  |  |  |
| Edit, n (%) |  |  |  |
| Reject, n (%) |  |  |  |
| Out of scope, n |  |  |  |
| Major diagnostic/rubric issue, n |  |  |  |

- Node-decision raw agreement: `[value]`
- Node-decision Cohen's kappa: `[value]`

| Controlled field | R1--R2 disagreements |
| --- | ---: |
| `scope_fit` |  |
| `granularity` |  |
| `diagnostic_usefulness` |  |
| `rubric_quality` |  |
| `decision` |  |

## Edge review

| Metric | R1 | R2 | Final confirmation |
| --- | ---: | ---: | ---: |
| Accept, n (%) |  |  |  |
| Edit, n (%) |  |  |  |
| Delete, n (%) |  |  |  |
| Invalid relation, n |  |  |  |
| Wrong type, n |  |  |  |
| Wrong direction, n |  |  |  |

- Edge-decision raw agreement: `[value]`
- Edge-decision Cohen's kappa: `[value]`

| Controlled field | R1--R2 disagreements |
| --- | ---: |
| `relation_validity` |  |
| `type_correct` |  |
| `replacement_type` |  |
| `direction_correct` |  |
| `provenance_class` |  |
| `decision` |  |

## Coverage

- Exact agreement across 50 task-coverage ratings: `[count]/50`
- Final `sufficient` / `partial` / `insufficient`: `[n] / [n] / [n]`
- Overall graph decisions: `R1=[value]`, `R2=[value]`, `final=[value]`
- Items requiring adjudication: `[count]`
- Unresolved items: `[must be 0]`

## Confirmation, edits, and promotion

- `promotion_readiness.status`: `[not_approved | edits_required | ready_for_structural_validation]`
- Node edits/rejections: `[summary]`
- Edge edits/deletions: `[summary]`
- Scope actions: `[summary]`
- Refrozen post-edit fingerprint: `[when applicable]`
- Structural validation: `[command and result]`
- Final graph version: `[not promoted or version]`
- Final node / edge SHA-256: `[hash] / [hash]`

## Paper-ready statement

> Two qualified and independent `[domain]` reviewers assessed every one of the
> fixed candidate graph's `[N]` nodes, `[E]` edges, and 50 representative
> tasks. Raw agreement on overall node and edge decisions was `[x]` and `[y]`
> (Cohen's kappa `[kx]` and `[ky]`). Every triggered item was handled through a
> JSON confirmation flow bound to the two input SHA-256 values; the reviewed
> graph was published only after required edits, refreezing, and structural
> validation.

## Claim boundary

This review supports content validity only for the declared domain aspect and
representative tasks. It does not establish authoring-method superiority,
exhaustive ontology recall, or universal psychometric validity of L0--L5 across
domains.
