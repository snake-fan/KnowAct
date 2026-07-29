# Method Map

| Method family | Representative work | Reliable element to reuse | KnowAct adaptation |
|---|---|---|---|
| Open extraction then schema control | [EDC](https://aclanthology.org/2024.emnlp-main.548/) | Defer canonicalization until candidate evidence exists. | Extract concepts locally, then reconcile against a frozen diagnostic specification. |
| Schema-first structured extraction | [SPIRES](https://doi.org/10.1093/bioinformatics/btae104), [GenIE](https://aclanthology.org/2022.naacl-main.342/) | Machine-valid output contracts. | Pydantic/JSON schema plus deterministic graph constraints. |
| Guideline-conditioned extraction | [GoLLIE](https://openreview.net/forum?id=Y3wpuxd7u9) | Positive, negative, and boundary examples. | Executable node and relation decision rules. |
| Iterative verification | [PiVe](https://aclanthology.org/2024.findings-acl.400/) | Corrective feedback from a distinct verifier. | Bounded retry using original source evidence and explicit error labels. |
| Propose--verify--prune | [SAC-KG](https://aclanthology.org/2024.acl-long.238/) | Precision-oriented role separation. | Add quarantine and human escalation; measure recall separately. |
| Entity/concept resolution | [KGGen](https://proceedings.neurips.cc/paper_files/paper/2025/hash/2b368455e832d2b1a60bcad8c4c6481f-Abstract-Conference.html) | Retrieve and iteratively cluster aliases. | Retrieval proposes pairs; LLM/rules adjudicate merge, split, and alias. |
| Judge and typed refine | [GraphJudge](https://aclanthology.org/2025.emnlp-main.554/), [GraphRefine](https://aclanthology.org/2026.acl-long.1353/) | Post-hoc quality control and typed edits. | Keep/fix/rewrite/delete/quarantine, with no self-approval. |
| Expert-efficient educational KG | [ACE](https://jedm.educationaldatamining.org/index.php/JEDM/article/view/737) | Rank likely prerequisite pairs for review. | Risk-ranked expert review of pedagogical edges. |
| Assessment design | [ECD](https://www.ets.org/research/policy_research_reports/publications/report/2003/hsgs.html) | Claims--evidence--task separation. | Treat rubrics as validated measurement artifacts. |

