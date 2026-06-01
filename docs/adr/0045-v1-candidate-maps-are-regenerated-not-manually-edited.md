# V1 candidate maps are regenerated rather than manually edited

KnowAct v1 treats a `Candidate Knowledge Map` as a discardable synthetic sample, not as a draft for manual content correction. A benchmark author reviews a generated candidate map and either promotes it unchanged or rejects it; when quality is poor, the author adjusts profile input or the map-authoring workflow and generates a new candidate run. This differs from graph authoring, where candidate nodes and edges may be manually corrected before promotion.

**Considered Options**

- Allow benchmark authors to edit candidate-map state and evidence content before promotion.
- Promote acceptable generated candidate maps unchanged and regenerate poor candidates after improving inputs or workflow behavior.

**Consequences**

Reviewed map provenance stays clear and benchmark artifacts better reflect the generation workflow under study, but map-authoring quality problems must be fixed at their source rather than patched one sample at a time.
