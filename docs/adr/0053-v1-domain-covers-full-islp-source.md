# V1 domain covers the full ISL Python source

Accepted. This amends ADR-0025 and ADR-0027: KnowAct v1 keeps a single first benchmark domain, but the canonical domain is now `statistical_learning_with_python` and its source scope is the full *An Introduction to Statistical Learning with Applications in Python* book rather than the earlier `classical_supervised_ml_algorithms` slice. The project is close enough to experiment runs that the first benchmark graph should reflect the full selected authoritative source instead of a demo-sized supervised-only subset.

**Considered Options**

- Keep `classical_supervised_ml_algorithms` and filter source segments to supervised-learning chapters.
- Rename the first domain to `statistical_learning_with_python` and extract candidate nodes from the full selected ISL Python source.

**Consequences**

Graph authoring should not exclude source sections merely because they are outside the old supervised-only slice. The segmenting and extraction pipeline should avoid hard-coded book-specific categories such as "lab" or "exercise"; any future source-specific inclusion or exclusion policy belongs in explicit source or domain configuration. Existing code, docs, artifacts, and benchmark-domain defaults that still name `classical_supervised_ml_algorithms` need migration or compatibility handling before full-source experiment runs are treated as final.
