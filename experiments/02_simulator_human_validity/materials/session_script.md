# Simulator Validation Session Script

[中文](session_script.zh-CN.md)

## Before the participant arrives

- confirm consent version and ethics approval;
- allocate a pseudonymous participant code;
- verify that Set A and Set B are frozen and disjoint;
- verify that the condition manifest and randomization seed are frozen;
- open a private data location outside the Git worktree;
- ensure the researcher cannot see future simulator outputs during Human
  Reviewed Map adjudication.

## Opening

Explain that the study evaluates a simulator, not the participant. There is no
requirement to answer every question correctly. Uncertainty, partial knowledge,
and explicit "I do not know" answers are useful data.

Obtain consent before collecting any study response.

## Phase 1: Profile Context

Administer `profile_context_questionnaire.csv`. Ask only the listed follow-ups.
Show the generated Profile Context to the participant and allow factual edits.

Do not ask the participant to assign L0-L5 mastery labels in this phase.

## Phase 2: Set A and map review

Present Set A in its frozen order or preregistered random order. Record answers
verbatim except for clearly marked transcription corrections.

Generate the Candidate Knowledge Map only from allowed Set A data. Review each
state using `human_map_review_form.csv`.

If the participant and researcher cannot resolve a state with a recorded
rationale, mark it `unresolved`. Do not force a favorable label.

## Phase 3: held-out human answers

Present Set B before the participant sees any simulator response. Remind the
participant not to search externally unless the protocol explicitly allows it.

Record skipped, timed-out, and "do not know" responses as outcomes rather than
deleting them.

## Phase 4: simulator generation

Run generation from the frozen condition manifest. Include every seed, fallback,
empty answer, refusal, and parse failure.

The participant is not present while hidden conditions are prepared. Never show
raw maps, evidence IDs, blueprints, or debug traces.

## Phase 5: self-fidelity rating

Use the frozen randomization manifest. Show only the question, the participant's
own answer when preregistered, and one anonymized candidate answer.

Collect all ten items, the overall replacement judgment, bias flags, and an
optional comment. Do not reveal the condition until all ratings are complete.

## Closing

Ask whether the participant wants to withdraw any free-text comment before the
session closes. Re-explain the withdrawal deadline and compensation process.

Store consent/linkage data separately from response data. Record deviations,
technical failures, and early withdrawal without inventing missing responses.
