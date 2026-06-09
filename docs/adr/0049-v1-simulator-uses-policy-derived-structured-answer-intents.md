# V1 simulator uses policy-derived structured answer intents

KnowAct v1 treats the `Simulator Answer Policy` as the simulator reasoning boundary that turns a grounded diagnostic situation into a structured `Simulator Answer Intent`. The policy may be LLM-backed, rule-based, or hybrid, but its output must parse into a strict schema; downstream expression and generation layers render that decision rather than deciding what the synthetic user knows or which evidence matters.

**Considered Options**

- Let the expression or generator layer infer answer content directly from graph rubrics, map state, and evidence.
- Keep policy as a simple mastery-to-stance mapper.
- Make policy the reasoning layer and require structured answer intents.

**Consequences**

The simulator has a clearer reasoning boundary and can use LLM judgement without exposing raw reviewed maps, mastery labels, hidden evidence ids, or prompt-prose decisions to generation. A hidden `Simulator Policy Decision Trace` may record node ids, mastery labels, evidence refs, selected rubric text, and policy metadata for benchmark-author audit, while the downstream `Simulator Answer Intent` remains de-identified. Validation failures should feed bounded regeneration: wording or coverage failures retry generation from the same intent, while unsafe or contradictory intents retry or fall back at the policy layer.
