# Experiment 02 Results

[中文](README.zh-CN.md)

No human data have been collected and there are no empirical Simulator
personal-fidelity results.

The automated workflow writes each resumable session to:

```text
private/sessions/{session_id}/session.json
```

Participant revisions to the Candidate Map are written to:

```text
private/map_reviews/{map_id}.json
```

`private/` is ignored by Git. A session records the question-bank version,
language, sampling seed, twenty-item order, human and Simulator answers,
self-evaluations, and `blind_review_status`. It is not an expert-blind-rating
result.

A later expert-rating stage must create a separate de-identified artifact with
random presentation identifiers while withholding participant code, Profile,
Map, self-evaluations, and debug traces. It must not overwrite the source
session.

Only a de-identified aggregate report should be committed after frozen
exclusion, missing-data, and analysis rules have been applied.
