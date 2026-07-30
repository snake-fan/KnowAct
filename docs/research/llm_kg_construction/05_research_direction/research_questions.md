# Research Questions and Hypotheses

These are optional graph-construction research questions for a future dedicated study. They are not part of the current KnowAct paper. The paper treats graph quality only as a prerequisite content-validity check: two independent domain experts review the complete approximately 20-node scoped graph and all of its edges, with disagreement adjudication and no authoring-method comparison.

## RQ-KG1: Construction quality

Does evidence-grounded staged authoring improve node and edge quality over one-shot and unverified staged LLM baselines under matched budgets?

- **H1a:** independent grounding verification increases node precision and lowers unsupported claims.
- **H1b:** a second coverage pass recovers recall lost by precision-oriented verification.

## RQ-KG2: Canonicalization

Does retrieval-assisted, decision-based canonicalization reduce duplicates and granularity errors without increasing over-merging?

- **H2:** candidate retrieval plus explicit merge/split/alias adjudication improves cluster F1 over lexical deduplication.

## RQ-KG3: Relation authoring

Do type-specific relation tests and evidence-aware verification outperform a single full-graph edge-generation prompt?

- **H3:** verified pairwise classification improves direction-sensitive edge precision while maintaining a predeclared recall floor.

## RQ-KG4: Diagnostic validity

Do ECD-grounded rubrics produce more monotonic, distinguishable, and observable mastery levels than unconstrained LLM enrichment?

- **H4:** expert rubric ratings and inter-rater agreement improve after ECD constraints and independent validation.

## RQ-KG5: Human effort

Can calibrated risk ranking reduce expert editing time without reducing adjudicated graph quality?

- **H5:** experts review fewer low-risk items and spend less total time at a non-inferior quality threshold.

## RQ-KG6: Reliability

Does checkpointed, bounded repair reduce silent corruption and improve resume correctness under injected failures?

- **H6:** the proposed workflow detects all invalid artifacts in the fault suite and never promotes a partial run.

## RQ-KG7: Downstream sensitivity

Do graph construction choices materially change simulator fidelity or tested-agent rankings?

- **H7:** graph variants with lower intrinsic validity produce larger ranking variance and more unsupported propagation errors.
