# Simulator Personal-Fidelity Result Template

> Do not prefill results. Mark analyses that have not run as "not run" rather
> than inserting expected values.

## 1. Frozen configuration

| Field | Value |
| --- | --- |
| Protocol version |  |
| Question-bank ID / version |  |
| Reviewed graph domain / version |  |
| Simulator provider / model |  |
| Language |  |
| Questions per participant | 20 |
| Data-freeze time |  |
| Exclusion-rule version |  |

## 2. Participants and flow completion

| Metric | Value |
| --- | --- |
| Consented |  |
| Created Profile |  |
| Confirmed Knowledge Map |  |
| Created twenty-item session |  |
| Completed all answers and ratings |  |
| Withdrew early |  |
| Sessions with technical failure |  |
| Included in analysis |  |

Report every exclusion and failure reason. Twenty item responses are not twenty
independent participants.

## 3. Item and generation completeness

| Metric | Count | Proportion |
| --- | ---: | ---: |
| Sampled items |  |  |
| Human answers saved |  |  |
| Simulator answers generated |  |  |
| Fallbacks |  |  |
| Warnings |  |  |
| Generation failures |  |  |
| Self-evaluations completed |  |  |

Report missingness and failures by question type, language, and participant.

## 4. Five participant ratings

Report the complete 1--5 distribution for each item. Do not silently collapse
the items into one score.

| Item | 1 | 2 | 3 | 4 | 5 | Median | IQR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Core-content similarity |  |  |  |  |  |  |  |
| Knowledge-level similarity |  |  |  |  |  |  |  |
| Capability-boundary similarity |  |  |  |  |  |  |  |
| Expression-style similarity |  |  |  |  |  |  |  |
| Overall representativeness |  |  |  |  |  |  |  |

Also report participant-level and question-level distributions so participants
with more usable responses do not receive unintended extra weight.

## 5. Overall replacement judgement

| Judgement | Count | Proportion |
| --- | ---: | ---: |
| Direct use |  |  |
| Minor bias |  |  |
| Major revision required |  |  |
| Not representative |  |  |

Primary descriptive proportion:

```text
(direct_use + minor_bias) / all valid self-evaluations
```

## 6. Biases and free text

Report predefined or derived bias categories, participants affected, answer
pairs affected, and a small number of consented de-identified examples. Do not
release re-identifying detail.

## 7. Descriptive strata

Possible descriptive strata include:

- mastery level;
- question type;
- language;
- Simulator warning or fallback;
- participant.

Do not make strong causal claims from sparse strata.

## 8. Later expert blind rating

| Item | Status |
| --- | --- |
| De-identified rating package | Not generated / generated |
| Expert rating | Not run / running / completed |
| Rating-result artifact |  |

Expert results remain separate from participant self-evaluations. If the stage
has not run, do not insert anticipated results.

## 9. Limitations and claim boundary

At minimum, discuss:

- participant-revised Profile and Map as operational ground truth rather than
  external objective truth;
- question-bank graph binding, content-validity, and instrument-validity status;
- circularity when Simulator and Profile/Map authoring share model or prompt
  structure;
- sample, domain, and provider/model transfer limits;
- why the current result does not support claims about agent ranking, effect
  direction, or rank reversal.
