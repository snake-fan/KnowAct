# P013 — [AgentBoard](https://proceedings.neurips.cc/paper_files/paper/2024/hash/877b40688e330a0e2a3fc24084208dfa-Abstract-Datasets_and_Benchmarks_Track.html)

**Ma et al., NeurIPS Datasets and Benchmarks 2024. Reading depth: D2.**

## Contribution

Adds a progress-rate metric and trajectory-level analysis for multi-turn agents in partially observable
environments, addressing the blindness of final-success-only evaluation. The paper validates progress
scores against human ratings on sampled trajectories and analyzes framework choices.

## KnowAct transfer

Report reconstruction quality after each turn and retain target plans, evidence updates, and failure
types for process analysis.

## Do not transfer

Some environments require human-annotated subgoals. Generic milestones are not a substitute for
calibrated node beliefs, so the progress metric must be redesigned for full-map error.
