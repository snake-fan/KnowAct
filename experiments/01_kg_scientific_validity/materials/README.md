# Experiment 01 Materials

[中文](README.zh-CN.md)

This directory uses offline HTML to collect reviews and imports/exports JSON
only. The legacy CSV forms are no longer execution materials.

## Files

- `review_pages/economy_kg_review.html`: independent Economy candidate KG review;
- `review_pages/islp_kg_review.html`: independent ISLP candidate KG review;
- `review_pages/ostep_kg_review.html`: independent OSTEP candidate KG review;
- `review_pages/compare_and_confirm.html`: imports two complete reviews of the
  same graph, computes raw agreement and Cohen's kappa, resolves triggered
  items, and exports confirmation JSON;
- `schemas/kg_review_submission.schema.json`: review submission contract;
- `schemas/kg_review_confirmation.schema.json`: comparison and confirmation
  contract;
- `../tools/build_review_pages.py`: rebuilds all four pages from the three
  explicitly bound candidate runs and their source metadata;
- `../templates/`: offline page templates.

## Independent review

1. Give the relevant domain HTML page separately to two qualified reviewers.
2. Before submission, neither reviewer may see the other's judgments, Agent
   traces, or previous internal AI reviews.
3. The page saves a local browser draft and can export `status=draft` JSON.
4. It enables `status=complete` export only after the four reviewer fields
   (`reviewer_id`, `role`, `experience_band`, and `introduction`), every node,
   every edge, all 50 representative tasks, and the overall decision pass
   conditional validation.
5. Use de-identified reviewer IDs such as `R1` and `R2`; do not enter names.

## Comparison and confirmation

1. Open `review_pages/compare_and_confirm.html`.
2. Import two `status=complete` review JSON files for the same graph.
3. The page checks schema, completeness, reviewer IDs, graph fingerprint, and
   exact item sets.
4. It computes raw agreement and Cohen's kappa for node and edge decisions and
   identifies controlled-field disagreements.
5. Resolve every disagreement, defect, edit, deletion, or inadequate-coverage
   trigger.
6. Export `knowact.kg_review_confirmation.v3` JSON.

`promotion_readiness.status` can be `not_approved`, `edits_required`, or
`ready_for_structural_validation`. Even the last status keeps
`promotion_ready=false`: repository structural validation and explicit
benchmark-author promotion remain separate steps.

## Rebuild and verify

From the repository root:

```bash
python3 experiments/01_kg_scientific_validity/tools/build_review_pages.py
python3 experiments/01_kg_scientific_validity/tools/build_review_pages.py --check
```

The three run bindings are explicit constants in the builder. A new candidate
run cannot silently replace an input under active review; changing an input
requires an intentional binding update, regenerated pages, and new hash checks.

Completed review JSON contains the reviewer's role, experience band, and short
introduction. Keep identifiable originals outside Git and archive only
de-identified copies when the release plan permits.
