# V1 scores the final reconstructed map

KnowAct v1 requires the tested agent to submit a final reconstructed knowledge map after the evaluation episode ends. Per-turn reconstruction snapshots, uncertainty notes, and question-selection rationales may be recorded as optional traces, but the primary score uses only the final map.

**Considered Options**

- Require reconstructed map output after every turn.
- Require only a final reconstructed map and make per-turn traces optional.

**Consequences**

V1 keeps baseline implementation simple while still leaving room for richer diagnostic traces in experiments that want them.
