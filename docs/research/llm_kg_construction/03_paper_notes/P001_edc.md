# P001 — [Extract, Define, Canonicalize](https://aclanthology.org/2024.emnlp-main.548/)

**Zhang and Soh, EMNLP 2024.**

## Problem

Large or unavailable schemas make direct schema-conditioned triple extraction difficult.

## Method

EDC performs open extraction, defines relation semantics, and canonicalizes results afterward. EDC+R retrieves only schema elements relevant to an input.

## Evidence

The paper evaluates on three KGC benchmarks and reports stronger extraction with schemas larger than those practical to place fully in a prompt.

## Limitation

The target is entity--relation triples. Entity resolution, curricular granularity, and diagnostic validity remain different problems.

## KnowAct transfer

Use open local concept discovery followed by explicit canonicalization. Retrieve candidate schema elements for context efficiency, but freeze KnowAct's four edge meanings before final classification.

