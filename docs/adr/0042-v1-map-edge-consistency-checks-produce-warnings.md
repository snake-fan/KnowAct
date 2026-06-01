# V1 map edge-consistency checks produce warnings

KnowAct v1 uses reviewed `Knowledge Edges` as soft diagnostic signals when reviewing a `Candidate Knowledge Map`, not as hard mastery-level monotonicity constraints. Edge-aware consistency checks should surface review warnings for suspicious state combinations without automatically rewriting or rejecting them, because realistic users may have uneven, memorized, or task-specific understanding.

**Considered Options**

- Reject or automatically rewrite candidate maps when node-level mastery values do not follow reviewed graph edges.
- Surface edge-aware consistency warnings for benchmark-author review while allowing explicitly reviewed uneven maps.

**Consequences**

Candidate-map generation exposes lightweight review hints, but reviewed-map promotion does not read, validate, recompute, or copy them. V1 maps can represent diagnostically useful knowledge gaps instead of forcing artificially smooth user profiles.
