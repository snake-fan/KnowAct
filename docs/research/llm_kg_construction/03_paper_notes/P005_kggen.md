# P005 — [KGGen](https://proceedings.neurips.cc/paper_files/paper/2025/hash/2b368455e832d2b1a60bcad8c4c6481f-Abstract-Conference.html)

**Mo et al., NeurIPS 2025.**

## Problem

Text extractors create sparse graphs when aliases and related forms remain separate.

## Method

KGGen separates entity and relation extraction, then iteratively clusters and deduplicates entities and relations. It introduces the MINE benchmark for useful information retention.

## Evidence

The paper compares with leading graph generators and reports competitive retrieval accuracy with more concise and generalizable graphs.

## Limitation

Entity concision is not identical to diagnostic construct granularity; over-clustering can erase skills that should be assessed separately.

## KnowAct transfer

Use lexical/embedding similarity for candidate retrieval only. Require explicit merge, alias, keep, or split adjudication with all evidence preserved.

