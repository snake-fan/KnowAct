# P001 — [Deep Knowledge Tracing](https://proceedings.neurips.cc/paper_files/paper/2015/hash/bac9162b47c56fc8a4d2a519803d51b3-Abstract.html)

**Piech et al., NeurIPS 2015. Reading depth: D2.**

## Contribution

Models a student's changing latent knowledge from sequential item interactions with a recurrent neural
network and evaluates future-response prediction on real student data.

## KnowAct transfer

Use it as the historical anchor for sequential belief revision and as motivation for a passive-history
baseline.

## Do not transfer

Prediction accuracy does not establish an explicit, calibrated full-map reconstruction. The method does
not choose observations and its latent vector is not directly the object KnowAct scores.
