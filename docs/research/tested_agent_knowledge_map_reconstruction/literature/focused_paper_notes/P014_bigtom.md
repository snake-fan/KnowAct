# P014 — [BigToM](https://proceedings.neurips.cc/paper_files/paper/2023/hash/2b9efb085d3829a2aadffab63ba206de-Abstract-Datasets_and_Benchmarks.html)

**Gandhi et al., NeurIPS Datasets and Benchmarks 2023. Reading depth: D2.**

## Contribution

Generates mental-state evaluations from causal templates, adds 25 control conditions, and compares
model inferences with human performance and human quality judgments.

## KnowAct transfer

Construct controls that remove the need for user-state inference or graph reasoning, then test whether
the same model advantage remains. Validate generated items with humans.

## Do not transfer

BigToM is static and supplies all evidence. It does not test selective questioning or a persistent
reconstructed user map.
