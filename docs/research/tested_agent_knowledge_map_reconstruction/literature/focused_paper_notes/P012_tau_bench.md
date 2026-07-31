# P012 — [τ-bench](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html)

**Yao et al., ICLR 2025. Reading depth: D2.**

## Contribution

Evaluates tool-using agents in dynamic simulated-user conversations with deterministic final database
checks and `pass^k` reliability over repeated trials.

## KnowAct transfer

Use deterministic hidden-map scoring, identical seeds across agents, repeated stochastic runs, and a
reliability statistic. Never report only the best run.

## Do not transfer

An externally verifiable database goal is not equivalent to an inferred latent mental state, so
KnowAct also needs calibration and evidence-validity measures.
