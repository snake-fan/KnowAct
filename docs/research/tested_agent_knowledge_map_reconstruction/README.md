# Tested Agent Knowledge-Map Reconstruction Research

## Status

This is the canonical research package for KnowAct tested-agent Knowledge-Map reconstruction. It
records the literature evidence, method hypotheses, experimental design, and implementation contract
for a tested agent that reconstructs a user's node-level Knowledge Map through finite-turn dialogue.

The central claim is deliberately narrow:

- The reviewed Authored Knowledge Graph is fixed and visible to the tested agent.
- The hidden object is the user's mastery state on those graph nodes.
- The agent asks diagnostic questions, updates evidence-backed beliefs, and submits a full-graph reconstruction.
- The proposed method is a literature-motivated, testable design. It is **not** called the best method before the registered comparison and ablation study is run.

Paper source remains under `paper/`. This package links the broader paper method to the narrower
experimental implementation so their status cannot drift into separate research roots.

The executable reconstruction study is maintained separately in
[`../../../experiments/03_agent_reconstruction/`](../../../experiments/03_agent_reconstruction/README.md).
This research package provides its literature and method basis; it is not the
result directory.

## Reading order

1. [Scope and quality gate](01_scope_and_quality_gate.md)
2. [Reviewed paper pool](02_reviewed_paper_pool.md)
3. [Evidence synthesis and research gap](03_evidence_synthesis.md)
4. [MapProbe and ECDA method relationship](method/README.md)
5. [Evidence-Calibrated Diagnostic Agent design](04_agent_design.md)
6. [Baselines and ablation plan](05_baselines_and_ablations.md)
7. [Implementation contract](06_implementation_contract.md)
8. [Supplementary literature artifacts](literature/README.md)

## Deliverables

| Deliverable | Result |
| --- | --- |
| Top-venue literature review | 41 formally published papers passed the venue gate; 27 are direct evidence and 14 are supporting mechanism/evaluation evidence. |
| Quality audit | Every counted paper has venue verification, relevance tier, evidence note, limitation, and design use. |
| Agent design | ECDA: evidence likelihood extraction, checkpoint-safe belief update, deterministic risk-aware question selection, and evidence-backed final projection. |
| Baselines | Fixed bank, seeded random bank, LLM bank selection, existing Simple LLM, passive reconstruction, and an oracle ceiling. |
| Ablations | Component, information, objective, inference, robustness, budget, and model-family ablations with paired evaluation. |
| Code | Typed belief, candidate utility, prompt/parser, tested-agent implementation, runtime wiring, and tests. |
| Supplementary artifacts | Earlier 14-paper focused notes, field maps, machine-readable reports, and HTML visualization retained under `literature/` without being added to the canonical audited count. |

## Terminology guardrail

“Knowledge graph reconstruction” is ambiguous in the literature. In KnowAct this work does **not** create or repair graph nodes and edges. It reconstructs a user-specific Knowledge Map over a reviewed graph. Graph authoring remains a separate benchmark-author workflow.

## Method names

- **Knowledge-Map Reconstruction Agent** names the tested-agent research role.
- **MapProbe** names the full paper-level evidence–belief–probe design.
- **ECDA** names the current experimental implementation of a narrower subset of MapProbe.

ECDA implements per-node L0-L5 marginal beliefs, model-proposed answer likelihoods, deterministic
Bayesian-style updates, and deterministic selection among multiple model-proposed question candidates.
It does not yet implement MapProbe's direct/indirect evidence ledger, typed belief propagation,
independent question verifier, or calibrated early-stopping rule.

## Current implementation boundary

The implementation adds an experimental `evidence_calibrated_agent` behind the existing `TestedAgent`
protocol. It preserves the tested-agent visibility boundary and checkpoint persistence. This is an
implemented research mechanism, not evidence of comparative benefit. The fixed/random bank policies
are reusable experimental components, but are not registered as formal runtime agent kinds until an
immutable, versioned expert question-bank binding is added to the Episode Manifest.
