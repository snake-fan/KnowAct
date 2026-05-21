# V1 edge proposal prioritizes precision

KnowAct v1 edge proposal should prioritize precision over recall. `candidate_edges.json` should include only candidate `Knowledge Edge` objects with a clear canonical edge type and a clear rationale. Weakly related, speculative, or merely associated node pairs should be omitted from the final edge list. V1 does not use a fixed `curation_confidence` threshold as the inclusion rule.

**Considered Options**

- Recall-first edge proposal that surfaces many possible relationships for review.
- Precision-first edge proposal that only emits clearer canonical relationships.
- Apply a fixed `curation_confidence` cutoff to candidate edge inclusion.

**Consequences**

Benchmark-author review stays focused on meaningful graph structure instead of triaging a large pool of vague relatedness. Some valid but subtle edges may be missed in v1, but the resulting candidate graph is less likely to be polluted by generic `supports` edges or unclear relationships. `curation_confidence` remains useful for review and calibration, but thresholds should wait until a few real candidate graphs reveal the score distribution.
