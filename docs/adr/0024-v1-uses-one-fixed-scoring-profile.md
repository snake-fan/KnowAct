# V1 uses one fixed scoring profile

KnowAct v1 uses a single fixed scoring profile, `squared_mastery_distance_v1`, across evaluation episodes. Episode manifests may reference this profile but must not override its level mapping, squared distance rule, missing prediction penalty, or episode aggregation rule.

**Considered Options**

- Allow each episode to define a custom scoring profile.
- Use one fixed scoring profile for all v1 episodes.

**Consequences**

V1 episode results remain comparable, but experimenting with alternative distance functions requires a new scoring profile version rather than ad hoc episode overrides.
