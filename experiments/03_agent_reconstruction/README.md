# Experiment 03: Agent Reconstruction

[中文](README.zh-CN.md)

## Purpose

This experiment measures how accurately a tested agent reconstructs a hidden
user Knowledge Map through bounded diagnostic dialogue over a visible reviewed
Knowledge Graph.

## Status

| Component | Status |
| --- | --- |
| Design | Prepared |
| Current agent implementations | Simple LLM and experimental ECDA available |
| Formal question-bank baselines | Deferred until immutable bank binding exists |
| Experiment manifests | Not frozen |
| Runs | Not run |
| Results | None |

## Contents

- [`design/experimental_design.md`](design/experimental_design.md): hypotheses,
  paired comparison, metrics, sample-size procedure, analysis, and acceptance
  gates.
- [`materials/README.md`](materials/README.md): artifacts that must be frozen
  before code execution.
- [`results/README.md`](results/README.md): generated artifact layout and result
  status.
- `runtime/`: ignored queue-control state used by the Episode Run Queue.

This package points to the detailed method evidence under
[`../../docs/research/tested_agent_knowledge_map_reconstruction/`](../../docs/research/tested_agent_knowledge_map_reconstruction/README.md).
