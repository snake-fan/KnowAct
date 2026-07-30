# KnowAct Paper Narrative Blueprint

> Status: proposed structural contract for author confirmation. This file fixes
> the argument and space allocation before prose and results are filled in. It
> does not claim that the proposed reconstruction agent or its experiments are
> complete.

## 1. Terminology and Research Boundary

The objective domain `Knowledge Graph` is public and fixed. It defines the
concepts and relations over which every tested agent reasons.

The hidden target is a user-specific `Reviewed Knowledge Map`. The tested agent
does not rediscover graph nodes or edges. It reconstructs the user's node-level
knowledge state through bounded diagnostic interaction.

The paper should therefore use:

- **Knowledge-Map Reconstruction Agent** for the proposed tested agent;
- **active knowledge-state diagnosis** for the task;
- **public Knowledge Graph** for the shared hypothesis space;
- **hidden user Knowledge Map** for the reconstruction target.

`Knowledge-graph reconstruction agent` should be avoided unless the research
scope is deliberately changed to include topology or schema induction.

## 2. One-Sentence Thesis

KnowAct evaluates functional user modeling as a closed-loop reconstruction
problem: under a limited interaction budget, an agent must maintain an explicit
belief over a user's knowledge map, select diagnostic questions that reduce
decision-relevant uncertainty, update the map from visible evidence, and submit
an evidence-backed full-map reconstruction.

## 3. Narrative Spine

The paper follows one causal chain. Later sections may add evidence, but they
must not change this chain.

```text
Useful assistance requires a model of what the user knows
  -> current evaluations do not identify whether that model was actively acquired
  -> an identifiable test needs a public state space, hidden target, finite budget,
     controlled observations, and a direct reconstruction score
  -> KnowAct supplies that measurement environment
  -> the central technical question becomes how an agent reconstructs the map
  -> the proposed agent must jointly estimate state, value probes, update from
     evidence, exploit graph structure cautiously, and decide when to stop
  -> controlled baselines and ablations test which parts cause reconstruction gains
  -> simulator and human studies determine how far the claim transfers
```

## 4. Claim Hierarchy

The paper must keep the following claims separate. Evidence for a lower claim
does not establish a higher one.

1. **Reconstruction:** the submitted map matches the reviewed hidden map.
2. **Active acquisition:** adaptive probes beat matched non-adaptive probes.
3. **Explicit state use:** the working map causally improves later decisions.
4. **Graph-aware diagnosis:** graph structure improves efficiency without
   unsupported propagation.
5. **Proxy robustness:** conclusions persist across simulator configurations.
6. **Human transfer:** conclusions persist in matched human interaction.

The first four claims concern the reconstruction agent. They form the paper's
main technical contribution. The final two concern benchmark validity.

## 5. Stable Main-Text Structure

Percentages are proportions of the main paper, not current word counts. Missing
content leaves a visible placeholder; it does not transfer its space to another
section.

| Section | Share | Fixed role |
| --- | ---: | --- |
| Abstract | 3% | Problem, gap, task, agent idea, evidence status |
| 1. Introduction | 12% | Establish the measurement failure and paper thesis |
| 2. Related Work | 10% | Locate the unresolved axis; do not enumerate papers |
| 3. Task and Benchmark | 15% | Define the identifiable reconstruction environment |
| 4. Knowledge-Map Reconstruction Agent | 27% | Present the central method in full |
| 5. Experimental Evaluation | 25% | Test reconstruction, acquisition, mechanism, and validity |
| 6. Discussion and Conclusion | 8% | Bound claims, limitations, and next research layer |

The Agent and Experimental Evaluation sections jointly retain at least 50% of
the main text. Knowledge-graph authoring, schema listings, prompt templates,
queue/runtime mechanics, and detailed review forms belong in appendices unless
they are necessary for a validity claim.

## 6. Section Contracts

### Abstract

**Input:** the complete paper and only results that have actually been run.

**Must answer:**

1. Why does active user modeling matter?
2. Why do existing static or outcome-only evaluations fail to identify it?
3. What is reconstructed, under what information and budget constraints?
4. What is the core reconstruction-agent idea?
5. What evidence supports the claim?

**Do not:** lead with implementation, enumerate artifacts, or claim empirical
superiority while results are incomplete.

### 1. Introduction

#### 1.1 The decision problem

Open with a setting in which the best next action depends on what the agent does
not yet know about the user. The motivating unit is a decision, not a generic
conversation.

#### 1.2 The measurement failure

Show why supplied-evidence ToM tasks remove acquisition from the policy and why
holistic interactive outcomes confound user modeling with general competence.

#### 1.3 The missing technical object

Introduce explicit, inspectable reconstruction of a user's knowledge map as the
missing object between interaction and downstream action.

#### 1.4 KnowAct in one loop

Preview the public graph, hidden map, bounded diagnostic interaction, agent
working map, and deterministic final comparison.

#### 1.5 Contributions

Reserve contributions for:

1. an identifiable active knowledge-map reconstruction task;
2. a graph-aware, evidence-backed reconstruction agent;
3. a discriminating evaluation that separates acquisition, state use, graph
   use, simulator robustness, and human transfer.

If the agent or experiments are not complete, mark the corresponding item as a
design or protocol contribution rather than an empirical contribution.

### 2. Related Work

Related Work should be organized by the unresolved decisions that shaped the
method, not by paper chronology.

#### 2.1 Mental-state inference versus functional use

Compare supplied evidence, chosen evidence, explicit latent state, and scored
object.

#### 2.2 User modeling, knowledge tracing, and active diagnosis

Separate passive history interpretation from agent-selected diagnostic probes.
Use computerized adaptive testing and knowledge tracing to motivate belief
updates and budgeted acquisition, while noting that KnowAct uses open-ended
language rather than a calibrated item bank.

#### 2.3 Planning and information acquisition in language agents

Identify methods relevant to uncertainty representation, information value,
active probing, memory/state updates, stopping, and traceable decisions.

#### 2.4 User simulation and interactive evaluation

Explain why simulator consistency, human fidelity, and ranking preservation are
different validity questions.

End the section with one synthesis paragraph that states exactly which
combination is missing: explicit full-map reconstruction plus agent-controlled
evidence acquisition plus process-level attribution.

### 3. Task and Benchmark

This section defines the experimental object. It should be complete but
deliberately shorter than the Agent section.

#### 3.1 Formal task

Define the public graph, hidden user map, visible history, turn budget, action,
observation, working map, and final submission.

#### 3.2 Identifiability requirements

Tie each design choice to the alternative explanation it blocks:

- public graph -> shared hypothesis space;
- hidden full map -> explicit reconstruction target;
- finite budget -> opportunity cost for questions;
- visibility boundary -> no hidden-state leakage;
- full-map submission -> no selective reporting;
- deterministic score -> no evaluator-model confound.

#### 3.3 Episode and simulator boundary

Describe only information access and observation production needed to interpret
agent behavior. Detailed simulator stages and runtime orchestration move to the
appendix.

#### 3.4 Evaluation objects

Define endpoint reconstruction and the process signals needed to attribute it:
question targets, working-map updates, visible support, budget use, and final
predictions.

### 4. Knowledge-Map Reconstruction Agent

This is the largest method section and must remain in the main paper even while
implementation is incomplete.

#### 4.1 Design objectives and agent state

State the requirements before naming modules:

- full-graph coverage under a small budget;
- explicit uncertainty rather than premature point estimates;
- evidence-linked updates;
- graph-aware but non-deterministic propagation;
- one coherent diagnostic action per turn;
- inspectable termination and finalization.

Define the agent state as a belief-bearing working map, not only a table of final
labels. The final representation choice remains a method decision to validate.

#### 4.2 Evidence interpretation

Map each visible answer to observable diagnostic signals. Distinguish answer
correctness, reasoning quality, transfer, self-correction, misconceptions, and
linguistic hedging. State what is implemented, planned, or unresolved.

#### 4.3 Belief and working-map update

Specify how evidence changes node-level mastery beliefs and confidence. Define
how conflicting observations, missing evidence, and stale assessments are
handled. A point-estimate baseline may coexist with a probabilistic proposed
agent.

#### 4.4 Graph-aware inference

Use `prerequisite_for`, `supports`, `part_of`, and `contrasts_with` as soft
diagnostic structure. Never copy mastery mechanically across an edge. Define
which observations license indirect updates and how unsupported propagation is
detected.

#### 4.5 Diagnostic target selection

Define the value of a candidate probe using unresolved uncertainty, expected
information gain, graph coverage, mastery-boundary discrimination, redundancy,
and remaining budget. State approximations explicitly.

#### 4.6 Integrated question generation

Convert a selected connected concept set and target boundary into one coherent
comparison, explanation, or application task. Separate target selection from
surface question realization so their failures can be ablated independently.

#### 4.7 Update--plan--act loop

Give one algorithm box that orders:

1. interpret the latest visible answer;
2. update evidence-backed node beliefs;
3. compute unresolved diagnostic priorities;
4. select a high-value connected target set;
5. ask one diagnostic question or finalize;
6. export a full-map reconstruction with support references.

#### 4.8 Stopping and final reconstruction

Define early stopping, forced finalization, unknown predictions, and unsupported
inference. Runtime fallback must be reported separately from successful agent
finalization.

#### 4.9 Implementation status and complexity

Use a status table:

| Component | Current status | Evidence required before claim |
| --- | --- | --- |
| Working-map contract | Implemented | schema and runtime tests |
| Evidence-linked node updates | Baseline implemented | semantic correctness study |
| Budget-aware question selection | Prompted baseline | controlled policy comparison |
| Graph-aware belief propagation | Not yet established | method definition and ablation |
| Calibrated uncertainty | Not yet established | calibration metrics and ablation |
| Integrated probe generation | Baseline implemented | grounding and diagnostic-yield analysis |
| Proposed reconstruction agent | Incomplete | end-to-end implementation and evaluation |

This table prevents partial implementation from being narrated as a completed
method.

### 5. Experimental Evaluation

Experiments are organized by claims, not by whichever result is available first.

#### 5.1 Research questions

- **RQ1 Reconstruction:** Can agents reconstruct full hidden maps better than a
  no-interaction or population-prior baseline?
- **RQ2 Active acquisition:** Does adaptive question selection beat matched
  fixed and random policies at equal budgets?
- **RQ3 Mechanism:** Which gains come from explicit state, uncertainty, graph
  structure, evidence linking, and integrated probing?
- **RQ4 Efficiency and calibration:** How quickly and reliably does uncertainty
  decrease, and are confidence estimates calibrated?
- **RQ5 Validity:** Do conclusions persist across simulators and transfer to
  matched human episodes?

#### 5.2 Compared agents

Keep identical input, tool, budget, finalization, and scoring contracts for:

1. no-interaction prior;
2. fixed-question baseline;
3. random-question baseline;
4. simple LLM baseline;
5. proposed reconstruction agent;
6. ablated variants of the proposed agent.

An oracle may be used only as an analysis ceiling and must never be presented as
a runnable fair baseline.

#### 5.3 Metrics

Separate:

- endpoint accuracy and ordinal distance;
- missing and unsupported predictions;
- turn-indexed reconstruction curves;
- question redundancy, grounding, and concept coverage;
- confidence calibration and information gain;
- token, latency, and interaction cost;
- simulator-to-human ranking agreement.

#### 5.4 Statistical design

Use paired episodes and treat the episode, not repeated stochastic calls, as the
independent unit. Predefine seeds, repetitions, uncertainty intervals, paired
tests, multiple-comparison handling, and effect sizes.

#### 5.5 Mechanism ablations

Ablate working map, graph edges, uncertainty, evidence references, planning,
integrated probing, and stopping separately. Each ablation should rule out one
alternative explanation.

#### 5.6 Robustness and human validation

Vary simulator model, grounding, answer policy, and profile style. Report both
absolute changes and agent rank reversals. Matched human episodes test state
fidelity, diagnostic usefulness, and ranking transfer.

#### 5.7 Error analysis

Use a prespecified taxonomy: missed evidence, over-propagation, under-
propagation, redundant probe, invalid grounding, stale working state,
miscalibration, premature finalization, and simulator leakage or artifact.

### 6. Discussion and Conclusion

Interpret results according to the claim hierarchy. Keep the distinction among
behavioral functional ToM, psychological ToM, knowledge-state reconstruction,
and downstream assistance explicit.

Limitations must cover authored target dependence, graph granularity, static
state, simulator fidelity, domain scope, open-ended probe variability, and
incomplete human transfer.

The next layer is downstream action: after reconstruction is established, test
whether the reconstructed map improves teaching, explanation, recommendation,
or collaboration. Do not merge that claim into the first paper unless it is
actually evaluated.

## 7. Appendix Allocation

Appendices preserve reproducibility without displacing the main agent method:

- graph and map authoring provenance;
- expert-review protocol and results;
- full schemas and semantic tool contracts;
- simulator prompts and leakage controls;
- reconstruction-agent prompts and pseudocode details;
- hyperparameters and provider settings;
- full tables, curves, statistical outputs, and error cases;
- runtime, checkpoint, queue, and artifact-layout details.

## 8. Structural Lock Rules

1. The Agent section stays the largest method section even before it is complete.
2. Missing agent content remains marked `TBD: method decision`, `TBD:
   implementation`, or `TBD: evidence`; benchmark details do not take its space.
3. Related Work grows by synthesis, not by adding one paragraph per paper.
4. Every main-text paragraph must serve one claim in the hierarchy.
5. Implementation facts, literature motivation, and research hypotheses must be
   labeled separately.
6. A claimed contribution must have both an implemented artifact and a matching
   experiment; otherwise it remains a proposed design contribution.
7. Results are inserted into predefined RQ slots. Available results do not
   determine section order.
8. New material that does not change claim interpretation, method understanding,
   or experimental validity moves to an appendix or is removed.

## 9. Reference-Selection Rule

Paper count is not a target. A reference enters the deep-reading set only if it
directly changes at least one of:

- the problem formulation;
- the reconstruction-agent state or update rule;
- diagnostic action selection;
- graph-aware inference;
- uncertainty, calibration, or stopping;
- simulator or human-validity design;
- a baseline, ablation, metric, or statistical decision;
- the paper's argument architecture.

Each selected paper must have a verified venue, an official paper page, clear
experimental evidence, and a documented reason for its influence on KnowAct.
Additional related papers may remain citation-only rather than receive equal
weight.
