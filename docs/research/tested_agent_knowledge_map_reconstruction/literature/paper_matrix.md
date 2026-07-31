# Paper-to-Design Matrix

`●` is a direct design anchor, `○` is a supporting constraint, and `—` means the paper should not be
used to justify that component.

| ID | State representation | Evidence update | Graph inference | Probe selection | Stop / abstain | Simulator validity | Process / reliability | Borrowed experiment pattern |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| P001 DKT | ● | ● | — | — | — | — | ○ | sequential prediction baseline |
| P002 pyKT | ○ | ● | — | — | — | — | ● | leakage audit; standardized splits |
| P003 BOBCAT | ○ | ○ | — | ● | — | — | ○ | fixed budgets; learned vs heuristic selection |
| P004 FACD | ● | ● | ○ | ○ | — | — | ○ | early-turn curves; component ablations |
| P005 LongTutor | ● | ● | — | ○ | — | ○ | ● | staged tasks; expert annotations; verifier analysis |
| P006 ParLD | ● | ● | — | — | — | — | ○ | turn-level diagnosis and downstream prediction |
| P007 ScaffoldLM | ● | ● | — | ○ | ○ | ○ | ○ | memory/control-loop ablations |
| P008 RAISE | ● | ○ | — | ● | ● | ○ | ○ | context-rich/free controls; cost-quality curve |
| P009 RLPA | ● | ● | — | ○ | — | ● | ○ | separate reconstruction and outcome rewards |
| P010 PERSONAMEM | ● | ● | — | — | — | ● | ○ | evolving-profile and long-context slices |
| P011 SimulatorArena | — | — | — | — | — | ● | ● | assistant-ranking agreement with humans |
| P012 τ-bench | — | — | — | ○ | — | ● | ● | deterministic final state; repeated-run pass^k |
| P013 AgentBoard | — | — | — | ○ | — | — | ● | progress curves and trajectory error analysis |
| P014 BigToM | — | ○ | — | — | — | ● | ○ | causal controls and alternative-explanation tests |

## Matrix conclusion

No selected paper provides the complete KnowAct method. The strongest synthesis is:

1. explicit sequential belief update from knowledge tracing and dynamic profiling;
2. target-before-language planning from adaptive testing and selective acquisition;
3. a persistent assessment memory and inspectable update–plan–act loop;
4. typed, attenuated graph evidence as a new component requiring its own ablation;
5. repeated-run, process-level, leakage-safe, and human-linked evaluation.

Graph-aware inference is the least directly supported column. It must be presented as a KnowAct
hypothesis and tested against no-graph, untyped-graph, and perturbed-graph controls.
