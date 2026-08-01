# Simulator Test Automated Session Script

[中文](session_script.zh-CN.md)

## Before the session

- confirm the consent version and ethics approval;
- assign a pseudonymous participant code and do not enter names or contact
  details in the system;
- confirm the reviewed graph, bilingual bank, provider/model, and sampling rule
  are frozen;
- verify access control and resume behavior for the private result directory;
- explain that the study evaluates the Simulator, not the participant, and that
  incorrect, partial, and "I do not know" answers are valid data.

## Phase 1: Profile

In the standalone participant Simulator Test app, enter relevant background,
experience, goals, and expression preferences. Generate the Profile Context,
let the participant revise every field, and confirm it only when accurate.

A confirmed Profile is not overwritten in place. Use a new pseudonymous user
ID if the Profile must be substantially recreated.

## Phase 2: Knowledge Map

Generate a Candidate Map from the confirmed Profile and reviewed graph. The
participant reviews every node and may revise mastery, misconceptions,
uncertainty boundaries, and an optional note. Confirmation publishes a new
immutable participant-reviewed map and saves the revision trace separately.

The facilitator must not choose a more favourable mastery level for the
participant.

## Phase 3: twenty questions and ratings

Choose a language and bilingual bank, then create the session. The system saves
the sampling seed and selects twenty unique questions.

For every question:

1. the participant answers independently;
2. submission saves the human answer first;
3. SAGE answers the same question;
4. the UI shows both answers side by side;
5. the participant completes five 1--5 ratings, a replacement judgement, and
   an optional comment;
6. saving advances to the next item.

Never show a Simulator answer before the participant submits their answer.
Never show the participant hidden Maps, evidence IDs, blueprints, or debug
traces.

## Interruption and technical failure

Resume the saved session after an interruption; do not create a replacement
session. If generation fails, retain the human answer and error record, repair
the provider, and retry the current item. Do not invent a Simulator answer.

## Closing

The system permits completion only after all twenty items contain a human
answer, Simulator answer, and self-evaluation. Re-explain withdrawal procedures
and keep consent or identity-linkage data separate from experiment responses.

Expert blind rating does not occur in the participant session. A later stage
must derive a separate de-identified rating package from the saved answer pairs.
