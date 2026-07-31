# P005 — [LongTutor](https://aclanthology.org/2026.acl-long.1371/)

**Li et al., ACL 2026. Reading depth: D2.**

## Contribution

Builds an expert-annotated benchmark over real learning logs and separates historical evidence
acquisition, knowledge-state diagnosis, and adaptive teaching action. Results expose a gap between
extracting evidence and using it correctly for diagnosis and action.

## KnowAct transfer

Score evidence interpretation, reconstructed state, and action quality separately. Use human
annotations for intermediate evidence and an independently checked generator–verifier pipeline for
scalable data expansion.

## Do not transfer

The tested model receives a pre-existing history rather than deciding which evidence to elicit.
