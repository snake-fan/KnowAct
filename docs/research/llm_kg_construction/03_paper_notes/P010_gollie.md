# P010 — [GoLLIE](https://openreview.net/forum?id=Y3wpuxd7u9)

**Sainz et al., ICLR 2024.**

## Problem

Information-extraction systems often fail to generalize to unseen schemas and nuanced label definitions.

## Method

GoLLIE conditions extraction on natural-language annotation guidelines and code-like schema descriptions.

## Evidence

The paper evaluates zero-shot generalization across many IE datasets and finds that detailed guidelines improve adherence.

## Limitation

Guideline following does not guarantee correct ontology scope, evidence, canonicalization, or graph-level coherence.

## KnowAct transfer

Write executable guidelines for every node and edge type, including positive examples, counterexamples, directionality, and boundary cases.

