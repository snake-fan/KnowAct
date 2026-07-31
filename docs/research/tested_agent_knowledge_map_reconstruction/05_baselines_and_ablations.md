# Baselines and Ablation Design

## 1. Experimental principle

No agent is designated “best” in advance. ECDA is the primary candidate. Its scientific value depends on beating credible controls under the same graph, hidden maps, simulator snapshots, turn budgets, model family, token budget, and retry policy.

Question selection and state estimation must be isolated. Otherwise a better final score cannot be attributed to a better question policy.

## 2. Primary baselines

| ID | Agent | Question policy | State estimator | Purpose |
| --- | --- | --- | --- | --- |
| B0 | Passive reconstruction | No diagnostic questions; reconstruct from the initial visible context | Same estimator where applicable | Negative control and quantifies dialogue value. |
| B1 | Fixed expert bank | Pre-registered deterministic bank order | Shared categorical LLM estimator | Reproducible non-adaptive baseline. |
| B2 | Seeded random bank | Uniform selection without replacement from the same bank | Same estimator as B1 | Tests whether adaptive selection beats chance. |
| B3 | Coverage-greedy bank | Choose the question covering the most unresolved nodes/graph clusters | Same estimator as B1 | Strong non-LLM structural baseline. |
| B4 | LLM bank selector | LLM selects one item from the same expert bank | Same estimator as B1 | Isolates semantic adaptive selection without free question generation. |
| B5 | Simple LLM Agent | Existing direct categorical update and direct free-form next-question choice | Existing Simple LLM prompt | Current implemented v1 reference. |
| B6 | ECDA | Multi-candidate generation plus deterministic risk-aware utility | Likelihood extraction plus persisted posterior | Primary candidate. |
| U0 | Oracle ceiling | Chooses questions with hidden-map access | Hidden-map-aware | Sanity-check ceiling only; never a tested agent and never included in fairness claims. |

### Question-bank fairness

B1–B4 must use one immutable expert-reviewed bank with:

- stable question IDs and version;
- validated target node IDs and mastery boundaries;
- no hidden-map-specific wording;
- equivalent bank visibility across policies;
- bank identity bound into the Episode Manifest before formal comparison.

Until that binding exists, fixed/random policy code is experimental utility code, not a formal runtime option.

## 3. Main hypotheses

- **H1:** B6 lowers full-map ordinal error versus B5 at equal turn and model-call budgets.
- **H2:** B4/B6 lower error versus B2, showing benefit beyond random selection.
- **H3:** B6 improves calibration and supported-prediction precision versus B5 even when ordinal error is similar.
- **H4:** Graph-aware selection improves unobserved-node coverage but can increase over-propagation; the net effect must be measured.
- **H5:** Benefits should persist across benchmark domains and tested-agent model families, not only one simulator/model pairing.

## 4. Component ablations

| ID | Remove or replace | Comparison | What it identifies |
| --- | --- | --- | --- |
| A1 | Posterior state → categorical-only state | ECDA vs ECDA-cat | Value of explicit uncertainty/persistence. |
| A2 | Bayesian update → latest-answer overwrite | ECDA vs ECDA-last | Value of accumulating evidence. |
| A3 | Likelihood vector → direct mastery label | ECDA vs ECDA-label | Value of separating evidence interpretation from decision projection. |
| A4 | Graph leverage term | ECDA vs ECDA-no-graph | Contribution and risk of graph-aware selection. |
| A5 | Coverage term | ECDA vs ECDA-EIG-only | Whether full-map coverage needs an explicit objective. |
| A6 | Redundancy penalty | ECDA vs ECDA-no-red | Whether repeated probes waste turn budget. |
| A7 | Complexity penalty | ECDA vs ECDA-no-complexity | Whether integrated questions become overloaded. |
| A8 | Outcome-confidence shrinkage | ECDA vs ECDA-no-shrink | Robustness to uncertain utility estimates. |
| A9 | Multi-candidate selector → direct LLM choice | ECDA vs ECDA-direct | Value of proposal/selection factorization. |
| A10 | Incremental updates → final-only reconstruction | ECDA vs ECDA-final | Value of persistent working beliefs. |
| A11 | Full dialogue → latest turn only | ECDA vs ECDA-latest-context | Value of longitudinal evidence. |
| A12 | Evidence notes/turn constraints | ECDA vs ECDA-no-provenance | Accuracy–traceability trade-off and unsupported-inference rate. |
| A13 | Independent verifier on/off | optional ECDA-verifier comparison | Whether verification adds value beyond correlated self-review. |
| A14 | Early stopping on/off | fixed-turn ECDA vs stop-enabled ECDA | Separates selection quality from stopping policy. |

## 5. Robustness and stress slices

- correct reasoning with verbal hedging;
- confident but incorrect answer;
- lucky correct answer without explanation;
- self-correction within one answer;
- clarification and non-answer;
- contradictory answers across turns;
- integrated answer with evidence for multiple connected nodes;
- superficial keyword match without rubric behavior;
- sparse/disconnected graph regions;
- high-degree nodes versus leaf nodes;
- domain and graph-version transfer;
- tested-agent and simulator same-family versus cross-family pairing.

## 6. Outcomes

### Primary

- mean squared ordinal mastery error over the full graph;
- macro average across episodes, then domains;
- paired ECDA–baseline difference with 95% bootstrap confidence interval.

### Secondary

- exact and within-one-level accuracy;
- macro F1 across L0–L5 plus unknown coverage;
- Brier score and expected calibration error for six-level beliefs;
- directly supported prediction precision/recall;
- unsupported-inference rate;
- node coverage and graph-cluster coverage by turn;
- error-area-under-turn-curve;
- questions, model calls, input/output tokens, latency, and estimated cost;
- question coherence and evidence-support agreement on an adjudicated subset.

### No single composite leaderboard metric

Accuracy, calibration, evidence quality, and cost are reported separately. If a composite is later needed, its weights must be preregistered rather than tuned after seeing results.

## 7. Experimental units and statistics

- Unit: immutable Evaluation Episode.
- Blocking: benchmark domain, graph version, hidden-map stratum, and turn budget.
- Pairing: every compared agent runs the same episode/simulator snapshot set.
- Seeds: at least five for stochastic policies; deterministic temperature-zero policies still repeat across simulator seeds.
- Confidence intervals: hierarchical/blocked bootstrap over episodes within domains.
- Multiple comparisons: Holm correction for the primary ECDA-versus-baseline family.
- Effect reporting: paired mean difference, median difference, standardized effect, interval, and raw per-episode artifacts.
- Missing/failure runs: report separately; do not silently drop tool/parse failures.

## 8. Sample-size procedure

1. Freeze a pilot set that is not reused for final inference.
2. Estimate the paired variance of full-map error from the pilot.
3. Choose the minimum practically meaningful effect before final runs.
4. Conduct paired power analysis for the planned blocked comparison.
5. Freeze episode count and exclusion rules in the experiment manifest.

The paper review does not determine sample size; observed benchmark variance does.

## 9. Acceptance criteria for promoting ECDA

Promotion from experimental to primary benchmark agent requires all of:

- statistically and practically meaningful improvement over B5 on primary full-map error;
- no material regression in at least two of calibration, evidence support, and cost-normalized efficiency;
- improvement in at least two domains, with no unexplained catastrophic domain failure;
- no visibility-boundary violation;
- stable results across at least two tested-agent model families or an explicit model-specific scope claim;
- human audit confirming that question coherence and cited evidence are not degraded.

If these conditions fail, ECDA remains an experimental agent and the ablation results determine which narrower component, if any, should be retained.
