# V1 reviewed graph versions are never overwritten

KnowAct v1 never overwrites an existing reviewed `Authored Knowledge Graph` version and does not expose an `overwrite=true` promotion option. If reviewed node, rubric, or edge content changes, the benchmark author publishes a new graph version. Candidate maps and evaluation episodes can therefore keep referring to an immutable graph basis without copying reviewed graph payloads or adding graph fingerprints to every downstream artifact.

**Considered Options**

- Allow explicit overwrite of an existing reviewed graph version while curating domain assets.
- Copy graph payloads or store fingerprints in downstream map artifacts.
- Require a new graph version whenever reviewed graph content changes.

**Consequences**

Reviewed graph publication retains superseded versions, but candidate-map promotion and episode replay remain reproducible through a simple benchmark-domain and graph-version reference.
