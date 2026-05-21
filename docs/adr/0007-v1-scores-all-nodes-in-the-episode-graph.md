# V1 scores all nodes in the episode graph

KnowAct v1 uses the authored knowledge graph for an evaluation episode as the scoring scope. Every knowledge node in that episode graph participates in structured map comparison, so v1 does not introduce a separate scored-node set. The ground-truth knowledge map must cover every node in the episode graph; missing reconstructed states are scored as missing predictions.

**Considered Options**

- Add an explicit scored-node subset for each episode.
- Treat all nodes in the episode knowledge graph as scored nodes.

**Consequences**

V1 episode configuration stays simpler, but benchmark authors must keep each episode graph sized and scoped so that scoring all of its nodes is meaningful.
