# P004 — [SAC-KG](https://aclanthology.org/2024.acl-long.238/)

**Chen et al., ACL 2024.**

## Problem

Domain KG construction needs high precision at scales where manual authoring is impractical.

## Method

SAC-KG iteratively expands entities using Generator, Verifier, and Pruner components.

## Evidence

The paper reports a graph above one million nodes and 89.32% precision, with human evaluation used on sampled output.

## Limitation

Recall is hard to quantify at that scale, and generic domain expansion differs from a bounded textbook concept inventory.

## KnowAct transfer

Reuse proposer--verifier separation and precision-first promotion. Add an independent coverage pass and a quarantine state so pruning does not hide recall loss.

