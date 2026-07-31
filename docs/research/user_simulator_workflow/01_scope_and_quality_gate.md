# Scope and Quality Gate

## Research Question

How should a simulator turn a reviewed, node-level user Knowledge Map into a
natural-language answer that is locally licensed by the question, faithful to
the user's epistemic state, and useful for comparing diagnostic agents?

This question contains three different validity targets:

1. **State fidelity:** does the answer express the intended mastery,
   misconception, uncertainty, and ability boundary?
2. **Boundary safety:** does the answer avoid exposing labels, identifiers,
   scoring fields, or unrelated hidden nodes?
3. **Proxy validity:** do agent comparisons under simulation agree with matched
   comparisons under human interaction?

Naturalness is secondary. A fluent answer can fail all three targets.

## Counted-Paper Gate

A paper counts toward the requested main-conference pool only when it satisfies
all of the following:

- it is formally published in the main proceedings or an explicitly named
  conference track of ACL, EMNLP, NAACL, EACL, LREC-COLING, ICLR, ICML,
  NeurIPS, AAAI, KDD, SIGIR, WSDM, or UIST;
- an official publisher, conference, proceedings, or anthology page is
  available;
- it contains an empirical evaluation rather than only an opinion or position;
- it changes at least one SAGE decision: state representation, information
  scoping, plan-to-text separation, simulator evaluation, human linkage, or
  statistical design;
- its transfer limitation to knowledge-state simulation is explicit.

The current pool contains **39 counted papers**. Findings papers, workshops,
technical reports, and preprints are excluded from this count even when they
are discussed as boundary evidence.

## Relevance and Evidence Tiers

| Tier | Meaning | Permitted use |
| --- | --- | --- |
| A | Direct user, learner, persona, or behavioral simulation with human or real-data evaluation | May motivate a simulator mechanism or validation endpoint |
| B | Grounded dialogue, plan-to-text generation, or controllable generation with empirical evaluation | May motivate workflow structure, not human fidelity |
| C | Evaluator or verification methodology with human comparisons | May motivate measurement, not serve as sole ground truth |

Venue quality does not remove transfer risk. A Tier B control method cannot by
itself establish that a simulated learner behaves like a person.

## Deep-Reading Core

The following papers carry the largest argumentative load:

| Paper | Why it is core | Transfer boundary |
| --- | --- | --- |
| Shi et al. (EMNLP-IJCNLP 2019) | Separates direct simulator quality from downstream dialogue-system effects | Slot-based task dialogue is narrower than open knowledge diagnosis |
| Yoon et al. (NAACL 2024) | Decomposes generative simulation into measurable subtasks and exposes preference/popularity distortions | Conversational recommendation models preferences rather than mastery |
| Luo et al. (LREC-COLING 2024) | Separates answer generation from verification | An LLM verifier is not proof of semantic fidelity or non-leakage |
| Wu et al. (ACL 2025) | Shows helpful LLMs overstate low-ability students and uses structured cognitive prototypes | Classroom behaviors do not directly validate KnowAct's L0–L5 map |
| Scarlatos et al. (ACL 2026) | Evaluates simulated students on linguistic, behavioral, and cognitive dimensions against real tutoring data | The tasks and student population differ from KnowAct |
| Hu and Collier (ACL 2024) | Quantifies weak persona effects rather than assuming prompts create faithful people | Population/personality behavior is not node-level knowledge |
| Santurkar et al. (ICML 2023) | Shows demographic steering does not eliminate representational misalignment | Opinion distributions are not individual diagnostic answers |
| Dou et al. (EMNLP 2025) | Tests both message behavior and assistant-ranking agreement with human interactions | Reported domains do not include knowledge-map reconstruction |
| Aher et al. (ICML 2023) | Demonstrates both replication and systematic distortion in LLM human simulations | Mostly static study responses, not multi-turn diagnosis |
| Chiang et al. (ICML 2024) | Supports blinded, pairwise human comparison and rank uncertainty | Assistant preference is not simulator state fidelity |

## Excluded but Relevant Boundary Evidence

The following categories may inform future work but do not enter the count:

- arXiv-only user simulators and persona agents;
- ACL Findings role-playing papers;
- education workshops on simulated students;
- benchmark proposals without human or real-data comparison;
- journal papers outside the declared conference gate.

Any future addition must be placed in the correct category before it is cited as
scientific support.

## Claim Boundary

The literature supports the need to:

- decompose simulation rather than use one unconstrained role prompt;
- condition content on an explicit task-relevant state;
- separate content planning from surface realization;
- measure overstatement, understatement, uncertainty, and misconception;
- compare simulator conclusions with matched human conclusions.

It does **not** establish that the current SAGE implementation is already
faithful. That is the purpose of the held-out, blinded, nested validation
protocol.
