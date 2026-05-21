# V1 candidate edge confidence is agent-suggested

In `candidate_edges.json`, `curation_confidence` may be an initial value suggested by the graph authoring workflow. After benchmark-author review, the same field in `authored_edges.json` represents the benchmark author's accepted or revised confidence value.

**Considered Options**

- Leave `curation_confidence` blank until human review.
- Use separate candidate and authored confidence fields.
- Use the same `curation_confidence` field, with candidate values treated as suggestions.

**Consequences**

Candidate and authored edge files keep the same schema, which makes validation, diffing, and promotion simpler. Reviewers should treat candidate confidence values as suggestions, not final author judgment.
