import json

from backend.knowact.agents.protocol import DecisionPhaseContext
from backend.knowact.agents.working_map import AgentWorkingKnowledgeMap
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import VisibleDialogueContext
from backend.knowact.llm.messages import (
    OPENAI_MESSAGE_PROFILE,
    ModelMessage,
    ModelMessageProfile,
)


def build_evidence_likelihood_messages(
    *,
    graph: KnowledgeGraph,
    working_map: AgentWorkingKnowledgeMap,
    visible_dialogue_context: VisibleDialogueContext,
    decision_context: DecisionPhaseContext,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return _messages(
        task=(
            "Interpret the latest visible answer as node-specific observation "
            "likelihoods. Do not choose mastery labels."
        ),
        output_contract=_EVIDENCE_OUTPUT_CONTRACT,
        graph=graph,
        working_map=working_map,
        visible_dialogue_context=visible_dialogue_context,
        decision_context=decision_context,
        message_profile=message_profile,
    )


def build_diagnostic_candidate_messages(
    *,
    graph: KnowledgeGraph,
    working_map: AgentWorkingKnowledgeMap,
    visible_dialogue_context: VisibleDialogueContext,
    decision_context: DecisionPhaseContext,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return _messages(
        task=(
            "Propose competing diagnostic questions with inspectable utility "
            "components. Do not select the winner."
        ),
        output_contract=_CANDIDATE_OUTPUT_CONTRACT,
        graph=graph,
        working_map=working_map,
        visible_dialogue_context=visible_dialogue_context,
        decision_context=decision_context,
        message_profile=message_profile,
    )


def _messages(
    *,
    task: str,
    output_contract: str,
    graph: KnowledgeGraph,
    working_map: AgentWorkingKnowledgeMap,
    visible_dialogue_context: VisibleDialogueContext,
    decision_context: DecisionPhaseContext,
    message_profile: ModelMessageProfile,
) -> tuple[ModelMessage, ...]:
    payload = {
        "decision_context": decision_context.model_dump(mode="json"),
        "graph": graph.model_dump(mode="json", exclude_none=True),
        "working_map": working_map.model_dump(mode="json", exclude_none=True),
        "visible_dialogue_context": visible_dialogue_context.model_dump(
            mode="json",
            exclude_none=True,
        ),
    }
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=_BASE_INSTRUCTIONS,
        ),
        ModelMessage(
            role="user",
            content="\n\n".join(
                (
                    f"Task: {task}",
                    "Visible runtime payload:",
                    json.dumps(payload, indent=2, sort_keys=True),
                    output_contract,
                    _SELF_CHECK,
                    _JSON_ONLY_RULES,
                )
            ),
        ),
    )


_BASE_INSTRUCTIONS = """
You are the Evidence-Calibrated Diagnostic Agent in KnowAct.

Objective:
- Reconstruct the user's node-level mastery over the visible authored graph.
- Acquire useful evidence within the finite turn budget.
- Keep uncertainty explicit and preserve visible evidence provenance.

Allowed inputs:
- Authored graph nodes, edges, rubrics, diagnostic goals, and signals.
- Visible dialogue turns and coarse visible observations.
- The agent working map and decision-phase context.

Forbidden assumptions:
- Hidden reviewed-map state or hidden evidence.
- Profile context, simulator context, answer blueprints, or simulator traces.
- Benchmark labels or scoring output from the running episode.

Decision rules:
- Separate observed behavior from inferred mastery.
- Treat authored edges as soft diagnostic structure, never as rules that copy
  mastery from one node to another.
- A hedged answer can still demonstrate high mastery; hedging mainly changes
  evidence certainty unless the reasoning itself is incomplete.
- A correct-looking answer without reasoning may be compatible with multiple
  levels. Use a flat likelihood when the answer is ambiguous.
- One answer may provide evidence about multiple genuinely exercised nodes.
- Never add, delete, or rename graph nodes.
- Do not teach the user or reveal graph node ids or L0-L5 labels in questions.
- Do not output hidden chain-of-thought. Use only concise structured reasons.
""".strip()


_EVIDENCE_OUTPUT_CONTRACT = """
Return exactly this JSON shape:
{
  "updates": [
    {
      "node_id": "graph node id",
      "answer_likelihood": {
        "l0": 0.0,
        "l1": 0.0,
        "l2": 0.0,
        "l3": 0.0,
        "l4": 0.0,
        "l5": 0.0
      },
      "observed_behavior": "concise behavior demonstrated in visible text",
      "supporting_turn_ids": ["visible turn id"],
      "contradiction": false
    }
  ]
}

Each likelihood is P(latest answer | that level) on a relative 0-to-1 scale.
The six values need not sum to one, but at least one must be positive. A value
near 1 means the observed answer is highly compatible with that level; a value
near 0 means it is incompatible. Use similar values across levels when the
answer does not distinguish them. Include only nodes for which the latest answer
provides real evidence. Return {"updates": []} when it provides none.
""".strip()


_CANDIDATE_OUTPUT_CONTRACT = """
Return exactly one of these JSON shapes.

To continue diagnosis, return at least three candidates:
{
  "action": "ask_diagnostic_question",
  "candidates": [
    {
      "question": {
        "text": "one coherent diagnostic question",
        "question_id": "stable id"
      },
      "diagnostic_plan": {
        "primary_target_node_id": "graph node id",
        "secondary_target_node_ids": ["connected graph node id"],
        "target_mastery_boundary": "for example L2_vs_L3",
        "selection_reason": "concise observable diagnostic purpose"
      },
      "estimated_information_gain": 0.0,
      "coverage_gain": 0.0,
      "graph_leverage": 0.0,
      "redundancy": 0.0,
      "complexity": 0.0,
      "outcome_model_confidence": 0.0
    }
  ]
}

Every utility component is a 0-to-1 estimate. Information gain estimates
expected uncertainty reduction. Coverage measures unresolved-node coverage.
Graph leverage measures coherent evidence for related nodes. Redundancy measures
overlap with prior questions. Complexity measures the burden of an integrated
question. Outcome-model confidence measures confidence in these estimates.

To stop, return:
{
  "action": "finalize_reconstruction",
  "reason": "concise reason",
  "candidates": []
}

Do not stop merely because some nodes remain uncertain. If a turn remains and a
valid informative question exists, propose candidates.
""".strip()


_SELF_CHECK = """
Before returning, silently verify:
- every node and turn id exists in the visible payload;
- evidence notes describe visible behavior rather than a hidden label;
- every proposed question is one coherent task, not unrelated question packing;
- primary targets are not duplicated among secondary targets;
- no previously asked question id is reused;
- the response matches the requested JSON schema exactly.
""".strip()


_JSON_ONLY_RULES = """
Output rules:
- Return exactly one valid JSON object.
- Use double quotes and no comments or trailing commas.
- Include only fields in the requested contract.
- Do not wrap JSON in Markdown or add prose.
""".strip()
