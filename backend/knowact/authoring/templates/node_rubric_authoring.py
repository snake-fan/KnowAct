from collections.abc import Sequence

from backend.knowact.authoring.schemas import SourceGroundedNodeSkeleton, SourceMaterial
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    JSON_ONLY_RULES,
    MASTERY_SCALE,
    SOURCE_GROUNDING_RULES,
    dump_model_list,
    render_parsed_source_markdown,
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
    skeletons: Sequence[SourceGroundedNodeSkeleton],
    source_materials: Sequence[SourceMaterial],
    *,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                "You are the KnowAct Node Rubric Authoring Agent Step.",
                AUTHORING_CONTEXT,
                SOURCE_GROUNDING_RULES,
                MASTERY_SCALE,
                NODE_RUBRIC_PATCH_SCHEMA_CONTRACT,
                """
This step writes rubric patches for source-grounded skeletons.
The workflow will merge each rubric patch with the matching skeleton to create complete candidate Knowledge Nodes.

Input boundary:
- Use only the skeletons, their source locators, Parsed Source Markdown, and the global MasteryScale.
- Do not use candidate edges, unreviewed neighboring nodes, graph traversal context, or outside memory.
- If the authoritative source itself explains a concept through a contrast or dependency, you may reflect that source-grounded context in the rubric.
- Use each skeleton's id exactly as provided.
- Do not copy skeleton name, type, definition, or source_locators into your JSON output.

Rubric expectations:
- diagnostic_goal should say what this node is meant to diagnose, not how to score a whole episode.
- levels must contain exactly L0-L5, using the global scale labels without renaming them.
- Each level description must be concrete for this node and should include what the user can do, what limits remain, and what misconceptions or boundary failures may appear.
- Do not write generic repeated level text that could apply to any node.
- diagnostic_signals should list observable answer signals that help distinguish levels, including positive signs, negative signs, and common misconceptions where source-grounded.
- simulator_behavior should describe knowledge-related answering behavior only. Do not include personality, tone preferences, hidden profile facts, mastery labels, or evidence ids.
""".strip(),
                """
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
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Author complete candidate Knowledge Nodes for every skeleton.",
                render_parsed_source_markdown(source_materials),
                """
Quality checklist:
- Every input skeleton has exactly one output node.
- No extra ungrounded nodes are added.
- Every output node has id, diagnostic_goal, complete L0-L5 levels, diagnostic_signals, and simulator_behavior.
- No output node includes name, type, definition, or source_locators.
- Rubrics are source-grounded and diagnostic, not teaching plans or episode scoring rules.
- No candidate/review status fields appear in objects.
""".strip(),
                f"Source-grounded node skeletons:\n\n{dump_model_list(skeletons)}",
            ),
        ),
    )
