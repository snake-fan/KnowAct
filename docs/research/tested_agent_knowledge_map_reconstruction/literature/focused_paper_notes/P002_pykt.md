# P002 — [pyKT](https://proceedings.neurips.cc/paper_files/paper/2022/hash/75ca2b23d9794f02a92449af65a57556-Abstract-Datasets_and_Benchmarks.html)

**Liu et al., NeurIPS Datasets and Benchmarks 2022. Reading depth: D2.**

## Contribution

Standardizes implementations, datasets, preprocessing, and evaluation for representative deep
knowledge-tracing models. Its protocol audit shows that seemingly small evaluation choices can create
label leakage or incomparable results.

## KnowAct transfer

Freeze visibility, splitting, preprocessing, and aggregation rules; keep graph labels and hidden maps
outside all tested-agent prompts; pair episode seeds across methods.

## Do not transfer

Next-response prediction and question/KC conventions are not the same target as full-map mastery error.
