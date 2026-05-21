# V1 uses evaluation episode manifests

KnowAct v1 declares each evaluation episode with an explicit manifest that binds the authored knowledge graph, hidden ground-truth knowledge map, optional profile context, turn budget, interaction rules, and scoring profile. This keeps runner configuration reproducible and prevents graph, map, simulator, and scoring settings from drifting apart.

**Considered Options**

- Pass graph, map, budget, and scoring settings as loose runner arguments.
- Use an evaluation episode manifest as the unit of benchmark configuration.

**Consequences**

V1 episodes are easier to validate and reproduce, but benchmark authors need to maintain manifest files alongside graph and map data.
