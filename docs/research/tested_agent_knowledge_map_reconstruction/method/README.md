# MapProbe and ECDA

MapProbe and ECDA address the same tested-agent task, but they name different method scopes.

| Component | Full MapProbe paper design | Current ECDA implementation |
| --- | --- | --- |
| Belief state | L0-L5 distribution plus direct, indirect, and contradiction ledgers | Checkpointed independent L0-L5 marginal per node |
| Evidence interpretation | Rubric-boundary observation with typed provenance and verification | Model-proposed per-level answer likelihood, observed-behavior note, contradiction flag, and visible turn references |
| Graph use | Relation-specific, attenuated belief messages with direct/indirect separation | Connected-target validation and a model-estimated graph-leverage term in question utility; no belief propagation |
| Probe policy | Score a target plan before question realization, then verify alignment | Generate at least three complete question candidates, validate them, and select deterministically by inspectable utility |
| Stopping | Frozen marginal-value and coverage rule | Forced finalization or model-requested finalization; calibrated early stopping is disabled |

ECDA is therefore an implemented experimental slice of the broader MapProbe hypothesis, not a second
Knowledge-Map reconstruction problem and not a validated replacement for the Simple LLM baseline.

## Sources of truth

- [`../04_agent_design.md`](../04_agent_design.md): executable ECDA design.
- [`../06_implementation_contract.md`](../06_implementation_contract.md): code and failure contract.
- [`../../../../paper/RECONSTRUCTION_AGENT_DESIGN.md`](../../../../paper/RECONSTRUCTION_AGENT_DESIGN.md):
  full MapProbe paper-method contract.
- [`mapprobe_research_direction.md`](mapprobe_research_direction.md): concise paper research direction.
- [`mapprobe_research_questions.md`](mapprobe_research_questions.md): questions fixed before results.

Implementation status must be reported component by component. “Implemented” does not mean
empirically beneficial, calibrated, or validated on human interaction.
