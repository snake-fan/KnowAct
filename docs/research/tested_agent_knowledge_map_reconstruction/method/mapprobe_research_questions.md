# Research Questions

These questions target the full MapProbe design. Implemented ECDA components answer none of them until
the matched comparisons and ablations are run.

1. Under matched interaction and base-model budgets, does an explicit evidence–belief–probe agent
   reconstruct the hidden full knowledge map more accurately than prior-only, passive, random,
   fixed-order, maximum-uncertainty, and prompted-LLM baselines?
2. Does it reach a fixed reconstruction-quality threshold in fewer turns, especially in the first five
   diagnostic interactions?
3. Which improvements are attributable to explicit belief revision, typed graph inference, target
   utility, question verification, and stopping?
4. Are confidence and abstention calibrated, and are results stable across repeated stochastic runs?
5. Do gains persist across domains, graph sizes, simulator models, answer styles, contradictions, and
   controlled graph-edge corruption?
6. Do simulator-based method rankings agree with a smaller independent human interaction study?

These questions are fixed before experimental results. If a component is not implemented, its question
and allocated paper space remain rather than being replaced by benchmark-description prose.
