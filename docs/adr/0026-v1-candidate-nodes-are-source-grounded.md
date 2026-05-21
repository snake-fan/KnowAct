# V1 candidate nodes are source-grounded

KnowAct v1 requires candidate knowledge nodes to be extracted from selected authoritative sources and to carry source locators. Candidate node inventories should not be brainstormed from common sense or model memory, because source grounding is what makes graph authoring auditable. Source locators are simple audit references, not mandatory quote spans.

**Considered Options**

- Draft a plausible node inventory first and attach sources later.
- Select authoritative sources first, then extract source-grounded candidate nodes.

**Consequences**

V1 graph authoring becomes slower, but every node can be traced back to source material before it is reviewed into the authored graph. The locator can stay lightweight as long as it points reviewers back to the relevant source location.
