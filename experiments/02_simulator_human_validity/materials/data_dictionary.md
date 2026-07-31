# Experiment 02 Data Dictionary

[中文](data_dictionary.zh-CN.md)

## Identifier hierarchy

| Field | Meaning | Release class |
| --- | --- | --- |
| `study_id` | Frozen protocol instance | Public |
| `participant_code` | Pseudonymous participant identifier | Restricted |
| `linkage_key` | Identity-to-code mapping stored separately | Private; never model input |
| `question_id` | Frozen Set A or Set B item | Public after release approval |
| `condition_id` | Frozen simulator condition | Public |
| `seed` | Repeated-generation seed or schedule index | Restricted until unblinding |
| `answer_artifact_id` | Internal human or simulator answer identifier | Restricted |
| `presentation_id` | Blinded rating item identifier | Restricted until unblinding |
| `rater_code` | Pseudonymous expert-rater identifier | Restricted |

## Core tables

### Participant profile

Contains questionnaire responses and the participant-confirmed Profile Context.
It must not contain names, contact details, or exact institution/employer data.

### Human answers

One row per participant-question attempt. Record verbatim text, timing,
skip/refusal state, and collection order. Set A and Set B remain distinguishable.

### Human Reviewed Map

Contains reviewed node states, evidence references to Set A only, correction
history, and unresolved status. Set B data must never enter this table.

### Simulator answers

One row per participant-question-condition-seed. Keep failure and fallback rows.
Raw hidden context, blueprints, and debug traces remain separate restricted
artifacts and are not sent to raters.

### Ratings

Participant self-fidelity ratings and expert ratings use separate tables. The
unblinding key is joined only after both rating datasets are frozen.

## Missing-value vocabulary

Use explicit values rather than empty strings in analysis exports:

- `not_applicable`;
- `not_asked`;
- `participant_skipped`;
- `participant_withdrew`;
- `technical_failure`;
- `generation_failure`;
- `fallback_answer`;
- `unratable`;
- `unresolved_map_state`.

Do not convert a skipped answer to L0 or a generation failure to a low
self-fidelity score unless the preregistration explicitly defines that rule.

## Visibility and release classes

- **Public:** protocol, blank instruments, frozen question text, aggregate
  statistics, approved de-identified excerpts.
- **Restricted:** participant codes, raw answers, Profile Context, Reviewed Map,
  ratings, randomization, and unblinding keys.
- **Private:** consent records, contact details, linkage key, withdrawal log.
- **Simulator-only:** hidden map/evidence, blueprints, raw hidden debug traces.

Private and restricted raw data must not be committed to this repository.
