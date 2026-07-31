# SAGE User-Simulator Workflow Research Package

> Status: literature audit and preregistration-oriented design package.
> Last updated: 2026-07-31.

This package supports the design and validation of the KnowAct user simulator.
It does not claim that the simulator is already human-faithful.

The proposed workflow name is:

> **SAGE — Scoped Answer Generation from Epistemic State**
> 基于认知状态的作用域受限回答生成

The package follows the research chain expected by KnowAct:

```text
current implementation
  -> quality-gated literature evidence
  -> limitations and alternative explanations
  -> falsifiable workflow design
  -> simulator and human validation
```

## Files

- [`01_scope_and_quality_gate.md`](01_scope_and_quality_gate.md): inclusion
  rules, venue gate, evidence tiers, and claim boundary.
- [`02_reviewed_paper_pool.md`](02_reviewed_paper_pool.md): 39 formally
  published main-conference papers with official links, empirical evidence,
  transfer limits, and concrete design uses.
- [`03_evidence_synthesis_and_sage.md`](03_evidence_synthesis_and_sage.md):
  evidence synthesis, formal workflow, alternatives, and ablations.
- [`../../../experiments/02_simulator_human_validity/`](../../../experiments/02_simulator_human_validity/README.md):
  canonical held-out human validation, proxy-validity protocol, and execution
  materials.

## Reading Rule

The paper pool is not a vote. A paper influences SAGE only when its venue,
empirical support, and transfer limit have been recorded. Findings papers,
workshops, and unreviewed preprints may be useful boundary evidence, but they do
not count toward the 39-paper main-conference pool.

## Claim Labels

- **Implemented fact:** observable in the current code or executable contract.
- **Literature-supported motivation:** a design choice transferred from prior
  evidence, with its transfer limit stated.
- **Research hypothesis:** a claim that still requires the frozen validation
  protocol.

SAGE is currently a name for the implemented workflow and its validation
contract. It is not yet evidence of human fidelity, non-leakage under
adversarial prompting, or preservation of agent rankings.
