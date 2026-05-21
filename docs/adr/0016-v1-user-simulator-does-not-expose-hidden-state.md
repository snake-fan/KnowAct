# V1 user simulator does not expose hidden state

KnowAct v1 conditions the user simulator on the hidden ground-truth knowledge map and simulator-only evidence, but the simulator must answer diagnostic questions naturally rather than exposing mastery labels, hidden evidence ids, or the full state table. This keeps the tested agent's task as inference from interaction instead of querying a benchmark oracle.

**Considered Options**

- Let the simulator return structured state when asked directly.
- Require the simulator to answer as a user while hiding benchmark labels and reference data.

**Consequences**

The tested agent must infer user knowledge state from conversational evidence, but simulator prompts need explicit leakage guards.
