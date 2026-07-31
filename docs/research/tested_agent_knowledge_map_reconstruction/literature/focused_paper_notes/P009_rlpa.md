# P009 — [RLPA](https://proceedings.neurips.cc/paper_files/paper/2025/hash/2fbc1ea60e215275e823c86338417162-Abstract-Conference.html)

**Zhao et al., NeurIPS 2025. Reading depth: D2.**

## Contribution

Frames multi-turn personalized alignment as an interaction process with explicit inferred profiles and
separate rewards for profile accuracy and profile-aligned responses. It compares prompting, retrieval,
supervised, preference, and reinforcement-learning variants.

## KnowAct transfer

Keep reconstruction quality independent from downstream response/action quality so the agent cannot
hide a wrong profile behind a plausible answer.

## Do not transfer

Profile slots, simulator construction, and reward models need separate validation for graph-indexed
knowledge states and agent-selected diagnostic questions.
