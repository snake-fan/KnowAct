# Gap Map

## Covered by prior work

- sequential latent-state modeling;
- learned and heuristic adaptive item selection;
- explicit conversational profile or cognitive-state memory;
- cost-aware selective information gathering and abstention;
- interactive simulator, reliability, and trajectory evaluation;
- causal controls for mental-state benchmarks.

## Not covered as one validated system

No focused-pool paper jointly tests:

1. a public typed concept graph with a hidden ordinal user state on every node;
2. open-ended agent-selected diagnostic questions rather than a fixed item bank;
3. evidence-grounded, inspectable full-map belief updates;
4. soft graph inference that preserves direct/indirect provenance;
5. matched-budget reconstruction curves and stopping decisions; and
6. simulator results linked to human behavior or agent rankings.

## Highest-risk proposed components

1. Graph propagation may amplify graph-authoring bias or correlated errors.
2. LLM-estimated information gain may only reward plausible-sounding questions.
3. A verifier may add cost without independent signal because it shares the same base model.
4. Simulator-specific policies may overfit response style rather than user knowledge.
5. Full-map scores may reward conservative priors unless coverage and selective risk are reported.

Each risk maps directly to a required control in the method-design contract.
