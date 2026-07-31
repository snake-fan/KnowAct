# P008 — [PENGUIN / RAISE](https://proceedings.neurips.cc/paper_files/paper/2025/hash/8c2bb821410066459be64d03a4dc5719-Abstract-Conference.html)

**Wu et al., NeurIPS 2025. Reading depth: D2.**

## Contribution

Defines personalized safety, adds context-rich and context-free benchmark variants, and proposes a
training-free agent that selects which user attributes to acquire under query cost and can abstain when
context is insufficient.

## KnowAct transfer

Score targets before generating their wording; measure quality–cost curves; include a sufficiency-based
stop or abstention decision; compare with simple acquisition heuristics.

## Do not transfer

Fixed user attributes and safety scores do not supply a likelihood model or graph-inference rule for
ordinal mastery.
