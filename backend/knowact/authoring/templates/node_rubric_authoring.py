from backend.knowact.authoring.schemas import NodeRubricAuthoringInput
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    INTERMEDIATE_SOURCE_GROUNDING_RULES,
    JSON_ONLY_RULES,
    MASTERY_SCALE,
    STOP_AFTER_JSON_RULES,
    TASK_DATA_BOUNDARY_RULES,
    dump_model_list,
    render_sections,
)
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage, ModelMessageProfile


NODE_RUBRIC_PATCH_SCHEMA_CONTRACT = """
Return node rubric patch objects that match the current parser contract:
- id: the exact id of one input skeleton.
- diagnostic_goal: the overall diagnostic target for this node.
- levels: object with exactly keys L0, L1, L2, L3, L4, L5. Each value is a non-empty node-specific description string.
- diagnostic_signals: non-empty list of observable answer signals useful for distinguishing mastery levels.
- simulator_behavior: concise knowledge-state response behavior for a simulator; do not include persona, preferences, or hidden labels.

Do not output name, type, definition, or source_locators. The workflow will copy those source-grounded fields from the matching input skeleton by id.
""".strip()


def build_node_rubric_authoring_messages(
    input_data: NodeRubricAuthoringInput,
    *,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                """
Role:
You are the KnowAct Node Rubric Authoring Agent Step.
""".strip(),
                """
Objective:
Write one rubric patch for every source-grounded skeleton so the workflow can merge patches into complete candidate Knowledge Nodes.
Success means every input skeleton has exactly one node-specific, source-grounded, parseable rubric patch.
""".strip(),
                AUTHORING_CONTEXT,
                TASK_DATA_BOUNDARY_RULES,
                INTERMEDIATE_SOURCE_GROUNDING_RULES,
                MASTERY_SCALE,
                NODE_RUBRIC_PATCH_SCHEMA_CONTRACT,
                """
Input boundary:
This step writes rubric patches for source-grounded skeletons.
The workflow will merge each rubric patch with the matching skeleton to create complete candidate Knowledge Nodes.
- Use only the skeletons, their source locators, source_grounding_notes, and the global MasteryScale.
- Do not use candidate edges, unreviewed neighboring nodes, graph traversal context, or outside memory.
- If the source_grounding_notes explain a concept through a contrast or dependency, you may reflect that source-grounded context in the rubric.
- Use each skeleton's id exactly as provided.
- Do not copy skeleton name, type, definition, or source_locators into your JSON output.
""".strip(),
                """
Process:
1. For each skeleton, identify the node-level understanding the benchmark should diagnose.
2. Map that understanding onto L0-L5 using the global scale and the skeleton's source_grounding_notes.
3. Write level descriptions that are specific enough to distinguish neighboring mastery states.
4. Add diagnostic_signals that a simulator or reviewer could observe in answers.
5. Write simulator_behavior as knowledge-state response behavior only.
""".strip(),
                """
Decision rules:
- diagnostic_goal should say what this node is meant to diagnose, not how to score a whole episode.
- levels must contain exactly L0-L5, using the global scale labels without renaming them.
- Each level description must be concrete for this node and should include what the user can do, what limits remain, and what misconceptions or boundary failures may appear.
- Do not write generic repeated level text that could apply to any node.
- diagnostic_signals should list observable answer signals that help distinguish levels, including positive signs, negative signs, and common misconceptions where source-grounded.
- simulator_behavior should describe knowledge-related answering behavior only. Do not include personality, tone preferences, hidden profile facts, mastery labels, or evidence ids.
- If input skeletons are empty, return {"nodes": []}.
- If one skeleton has sparse grounding, still return one conservative patch using only the provided fields; do not invent source passages or omit the skeleton.
""".strip(),
                """
Output contract:
Return JSON with this exact top-level shape:
{
  "nodes": [
    {
      "id": "same_as_skeleton",
      "diagnostic_goal": "Node-level diagnostic goal.",
      "levels": {
        "L0": "Node-specific description.",
        "L1": "Node-specific description.",
        "L2": "Node-specific description.",
        "L3": "Node-specific description.",
        "L4": "Node-specific description.",
        "L5": "Node-specific description."
      },
      "diagnostic_signals": [
        "Observable signal for assigning or ruling out levels."
      ],
      "simulator_behavior": "Knowledge-state behavior for simulator answers."
    }
  ]
}

The complete response must be a JSON object with exactly one top-level key: "nodes".
"nodes" must be an array with exactly one object for every input skeleton and no extra objects.
Every node rubric patch must include all fields shown above, and "levels" must contain exactly L0, L1, L2, L3, L4, and L5.
""".strip(),
                """
Final check before output:
- Every input skeleton id appears exactly once.
- No output object includes name, type, definition, source_locators, source_grounding_notes, candidate status, edges, user states, or evidence.
- Every diagnostic_goal, level description, diagnostic signal, and simulator_behavior is nonblank and node-specific.
- The output can be parsed as one JSON object with top-level key "nodes".
""".strip(),
                STOP_AFTER_JSON_RULES,
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Author complete candidate Knowledge Nodes for every skeleton.",
                """
Quality checklist:
- Every input skeleton has exactly one output node.
- No extra ungrounded nodes are added.
- Every output node has id, diagnostic_goal, complete L0-L5 levels, diagnostic_signals, and simulator_behavior.
- No output node includes name, type, definition, or source_locators.
- Rubrics are grounded in the provided source locators and source_grounding_notes, not teaching plans or episode scoring rules.
- No candidate/review status fields appear in objects.
""".strip(),
                f"Source-grounded node skeletons:\n\n{dump_model_list(input_data.skeletons)}",
            ),
        ),
    )
