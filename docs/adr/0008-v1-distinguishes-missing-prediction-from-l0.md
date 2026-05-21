# V1 distinguishes missing prediction from L0

KnowAct v1 treats a missing reconstructed state for a scored knowledge node as a missing prediction, not as L0 mastery. L0 is a real user knowledge state, while a missing prediction means the tested agent failed to provide a judgment for a node that belongs to the episode graph.

**Considered Options**

- Coerce missing reconstructed states to L0.
- Track missing predictions separately and apply the maximum distance penalty defined by the mastery distance function.

**Consequences**

V1 scoring can distinguish "the agent judged the user has no effective understanding" from "the agent did not make a prediction," but scoring reports need a separate missing prediction rate.
