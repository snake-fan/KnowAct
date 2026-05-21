# V1 graph authoring uses an agent workflow

KnowAct v1 will implement graph authoring through one project-owned agent workflow that calls model APIs over authoritative source material. One agent step reads the authoritative PDF or source material directly, extracts source-grounded node skeletons, and produces source locators; a later node rubric step completes diagnostic goals, L0-L5 rubrics, diagnostic signals, and simulator behavior; another step uses complete candidate nodes, including rubrics, to propose candidate edges for benchmark-author review. The workflow's final review output is two JSON list files, one for nodes and one for edges. This workflow replaces a manually brainstormed inventory but does not directly produce an accepted authored graph.

**Considered Options**

- Manually write the first candidate node inventory.
- Use one project-owned graph authoring agent workflow to generate node and edge JSON list files from source material.

**Consequences**

The next implementation work focuses on the graph authoring workflow infrastructure, including node skeleton extraction, source locator extraction, node rubric authoring, and edge proposal, but the human review gate remains required before any candidate output becomes an authored graph.
