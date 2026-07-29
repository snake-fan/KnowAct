# Problem Map

| Problem | Observable failure | Why it matters in KnowAct |
|---|---|---|
| Target underspecification | Attractive but inconsistent concept inventory | The benchmark score depends on what counts as a node. |
| Boundary loss | Concepts crossing segment boundaries are omitted | Zero-overlap chunks create systematic recall holes. |
| Hallucinated grounding | Definition or edge cannot be supported by the source | The hidden benchmark artifact becomes unauditable. |
| Granularity drift | Chapters, topics, equations, and skills are mixed | Mastery levels become incomparable and hard to diagnose. |
| Duplicate concepts | Synonyms survive as separate nodes | User state and scores are double counted. |
| Over-merging | Distinct skills collapse into one node | A single question cannot diagnose the mixed construct. |
| Relation confusion | Prerequisite, support, and part-of are conflated | Graph-aware policies receive misleading structure. |
| Rubric invention | L0--L5 claims are presented as textbook facts | Assessment design is confused with source extraction. |
| Self-verification | A generator accepts its own rationale | Correlated errors survive review. |
| Silent repair | Retries overwrite provenance or partially succeed | A reviewed graph cannot be reproduced. |
| Review bias | Experts only correct model candidates | Missing nodes are rarely recovered, inflating apparent recall. |

