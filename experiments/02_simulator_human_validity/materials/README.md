# Experiment 02 Materials

[中文](README.zh-CN.md)

## Current main-flow materials

- [`benchmark/question_banks/`](../../../benchmark/question_banks/README.md):
  independently versioned Economy, ISLP, and OSTEP banks; each contains 80
  atomic bilingual items, of which 20 are sampled per participant.
- [`participant_information_and_consent.md`](participant_information_and_consent.md):
  adaptable participant information and consent template.
- [`session_script.md`](session_script.md): facilitation and failure-handling
  guidance for the automated session.
- [`data_dictionary.md`](data_dictionary.md): session, answer-pair, rating, and
  access classifications.

Profile editing, node-level Map review, question sampling, answer comparison,
and the five-item self-rating are integrated into the standalone
`simulator-test-frontend/`; researchers do not need to transfer data manually
between CSV forms, and participants are not given the internal research
workbench.

## Question-bank contract

The bank is stored as a benchmark artifact, independent from frontend code,
experiment-specific materials, and participant sessions. Every item
has a stable `question_id`, concept key, question type, one cognitive operation,
accepted source references, and semantically equivalent English and Chinese
wording. Changing language does not change item identity. The backend admits a
bank only when its review artifact covers every item, contains a concise
roleplay answer with an explicit cognitive signal, and matches the bank's
content hash.

The current `reviewed_target_node_ids` are not yet formally bound. The bank is
suitable for development and pilot use, but author-side source/roleplay
screening is not domain-expert or psychometric validation.

## Deferred legacy materials

The following files remain for possible future extensions and are not required
by the current participant session:

- `question_set_a_islp_draft.csv` and `question_set_b_islp_draft.csv`;
- `leakage_challenge_suite.csv`;
- `condition_manifest_template.json` and
  `randomization_manifest_template.csv`;
- the old ten-item `self_fidelity_rating_form.csv`;
- `blinded_expert_rating_form.csv`.

When expert blind rating is connected, it should consume a new de-identified
package derived from saved sessions. Raters must not receive hidden Maps,
participant self-evaluations, or debug traces.

## Execution order

1. Obtain ethics approval and freeze the consent version.
2. Review bilingual equivalence and bind the bank to the reviewed graph.
3. Run cognitive interviews on the Profile, Map, and five-item rating UI.
4. Pilot the end-to-end flow, resume behavior, failures, and export.
5. Freeze the bank, graph, provider/model, and sampling rule.
6. Begin formal collection only after those gates pass.

Consent, contact, linkage, and raw-response data must not be committed.
