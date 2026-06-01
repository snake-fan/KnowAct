# V1 reviewed ground-truth map ids are never overwritten

KnowAct v1 never overwrites an existing reviewed `Ground-Truth Knowledge Map` identity and does not expose an `overwrite=true` promotion option. A replacement synthetic sample must be promoted under a new `map_id`, preserving the hidden truth referenced by existing evaluation episodes. Reviewed graph versions follow the same immutable-publication principle: corrections publish a new graph version.

**Considered Options**

- Allow explicit overwrite of an existing reviewed map id.
- Require a new map id for every newly promoted synthetic sample.

**Consequences**

Reviewed hidden maps remain reproducible and episode references cannot drift silently, at the cost of retaining superseded reviewed map snapshots.
