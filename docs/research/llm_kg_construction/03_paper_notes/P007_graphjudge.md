# P007 — [GraphJudge](https://aclanthology.org/2025.emnlp-main.554/)

**Huang et al., EMNLP 2025.**

## Problem

Noisy documents, domain knowledge, and hallucination reduce the precision of generated KGs.

## Method

GraphJudge first performs entity-centric denoising, then applies a fine-tuned LLM judge to generated triples.

## Evidence

The paper evaluates on two general and one domain-specific text--graph datasets and reports state-of-the-art results.

## Limitation

Binary filtering can trade away coverage, and a learned judge can inherit domain or generator biases.

## KnowAct transfer

Use a source-visible independent judge, but require error labels and typed repair rather than only keep/delete. Evaluate calibration and risk--coverage behavior.

