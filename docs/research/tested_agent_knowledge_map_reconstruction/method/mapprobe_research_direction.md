# Final Research Direction

This is the full MapProbe research direction. The current ECDA implementation covers a narrower
belief-update and multi-candidate selection slice; see [`README.md`](README.md) for the component map.

Build and evaluate an auditable knowledge-map reconstruction agent whose explicit control loop is:

1. interpret visible answers against node mastery rubrics;
2. revise ordinal node beliefs while retaining evidence provenance;
3. apply bounded, typed graph messages without deterministic mastery copying;
4. score diagnostic targets before generating question language;
5. verify plan–question alignment; and
6. stop or abstain based on marginal value and coverage.

The paper contribution should be framed as a benchmark–agent co-design: KnowAct supplies a hidden
structured user state and a strict visibility/scoring contract; the agent supplies a falsifiable policy
for acquiring evidence and reconstructing that state.

Detailed method and experiment requirements are fixed in
[`paper/RECONSTRUCTION_AGENT_DESIGN.md`](../../../../paper/RECONSTRUCTION_AGENT_DESIGN.md).
