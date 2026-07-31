# SAGE Simulator Human-Validity Results

[中文模板](results_summary_template.zh-CN.md)

> Status: unfilled result template. No human-validity result is claimed.

## Frozen study

- Study ID: `[id]`
- Protocol version: `[version]`
- Ethics approval: `[identifier]`
- Domain and graph version: `[binding]`
- SAGE code/prompt revision: `[revision]`
- Conditions and seeds: `[manifest reference]`
- Pilot/final split: `[rule]`
- Collection dates: `[range]`

## Participants and data flow

| Quantity | Count |
| --- | ---: |
| Consented |  |
| Completed Set A |  |
| Completed map review |  |
| Completed Set B |  |
| Completed self-fidelity ratings |  |
| Included in primary analysis |  |
| Withdrawn |  |
| Excluded by preregistered rule |  |

Report recruitment strata, compensation, missingness, unresolved map states,
technical failures, and protocol deviations without identifying participants.

## Instrument checks

- Expert content review: `[result]`
- Cognitive interviews: `[result]`
- Missing-item rate: `[value]`
- Floor/ceiling patterns: `[result]`
- Factor or reliability analysis, if justified: `[result]`
- Decision on item-level versus scale reporting: `[decision]`

## Primary endpoint A: state-fidelity error

| Condition | Participants | Questions | Seeds | Mean absolute mastery error | 95% CI | Signed error |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Human reference |  |  |  | 0 |  | 0 |
| Full SAGE |  |  |  |  |  |  |
| Baselines/ablations |  |  |  |  |  |  |

State how repeated seeds and questions were aggregated within participants.

## Primary endpoint B: participant representation

Report the full ordinal distribution of SF10 and the participant-level
proportion rated `direct_use` or `minor_bias`. Do not report an unvalidated
ten-item mean as the primary result.

## Secondary endpoints

| Outcome | Full SAGE | Comparator | Paired effect | 95% CI |
| --- | ---: | ---: | ---: | --- |
| Ability-boundary error |  |  |  |  |
| Uncertainty omission |  |  |  |  |
| Misconception omission |  |  |  |  |
| Invented misconception |  |  |  |  |
| Diagnostic usefulness |  |  |  |  |
| Style authenticity |  |  |  |  |
| Fallback rate |  |  |  |  |
| Seed variance |  |  |  |  |

## Blinded-rating reliability

Report agreement separately for expressed mastery, correctness, ability
boundary, uncertainty, misconception, diagnostic usefulness, naturalness, and
profile consistency.

## Leakage study

| Category | Challenges | Exact forbidden hits | Semantic leaks | Fallbacks | Failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct fields |  |  |  |  |  |
| Cross-node scope |  |  |  |  |  |
| Prompt/history injection |  |  |  |  |  |
| Internal artifacts |  |  |  |  |  |

Zero observed hits is bounded evidence on this challenge suite, not a universal
non-leakage proof.

## Proxy-validity study

- Agents and matched episodes: `[set]`
- Rank correlation and interval: `[result]`
- Paired effect-direction agreement: `[result]`
- Rank reversals: `[result]`
- Absolute score shift: `[result]`

## Claim decision

| Claim | Evidence threshold met? | Supported scope or reason withheld |
| --- | --- | --- |
| Structural access isolation |  |  |
| Output safety |  |  |
| State fidelity |  |  |
| Style authenticity |  |  |
| Proxy validity |  |  |

## Deviations and limitations

List every preregistration deviation, unresolved bias, provider drift, excluded
condition, and scope limitation. Naturalness cannot substitute for a failed
state-fidelity or proxy-validity endpoint.
