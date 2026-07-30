# Top-Conference Writing Analysis for KnowAct

This note records the writing sample used for the argument-level revision of the paper. The goal was not to imitate surface phrasing, but to study how strong benchmark papers establish a construct, turn limitations of prior evaluation into design requirements, and connect each component to an interpretable claim.

## Sample

The sample contains 24 accepted papers from ICLR, NeurIPS, ICML/COLM, ACL-family main conferences, KDD, and LREC-COLING.

1. [Revisiting the Evaluation of Theory of Mind through Question Answering](https://aclanthology.org/D19-1598/) — EMNLP-IJCNLP 2019
2. [Understanding Social Reasoning in Language Models with Language Models (BigToM)](https://proceedings.neurips.cc/paper_files/paper/2023/hash/2b9efb085d3829a2aadffab63ba206de-Abstract-Datasets_and_Benchmarks.html) — NeurIPS 2023
3. [FANToM](https://aclanthology.org/2023.emnlp-main.890/) — EMNLP 2023
4. [OpenToM](https://aclanthology.org/2024.acl-long.466/) — ACL 2024
5. [ToMBench](https://aclanthology.org/2024.acl-long.847/) — ACL 2024
6. [SOTOPIA](https://openreview.net/forum?id=mM7VurbA4r) — ICLR 2024
7. [AgentSense](https://aclanthology.org/2025.naacl-long.257/) — NAACL 2025
8. [LaMP](https://aclanthology.org/2024.acl-long.399/) — ACL 2024
9. [PERSONAMEM](https://openreview.net/forum?id=6ox8XZGOqP) — COLM 2025
10. [LongTutor](https://aclanthology.org/2026.acl-long.1371/) — ACL 2026
11. [Deep Knowledge Tracing](https://proceedings.neurips.cc/paper_files/paper/2015/hash/bac9162b47c56fc8a4d2a519803d51b3-Abstract.html) — NeurIPS 2015
12. [Context-Aware Attentive Knowledge Tracing](https://dl.acm.org/doi/10.1145/3394486.3403282) — KDD 2020
13. [DuetSim](https://aclanthology.org/2024.lrec-main.481/) — LREC-COLING 2024
14. [SimulatorArena](https://aclanthology.org/2025.emnlp-main.1786/) — EMNLP 2025
15. [Extract, Define, Canonicalize](https://aclanthology.org/2024.emnlp-main.548/) — EMNLP 2024
16. [SAC-KG](https://aclanthology.org/2024.acl-long.238/) — ACL 2024
17. [KGGen](https://proceedings.neurips.cc/paper_files/paper/2025/hash/2b368455e832d2b1a60bcad8c4c6481f-Abstract-Conference.html) — NeurIPS 2025
18. [MINT](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8a0d3ae989a382ce6e50312bc35bf7e1-Abstract-Conference.html) — ICLR 2024
19. [AgentBench](https://proceedings.iclr.cc/paper_files/paper/2024/hash/e9df36b21ff4ee211a8b71ee8b7e9f57-Abstract-Conference.html) — ICLR 2024
20. [WebArena](https://openreview.net/forum?id=rmiwIL98uQ) — ICLR 2024
21. [SWE-bench](https://openreview.net/forum?id=VTF8yNQM66) — ICLR 2024
22. [AgentBoard](https://proceedings.neurips.cc/paper_files/paper/2024/hash/877b40688e330a0e2a3fc24084208dfa-Abstract-Datasets_and_Benchmarks_Track.html) — NeurIPS 2024
23. [OSWorld](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5d413e48f84dc61244b6be550f1cd8f5-Abstract-Datasets_and_Benchmarks_Track.html) — NeurIPS 2024
24. [AppWorld](https://aclanthology.org/2024.acl-long.850/) — ACL 2024

## Recurring Argument Patterns

### 1. Define a measurement failure, not merely an uncovered topic

Strong introductions explain why an existing score cannot identify the target capability. For KnowAct, the gap is not simply that prior work is non-interactive. Static ToM tasks remove evidence acquisition from the tested policy, while holistic interactive outcomes can be achieved without an accurate user model.

### 2. Turn each design choice into a response to an alternative explanation

A public graph makes the hypothesis space shared; a hidden map makes the target identifiable; a fixed budget makes question choice consequential; a visibility boundary blocks leakage; non-adaptive controls test whether interaction alone explains performance; deterministic scoring avoids evaluator-model confounds.

### 3. Separate the construct from its operationalization

The paper should state that functional ToM is an operational claim about infer–update–act behavior. It should not imply a human-like cognitive mechanism. The graph, simulator, and working map are measurement instruments, not a theory of human cognition.

### 4. Synthesize related work by unresolved axis

Related Work should compare what evidence is supplied, who selects it, whether the latent state is explicit, and what is scored. Paper-by-paper summaries are useful only when they establish one of these contrasts.

### 5. Present experiments as discriminating tests

Each comparison should say which explanation it rules in or out. Adaptive versus fixed policies tests state-conditioned action; working-map ablation tests explicit state maintenance; simulator variation tests ranking dependence; matched human episodes test external validity.

### 6. Interpret success conservatively

Endpoint accuracy alone supports a weaker claim than adaptive gains with evidence-backed traces. The discussion should distinguish reconstruction, adaptive acquisition, simulator robustness, and transfer to humans instead of treating them as one result.

## Revision Rule

Main-text implementation detail is retained only when it establishes validity, comparability, or auditability. Operational chronology, schemas, retry behavior, and full authoring stages belong in the appendices.
