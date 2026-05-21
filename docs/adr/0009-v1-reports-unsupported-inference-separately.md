# V1 reports unsupported inference separately

KnowAct v1 computes mastery-level distance even when a reconstructed user knowledge state lacks visible evidence, then reports that state as unsupported inference. This keeps the primary map-to-map comparison focused on structured mastery predictions while still exposing when an agent is making unsupported guesses.

**Considered Options**

- Treat unsupported reconstructed states as automatically incorrect.
- Score mastery-level distance normally and report unsupported inference separately.

**Consequences**

V1 can distinguish close but unsupported predictions from distant predictions, but reports need to include unsupported inference rate so evidence grounding remains visible.
