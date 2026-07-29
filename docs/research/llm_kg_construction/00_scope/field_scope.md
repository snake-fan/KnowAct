# Field Scope: Reliable LLM-Assisted KG Authoring for KnowAct

## Motivation

KnowAct needs a domain graph whose nodes are stable, diagnosable concepts and whose edges support knowledge-state diagnosis. This is narrower than open information extraction and broader than extracting literal textbook triples.

The study asks how LLMs can reduce authoring effort without weakening source fidelity, pedagogical validity, or reproducibility.

## Included

- LLM-based text-to-KG extraction, schema induction, canonicalization, verification, and repair.
- Long-document and domain-KG workflows with explicit provenance.
- Educational concept and prerequisite graph construction.
- Ontology-engineering and assessment-design foundations needed to define the target artifact.
- Human-in-the-loop validation and operational failure recovery.

## Excluded

- KG embedding, link prediction, and question answering unless used inside construction.
- Pure entity linking over an already fixed graph.
- Autonomous-agent complexity that is not tied to a measurable construction benefit.
- Evaluation based only on an LLM judge.

## Unit of Analysis

The output is not a bag of triples. It is a versioned graph package containing nodes, typed edges, source evidence, diagnostic rubrics, provenance class, confidence, workflow traces, and human decisions.

## Time and Source Boundary

The focused pool covers foundational work and primary papers available through July 2026. The pool is intentionally small: it supports a defensible workflow rather than a claim of exhaustive surveying.

## Quality Criteria

1. Source support and precise provenance.
2. Node coverage without semantic duplication or unstable granularity.
3. Correct relation type and direction.
4. Diagnostic usefulness and rubric validity.
5. Calibrated abstention and low silent-corruption risk.
6. Reproducibility, resumability, and bounded cost.

