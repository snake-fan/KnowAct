# Experiment 02 Data Dictionary

[中文](data_dictionary.zh-CN.md)

## Identifiers

| Field | Meaning | Release class |
| --- | --- | --- |
| `participant_code` | pseudonymous participant code | restricted |
| `profile_id` | participant-confirmed Profile Context | restricted |
| `map_id` | participant-confirmed reviewed Knowledge Map | restricted |
| `session_id` | one resumable Simulator Test session | restricted |
| `question_bank_id` / `question_bank_version` | frozen bank identity | public |
| `question_id` | stable bilingual-item identity | public after approval |
| `sampling_seed` | reproducible twenty-item sample and order | restricted |
| `blind_review_status` | later expert-rating workflow status | restricted |

## Session-level data

A session stores participant, domain, confirmed graph/profile/map identities,
language, provider, bank version, sampling seed, twenty sampled questions in
fixed order, timestamps, and completion status.

Profile, Map, and raw answers are participant data. Names, contact details,
precise institutional identity, and linkage keys must not enter the session.

## Question-level data

Each `question_result` stores:

- question identity, displayed text, and sampled order;
- the human answer and submission time;
- Simulator answer, coarse observation, warnings, generation error, and hidden
  trace reference;
- five 1--5 self-ratings;
- an overall `direct_use | minor_bias | major_revision |
  not_representative` judgement;
- an optional free-text comment;
- `blind_review_status = pending` until a later rating stage.

The five ratings cover core content, expressed knowledge level, capability
boundary, expression style, and overall representativeness. They must not be
silently collapsed into one scale before instrument validation.

## Map-review data

`map_reviews/{map_id}.json` stores Candidate Map identity, node-level
participant revisions, and final reviewed-map identity. The final Map's
Simulator `self_report` evidence is `simulator_only` and must not enter an
expert-rating package.

## Missingness and failure

- An unanswered human item remains incomplete and does not trigger generation.
- A Simulator failure retains the human answer and `simulator_error` and may be
  retried.
- A missing rating leaves the session `in_progress`.
- The session becomes `completed` only when all twenty items are complete.

Do not convert a skipped human answer to L0 or a generation failure to a low
rating.

## Visibility and release

- **Public:** protocol, bank definition, blank instruments, aggregate
  statistics, and approved de-identified excerpts.
- **Restricted:** participant code, Profile, Map, raw answers, sessions,
  ratings, and sampling seed.
- **Private:** consent, contact information, identity linkage, and withdrawal
  records.
- **Simulator only:** hidden Map/evidence, blueprints, and hidden debug traces.

Restricted and private raw data must not be committed. An expert-rating package
must use new presentation IDs and exclude participant code, Profile, Map,
self-evaluations, and debug traces.
