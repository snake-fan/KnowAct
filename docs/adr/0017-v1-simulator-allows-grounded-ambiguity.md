# V1 simulator allows grounded ambiguity

KnowAct v1 allows the user simulator to answer with natural ambiguity, including uncertainty, partial correctness, self-correction, not knowing, and misconceptions. That ambiguity must remain grounded in the hidden ground-truth knowledge map and simulator-only evidence, so it does not become random behavior or state drift.

**Considered Options**

- Require simulator answers to be clear, complete, and directly diagnostic every time.
- Allow natural ambiguity while constraining it by hidden map and evidence.

**Consequences**

The interaction becomes more realistic and challenging, but simulator prompts and validation need to prevent evasive or contradictory answers.
