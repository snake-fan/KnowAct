# V1 simulator uses policy-derived structured answer blueprints

KnowAct v1 treats the `Simulator Answer Policy` as the simulator reasoning boundary that turns a grounded diagnostic situation into a structured `Simulator Answer Blueprint`. The policy may be LLM-backed, rule-based, or hybrid, but its output must parse into a strict schema; downstream generation renders that blueprint rather than deciding what the synthetic user knows or which evidence matters.

**Considered Options**

- Let the generator infer answer content directly from graph rubrics, map state, and evidence.
- Keep policy as a simple mastery-to-stance mapper.
- Make policy the reasoning layer and require structured answer blueprints.

**Consequences**

The simulator has a clearer reasoning boundary and can use LLM judgement without exposing raw reviewed maps, mastery labels, hidden evidence ids, or prompt-prose decisions to generation. A hidden `Simulator Policy Decision Trace` may record node ids, mastery labels, evidence refs, selected rubric text, and policy metadata for benchmark-author audit, while the downstream `Simulator Answer Blueprint` remains de-identified. There is no separate post-generation validation agent: the generator receives only the de-identified blueprint, visible dialogue, and an optional style hint. Failed or malformed generation may retry from the same blueprint before safe fallback, while unsafe or contradictory blueprints retry or fall back at the policy layer.
