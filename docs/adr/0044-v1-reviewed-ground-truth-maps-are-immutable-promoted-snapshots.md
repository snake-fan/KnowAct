# V1 reviewed ground-truth maps are immutable promoted snapshots

KnowAct v1 publishes a benchmark-author reviewed `Candidate Knowledge Map` through explicit promotion as an immutable `Ground-Truth Knowledge Map` snapshot with a `map_manifest.json`. The manifest binds map identity, synthetic user identity, benchmark domain, reviewed graph version, confirmed profile-context snapshot, and originating candidate run. Promotion revalidates the candidate map but does not consume generation-time consistency warnings.

**Considered Options**

- Edit one mutable ground-truth-map file in place.
- Explicitly promote reviewed candidate-map runs into immutable ground-truth-map snapshots.

**Consequences**

Map authoring needs candidate-run directories, promotion logic, and manifest storage, but evaluation episodes can reliably bind reviewed hidden maps without losing their authoring provenance.
