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


def build_assessment_update_messages(
    *,
    graph: KnowledgeGraph,
    working_map: AgentWorkingKnowledgeMap,
    visible_dialogue_context: VisibleDialogueContext,
    decision_context: DecisionPhaseContext,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=_BASE_INSTRUCTIONS,
        ),
        ModelMessage(
            role="user",
            content=_render_task_payload(
                task=(
                    "Update the Agent Working Knowledge Map from the latest "
                    "visible simulator answer."
                ),
                output_contract=_ASSESSMENT_OUTPUT_CONTRACT,
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=visible_dialogue_context,
                decision_context=decision_context,
            ),
        ),
    )


def build_next_action_messages(
    *,
    graph: KnowledgeGraph,
    working_map: AgentWorkingKnowledgeMap,
    visible_dialogue_context: VisibleDialogueContext,
    decision_context: DecisionPhaseContext,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=_BASE_INSTRUCTIONS,
        ),
        ModelMessage(
            role="user",
            content=_render_task_payload(
                task="Choose the next tested-agent action.",
                output_contract=_NEXT_ACTION_OUTPUT_CONTRACT,
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=visible_dialogue_context,
                decision_context=decision_context,
            ),
        ),
    )


def _render_task_payload(
    *,
    task: str,
    output_contract: str,
    graph: KnowledgeGraph,
    working_map: AgentWorkingKnowledgeMap,
    visible_dialogue_context: VisibleDialogueContext,
    decision_context: DecisionPhaseContext,
) -> str:
    payload = {
        "decision_context": decision_context.model_dump(mode="json"),
        "graph": graph.model_dump(mode="json", exclude_none=True),
        "working_map": working_map.model_dump(mode="json", exclude_none=True),
        "visible_dialogue_context": visible_dialogue_context.model_dump(
            mode="json",
            exclude_none=True,
        ),
    }
    return "\n\n".join(
        (
            f"Task: {task}",
            "Visible runtime payload:",
            json.dumps(payload, indent=2, sort_keys=True),
            output_contract,
            _JSON_ONLY_RULES,
        )
    )


_BASE_INSTRUCTIONS = """
You are the Simple LLM Agent baseline in KnowAct v1.

Use only the tested-agent-visible payload:
- Authored Knowledge Graph nodes and edges.
- Visible dialogue turns.
- The Agent Working Knowledge Map.
- Decision Phase Context.

Do not assume hidden reviewed-map state, hidden evidence, profile context,
simulator traces, answer blueprints, or benchmark labels. Do not teach or tutor
the user. Your role is active knowledge-state diagnosis: update supported
working judgments and choose one diagnostic question when allowed.

Working-map rules:
- Non-unknown assessments must cite one or more visible supporting_turn_ids.
- Non-unknown assessments need a concise assessment_note.
- Use "unknown" when the visible evidence does not support a judgment.
- You may infer indirectly from visible answers and visible graph relations,
  but keep assessment_note concise and cite the visible turn that supports it.
- One answer may support updates to multiple nodes. Update every node for which
  the answer shows observable competence, including concepts genuinely used in
  an integrated task rather than only the concept named in the question.
- Match each judgment against that node's authored levels, diagnostic_goal, and
  diagnostic_signals. Choose the highest level whose described behavior is
  clearly demonstrated; do not impose a separate global interpretation of L0-L5.
- Separate mastery from diagnostic confidence. Correct reasoning, task success,
  transfer, and self-correction determine mastery. Verbal hedges such as "I want
  to double-check" primarily lower diagnostic_confidence and must not by
  themselves lower mastery when the demonstrated work satisfies the rubric.
- Graph-mediated inference must name the observed behavior in assessment_note
  and cite the turn. Edges are soft diagnostic structure, not rules that copy a
  mastery level from one node to another.
- Do not add, remove, or rename graph nodes.

Question-selection rules:
- Preserve full-graph reconstruction under the finite turn budget. Do not scan
  nodes in graph order or default to one isolated textbook question per node.
- Maximize expected information gain. Compare remaining turns with unresolved
  nodes and prefer one coherent integrated task that can reveal competence on a
  related concept cluster when the graph and rubrics support it.
- One Diagnostic Question may contain one connected scenario, construction,
  comparison, explanation, or application with dependent steps. It may target
  multiple related nodes. It must not pack unrelated independent questions.
- Use graph edges to identify useful clusters and prerequisite chains, but make
  the question answerable as one coherent task. Do not reveal node ids or level
  labels to the user.
- Use follow-up questions when they distinguish a specific adjacent mastery
  boundary or resolve contradictory evidence; otherwise expand coverage.
- The diagnostic plan is private tested-agent trace metadata. Its primary and
  secondary targets must be graph node ids, and its reason must explain why this
  question is more informative than another isolated probe.
""".strip()


_ASSESSMENT_OUTPUT_CONTRACT = """
Return exactly this JSON shape:
{
  "updates": [
    {
      "node_id": "graph node id",
      "assessed_mastery_level": "unknown|L0|L1|L2|L3|L4|L5",
      "diagnostic_confidence": "unknown|low|medium|high",
      "assessment_note": "concise visible-evidence note, or omit/null for unknown",
      "supporting_turn_ids": ["visible turn id"]
    }
  ]
}

Return {"updates": []} when no working-map judgment should change.
Only include nodes whose assessment should change.
""".strip()


_NEXT_ACTION_OUTPUT_CONTRACT = """
Return exactly one of these JSON shapes:
{
  "action": "ask_diagnostic_question",
  "question": {
    "text": "one diagnostic question",
    "question_id": "optional stable id"
  },
  "diagnostic_plan": {
    "primary_target_node_id": "graph node id",
    "secondary_target_node_ids": ["related graph node id"],
    "target_mastery_boundary": "for example L2_vs_L3 or broad_initial_probe",
    "selection_reason": "why this coherent probe has high information value"
  }
}

or:
{
  "action": "finalize_reconstruction",
  "reason": "optional concise reason"
}

If remaining_diagnostic_turns is 0, choose finalize_reconstruction.
Ask only one primary Diagnostic Question. Do not include multiple independent
questions in one text.
""".strip()


_JSON_ONLY_RULES = """
Output rules:
- Return exactly one valid JSON object.
- The first non-whitespace character must be { and the last non-whitespace character must be }.
- Do not return a top-level array, JSON Lines, YAML, XML, Markdown, or prose.
- Use double quotes for every JSON key and string; do not use comments or trailing commas.
- Include only the fields in the requested output contract.
- Do not wrap JSON in Markdown fences.
- Do not include commentary, reasoning notes, review notes, or debug logs.
""".strip()
