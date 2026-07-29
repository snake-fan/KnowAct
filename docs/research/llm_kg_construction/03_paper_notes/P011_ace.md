# P011 — [ACE](https://jedm.educationaldatamining.org/index.php/JEDM/article/view/737)

**Aytekin and Saygın, Journal of Educational Data Mining 2024.**

## Problem

Experts cannot feasibly label every possible prerequisite pair in an educational concept inventory.

## Method

ACE scores and ranks pairs using semantic representations, asks experts about high-value candidates, and exploits graph inferences during iterative construction.

## Evidence

The study reports accurate graphs, reduced expert effort on benchmark data, and a downstream study in which prerequisite ordering relates to learner outcomes.

## Limitation

ACE begins with concepts already identified; its prerequisite meaning and inference policy must be aligned with KnowAct before reuse.

## KnowAct transfer

Use high-recall pair ranking and risk-prioritized expert review. Do not automatically materialize transitive prerequisite edges in the benchmark graph.

