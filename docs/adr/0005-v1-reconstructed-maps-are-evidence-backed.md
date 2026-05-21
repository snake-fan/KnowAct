# V1 reconstructed maps are evidence-backed

KnowAct v1 requires each user knowledge state in a reconstructed knowledge map to cite tested-agent-visible evidence. This makes profile reconstruction auditable and prevents an agent from receiving full credit for unsupported guesses that happen to match the hidden ground truth.

**Considered Options**

- Allow reconstructed states without evidence references and score only final mastery distance.
- Require reconstructed states to cite visible evidence records and score unsupported inference separately.

**Consequences**

The tested agent output format is stricter, but evaluation can distinguish accurate, evidence-grounded inference from lucky or leaked predictions.
