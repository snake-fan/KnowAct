# V1 uses an explicit turn budget

KnowAct v1 configures the maximum number of interaction turns explicitly for each evaluation episode. The turn budget is not derived from the number of knowledge nodes in the episode graph, because graph granularity and interaction budget are separate design choices.

**Considered Options**

- Derive `max_turns` from the number of nodes in the episode graph.
- Configure `max_turns` explicitly per episode.

**Consequences**

Benchmark authors can control episode difficulty directly, but episode configs must document their chosen turn budget.
