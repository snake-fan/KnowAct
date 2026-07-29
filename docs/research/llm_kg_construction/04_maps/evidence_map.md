# Evidence Map

| Claim | Evidence base | Confidence | Required local test |
|---|---|---|---|
| Staging helps control schema and context | EDC, KGGen | Medium-high | One-shot vs staged, budget matched. |
| Independent verification can improve structured generation | PiVe, SAC-KG, GraphJudge, GraphRefine | Medium-high | Staged workflow with and without verifier. |
| Typed repair is safer than deletion-only filtering | GraphRefine | Medium | Compare coverage and precision after repair. |
| Retrieval can reduce pairwise/global context cost | EDC, KGGen, ACE | Medium | Recall of duplicate and edge candidates at fixed top-k. |
| More agents improve quality | KARMA and other multi-role systems | Low as a causal claim | Hold prompts, models, tokens, and checks constant while varying role separation. |
| Expert prioritization can reduce prerequisite review effort | ACE | Medium | Review time and accepted-without-edit rate. |
| Source-grounded triples imply valid diagnostic rubrics | No direct support | Low | Separate expert rubric study under ECD criteria. |

Cross-paper numbers are not pooled. Each paper uses different graph definitions, data, evaluators, and recall denominators.

