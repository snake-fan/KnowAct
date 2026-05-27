# V1 graph authoring uses intermediate artifacts after extraction

KnowAct v1 keeps full `Parsed Source Markdown` as the LLM input for the `Node Extraction Agent Step`, but later graph-authoring steps consume `Graph Authoring Intermediate Artifacts` from earlier workflow steps instead of re-reading the full source markdown. This amends ADR-0033 and ADR-0035: node rubric authoring uses source-grounded skeletons, source locators, extraction-produced definitions or notes, and the global `MasteryScale`; edge proposal uses complete candidate nodes, rubrics, source locators, and workflow-produced intermediate information. The decision reduces context load and makes the workflow more replayable, at the cost of requiring extraction and intermediate artifacts to carry enough source-grounded information for downstream steps.

**Considered Options**

- Pass full `Parsed Source Markdown` into every graph-authoring step.
- Let only node extraction read full `Parsed Source Markdown`, then pass structured workflow intermediate artifacts forward.

**Consequences**

`Node Extraction Agent Step` becomes the source-reading boundary for the graph-authoring workflow. Later steps should be prompt-shaped around persisted structured inputs, not around full source text. Run directories should preserve intermediate artifacts and log their artifact URIs so failed runs can be inspected and resumed without treating `workflow_log.json` as the data source. The final review output remains exactly `candidate_nodes.json` and `candidate_edges.json`.
