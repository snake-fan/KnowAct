# V1 starts with one benchmark domain

KnowAct v1 starts with a single benchmark domain instead of a multi-domain suite: `classical_supervised_ml_algorithms`. This keeps the first benchmark slice focused on validating authoring, simulation, active diagnosis, final reconstruction, and scoring before introducing cross-domain difficulty calibration. The first graph targets 30-50 knowledge nodes, enough to distinguish different user knowledge structures while keeping deep learning, reinforcement learning, and unsupervised learning out of the first slice.

**Considered Options**

- Build multi-domain support from the start.
- Start with one well-scoped classical supervised ML algorithms domain and expand later.

**Consequences**

V1 results will not yet claim cross-domain generality, but the benchmark will be easier to build, inspect, and debug.
