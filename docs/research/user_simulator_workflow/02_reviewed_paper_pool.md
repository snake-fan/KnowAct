# Reviewed Main-Conference Paper Pool

## Audit Summary

- Counted papers: **39**
- Tier A, direct simulation or construct evidence: **25**
- Tier B, workflow and controlled-generation evidence: **10**
- Tier C, evaluator and measurement evidence: **4**
- Publication gate: formal main-conference or named conference track
- Source gate: official anthology, proceedings, publisher, DOI, or conference page

The pool is deliberately broader than “user simulator” as a keyword. SAGE needs
evidence about user and student simulation, persona conditioning, grounded
dialogue, plan-to-text separation, controllable generation, and human-linked
evaluation.

## A. Direct Simulation and Construct Evidence

| ID | Paper and official source | Venue / tier | Empirical evidence | SAGE use and transfer limit |
| --- | --- | --- | --- | --- |
| P01 | [How to Build User Simulators to Train RL-based Dialog Systems](https://aclanthology.org/D19-1206/) | EMNLP-IJCNLP 2019 / A | Compares six simulators using direct automatic, direct human, and downstream evaluation | Requires both construct and downstream validation; slot-goal dialogue is narrower than epistemic answers |
| P02 | [Evaluating Conversational Recommender Systems via User Simulation](https://doi.org/10.1145/3394486.3403202) | KDD 2020 / A | Models preference and interaction, then compares simulated evaluation with human judgments | Motivates rank preservation; recommendation preference is not mastery |
| P03 | [UserSimCRS: A User Simulation Toolkit for Evaluating Conversational Recommender Systems](https://doi.org/10.1145/3539597.3573029) | WSDM 2023 / A | Implements configurable agenda, persona, satisfaction, and response components | Supports factorized configuration; toolkit evidence is domain-specific |
| P04 | [Evaluating Large Language Models as Generative User Simulators for Conversational Recommendation](https://aclanthology.org/2024.naacl-long.83/) | NAACL 2024 / A | Evaluates five decomposed simulation tasks and reports preference, diversity, and coherence failures | Direct support for component-level tests; preferences differ from knowledge states |
| P05 | [DuetSim: Building User Simulator with Dual Large Language Models for Task-Oriented Dialogues](https://aclanthology.org/2024.lrec-main.481/) | LREC-COLING 2024 / A | Separates response generation and verification; evaluates on task dialogue and human preference | Motivates separation; an LLM verifier cannot certify hidden-state safety |
| P06 | [USimAgent: Large Language Models for Simulating Search Users](https://doi.org/10.1145/3626772.3657963) | SIGIR 2024 / A | Models querying, clicking, and stopping behaviors in search sessions | Motivates action-level fidelity; search traces are not open-ended explanations |
| P07 | [On Generative Agents in Recommendation](https://doi.org/10.1145/3626772.3657844) | SIGIR 2024 / A | Evaluates profile-, memory-, and action-based recommendation agents against user behavior | Motivates state/action decomposition; recommendation actions do not validate mastery expression |
| P08 | [SimulatorArena: Are User Simulators Reliable Proxies for Multi-Turn Evaluation of AI Assistants?](https://aclanthology.org/2025.emnlp-main.1786/) | EMNLP 2025 / A | Compares simulated and human conversations, message behavior, ratings, and assistant rankings | Primary basis for matched rank validation; its tasks are not knowledge diagnosis |
| P09 | [Using Large Language Models to Simulate Multiple Humans and Replicate Human Subject Studies](https://proceedings.mlr.press/v202/aher23a.html) | ICML 2023 / A | Replicates several human studies and documents systematic deviations | Simulation can reproduce and distort; mostly static study responses |
| P10 | [SOTOPIA: Interactive Evaluation for Social Intelligence in Language Agents](https://openreview.net/forum?id=mM7VurbA4r) | ICLR 2024 / A | Compares role-play interactions among language agents and humans in open-ended social scenarios | Supports human-linked interactive evaluation; social goal completion is not epistemic-state fidelity |
| P11 | [Simulating Classroom Education with LLM-Empowered Agents](https://aclanthology.org/2025.naacl-long.520/) | NAACL 2025 / A | Evaluates multi-agent classroom simulation and student behavior | Supports educational-state conditioning; classroom ecology adds confounds absent from KnowAct |
| P12 | [Embracing Imperfection: Simulating Students with Diverse Cognitive Levels Using LLM-based Agents](https://aclanthology.org/2025.acl-long.488/) | ACL 2025 / A | Uses structured cognitive prototypes and evaluates diverse ability simulation | Direct support for epistemic prototypes and overperformance tests; prototype scale differs from L0–L5 |
| P13 | [SMART: Simulated Students Aligned with Item Response Theory for Question Difficulty Prediction](https://aclanthology.org/2025.emnlp-main.1274/) | EMNLP 2025 / A | Aligns simulated ability with item-response structure and real response data | Motivates ability calibration; item difficulty is narrower than free-text fidelity |
| P14 | [Simulated Students in Tutoring Dialogues: Substance or Illusion?](https://aclanthology.org/2026.acl-long.1960/) | ACL 2026 / A | Compares linguistic, behavioral, and cognitive fidelity against real tutoring dialogue | Direct warning against prompt-only simulation; population and task remain different |
| P15 | [Generating and Evaluating Tests for K-12 Students with Language Model Simulations](https://aclanthology.org/2023.emnlp-main.135/) | EMNLP 2023 / A | Uses language models to simulate responses and estimate assessment difficulty | Supports held-out diagnostic items; constrained K-12 tests differ from open answers |
| P16 | [Character-LLM: A Trainable Agent for Role-Playing](https://aclanthology.org/2023.emnlp-main.814/) | EMNLP 2023 / A | Trains and evaluates character-conditioned agents across roles and behaviors | Shows role consistency needs explicit evaluation; fictional character fidelity is not epistemic fidelity |
| P17 | [InCharacter: Evaluating Personality Fidelity in Role-Playing Agents through Psychological Interviews](https://aclanthology.org/2024.acl-long.102/) | ACL 2024 / A | Uses psychological interview instruments across characters and personality scales | Motivates construct-specific interviews; personality scales cannot replace knowledge rubrics |
| P18 | [Generative Agents: Interactive Simulacra of Human Behavior](https://doi.org/10.1145/3586183.3606763) | UIST 2023 / A | Ablates memory, reflection, and planning and evaluates perceived believability | Supports modular state-to-action design; believability is not individual state fidelity |
| P19 | [Whose Opinions Do Language Models Reflect?](https://proceedings.mlr.press/v202/santurkar23a.html) | ICML 2023 / A | Compares model opinions with demographic distributions and steering conditions | Warns that persona prompting does not remove misalignment; opinions differ from knowledge |
| P20 | [Quantifying the Persona Effect in LLM Simulations](https://aclanthology.org/2024.acl-long.554/) | ACL 2024 / A | Measures how much persona variables change simulated responses | Supports keeping Profile Context stylistic and secondary; population effects are not individual fidelity |
| P21 | [Sociodemographic Prompting is Not Yet an Effective Approach for Simulating Subjective Judgments](https://aclanthology.org/2025.naacl-short.71/) | NAACL 2025 / A | Tests demographic prompts against human subjective judgments | Adds a negative control for persona claims; short-paper scope and subjective tasks limit transfer |
| P22 | [Cultural Conditioning or Placebo? On the Effectiveness of Sociodemographic Prompting](https://aclanthology.org/2024.emnlp-main.884/) | EMNLP 2024 / A | Evaluates cultural and demographic conditioning across models and tasks | Motivates reporting conditioning effects, not assuming them; not about node-level mastery |
| P23 | [Personalizing Dialogue Agents: I Have a Dog, Do You Have Pets Too?](https://aclanthology.org/P18-1205/) | ACL 2018 / A | Introduces persona-conditioned dialogue and human evaluation | Establishes persona-conditioned realization; persona facts must not become knowledge evidence |
| P24 | [Wizard of Wikipedia: Knowledge-Powered Conversational Agents](https://openreview.net/forum?id=r1l73iRqKm) | ICLR 2019 / A | Grounds open dialogue in selected knowledge and evaluates human judgments | Supports selecting local evidence before generation; encyclopedic truth differs from user knowledge |
| P25 | [Towards Empathetic Open-domain Conversation Models](https://aclanthology.org/P19-1534/) | ACL 2019 / A | Conditions dialogue on situations and evaluates empathy and relevance | Supports separating context from realization; empathy does not establish epistemic fidelity |

## B. Workflow and Controlled-Generation Evidence

| ID | Paper and official source | Venue / tier | Empirical evidence | SAGE use and transfer limit |
| --- | --- | --- | --- | --- |
| P26 | [AnyTOD: A Programmable Task-Oriented Dialog System](https://aclanthology.org/2023.emnlp-main.1006/) | EMNLP 2023 / B | Uses explicit programs to constrain dialogue behavior across tasks | Supports inspectable intermediate plans; programs do not represent human cognition |
| P27 | [Symbolic Planning and Code Generation for Grounded Dialogue](https://aclanthology.org/2023.emnlp-main.460/) | EMNLP 2023 / B | Separates symbolic planning from grounded language generation | Supports blueprint-before-realization; task plans differ from mastery boundaries |
| P28 | [TOD-Flow: Modeling the Structure of Task-Oriented Dialogues](https://aclanthology.org/2023.emnlp-main.204/) | EMNLP 2023 / B | Learns and evaluates structured dialogue flows | Supports explicit stage contracts; flow correctness is not user fidelity |
| P29 | [Plan-and-Write: Towards Better Automatic Storytelling](https://ojs.aaai.org/index.php/AAAI/article/view/4726) | AAAI 2019 / B | Shows planning before realization can improve global coherence | Supports content/surface separation only; stories are not diagnostic answers |
| P30 | [Plug and Play Language Models](https://openreview.net/forum?id=U3uGMztyH5S2) | ICLR 2020 / B | Controls generated attributes without retraining the base model | Supports controllability as a design axis; attribute control is not state fidelity |
| P31 | [FUDGE: Controlled Text Generation With Future Discriminators](https://aclanthology.org/2021.naacl-main.276/) | NAACL 2021 / B | Steers generation with learned future discriminators | Motivates measurable generation constraints; discriminators need target-specific validation |
| P32 | [DExperts: Decoding-Time Controlled Text Generation with Experts and Anti-Experts](https://aclanthology.org/2021.acl-long.522/) | ACL 2021 / B | Controls style and toxicity at decoding time | Supports style/content separation; safety attributes are not epistemic states |
| P33 | [RARR: Researching and Revising What Language Models Say](https://aclanthology.org/2023.acl-long.910/) | ACL 2023 / B | Retrieves evidence and revises generated text while preserving intent | Motivates evidence-linked revision; external facts differ from hidden user evidence |
| P34 | [SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models](https://aclanthology.org/2023.emnlp-main.557/) | EMNLP 2023 / B | Detects factual inconsistency through sampled generations | Motivates stress tests, not a safety proof; self-consistency can preserve shared errors |
| P35 | [Self-Refine: Iterative Refinement with Self-Feedback](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html) | NeurIPS 2023 / B | Tests iterative self-feedback across generation tasks | Motivates bounded repair; more calls are not an explanation of fidelity |

## C. Evaluator and Measurement Evidence

| ID | Paper and official source | Venue / tier | Empirical evidence | SAGE use and transfer limit |
| --- | --- | --- | --- | --- |
| P36 | [G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment](https://aclanthology.org/2023.emnlp-main.153/) | EMNLP 2023 / C | Compares model-based rubric scores with human judgments | Supports structured secondary ratings; model judges cannot be primary human-fidelity evidence |
| P37 | [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html) | NeurIPS 2023 Datasets and Benchmarks / C | Studies judge agreement, biases, and pairwise assistant evaluation | Requires judge-bias audits; assistant quality is not simulator fidelity |
| P38 | [Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference](https://proceedings.mlr.press/v235/chiang24b.html) | ICML 2024 / C | Uses blinded pairwise human preferences and rank uncertainty | Supports blind source comparison and ranking intervals; preference is only one endpoint |
| P39 | [FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation](https://aclanthology.org/2023.emnlp-main.741/) | EMNLP 2023 / C | Decomposes claims into atomic supported units and compares evaluation methods | Supports claim-level leakage audits; user fidelity is not reducible to factuality |

## Cross-Paper Conclusions

1. No single paper validates SAGE as a complete workflow.
2. Direct simulator evidence consistently separates surface quality from
   task-relevant fidelity.
3. Educational studies make overperformance and erased misconceptions central
   failure modes.
4. Persona studies make style conditioning a hypothesis, not a substitute for
   reviewed epistemic state.
5. Human-linked ranking agreement is necessary when the simulator is used to
   compare tested agents.
6. Controlled-generation papers justify modularity and inspectability, not
   claims about human cognition.
