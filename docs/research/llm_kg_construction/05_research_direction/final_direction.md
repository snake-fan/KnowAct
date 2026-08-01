# Final Direction

For the canonical implementation-aligned method description, see [Final Method: KnowAct Knowledge Graph Generation](./final_kg_generation_method.md) and its [Chinese version](./final_kg_generation_method.zh-CN.md).

This file records the proposed EDGA research direction. It does not describe the current production workflow as an empirically validated EDGA implementation.

## Recommended framing

Use the descriptive name **Evidence-Grounded Diagnostic Graph Authoring (EDGA)**. The contribution is a reliable adaptation and evaluation protocol, not a claim that a novel multi-agent topology solves KG construction.

## Core claim

For a fixed source corpus and diagnostic graph specification, EDGA creates a reviewable candidate graph by combining high-recall local extraction, independent source verification, explicit canonicalization, ECD-grounded rubric design, type-specific edge checks, graph constraints, and expert adjudication.

## Claims that are currently supportable

- Existing KGC work motivates decomposition, schema control, verification, resolution, and repair.
- Educational and assessment theory motivates competency questions, diagnostic node criteria, and separate validation of rubrics.
- KnowAct requires a hybrid authoring method because its graph mixes source-grounded domain structure with expert-designed measurement artifacts.

## Claims that require experiments

- EDGA is better than the current workflow or any external baseline.
- Independent verification improves the precision--recall tradeoff in this domain.
- Risk-ranked review reduces expert time.
- Graph quality changes downstream agent rankings.

## Minimum publishable evidence

1. A locked, independently authored reference subset.
2. One-shot, simple staged, unverified, and EDGA baselines with matched budgets.
3. Node, edge, canonicalization, rubric, provenance, reliability, cost, and review-effort metrics.
4. At least two independent domain experts and one adjudicator.
5. Complete source-to-promotion traces for every reported graph.
