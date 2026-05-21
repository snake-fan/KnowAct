# V1 uses a unified evidence record

KnowAct v1 represents ground-truth profile evidence and interaction observations with one shared evidence record structure, distinguished by evidence type, evidence kind, and visibility. This keeps simulator-only reference data and tested-agent-visible observations comparable without allowing their access boundaries, diagnostic forms, or lifecycle to blur.

**Considered Options**

- Create separate schemas for ground-truth evidence and interaction observations.
- Use one evidence record schema with explicit type, kind, and visibility fields.
- Leave the diagnostic form of evidence implicit inside freeform signal text.

**Consequences**

Evidence processing, validation, and scoring can share machinery, but every evidence record must be careful about visibility so hidden reference data is not leaked to the tested agent. Evidence kind remains orthogonal to evidence type: `prior_answer`, `worked_example`, `self_report`, `misconception_trace`, and `background_fact` describe the observable diagnostic form, not who can see the evidence or whether it came from profile authoring or interaction.
