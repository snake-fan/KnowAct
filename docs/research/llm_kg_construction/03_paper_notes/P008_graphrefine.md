# P008 — [GraphRefine](https://aclanthology.org/2026.acl-long.1353/)

**Kim et al., ACL 2026.**

## Problem

Generated triples exhibit both factual and representational inconsistencies that deletion-only filters cannot repair well.

## Method

GraphRefine derives an error taxonomy from human evaluation and selects triple-level delete, edit, or rewrite operations.

## Evidence

Experiments across generative extractors show broader quality gains than deletion-only refinement.

## Limitation

The unit is still a factual triple, not a diagnostic concept, rubric, or graph-level pedagogical constraint.

## KnowAct transfer

Adopt `KEEP`, `FIX`, `REWRITE`, `DELETE`, and `QUARANTINE`. Require another verifier or human to approve rewritten evidence-sensitive content.

