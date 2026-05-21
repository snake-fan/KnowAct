# V1 rubric authoring avoids unreviewed graph context

KnowAct v1 node rubric authoring uses a narrow input scope: the source-grounded node skeleton, the relevant authoritative source/source locator, and the global `MasteryScale`. It must not use unreviewed neighboring nodes, candidate edges, or graph traversal context as rubric-generation input.

**Considered Options**

- Let rubric authoring use candidate graph context, including neighboring nodes and proposed edges.
- Keep rubric authoring grounded only in the node skeleton, source material, and global mastery scale.

**Consequences**

Node rubrics remain grounded in the source and global diagnostic scale instead of being shaped by unreviewed graph relations. If the authoritative source itself explains a concept through contrasts or dependencies, the rubric may reflect that source-grounded context, but candidate edges do not become evidence for node diagnostic standards.
