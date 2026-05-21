# V1 turns contain one diagnostic question

KnowAct v1 defines one interaction turn as one tested-agent diagnostic question followed by one user simulator answer. Compound batches of multiple independent questions are disallowed so the explicit turn budget remains comparable across agents.

**Considered Options**

- Allow each turn to contain multiple diagnostic questions.
- Restrict each turn to one primary diagnostic question.

**Consequences**

Turn counts become meaningful as diagnostic opportunities, but agents must prioritize what to ask rather than packing many probes into one response.
