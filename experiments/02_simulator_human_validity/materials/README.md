# Experiment 02 Materials

[中文](README.zh-CN.md)

## Recommended execution order

1. Obtain ethics approval and version the consent text.
2. Bind both question sets to one reviewed graph and complete expert review.
3. Run cognitive interviews on the participant-facing rating instrument.
4. Pilot the session flow, randomization, data export, and missing-data rules.
5. Freeze `condition_manifest_template.json` as a concrete run manifest.
6. Collect Set A data and adjudicate Human Reviewed Maps.
7. Collect held-out Set B human answers before showing simulator answers.
8. Generate all frozen conditions and seeds.
9. Run participant self-fidelity ratings and blinded expert ratings.
10. Execute the leakage suite and, if preregistered, the matched-agent proxy
    study.

## Material inventory

- `participant_information_and_consent.md`: adaptable information and consent
  text; local ethics requirements take precedence.
- `session_script.md`: researcher script and ordering guardrails.
- `profile_context_questionnaire.csv`: minimal de-identified background and
  expression-style questionnaire.
- `question_set_a_islp_draft.csv`: map-authoring prompts.
- `question_set_b_islp_draft.csv`: held-out validation prompts.
- `human_map_review_form.csv`: participant/researcher state review and
  unresolved-item handling.
- `self_fidelity_rating_form.csv`: participant-facing item-level instrument.
- `blinded_expert_rating_form.csv`: source-blinded answer annotations.
- `leakage_challenge_suite.csv`: direct and semantic leakage challenges.
- `randomization_manifest_template.csv`: presentation order and blinding
  manifest.
- `condition_manifest_template.json`: frozen model, prompt, condition, seed,
  and artifact bindings.
- `data_dictionary.md`: identifiers, visibility, missing values, and release
  classes.

## Material status

All instruments are drafts until expert content review and pilot testing are
complete. The two ISLP question sets use provisional concept keys rather than
reviewed node IDs because no suitable reviewed graph snapshot is currently
present in the checkout.

Set A and Set B must remain disjoint after freezing. Set B answers, ratings, or
errors must not be used to revise the participant map, simulator prompt,
instrument, thresholds, or exclusion rules.
