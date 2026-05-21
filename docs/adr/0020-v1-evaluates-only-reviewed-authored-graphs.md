# V1 evaluates only reviewed authored graphs

KnowAct v1 may use LLM workflows to produce candidate knowledge graphs during authoring, but evaluation episodes run only on benchmark-author reviewed authored knowledge graphs. This keeps graph quality issues separate from the tested agent's active diagnosis task.

**Considered Options**

- Use LLM-generated graphs directly in evaluation.
- Treat LLM-generated graphs as candidates that require review before evaluation.

**Consequences**

V1 benchmark construction needs an authoring review step, but evaluation results are less likely to be confounded by unvalidated graph structure.
