# Evidence Synthesis and Research Gap

## 1. What is established, motivated, and still hypothetical

### Implemented facts in current KnowAct

- The reviewed Knowledge Graph is tested-agent-visible.
- The hidden reviewed Knowledge Map, profile context, hidden evidence, simulator prompt, and simulator trace are not visible.
- The agent owns a full-graph working map with categorical mastery, diagnostic confidence, notes, and visible supporting turn IDs.
- Runtime supports a single diagnostic question per turn, forced finalization, turn checkpoints, and full-map scoring.
- The existing `simple_llm_agent` asks an LLM to update states and choose the next question, but its “expected information gain” is a prompt instruction rather than an explicitly computed acquisition score.
- The experimental `evidence_calibrated_agent` persists per-node L0-L5 marginals, applies deterministic Bayesian-style updates to model-proposed answer likelihoods, validates multiple question candidates, and selects one with an inspectable deterministic utility. These are implementation facts, not comparative-performance evidence.

### Literature-supported design motivations

- Persisting a learner-specific state separately from fixed concept identity is supported by DKVMN and cognitive-diagnosis work.
- Adaptive question selection is supported by BOBCAT, NCAT, and GMOCAT.
- Relation-aware estimation is supported by RKT, RCD, KSCD, HierCDF, and graph-transfer work.
- Open-ended answer semantics matter beyond binary correctness, supported by OKT, SQKT, option tracing, and recent LLM KT work.
- Uncertainty and calibration deserve explicit treatment, supported by UKT, KARL, Bayesian active learning, and CAT.
- Standardized evaluation and leakage control are essential, supported by pyKT, ToMBench, BigToM, and agent benchmarks.

### Unverified KnowAct hypotheses

- A six-level explicit posterior will outperform a categorical-only working state.
- Model-estimated answer likelihoods will be calibrated enough to improve Bayesian updates.
- Graph-aware multi-node probes will improve full-map error at a fixed turn budget.
- A deterministic risk-aware selector will be more reliable than asking the LLM to choose one question directly.
- A proposer/verifier separation will reduce unsupported state changes enough to justify its extra model cost.

These remain hypotheses until the registered experiment is completed.

## 2. Field map

The canonical synthesis below is backed by the 41-paper audited pool. Earlier focused notes, maps,
machine-readable reports, and an HTML view are retained as
[supplementary literature artifacts](literature/README.md); their 14-paper count is not added to the
canonical audited count.

| Problem | Dominant literature approach | Strongest transferable lesson | Missing for KnowAct |
| --- | --- | --- | --- |
| Learner state | RNN/attention/memory or cognitive-diagnosis latent vector | Maintain state across observations; separate concepts from user state. | Interpretable six-level node posterior with cited language evidence. |
| Question selection | Information heuristics, bilevel learning, RL, multi-objective CAT | Selection must be compared to fixed and random policies under equal budgets. | Calibrated answer-outcome model for free-form diagnostic questions. |
| Graph structure | Relation attention, GNNs, hierarchy/Bayesian networks | Relations can share evidence and improve cold-start coverage. | Edge-type semantics and safeguards against over-propagation. |
| Open-ended evidence | Code/text encoders, LLM analyst/profile modules | Preserve semantic evidence and misconceptions; binary correctness discards signal. | Reliable likelihood extraction aligned to authored node rubrics. |
| Hidden-state reasoning | ToM benchmarks and social agents | Information asymmetry, consistency controls, and human ceilings matter. | Educational knowledge states differ from beliefs, goals, and preferences. |
| Agent loop | ReAct/reflection/memory architectures | Typed state-action loops are preferable to one terminal guess. | Reflection may be correlated self-critique, not independent validation. |
| Evaluation | KT benchmarks, agent trajectories, calibration studies | Immutable protocols, leakage checks, and process metrics are needed. | Full-map ordinal scoring, support quality, efficiency, and calibration in one harness. |

## 3. Why no existing paper directly solves the task

The closest papers cover only subsets of the target:

- KT/CD papers usually observe many binary response logs and predict future correctness.
- CAT papers select from calibrated item banks and often optimize one-dimensional or learned response models.
- open-ended KT papers exploit language but do not actively elicit a complete graph-wide mastery map.
- ToM papers evaluate hidden-state reasoning but not authored pedagogical levels.
- LLM-agent papers study action success, not calibrated user-state reconstruction.

KnowAct therefore needs a composed method and, more importantly, a comparison that isolates each composition choice.

## 4. Design synthesis

The evidence supports a five-part architecture:

1. **Evidence interpreter:** turns the latest visible answer into node-specific likelihoods and observed-behavior notes.
2. **Belief updater:** applies a deterministic Bayesian-style update to persisted six-level node distributions.
3. **Candidate proposer:** generates multiple coherent questions with explicit target nodes and mastery boundaries.
4. **Risk-aware selector:** deterministically scores candidates using expected information gain, graph coverage, redundancy, and complexity.
5. **Evidence-backed projector:** maps posteriors to the existing categorical working-map/final submission while retaining uncertainty and turn provenance.

This is named the **Evidence-Calibrated Diagnostic Agent (ECDA)**. “Calibrated” names an explicit evaluation objective and data representation; it is not a claim that the initial zero-shot likelihood estimates are already calibrated.

## 5. Key failure modes carried into the experiment

| Failure mode | Detection |
| --- | --- |
| Correct guess interpreted as mastery | Contradictory follow-up subset; anomaly/guessing scenario slice. |
| Verbal uncertainty interpreted as low mastery | Controlled answers with correct reasoning plus hedging. |
| Graph over-propagation | Directly observed versus graph-inferred node metrics; no-graph ablation. |
| Same-model circular validation | Independent model-family and human-adjudicated subset. |
| High final accuracy from unsupported inference | Evidence precision/coverage and unsupported-prediction rate. |
| Information-gain theater | Compare computed selector with direct LLM selection, coverage, fixed, and random policies. |
| Question packing | Structural validator and human question-coherence audit. |
| Early finalization hiding unknowns | Coverage curves and score versus turn-budget plots. |
| Benchmark leakage | Immutable manifests, provider/model snapshots, source separation, and prompt audit. |

## 6. Research contribution that can be claimed only after validation

If the experiment succeeds, the defensible contribution is not “the best knowledge tracing agent.” It is narrower: an evidence-backed, graph-aware, uncertainty-explicit interactive reconstruction policy that improves full-map diagnosis under fixed dialogue budgets on KnowAct, with component effects established by preregistered baselines and ablations.
