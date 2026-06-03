# V1 reviewed maps are structured and evidence-backed

KnowAct v1 represents the ground-truth user state as graph-bound structured data over the authored knowledge graph, not as a freeform user profile. Each user knowledge state should be backed by traceable evidence, which may be synthetic, so the user simulator has a constrained basis for answering and the evaluator has a clear reference for scoring.

**Considered Options**

- Generate freeform user profiles and ask the simulator to behave consistently with them.
- Generate structured reviewed maps with evidence-backed node-level user states.

**Consequences**

V1 benchmark data is more constrained and easier to score, but profile generation must include validation for node coverage, evidence quality, and edge-aware consistency.
