# Tested-Agent Knowledge Map Reconstruction Experiment

[中文](experimental_design.zh-CN.md)

> Status: preregistration-oriented design; no comparative run result is
> claimed.

## 1. Research objective and claim boundary

The experiment asks whether a tested agent can reconstruct a user's node-level
Knowledge Map more accurately and efficiently by actively selecting diagnostic
questions under a fixed turn budget.

The reviewed Knowledge Graph is public to the agent. The hidden object is the
user-specific mastery state over its nodes. Graph-node or graph-edge generation
is not part of this experiment.

The strongest supported claim depends on upstream evidence:

- without Experiment 02, results describe reconstruction against a synthetic
  simulator benchmark only;
- with simulator state-fidelity and safety evidence, results may support
  simulator-mediated agent comparison in the validated scope;
- matched human episodes are required before claiming transfer to human users.

## 2. Research questions

| ID | Research question |
| --- | --- |
| RQ-A1 | How accurately does each agent reconstruct the full hidden map under the same turn budget? |
| RQ-A2 | Does adaptive question selection improve reconstruction over non-adaptive or random selection? |
| RQ-A3 | Does explicit uncertainty and evidence accumulation improve calibration and reduce unsupported inference? |
| RQ-A4 | How do gains vary by domain, graph region, mastery stratum, turn budget, and model pairing? |
| RQ-A5 | What accuracy, latency, token, model-call, and failure trade-offs accompany each method? |

## 3. Confirmatory hypotheses

- **H-A1:** ECDA lowers paired Episode Mastery Distance relative to the Simple
  LLM Agent under equal graph, hidden map, turn budget, provider/model family,
  simulator condition, and retry policy.
- **H-A2:** After a versioned expert question bank is bound into manifests,
  adaptive bank selection and ECDA lower error relative to seeded random
  selection.
- **H-A3:** ECDA reduces missing predictions or unsupported inference without a
  practically meaningful regression in primary mastery distance.
- **H-A4:** Any claimed benefit is not confined to one domain or one
  tested-agent/simulator model pairing.

H-A2 is deferred until the question-bank identity, version, and content hash are
part of the immutable episode contract.

## 4. Preconditions and frozen inputs

Before confirmatory execution, freeze:

- reviewed graph version and hashes;
- reviewed map IDs, map strata, and exclusion rules;
- simulator workflow, provider/model, prompt revision, condition, temperature,
  and repeated-seed policy;
- tested-agent code revision, provider/model, prompt revision, temperature, and
  retry policy;
- agent kind, turn budget, scoring profile, and episode identity;
- primary contrasts, practical-effect threshold, sample-size rule, bootstrap
  blocks, and multiplicity family;
- failure, fallback, cancellation, restart, and missing-run handling.

Every compared condition receives the same visible graph and equivalent hidden
map/simulator setup. A new agent condition uses a new immutable episode ID
rather than mutating an existing completed episode.

## 5. Conditions

### 5.1 Executable core comparison

| ID | Agent | Current status | Role |
| --- | --- | --- | --- |
| C0 | Simple LLM Agent | Implemented runtime kind | Current direct categorical baseline |
| C1 | Evidence-Calibrated Diagnostic Agent | Implemented experimental runtime kind | Primary research candidate |

Both conditions use the same Tested Agent protocol, working-map tools,
visibility boundary, finalization path, and scoring profile.

### 5.2 Deferred bank-policy comparison

| ID | Policy | Status |
| --- | --- | --- |
| B1 | Fixed expert-bank order | Code component exists; formal binding missing |
| B2 | Seeded random bank | Code component exists; formal binding missing |
| B3 | Coverage-greedy bank | Design only |
| B4 | LLM bank selector | Design only |

These conditions enter confirmatory analysis only after an immutable reviewed
question bank is stored, validated, and referenced by each Episode Manifest.

### 5.3 Diagnostic ceilings and negative controls

A passive no-question reconstruction condition may quantify the value of
dialogue. An oracle may be used only as an offline sanity-check ceiling. It is
never a tested agent and is excluded from fairness claims.

## 6. Experimental design

Use a paired blocked design. Each agent condition runs the same domain, reviewed
graph, hidden-map stratum, turn budget, simulator condition, and simulator seed
schedule.

The immutable Evaluation Episode is the runtime unit. The independent
scientific unit is the hidden user/map sample, not an individual turn, node, or
repeated model seed.

Repeated seeds estimate stochastic variation. They are not treated as
independent users, and no best-of-seed result is selected.

Recommended blocks:

- benchmark domain and graph version;
- hidden-map mastery-distribution stratum;
- turn budget;
- tested-agent model family;
- simulator model family and seed schedule.

## 7. Primary outcome

The primary outcome is mean full-graph Episode Mastery Distance under
`squared_mastery_distance_v1`.

For graph node \(n\), ground-truth level \(y_n \in \{0,\ldots,5\}\), and
submitted prediction \(\hat y_n\):

\[
d_n =
\begin{cases}
(\hat y_n-y_n)^2, & \hat y_n \neq \text{unknown},\\
36, & \hat y_n = \text{unknown}.
\end{cases}
\]

\[
D_{\mathrm{episode}}=\frac{1}{|V|}\sum_{n\in V}d_n.
\]

Lower is better. All nodes in the episode graph are scored.

## 8. Secondary outcomes

- exact and within-one-level mastery accuracy;
- signed mastery error and over/under-estimation rates;
- missing-prediction rate;
- unsupported-inference rate;
- directly supported prediction precision and recall;
- Brier score and calibration error when a condition exposes six-level beliefs;
- node and graph-cluster coverage by turn;
- mastery error area under the turn curve when valid intermediate projections
  are available;
- questions, model calls, input/output tokens, latency, estimated cost, parse
  failures, retry exhaustion, fallback, cancellation, and restart rates;
- blinded human ratings of question coherence and evidence support on a
  preregistered subset.

Accuracy, calibration, support, and cost remain separate outcomes. Do not tune a
composite leaderboard score after seeing results.

## 9. Ablations

Prioritize a small confirmatory family:

| ID | Change | Targeted mechanism |
| --- | --- | --- |
| A1 | Posterior state replaced by categorical-only state | Explicit uncertainty |
| A2 | Accumulated update replaced by latest-answer overwrite | Longitudinal evidence |
| A3 | Graph leverage term removed | Graph-aware selection |
| A4 | Coverage term removed | Full-map coverage objective |
| A5 | Multi-candidate utility replaced by direct LLM choice | Proposal/selection factorization |
| A6 | Evidence-note and turn-reference constraints removed | Traceability and unsupported inference |

Additional ablations remain exploratory unless added to the preregistration
before final data are observed.

## 10. Sample-size procedure

1. Run an engineering fixture set to validate artifact and failure handling.
2. Freeze a pilot set that will not enter confirmatory inference.
3. Estimate paired variance for the primary C1-minus-C0 contrast.
4. Choose the smallest practically meaningful improvement before final runs.
5. Conduct paired power analysis under the planned blocking structure.
6. Freeze episode count, seeds, stopping rule, and exclusion criteria.

Do not invent a fixed sample count before pilot variance and operational failure
rates are known.

## 11. Statistical analysis

- aggregate nodes into the preregistered episode-level primary score;
- estimate paired condition differences within blocks;
- use a hierarchical or blocked bootstrap over map samples within domains;
- report paired mean, median, standardized effect, 95% confidence interval, and
  complete per-episode distribution;
- use Holm correction for the confirmatory ECDA-versus-baseline family;
- report domain and model-family interactions without replacing the primary
  contrast;
- retain failed and fallback runs in the operational report and apply only
  preregistered inferential handling.

If multiple simulator seeds are used for one map, first aggregate them within
the map-condition cell or model their repeated-measure structure explicitly.

## 12. Leakage and fairness checks

Before analysis, verify that tested-agent payloads and persisted traces contain
no hidden map, Profile Context, simulator debug trace, answer blueprint, hidden
evidence, or scoring input.

Compared agents must use the same visible graph, turn budget, simulator
schedule, finalization contract, scoring code, and retry ceiling. Model-call and
token differences are measured rather than silently equalized after the fact.

## 13. Result artifact contract

Formal runtime artifacts are written under:

```text
experiments/03_agent_reconstruction/results/runs/{run_id}/
```

The run directory contains the immutable manifest snapshot, committed turns,
visible transcript, latest working map, agent tool trace, final output, and
scoring report. Resume-only checkpoint state is removed after completion.

The aggregate report must record code revision, artifact hashes, model names,
provider dates, prompts, condition IDs, all exclusions, and every failed run.

## 14. Decision rule and interpretation

ECDA is promoted from experimental candidate only if it shows a statistically
and practically meaningful improvement over the Simple LLM baseline on primary
full-map error, has no material safety or support regression, and does not rely
on one unexplained domain/model failure pattern.

If the primary contrast fails, report the null or adverse result. Secondary
naturalness, a favorable seed, or one domain slice cannot rescue the primary
claim.

If upstream simulator validity remains incomplete, label the conclusion as
synthetic-benchmark reconstruction performance and do not generalize it to
human users.
