# Experiment 01: KG Scientific Validity

[中文](README.zh-CN.md)

## Purpose

This experiment evaluates the three currently generated Candidate Knowledge
Graphs: `Economy`, `ISLP`, and `OSTEP`. Qualified domain experts review node
scope fit, diagnostic usefulness, L0--L5 rubric quality, and edge validity,
type, direction, and provenance.

The study supports only a bounded content-validity claim. It does not establish
that the current authoring workflow is superior to another method or that a
graph exhaustively covers its domain.

## Current status

| Component | Status |
| --- | --- |
| Study design | Rebound to the three existing candidate runs |
| Independent review pages | Three offline HTML pages generated |
| Review data format | `knowact.kg_review_submission.v3` JSON |
| Comparison and confirmation | Driven by two complete review JSON files; exports `knowact.kg_review_confirmation.v3` JSON |
| Expert review | Not run |
| Results | Template only |

## Frozen review inputs

| Domain | Candidate run | Nodes | Edges | Representative tasks | Review page |
| --- | --- | ---: | ---: | ---: | --- |
| Economy | `kg_metadata_v1_economy_20260730_contract_retry_v6` | 22 | 20 | 50 | [`economy_kg_review.html`](materials/review_pages/economy_kg_review.html) |
| ISLP | `kg_metadata_v1_islp_20260730_evidence_v2` | 21 | 29 | 50 | [`islp_kg_review.html`](materials/review_pages/islp_kg_review.html) |
| OSTEP | `kg_metadata_v1_ostep_20260730_robust_v2` | 24 | 28 | 50 | [`ostep_kg_review.html`](materials/review_pages/ostep_kg_review.html) |

These are candidate artifacts, not reviewed benchmark graphs. Each page embeds
its nodes, edges, scope, source metadata, artifact SHA-256 values, and one
derived `graph_fingerprint`.

## Entry points

- [`design/experimental_design.md`](design/experimental_design.md): reviewer
  eligibility, independent review, controlled fields, JSON comparison,
  adjudication, and acceptance rules;
- [`materials/README.md`](materials/README.md): pages, JSON Schemas, builder,
  and execution instructions;
- [`materials/review_pages/compare_and_confirm.html`](materials/review_pages/compare_and_confirm.html):
  imports two complete reviews of the same graph, computes agreement, and
  exports the confirmation JSON;
- [`results/results_summary_template.md`](results/results_summary_template.md):
  unfilled aggregate result template.

## Data flow

```text
Frozen Candidate KG HTML
  -> complete R1 review JSON
  -> complete R2 review JSON
  -> JSON comparison and adjudication
  -> confirmation JSON
  -> required edits and refreeze
  -> structural validation
  -> explicit benchmark-author promotion
```

The review and confirmation stages do not use CSV. The confirmation JSON does
not perform promotion. Any edit, deletion, rejection, or scope issue requires
updated candidate artifacts, a newly hashed review package, and the review
follow-up required by the protocol.
