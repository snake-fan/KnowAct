# V1 does not threshold candidate edges by confidence

KnowAct v1 does not set a fixed `curation_confidence` cutoff for whether a candidate `Knowledge Edge` enters `candidate_edges.json`. Candidate edge inclusion is controlled by precision-first rationale quality: the edge must have a clear canonical type and a clear rationale. `curation_confidence` remains required, but it is used as a review and calibration signal rather than a hard inclusion threshold. In candidate files, the graph authoring workflow may provide an initial suggested value; after review, the same field carries the benchmark author's accepted or revised value.

**Considered Options**

- Require candidate edges to meet a fixed `curation_confidence` threshold.
- Use precision-first rationale quality without a numeric threshold in v1.

**Consequences**

V1 avoids inventing an arbitrary confidence cutoff before seeing real generated graphs. Reviewers still receive confidence values, and a threshold can be introduced later after the project observes how candidate edge confidence is distributed across actual authoring runs.
