# V1 evaluates only reviewed maps

KnowAct v1 may use LLM workflows to produce candidate knowledge maps during authoring, but evaluation episodes use only benchmark-author reviewed maps. This keeps simulator behavior and scoring references grounded in consistent, evidence-backed user states.

**Considered Options**

- Use LLM-generated knowledge maps directly as hidden references.
- Treat LLM-generated maps as candidates that require review before evaluation.

**Consequences**

V1 benchmark construction needs a map review step, but evaluation results are less likely to be confounded by inconsistent synthetic user states.
