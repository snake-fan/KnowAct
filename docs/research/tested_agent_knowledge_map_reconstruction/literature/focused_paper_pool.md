# Focused Paper Pool

> Supplementary 14-paper view. These local `P001`–`P014` entries must be reconciled against
> [`../02_reviewed_paper_pool.md`](../02_reviewed_paper_pool.md) before supporting a canonical method
> or empirical claim. Do not add 14 to the canonical 41-paper count.

The role column states why a paper remains in the pool. `D2` means its official full text has been
audited for the indicated transfer; `D1` means the archival record and central evidence are verified,
but detailed experimental claims are not yet cleared for use.

| ID | Paper | Venue | Depth | Primary role in KnowAct | Critical transfer boundary |
|---|---|---|---|---|---|
| P001 | [Deep Knowledge Tracing](https://proceedings.neurips.cc/paper_files/paper/2015/hash/bac9162b47c56fc8a4d2a519803d51b3-Abstract.html) | NeurIPS 2015 | D2 | sequential latent-state baseline | passive item responses; no explicit scored full map or active acquisition |
| P002 | [pyKT](https://proceedings.neurips.cc/paper_files/paper/2022/hash/75ca2b23d9794f02a92449af65a57556-Abstract-Datasets_and_Benchmarks.html) | NeurIPS D&B 2022 | D2 | leakage-safe KT evaluation and standardized comparisons | next-response prediction differs from full-map reconstruction |
| P003 | [BOBCAT](https://www.ijcai.org/proceedings/2021/332) | IJCAI 2021 | D2 | budgeted informative-question selection | assumes a calibrated fixed item bank and historical response data |
| P004 | [FACD](https://www.ijcai.org/proceedings/2025/648) | IJCAI 2025 | D2 | early-turn diagnosis and cold-start analysis | binary item responses and collaborative training data, not open dialogue |
| P005 | [LongTutor](https://aclanthology.org/2026.acl-long.1371/) | ACL 2026 | D2 | evidence–diagnosis–action decomposition and expert annotation | passive historical logs; evidence is not agent-selected |
| P006 | [ParLD](https://ojs.aaai.org/index.php/AAAI/article/view/40736) | AAAI 2026 | D1 | turn-level interpretation and explicit cognitive-state update | component multiplicity is not evidence that multi-agent design is necessary |
| P007 | [ScaffoldLM](https://aclanthology.org/2026.acl-long.325/) | ACL 2026 | D2 | assessment-driven memory and plan–state–action control loop | synthetic math tutoring and evaluator-dependent quality, not full-map reconstruction accuracy |
| P008 | [PENGUIN / RAISE](https://proceedings.neurips.cc/paper_files/paper/2025/hash/8c2bb821410066459be64d03a4dc5719-Abstract-Conference.html) | NeurIPS 2025 | D2 | selective user-information acquisition, cost, and abstention | fixed context attributes and a safety outcome, not graph mastery |
| P009 | [RLPA](https://proceedings.neurips.cc/paper_files/paper/2025/hash/2fbc1ea60e215275e823c86338417162-Abstract-Conference.html) | NeurIPS 2025 | D2 | separate profile-reconstruction and response rewards | simulated slot profiles and response actions, not diagnostic graph probes |
| P010 | [PERSONAMEM](https://openreview.net/forum?id=6ox8XZGOqP) | COLM 2025 | D1 | evolving profiles and long-history failure modes | passive selection from supplied histories; no active information acquisition |
| P011 | [SimulatorArena](https://aclanthology.org/2025.emnlp-main.1786/) | EMNLP 2025 | D1 | human–simulator behavior and ranking agreement | two tasks do not validate KnowAct's simulator automatically |
| P012 | [τ-bench](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html) | ICLR 2025 | D2 | deterministic end-state evaluation and repeated-run reliability | evaluates tool-use goals, not latent user-state estimates |
| P013 | [AgentBoard](https://proceedings.neurips.cc/paper_files/paper/2024/hash/877b40688e330a0e2a3fc24084208dfa-Abstract-Datasets_and_Benchmarks_Track.html) | NeurIPS D&B 2024 | D2 | process metrics beyond final success | human-annotated subgoals and generic environment progress are not diagnostic belief quality |
| P014 | [BigToM](https://proceedings.neurips.cc/paper_files/paper/2023/hash/2b9efb085d3829a2aadffab63ba206de-Abstract-Datasets_and_Benchmarks.html) | NeurIPS D&B 2023 | D2 | causal templates, control conditions, and human quality checks | static supplied evidence; no active querying or persistent user map |

## Supporting citations, not method anchors

FANToM, SOTOPIA, and LaMP remain useful for positioning conversational Theory of Mind, interactive
social evaluation, and passive profile retrieval. They are deliberately not used to enlarge the core
method argument because they do not resolve a currently uncovered design decision.
