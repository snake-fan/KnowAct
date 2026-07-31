# Field Research Map

## Central question

How should an LLM agent actively recover a hidden graph-indexed user knowledge state from a small
number of open-ended interactions, and what evidence is sufficient to attribute any gain to the agent
design?

## Evidence chain

```text
knowledge tracing
  supplies sequential state update
adaptive testing
  supplies budgeted target selection
dynamic profiling and tutoring
  supply explicit dialogue state and assessment memory
interactive benchmarks
  supply simulator, reliability, and trajectory controls
KnowAct
  combines these under a public graph / hidden map boundary
```

## Intended contribution boundary

The literature supports building and testing this composition. It does not yet prove that typed graph
propagation, LLM-estimated information gain, verifier decomposition, or early stopping improve
reconstruction. Those are the paper's central hypotheses.
