from collections.abc import Sequence

from backend.knowact.authoring.schemas import SourceGroundedNodeSkeleton, SourceMaterial
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    JSON_ONLY_RULES,
    MASTERY_SCALE,
    NODE_SCHEMA_CONTRACT,
    SOURCE_GROUNDING_RULES,
    dump_model_list,
    render_uploaded_pdf_source_reference,
    render_sections,
)
from backend.knowact.llm.messages import ModelMessage


def build_node_rubric_authoring_messages(
    skeletons: Sequence[SourceGroundedNodeSkeleton],
    source_materials: Sequence[SourceMaterial],
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role="developer",
            content=render_sections(
                "You are the KnowAct Node Rubric Authoring Agent Step.",
                AUTHORING_CONTEXT,
                SOURCE_GROUNDING_RULES,
                MASTERY_SCALE,
                NODE_SCHEMA_CONTRACT,
                """
This step turns source-grounded skeletons into complete candidate Knowledge Nodes.

Input boundary:
- Use only the skeletons, their source locators, the uploaded original PDF, and the global MasteryScale.
- Do not use candidate edges, unreviewed neighboring nodes, graph traversal context, or outside memory.
- If the authoritative source itself explains a concept through a contrast or dependency, you may reflect that source-grounded context in the rubric.
- Preserve each skeleton's id, name, type, definition, and source_locators unless the input is internally inconsistent.

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
      "name": "same_as_skeleton",
      "type": "concept",
      "definition": "same_or_source-grounded_refinement",
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
      "simulator_behavior": "Knowledge-state behavior for simulator answers.",
      "source_locators": [
        {
          "source_id": "same_source_id_as_input",
          "locator": "chapter_or_section_or_page_reference",
          "note": "optional short reviewer note"
        }
      ]
    }
  ]
}
""".strip(),
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Author complete candidate Knowledge Nodes for every skeleton.",
                render_uploaded_pdf_source_reference(source_materials),
                """
Quality checklist:
- Every input skeleton has exactly one output node.
- No extra ungrounded nodes are added.
- Every output node has definition, diagnostic_goal, complete L0-L5 levels, diagnostic_signals, simulator_behavior, and source_locators.
- Rubrics are source-grounded and diagnostic, not teaching plans or episode scoring rules.
- No candidate/review status fields appear in objects.
""".strip(),
                f"Source-grounded node skeletons:\n\n{dump_model_list(skeletons)}",
            ),
        ),
    )
