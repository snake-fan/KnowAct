# Scope and Paper Quality Gate

## 1. Research question

Given a visible reviewed Knowledge Graph, a finite turn budget, and only the visible dialogue history, how should a tested agent select diagnostic questions and reconstruct a calibrated, evidence-backed mastery state for every graph node?

The target is not ordinary next-answer prediction. It combines four problems:

1. semantic interpretation of open-ended answers;
2. uncertain node-level state estimation;
3. active selection of the next diagnostic question;
4. full-map evaluation under a strict hidden-information boundary.

## 2. Scope boundaries

### Included

- knowledge tracing and cognitive diagnosis;
- computerized adaptive testing and active question selection;
- graph-aware and hierarchy-aware diagnosis;
- open-ended or language-mediated student modeling;
- LLM user profiling and iterative agent state updates;
- Theory-of-Mind benchmarks relevant to hidden-state inference;
- agent architecture, uncertainty, calibration, and active learning mechanisms.

### Excluded from the core claim

- domain Knowledge Graph extraction, completion, or ontology induction;
- tutoring-policy optimization whose primary objective is to teach rather than diagnose;
- recommendation or personalization without knowledge-state inference;
- papers available only as arXiv preprints;
- workshop papers, Findings papers, posters without a full archival paper, and venue status that could not be verified.

## 3. Quality gate applied before design use

A paper counts toward the required pool only if all mandatory gates pass.

| Gate | Pass condition | Why it matters |
| --- | --- | --- |
| G1 archival status | Official proceedings, ACL Anthology, OpenReview accepted-conference page, or publisher DOI confirms publication. | Prevents preprints and ambiguous submissions from being counted as top-conference evidence. |
| G2 venue quality | Main technical track or formal Datasets & Benchmarks track at NeurIPS, ICML, ICLR, ACL, EMNLP, AAAI, IJCAI, KDD, WWW, SIGIR, CIKM, CHI/UIST or an equivalently selective venue. | Venue name alone is not enough; track status matters. |
| G3 problem relevance | The paper contributes direct evidence for state diagnosis/question selection, or a clearly named supporting mechanism for interactive agents. | Prevents generic LLM-agent papers from being treated as direct KT evidence. |
| G4 empirical evidence | The official paper reports datasets/tasks, comparison evidence, and enough method detail to identify what was tested. | A method slogan without evaluation cannot justify a design choice. |
| G5 limitation audit | At least one transfer or validity limitation is recorded before the paper influences the design. | Stops benchmark-specific gains from becoming universal prescriptions. |

## 4. Evidence tiers

- **A — direct:** estimates per-concept knowledge, chooses diagnostic items, or models open-ended diagnostic evidence.
- **B — adjacent:** evaluates hidden mental-state inference, user profiling, or interactive agent state/action loops.
- **C — mechanism:** supplies a reusable uncertainty, information-gain, reflection, memory, or evaluation mechanism.

Only A/B papers may motivate the task formulation. C papers may motivate an implementation component but cannot establish effectiveness on KnowAct.

## 5. Empirical strength rubric

- **E3:** multiple real/public datasets or environments, competitive baselines, and ablation/calibration/human validation.
- **E2:** at least one substantive dataset or environment with comparisons, but incomplete calibration, human validation, or transfer evidence.
- **E1:** narrow case study or indirect task evidence; retained only as supporting context.

The audit does not rank papers by citation count. Citation count is age- and community-dependent and does not answer whether the evidence transfers to open-ended, full-map reconstruction.

## 6. Validity questions asked of every paper

1. Does it recover a knowledge state, or only predict the next response?
2. Are responses binary/ID-based or open-ended natural language?
3. Does the method actively choose questions, or passively consume a log?
4. Are concept relations observed, learned, or assumed?
5. Is uncertainty calibrated, merely represented, or absent?
6. Does evaluation measure the full latent map, only downstream accuracy, or a proxy?
7. Could information leakage, simulator coupling, or train/test preprocessing inflate results?
8. Is there an ablation that isolates the claimed component?

## 7. Decision rule

The design in this directory uses a paper only after recording its answers in the reviewed pool. Repeated mechanisms across independent paper families receive more design weight than a single reported leaderboard gain.

## 8. Rejected or non-counted examples

| Category | Decision | Reason |
| --- | --- | --- |
| ACL/EMNLP Findings-only ToM or KT papers | Not counted | Useful emerging evidence, but outside the predeclared main-track gate. |
| ICLR workshop AgentBoard | Not counted | Valuable evaluation ideas, but the retrieved record is an ICLR workshop poster rather than ICLR main conference. |
| Recent arXiv-only dialogue-KT methods | Not counted | Publication and peer-review status are not established. |
| Educational Advances in AI special-track papers | Not counted in the strict core unless the official page identifies the AAAI technical track | Avoids treating all AAAI-hosted tracks as equivalent evidence. |

## 9. What the quality gate does not prove

Passing the gate means a paper is credible enough to inform a hypothesis. It does not prove that its method transfers to KnowAct. That claim requires the baseline and ablation protocol in this directory, run on immutable Episode Manifests with independent statistical analysis.
