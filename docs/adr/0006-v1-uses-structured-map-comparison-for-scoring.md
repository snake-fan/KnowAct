# V1 uses structured map comparison for scoring

KnowAct v1 scores the tested agent by automatically comparing quantifiable user-state fields in the reconstructed knowledge map against the ground-truth knowledge map, especially mastery level. It does not introduce a separate evaluator agent or LLM judge for primary scoring, because v1 should measure evidence-backed diagnosis rather than add another subjective interpretation layer.

**Considered Options**

- Use an evaluator agent or LLM judge to rate the reconstructed profile.
- Use structured map comparison over mastery levels, misconceptions, and evidence support.

**Consequences**

V1 scoring is simpler and more reproducible, but it only evaluates fields that can be represented in the structured maps.
