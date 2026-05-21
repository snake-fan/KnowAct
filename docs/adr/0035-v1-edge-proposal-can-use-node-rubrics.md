# V1 edge proposal can use node rubrics

KnowAct v1 edge proposal runs after candidate nodes have complete diagnostic rubrics. The edge proposal step may use the full `candidate_nodes.json`, including `diagnostic_goal`, L0-L5 `levels`, diagnostic signals, `simulator_behavior`, source locators, and relevant source material, to propose candidate `Knowledge Edge` objects. It should propose edges precision-first: only clear canonical edges with clear rationales enter `candidate_edges.json`.

**Considered Options**

- Restrict edge proposal to node skeletons and source locators only.
- Allow edge proposal to use complete candidate node rubrics.

**Consequences**

The graph authoring dependency direction stays one-way: node rubrics are authored without candidate graph context, then edge proposal may use those rubrics to judge cognitive dependencies, support, composition, and contrasts. Proposed edges remain candidate data and still require benchmark-author review before becoming authored graph data. Weak, speculative, or merely related node pairs are omitted rather than preserved in the final edge list.
