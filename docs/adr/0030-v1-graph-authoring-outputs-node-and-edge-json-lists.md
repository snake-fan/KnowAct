# V1 graph authoring outputs node and edge JSON lists

KnowAct v1 graph authoring workflow produces exactly two final review outputs: a JSON list of `Knowledge Node` objects and a JSON list of `Knowledge Edge` objects. File names may include candidate status, for example `candidate_nodes.json` and `candidate_edges.json`, but the JSON objects themselves must not include `candidate`, `candidate_status`, `review_status`, or similar fields. The edge list uses the normal `Knowledge Edge` schema: `id`, `source`, `target`, `type`, `rationale`, `weight`, and `curation_confidence`.

**Considered Options**

- Produce one combined review artifact containing nodes, edges, validation notes, rationales, and review metadata.
- Produce two plain JSON list files using the normal node and edge schemas.
- Reuse the node rubric schema for edge objects.

**Consequences**

The authoring output stays close to the eventual graph data model and is easier to inspect, diff, and promote into an authored graph. Validation notes and intermediate checks can exist as workflow logs, but they are not part of the final graph-authoring answer contract. Edge objects describe relationships between nodes and do not duplicate node-level fields such as `definition`, `diagnostic_goal`, `levels`, or source locators.
