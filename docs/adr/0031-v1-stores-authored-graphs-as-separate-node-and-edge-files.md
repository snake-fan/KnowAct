# V1 stores authored graphs as separate node and edge files

After benchmark-author review, KnowAct v1 stores an authored knowledge graph as separate JSON list files for nodes and edges, typically `authored_nodes.json` and `authored_edges.json`. A lightweight `graph_manifest.json` may exist to bind graph id, version, source metadata, and file paths, but it must not inline or replace the node and edge lists. V1 does not prescribe repository or dataset directory layout yet; the benchmark author will specify that later.

**Considered Options**

- Merge reviewed nodes and edges into one combined graph JSON file.
- Store reviewed nodes and edges as separate JSON list files.
- Require a manifest as the only graph entry point.
- Prescribe a domain/version directory layout now.

**Consequences**

Node and edge schemas remain independently inspectable and easy to diff from their candidate versions. A manifest can still provide stable graph metadata for runners or datasets, but graph content remains in the separate authored node and edge files. Implementations should avoid hardcoding graph directory paths until a graph file layout is explicitly defined.
