# Field Scope: Interactive Knowledge-Map Reconstruction Agents

> Supplementary focused-map artifact. The canonical claim gate is
> [`../01_scope_and_quality_gate.md`](../01_scope_and_quality_gate.md); this earlier `D1`/`D2` rubric
> is retained to interpret the focused notes, not to enlarge the canonical audited count.

## Motivation

KnowAct evaluates whether an agent can infer a hidden user's node-level knowledge state through a
budgeted dialogue. The public knowledge graph is fixed; the latent object is the user's knowledge map
over that graph. This review therefore studies methods for state inference, diagnostic action selection,
explicit user-profile maintenance, and credible multi-turn evaluation.

The pool is intentionally small. It is designed to justify concrete method and experiment decisions,
not to maximize citation count or claim an exhaustive survey.

## Included

- knowledge tracing and cognitive diagnosis that update latent competence from sequential evidence;
- computerized adaptive testing and selective information acquisition;
- LLM methods that explicitly maintain or diagnose a changing user/student state;
- interactive agent benchmarks with simulator, reliability, or trajectory-evaluation evidence;
- construct-validity controls relevant to latent mental-state inference.

## Excluded

- knowledge-graph construction, embedding, completion, or QA unless directly used for user-state
  reconstruction;
- passive personalization from a supplied profile when it adds no state-inference or acquisition
  mechanism;
- tutoring methods evaluated only on response helpfulness without a diagnostic-state outcome;
- papers whose only support is an arXiv preprint when an archival version is unavailable;
- systems that use an LLM judge as the only evidence of the claimed reconstruction improvement.

## Unit of Analysis

The target system is a tested agent that receives a reviewed graph, an initially unknown full-map
shell, a visible interaction history, and a finite turn budget. Its outputs are evidence-grounded node
beliefs, diagnostic target plans, natural-language questions, and a final full-map reconstruction.

## Source and Time Boundary

Primary, official proceedings pages and final papers available through 30 July 2026 are used. Search
results, blogs, and citation counts are not treated as quality evidence.

## Quality Gates

Every focused-pool paper must pass all four gates:

1. **Provenance:** archival publication at a selective peer-reviewed venue, or a field-defining older
   paper with an official proceedings version.
2. **Decision relevance:** it changes at least one KnowAct design decision about state, update,
   action, stopping, simulator validity, or evaluation.
3. **Evidence adequacy:** the paper reports comparisons, controls, ablations, human evidence, or
   other analysis proportional to the claim borrowed here.
4. **Transfer boundary:** the review records what cannot be imported into KnowAct without new
   validation.

Venue prestige is a screening signal, not proof of correctness. No paper is called “best”; each is
assigned a bounded role in the design argument.

## Reading-Depth Labels

- **D2 — audited:** official full text inspected for problem, method, experimental design, and stated
  limitations.
- **D1 — verified:** official venue, abstract, central method, and headline evidence verified; a full
  experiment-table audit remains before the paper is cited for fine-grained numerical claims.
- **D0 — candidate:** discovered but not yet eligible for the focused pool.

Only D1/D2 papers appear in the pool. Only D2 papers may determine a detailed method or experiment
choice. D1 papers can motivate a direction but cannot support precise comparative claims.

## Review Questions

1. What explicit state should the reconstruction agent maintain?
2. How should open-ended answers become node-level evidence without label leakage?
3. How can graph relations inform beliefs without copying mastery across nodes?
4. Which diagnostic question should be asked next under a strict budget?
5. When should the agent stop or abstain?
6. Which comparisons and controls can attribute gains to agent design rather than model scale,
   simulator bias, or extra calls?
