# P002 — [SPIRES: Structured Prompt Interrogation and Recursive Extraction of Semantics](https://doi.org/10.1093/bioinformatics/btae104)

**Bioinformatics, 2024.**

## Problem

Free-form LLM output is difficult to validate and align with domain ontologies.

## Method

SPIRES/OntoGPT uses LinkML schemas to drive recursive extraction and grounds terms against ontologies.

## Evidence

The system demonstrates schema-conformant extraction in biomedical use cases and exposes a reusable typed workflow.

## Limitation

It assumes useful schemas and ontologies and does not solve educational construct validity.

## KnowAct transfer

Treat every stage output as a machine-valid contract. Separate schema validation from semantic/source validation; passing Pydantic is necessary but not sufficient.

