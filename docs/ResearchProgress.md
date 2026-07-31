# Research Progress

Current experiment status is maintained in
[`../experiments/README.md`](../experiments/README.md).

The repository now separates research evidence from experiment execution:

- literature review and method synthesis remain in `docs/research/`;
- Experiment 01 stores KG expert-validation design, forms, and result template
  under `experiments/01_kg_scientific_validity/`;
- Experiment 02 stores SAGE human-validity design, participant/rater materials,
  held-out question sets, and result template under
  `experiments/02_simulator_human_validity/`;
- Experiment 03 stores the tested-agent reconstruction design and generated
  Episode Run artifacts under `experiments/03_agent_reconstruction/`.

Do not duplicate mutable experiment status in this file. Update the relevant
experiment README when a design is frozen, a material passes pilot review, a
run completes, or a result is analyzed.
