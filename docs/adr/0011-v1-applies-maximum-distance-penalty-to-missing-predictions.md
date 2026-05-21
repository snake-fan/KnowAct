# V1 applies maximum distance penalty to missing predictions

KnowAct v1 assigns missing predictions a distance penalty of 36, which is larger than the maximum valid L0-L5 squared distance of 25. This prevents tested agents from lowering their average distance by omitting uncertain nodes, while still reporting missing prediction rate separately from unsupported inference.

**Considered Options**

- Exclude missing predictions from mean mastery distance.
- Coerce missing predictions to L0.
- Assign missing predictions a fixed distance penalty of 36.

**Consequences**

V1 scoring encourages complete reconstructed maps over the episode graph while keeping the missing prediction penalty simple and reproducible.
