# V1 graph authoring has extraction, rubric, and edge steps

KnowAct v1 uses one graph authoring agent workflow with separate node extraction, node rubric authoring, and edge proposal steps. The node extraction step reads authoritative source material, extracts source-grounded node skeletons, and produces source locators. The node rubric authoring step completes diagnostic goals, L0-L5 rubrics, diagnostic signals, and simulator behavior. The edge step proposes candidate edges after complete candidate nodes and their rubrics are available. The steps are intermediate responsibilities inside one workflow whose final review output is a node JSON list and an edge JSON list.

**Considered Options**

- Build two independent workflows for node extraction and edge proposal.
- Make the extraction step produce complete nodes in one pass.
- Use one graph authoring workflow with distinct extraction, rubric, and edge proposal steps.

**Consequences**

Node identity extraction, diagnostic rubric authoring, and edge generation remain separate responsibilities, but they stay part of one graph-authoring task. Edge proposal may use the completed node rubrics, while rubric authoring does not use unreviewed candidate edges. Edge proposal is precision-first: unclear, weakly related, or speculative relations are omitted from the final edge list. The final graph-authoring answer is two JSON list files rather than a separate workflow per responsibility.
