# P003 — [PiVe](https://aclanthology.org/2024.findings-acl.400/)

**Han et al., Findings of ACL 2024.**

## Problem

LLMs frequently produce incomplete or invalid graph structures.

## Method

A trained smaller verifier diagnoses errors and sends fine-grained corrective instructions to the generator over iterative rounds.

## Evidence

PiVe reports consistent improvement on three graph-generation datasets and studies an offline correction option.

## Limitation

Its verifier is especially oriented toward omitted graph content; KnowAct also needs grounding, granularity, merge, direction, and rubric errors.

## KnowAct transfer

Use an independent verifier with an explicit error taxonomy and a maximum retry budget. Always return semantic errors with the original evidence span.

