# Knowledge-Map Reconstruction Agent: Method Design Contract

Status: **partially implemented research design, not yet empirically validated**.

This document fixes the method claim before comparative results exist. It is subordinate to
[`NARRATIVE_BLUEPRINT.md`](NARRATIVE_BLUEPRINT.md): implementation details may change, but the paper's
central problem, section proportions, research questions, and evidence requirements must not drift.

## 1. Exact problem statement

KnowAct exposes a reviewed, user-independent knowledge graph

\[
G=(V,E,R),
\]

where nodes are diagnosable concepts, edges are typed relations, and every node defines an ordinal
mastery rubric \(\mathcal{L}=\{L0,\ldots,L5\}\). The simulator privately holds the user's ground-truth
node states \(Z^*=\{z_v^*:v\in V\}\). The tested agent sees only \(G\), its own dialogue with the user,
its remaining interaction budget, and its current working map.

At turn \(t\), the agent must jointly:

1. interpret the latest open-ended answer as evidence about one or more nodes;
2. update an explicit belief over the user's node-level mastery;
3. choose a diagnostic target and realize it as one coherent question; and
4. decide whether another interaction is worth its cost.

The final output is a reconstructed **knowledge map over the public graph**, not a reconstructed
knowledge graph. The graph's nodes, edges, rubrics, and version are never hidden and are never edited
by the tested agent.

## 2. Intended contribution

The proposed contribution is not “an LLM with a longer prompt.” It is an auditable
**evidence–belief–probe control loop** whose intermediate objects can be independently scored.

Working name: **MapProbe**. The name is provisional; the paper's argument does not depend on it.

The current experimental `evidence_calibrated_agent`, abbreviated **ECDA**, implements a narrower
MapProbe slice: checkpointed L0-L5 node marginals, model-proposed answer likelihoods, deterministic
Bayesian-style updates, and deterministic selection among multiple model-proposed question candidates.
It does not yet implement the full direct/indirect evidence ledger, typed graph belief propagation,
target-before-language question verification, or calibrated early stopping specified below.

MapProbe differs from the current `simple_llm` baseline in four falsifiable ways:

| Component | Current prompted baseline | Proposed MapProbe |
|---|---|---|
| State | one hard level and coarse confidence per node | ordinal belief distribution plus direct/indirect evidence ledger |
| Update | free-form LLM assessment constrained by schema | rubric-grounded evidence extraction followed by explicit belief revision |
| Graph use | graph shown in prompt; no formal propagation rule | edge-type-specific, uncertainty-decayed soft messages |
| Action | LLM chooses a target and question together | target utility is scored before question realization and verified afterward |
| Stop | budget or LLM decision | budget plus estimated marginal reconstruction gain and coverage constraints |

No superiority claim is permitted until these differences are evaluated under matched model,
prompt-access, token-budget, and interaction-budget controls.

## 3. Agent state

For every node \(v\), MapProbe maintains

\[
B_t(v)=\langle p_t(l\mid v),\;D_t(v),\;I_t(v),\;C_t(v)\rangle,
\]

where:

- \(p_t(l\mid v)\) is a probability distribution over \(L0\ldots L5\);
- \(D_t(v)\) is direct evidence explicitly demonstrated for \(v\);
- \(I_t(v)\) is indirect evidence received through graph relations;
- \(C_t(v)\) records contradictions, ambiguity, and missing coverage.

Each evidence item contains a turn identifier, target node, observed rubric boundary, polarity,
evidence strength, answer span or short rationale, and provenance class (`direct` or `graph_inferred`).
The public runtime schema may continue to expose a hard level and coarse confidence, but those values
are projections of the richer internal state rather than the entire state itself.

Initial beliefs must be fixed before seeing the hidden profile. Candidate initializations are a uniform
prior and a training-split empirical prior. They are separate experimental conditions; the empirical
prior cannot be used in zero-shot transfer experiments unless it is estimated only from permitted
training domains.

## 4. Evidence interpretation

The evidence interpreter converts the latest visible turn into a typed set of observations. It receives
the question plan, the answer, the relevant node definitions, and mastery rubrics. It must answer:

- What capability did the response actually demonstrate?
- Which adjacent mastery boundary does it support or contradict?
- Was the evidence elicited directly, volunteered incidentally, or inferred from a related node?
- Is the answer incomplete, internally inconsistent, copied from the prompt, or off-target?

The interpreter is forbidden to see the hidden profile or scorer output. It must cite visible turn IDs,
must preserve `unknown` when evidence is insufficient, and must separate mastery evidence from verbal
confidence. A structured verifier checks node existence, rubric consistency, evidence provenance, and
whether the cited text supports the claimed boundary.

This module should first be evaluated in isolation against human annotations. End-to-end gains cannot
establish that the intermediate diagnoses are valid.

## 5. Belief revision

For each direct observation \(o_t\), update only the implicated node beliefs:

\[
p_t(l\mid v) \propto p_{t-1}(l\mid v)\,P(o_t\mid l,v).
\]

The current ECDA slice asks the model for a six-level observation-likelihood vector and applies the
update deterministically. These zero-shot likelihoods are neither learned nor assumed calibrated. A
small frozen ordinal likelihood table remains a reproducible baseline, while a learned observation
model becomes eligible only after enough adjudicated interactions exist.

Contradictory evidence does not overwrite earlier evidence. It increases posterior uncertainty and is
recorded for possible follow-up. Repeated semantically equivalent answers receive a redundancy
discount so that verbosity does not masquerade as independent evidence.

The hard submitted level is the posterior mode. A node may remain `unknown` when entropy is high or
direct coverage is absent. The abstention rule and threshold must be selected on a development split
and frozen before test evaluation.

## 6. Graph-aware soft inference

Graph edges are evidence-routing priors, not deterministic mastery rules. For an edge
\((u,r,v)\), MapProbe may send an indirect message from \(u\) to \(v\):

\[
m_{u\rightarrow v}^{(r)}(l)
=\alpha_r\,q_r(l\mid B_t(u)),
\qquad 0\leq\alpha_r<1.
\]

The relation-specific transform \(q_r\) and attenuation \(\alpha_r\) must follow the graph semantics.
For example, strong evidence on a prerequisite can raise the plausibility of higher downstream
mastery, but it cannot copy a level. Negative evidence may motivate a probe of a prerequisite without
proving downstream non-mastery. Only one bounded propagation hop is allowed in the first version;
multi-hop propagation is an ablation because it can amplify graph-authoring errors.

Direct and indirect evidence are retained separately. A final prediction supported only by propagation
must be identifiable in analysis. This makes it possible to measure whether graph use improves
coverage or merely creates confident correlated errors.

## 7. Diagnostic target selection

Before generating language, the planner scores a candidate node or small connected target set \(S\):

\[
U_t(S)=
\lambda_1\widehat{IG}_t(S)
+\lambda_2\operatorname{Coverage}(S)
+\lambda_3\operatorname{BoundaryRisk}(S)
+\lambda_4\operatorname{GraphReach}(S)
-\lambda_5\operatorname{Redundancy}(S)
-\lambda_6\operatorname{Cost}(S).
\]

- `IG` estimates expected reduction in full-map uncertainty under plausible answers.
- `Coverage` rewards direct evidence for untouched or weakly supported nodes.
- `BoundaryRisk` prioritizes nodes whose posterior mass straddles a high-loss mastery boundary.
- `GraphReach` rewards a target that can inform a local neighborhood, with attenuation.
- `Redundancy` penalizes probes similar to previous questions or already-supported evidence.
- `Cost` captures the remaining interaction budget and expected answer burden.

The first implementation may estimate information gain using a small answer-outcome model or a
training-split simulator. It must not query the episode's hidden simulator state. A simpler entropy-plus-
coverage heuristic remains a required baseline so that apparent gains are not attributed to expensive
planning without evidence.

The planner outputs the existing visible `DiagnosticQuestionPlan`: primary target, optional secondary
targets, mastery boundary, and selection reason. This preserves compatibility with the current runtime
and exposes the decision for later trajectory analysis.

## 8. Question realization and verification

The realizer converts a target plan into one natural, answerable diagnostic question. A good question:

- discriminates the named adjacent mastery boundary;
- elicits reasoning, application, transfer, comparison, or self-correction rather than self-report;
- does not reveal the rubric, expected answer, or hidden state;
- does not bundle unrelated subquestions; and
- can be answered within the simulator's single-turn response boundary.

A bounded verifier checks alignment between the target plan and generated question. It can return
`accept`, `rewrite`, or `abstain-and-select-next`. The verifier is not evidence that multi-agent
decomposition is intrinsically better; its value must be established through a verifier ablation and
question-quality annotations.

## 9. Update–plan–act loop

```text
initialize full-graph belief shell
while diagnostic budget remains:
    if a visible answer exists:
        extract rubric-grounded observations
        verify evidence and update direct beliefs
        route bounded, typed indirect messages
    score diagnostic targets
    estimate best target's marginal utility
    if stop rule is satisfied:
        break
    realize and verify one diagnostic question
    ask user simulator
project beliefs to the required full-map submission
```

The runtime remains responsible only for visibility, turn order, persistence, and scoring. It must not
perform diagnosis or action selection on the tested agent's behalf.

## 10. Stopping and finalization

MapProbe finalizes when the budget is exhausted or when all of the following hold:

1. the best estimated marginal utility is below a development-set threshold;
2. every high-priority node is directly observed or explicitly abstained on; and
3. unresolved contradictions cannot be profitably disambiguated within the remaining budget.

This rule must be compared with fixed-turn policies at every available budget. A method that stops
earlier but loses reconstruction quality is not more efficient merely because it asks fewer questions.

The submitted map covers every public node. For each node it reports `L0`–`L5` or `unknown`, a
diagnostic confidence projection, an assessment note, and supporting visible turn IDs. Scoring treats
abstention explicitly; the paper must report both error on attempted nodes and coverage-adjusted error.

## 11. Research questions fixed before results

**RQ1 — Reconstruction quality.** Under matched interaction and model budgets, does MapProbe reduce
full-map mastery error relative to non-interactive, random-probe, fixed-order, and prompted-LLM
baselines?

**RQ2 — Sample efficiency.** Does it reach the same reconstruction quality with fewer diagnostic
turns, and does the advantage persist across 1/3/5/10-turn budgets?

**RQ3 — Mechanism attribution.** Which gains come from explicit belief revision, graph-aware
inference, utility-based target selection, and question verification?

**RQ4 — Reliability and calibration.** Are node confidence, abstention, and episode-to-episode
variance calibrated, including repeated runs over the same hidden profile?

**RQ5 — Transfer and robustness.** Does the agent generalize across domains, graph sizes, simulator
models, answer styles, contradiction rates, and graph-edge perturbations?

**RQ6 — Simulator validity.** Do conclusions and agent rankings survive a smaller human interaction
study or an independently validated simulator configuration?

## 12. Required comparison set

All methods use the same public graph, mastery rubrics, simulator, tested-agent model where applicable,
maximum turns, and scorer.

1. **Prior-only:** submit the frozen prior without dialogue.
2. **Transcript-only one shot:** consume a fixed transcript, then reconstruct once.
3. **Random probe:** random target; matched question realizer.
4. **Fixed traversal:** deterministic graph order; matched question realizer.
5. **Uncertainty heuristic:** choose maximum-entropy node without graph reach or lookahead.
6. **Current simple LLM:** existing prompt-based update and plan baseline.
7. **MapProbe:** full proposed method.
8. **Oracle-analysis bounds:** privileged target or evidence labels only as clearly separated upper
   bounds, never as deployable baselines.

Model-family comparisons are secondary. The primary causal comparison holds the base model fixed and
changes only the agent mechanism.

## 13. Metrics and statistical design

### Primary outcome

- full-map squared mastery distance, matching the benchmark scoring contract;
- area under the reconstruction-quality-versus-turn curve;
- turns required to reach a predeclared error threshold.

### Secondary outcomes

- exact and within-one-level node accuracy;
- direct-evidence coverage and abstention rate;
- confidence calibration and selective risk–coverage curves;
- error by node depth, relation type, mastery level, and direct versus propagated support;
- contradiction resolution rate and repeated-run reliability;
- token, latency, and model-call cost;
- human-rated evidence validity and question discriminativeness on a stratified sample.

Use paired episode seeds across methods. Report paired bootstrap confidence intervals and effect sizes,
not only means. Correct families of related ablation tests. Predeclare the primary metric, aggregation
unit, exclusion rules, and development/test split. Never select the best run from repeated stochastic
runs; report the distribution and a reliability statistic.

## 14. Required ablations and stress tests

- remove explicit belief distribution and retain only hard labels;
- remove graph propagation;
- replace typed propagation with untyped propagation;
- remove information gain, coverage, redundancy, or cost terms one at a time;
- replace planner with maximum entropy;
- remove question verifier;
- remove abstention;
- corrupt or delete controlled fractions of graph edges;
- vary answer verbosity, hedging, misconception, contradiction, and off-target behavior;
- swap simulator model and prompt while keeping profiles fixed;
- use cross-domain held-out graphs and unseen graph sizes.

The edge-perturbation study is essential: otherwise a graph-aware agent can appear better only because
the benchmark graph and inference assumptions share the same authoring bias.

## 15. Claim–evidence contract

| Intended paper claim | Minimum required evidence | Claim if evidence is absent |
|---|---|---|
| explicit state improves reconstruction | matched-base-model ablation with paired intervals | “we expose an auditable state” |
| graph structure improves efficiency | no-graph and perturbed-graph controls | “the method can use graph structure” |
| planning selects informative questions | matched realizer plus random/fixed/entropy baselines | “the planner implements a utility heuristic” |
| verifier improves question quality | verifier ablation plus human question ratings | “the verifier is a quality-control mechanism” |
| simulator results predict real interaction | ranking agreement with human study | “results hold under the evaluated simulator” |
| method is robust | simulator, domain, seed, and graph-perturbation tests | scope claim to tested conditions |

## 16. Implementation status and paper-space rule

| Item | Status on 2026-07-31 | How the paper should describe it now |
|---|---|---|
| public graph and hidden-map visibility boundary | implemented | present-tense system fact |
| full working-map shell and hard node assessments | implemented | present-tense baseline infrastructure |
| simple LLM update and target-plan baseline | implemented | present-tense baseline |
| checkpointed per-node L0-L5 marginal belief | implemented in ECDA | present-tense experimental mechanism; no benefit claim |
| model-proposed likelihood and deterministic belief update | implemented in ECDA | present-tense experimental mechanism; calibration remains unverified |
| direct/indirect evidence ledger and verifier | not implemented | proposed design / TBD result |
| typed graph propagation | not implemented | proposed design / TBD result |
| deterministic multi-candidate question utility | implemented in ECDA | present-tense experimental mechanism; no benefit claim |
| target-before-language planning and question verifier | not implemented | proposed design / TBD result |
| calibrated stopping rule | not implemented | proposed design / TBD result |
| matched ablations and human validation | not run | reserved experiment subsections and empty tables |

The Agent section retains its allocated paper space even while these components are incomplete. Empty
method and result slots are marked `TBD`; benchmark-construction prose must not expand into them.

## 17. Decisions still requiring empirical resolution

1. Whether a categorical distribution is sufficient or an ordinal latent-variable model is needed.
2. Whether information gain can be estimated reliably without training a response model.
3. Which edge types support useful directional messages and with what attenuation.
4. Whether multi-node integrated questions improve efficiency without harming attribution.
5. Whether the verifier's benefit exceeds its extra calls and correlated-judge risk.
6. Whether early stopping remains safe under sparse, contradictory, or adversarial answers.

These are research questions, not implementation details to hide. The paper should present the chosen
variants only after comparative evidence exists.
