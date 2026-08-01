# Experiment 02: Simulator Personal Fidelity

[中文](README.zh-CN.md)

## Purpose

This experiment asks whether SAGE Simulator answers represent a participant
after that participant has personally confirmed their Profile Context and
Knowledge Map.

The current study collects participant self-evaluations only. Expert blind
rating will operate on saved answer pairs in a later, separate stage. Leakage
challenges, complex ablations, and agent-ranking transfer are not part of the
current participant flow.

## Automated flow

```text
enter, generate, revise, and confirm personal Profile Context
  -> generate, revise node by node, and confirm Knowledge Map
  -> sample 20 questions from an independent bilingual bank
  -> submit the human answer before generating the Simulator answer
  -> compare both answers and complete five self-rating items
  -> save a resumable private experiment session
  -> later export a separate expert-blind-rating package
```

The participant entry point is the independently deployable
[`simulator-test-frontend/`](../../simulator-test-frontend/README.md), not the
internal research workbench. Progress is saved after each question and an
incomplete session can be resumed with its session code.

## Status

| Component | Status |
| --- | --- |
| Simplified main protocol | Implemented |
| Automated frontend/backend workflow | Implemented |
| Independent bilingual bank | Economy, ISLP, and OSTEP each contain 80 atomic paired items with hash-bound roleplay reviews |
| Twenty-question sampling | Implemented with persisted seed and order |
| Five-item participant rating | Integrated; cognitive interviews and pilot pending |
| Expert blind rating | Deferred; not yet connected to the main flow |
| Human data and empirical results | Not collected |

## Contents

- [`design/experimental_design.md`](design/experimental_design.md): simplified
  Chinese main protocol.
- [`materials/README.md`](materials/README.md): question bank, participant
  materials, and legacy-material status.
- [`results/README.md`](results/README.md): private-session location, result
  status, and release boundary.

## Formal-collection gate

The implementation is suitable for integration testing and pilot work. Before
formal collection:

1. obtain ethics approval or an equivalent local review;
2. bind bank concepts to the current reviewed graph and obtain domain-expert
   review of content and Chinese-English equivalence; the current source and
   roleplay screening is author-side only;
3. conduct cognitive interviews and a pilot of Profile, Map, and rating UI;
4. freeze bank and graph versions, provider/model, sampling, and exclusion
   rules.

Until human data have been collected and analysed, the project may claim only
that the workflow is implemented—not that SAGE has human-validity support.
