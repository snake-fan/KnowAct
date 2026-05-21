# V1 exposes the authored graph to the tested agent

KnowAct v1 gives the tested agent access to the authored knowledge graph, including node definitions, diagnostic rubrics, edge types, rationales, and relationship strengths, while hiding the ground-truth knowledge map. This keeps the benchmark focused on active user-state diagnosis rather than mixing diagnosis with domain graph discovery.

**Considered Options**

- Hide both the authored graph and the ground-truth knowledge map.
- Expose the authored graph while hiding the ground-truth knowledge map.

**Consequences**

V1 results should be interpreted as measuring how well an agent uses known domain structure to diagnose a user's knowledge state, not how well it constructs domain knowledge from scratch.
