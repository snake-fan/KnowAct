# P006 — [KARMA](https://proceedings.neurips.cc/paper_files/paper/2025/hash/517f9b9c227b9dd51dba4560f37165ed-Abstract-Conference.html)

**Lu et al., NeurIPS 2025.**

## Problem

Scientific KG construction across many documents requires extraction, integration, conflict resolution, and provenance.

## Method

KARMA coordinates nine specialized agents across the construction lifecycle.

## Evidence

The paper reports large-scale PubMed construction, LLM-assisted correctness estimates, and fewer conflicts.

## Limitation

The evaluation relies partly on LLM verification, and the study does not establish that nine agents outperform a simpler workflow holding all checks and budgets fixed.

## KnowAct transfer

Borrow bounded role specialization and conflict handling. Treat role count as an implementation choice, not a scientific contribution.

