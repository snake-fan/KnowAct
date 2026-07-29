# P009 — [GenIE](https://aclanthology.org/2022.naacl-main.342/)

**Josifoski et al., NAACL 2022.**

## Problem

Autoregressive extraction can emit entities and relations outside a target KG schema.

## Method

GenIE constrains generation with entity and relation tries, producing valid closed-schema triples end to end.

## Evidence

The paper evaluates closed information extraction and demonstrates competitive extraction with constrained decoding.

## Limitation

A fixed entity/relation inventory is unsuitable for initial concept discovery and does not test source evidence or rubric validity.

## KnowAct transfer

Use hard constraints after candidate discovery: legal relation labels, endpoints, identifier format, provenance classes, and required fields.

