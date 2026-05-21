# V1 source locators use simple source references

KnowAct v1 source locators only need to point reviewers to where a knowledge node is mentioned in an authoritative source. Chapter, section, pages, URL, lecture, slide, paragraph, or reference entry are sufficient when they let the benchmark author find the relevant material. V1 does not require `quote`, `evidence_span`, exact text offsets, or full excerpts in the node schema.

**Considered Options**

- Require exact quotes or evidence spans for every candidate node.
- Use simple structured source references that are enough for review.

**Consequences**

Graph authoring stays lighter and the node schema avoids becoming an excerpt store. Reviewers may still keep quotes or spans in workflow logs or review notes, but those details are not required fields on `Knowledge Node`.
