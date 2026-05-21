# V1 uses squared mastery distance

KnowAct v1 maps L0-L5 mastery levels to numeric scores 0-5 and computes mastery level distance as the squared difference between predicted and ground-truth scores. This keeps scoring simple while penalizing distant mastery mistakes more strongly than near misses.

**Considered Options**

- Use linear absolute distance between L0-L5 scores.
- Use a custom continuous embedding or penalty matrix.
- Use squared distance over the simple 0-5 mastery score mapping.

**Consequences**

V1 scoring remains easy to implement and explain, but large overestimates or underestimates of user mastery have disproportionately higher cost.
