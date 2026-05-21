# V1 splits node extraction from rubric authoring

KnowAct v1 graph authoring does not ask the node extraction step to produce complete `Knowledge Node` objects in one pass. The node extraction step reads authoritative source material and produces source-grounded node skeletons with identity fields and source locators. A later node rubric authoring step completes `diagnostic_goal`, L0-L5 `levels`, diagnostic signals, and `simulator_behavior`. In v1, rubric authoring uses only the node skeleton, authoritative source/source locator, and global `MasteryScale`, not unreviewed neighboring nodes or candidate edges.

**Considered Options**

- Have the extraction step generate complete nodes, including rubrics, in one pass.
- Split source-grounded node identity extraction from diagnostic rubric authoring.

**Consequences**

Source grounding and diagnostic design can be reviewed separately, while remaining inside the same graph authoring workflow. The final `candidate_nodes.json` still contains complete `Knowledge Node` objects; the skeleton list is an intermediate workflow artifact, not the final graph-authoring answer.
