# V1 profile context guides generation, not scoring

KnowAct v1 may use persona, background, preferences, and task goals as profile context when generating candidate knowledge maps and simulator behavior. This context must remain consistent with the ground-truth knowledge map, but it is not part of the primary episode mastery distance score.

**Considered Options**

- Include persona and preferences in the primary reconstruction score.
- Use profile context to constrain map generation and simulation, while scoring only structured knowledge-map state.

**Consequences**

V1 avoids freeform profile-similarity scoring while still allowing simulated users to be coherent and realistic.
