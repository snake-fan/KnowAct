# V1 focuses on active knowledge-state diagnosis

KnowAct v1 treats each evaluation run as an active diagnosis task: the tested agent asks diagnostic questions to infer a fixed ground-truth knowledge map over an authored knowledge graph. This deliberately excludes teaching and tutoring actions during the episode, because allowing the simulator's knowledge state to change would mix profile reconstruction with learning effects and make scoring less interpretable.

**Considered Options**

- Allow diagnosis, explanation, teaching, and recommendation in the same interaction.
- Restrict v1 to diagnostic questions while keeping the user's ground-truth knowledge state fixed.

**Consequences**

V1 can measure whether ToM-like user modeling improves question selection and reconstruction accuracy, but it does not yet evaluate whether an agent teaches better after modeling the user.
