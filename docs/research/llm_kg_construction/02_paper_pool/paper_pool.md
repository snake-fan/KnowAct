# Focused Paper Pool

## Core pool

| ID | Year | Paper | Contribution used by KnowAct | Important limitation |
|---|---:|---|---|---|
| P001 | 2024 | [EDC](https://aclanthology.org/2024.emnlp-main.548/) | Extract--define--canonicalize; schema retrieval. | Factual triples, not diagnostic concepts. |
| P002 | 2024 | [SPIRES / OntoGPT](https://doi.org/10.1093/bioinformatics/btae104) | Schema-first extraction with LinkML and ontology grounding. | Biomedical orientation and schema dependence. |
| P003 | 2024 | [PiVe](https://aclanthology.org/2024.findings-acl.400/) | Independent iterative verification and corrective feedback. | Verification emphasizes missing graph content. |
| P004 | 2024 | [SAC-KG](https://aclanthology.org/2024.acl-long.238/) | Generator--verifier--pruner roles and precision-first expansion. | Recall is difficult to establish at web scale. |
| P005 | 2025 | [KGGen](https://proceedings.neurips.cc/paper_files/paper/2025/hash/2b368455e832d2b1a60bcad8c4c6481f-Abstract-Conference.html) | Separate entity/relation passes and iterative clustering. | Generic entities are unlike curricular concepts. |
| P006 | 2025 | [KARMA](https://proceedings.neurips.cc/paper_files/paper/2025/hash/517f9b9c227b9dd51dba4560f37165ed-Abstract-Conference.html) | Specialized roles, conflict resolution, provenance at scale. | Many-agent design is not itself causal evidence. |
| P007 | 2025 | [GraphJudge](https://aclanthology.org/2025.emnlp-main.554/) | Entity-centric denoising and a trained triple judge. | Binary filtering can lower coverage. |
| P008 | 2026 | [GraphRefine](https://aclanthology.org/2026.acl-long.1353/) | Error taxonomy and delete/edit/rewrite repair actions. | Triple-level factual scope. |
| P009 | 2022 | [GenIE](https://aclanthology.org/2022.naacl-main.342/) | Constrained generation under a fixed schema. | Fixed schemas limit open discovery. |
| P010 | 2024 | [GoLLIE](https://openreview.net/forum?id=Y3wpuxd7u9) | Annotation guidelines as executable extraction instructions. | IE guideline following, not end-to-end KG review. |
| P011 | 2024 | [ACE](https://jedm.educationaldatamining.org/index.php/JEDM/article/view/737) | Rank candidate prerequisite pairs for expert labeling. | Assumes a concept inventory. |
| P012 | 2003 | [Evidence-Centered Design](https://www.ets.org/research/policy_research_reports/publications/report/2003/hsgs.html) | Separates claims about competence, evidence, and diagnostic tasks. | Not a KG construction method. |
| P013 | 1995 | [Competency Questions](https://doi.org/10.1007/978-0-387-34847-6_3) | Scope an ontology by the questions it must answer. | Requires domain-specific author judgment. |

## Supporting standards

- [SHACL](https://www.w3.org/TR/shacl/) for machine-checkable graph constraints.
- [PROV-O](https://www.w3.org/TR/prov-o/) as a vocabulary for source and activity provenance.
- [ALCE](https://aclanthology.org/2023.emnlp-main.398/) for the distinction between citation correctness and citation completeness.

## Selection caveat

This pool is a decision-focused review, not a systematic review. Reported performance is not compared directly across papers because datasets, graph semantics, models, and recall denominators differ.

