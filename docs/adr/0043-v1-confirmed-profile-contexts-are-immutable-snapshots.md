# V1 confirmed profile contexts are immutable snapshots

KnowAct v1 publishes each benchmark-author confirmed `Profile Context` as an immutable artifact snapshot for one synthetic benchmark user, identified by `user_id`. Candidate-map generation reads a saved confirmed snapshot by user id; changing a confirmed context requires publishing a new user id rather than silently overwriting the existing artifact, so maps and evaluation episodes retain a reproducible persona basis without introducing a duplicate profile-context identity.

**Considered Options**

- Allow a confirmed profile-context file to be edited in place.
- Publish immutable confirmed snapshots and require a new id for later edits.

**Consequences**

Profile-context authoring needs separate editable candidate artifacts and confirmed snapshot storage, but map generation, debugging, and episode replay can reliably refer to the same persona basis.
