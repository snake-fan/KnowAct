# V1 confirmed user profiles are never overwritten

KnowAct v1 never overwrites an existing confirmed synthetic-user `Profile Context` snapshot and does not expose an `overwrite=true` confirmation option. If persona content changes, the benchmark author publishes it under a new `user_id`, preserving the profile basis referenced by existing ground-truth maps and evaluation episodes.

**Considered Options**

- Allow explicit overwrite of an existing confirmed user profile.
- Require a new user id whenever confirmed persona content changes.

**Consequences**

Confirmed user profiles remain reproducible and map semantics cannot drift silently, at the cost of retaining superseded synthetic-user snapshots.
