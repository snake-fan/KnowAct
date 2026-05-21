# V1 uses mastery level distance as the primary map score

KnowAct v1 uses mastery level distance as the primary structured comparison signal between the ground-truth knowledge map and the reconstructed knowledge map. The distance is produced by an explicit mastery distance function. Exact mastery match is represented by zero distance and may receive an optional bonus, rather than being maintained as a separate primary metric.

**Considered Options**

- Use exact mastery match as the primary score and distance as an auxiliary metric.
- Use an explicit mastery distance function as the primary score, with zero distance as an optional exact mastery bonus.

**Consequences**

V1 scoring can distinguish near misses from large errors while staying fully structured and reproducible. The distance function must be documented so results remain comparable across runs.
