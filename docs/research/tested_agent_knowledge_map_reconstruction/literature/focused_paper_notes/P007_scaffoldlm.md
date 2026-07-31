# P007 — [ScaffoldLM](https://aclanthology.org/2026.acl-long.325/)

**Li et al., ACL 2026. Reading depth: D2.**

## Contribution

Maintains a stepwise tutoring plan, progress, inferred learner state, and dialogue history in an
assessment-driven memory that selects subsequent tutoring actions. The paper separately ablates the
plan and assessment components.

## KnowAct transfer

Use an explicit, persistent plan–state–action memory rather than regenerating the entire latent state
from an unstructured transcript each turn.

## Do not transfer

Scaffolding quality is not reconstruction accuracy. Training is primarily synthetic, data construction
uses consistency and LLM checks, and several outcome dimensions depend on automated evaluation.
