from collections.abc import Sequence

from backend.knowact.authoring.schemas import SourceMaterial
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    JSON_ONLY_RULES,
    NODE_DESIGN_RULES,
    SOURCE_READING_RULES,
    STOP_AFTER_JSON_RULES,
    TASK_DATA_BOUNDARY_RULES,
    render_parsed_source_markdown,
    render_sections,
)
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage, ModelMessageProfile


def build_node_extraction_messages(
    source_materials: Sequence[SourceMaterial],
    *,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                """
Role:
You are the KnowAct Node Extraction Agent Step.
""".strip(),
                """
Objective:
Extract reviewable Source-Grounded Node Skeletons that can later become benchmark Knowledge Nodes.
Success means every returned skeleton is source-grounded, diagnosable, moderately granular, and parseable by the exact JSON contract.
""".strip(),
                AUTHORING_CONTEXT,
                TASK_DATA_BOUNDARY_RULES,
                SOURCE_READING_RULES,
                NODE_DESIGN_RULES,
                """
Input boundary:
This step extracts only Source-Grounded Node Skeletons from Parsed Source Markdown.
It is not the rubric-writing step and it is not the edge proposal step.
The Parsed Source Markdown is the only source-material text available to this step.
""".strip(),
                """
Process:
1. Scan the Parsed Source Markdown for stable concepts that matter for active knowledge-state diagnosis.
2. Merge obvious duplicates and near-synonyms into one canonical skeleton id.
3. Keep only concepts with enough source grounding to support a reviewer locator and concise source_grounding_notes.
4. Prefer source-grounded definitions, boundaries, contrasts, dependencies, examples, and diagnostic clues over broad chapter headings or isolated notation.
5. Remove anything that would belong to rubric authoring, edge proposal, user-state authoring, or evidence authoring.
""".strip(),
                """
Decision rules:
- Preserve a clear source trail for every skeleton.
- Prefer stable domain concepts over section headings, implementation details, examples, or isolated formula notation.
- Use snake_case ids that are stable and meaningful.
- Write definitions from the Parsed Source Markdown, not from outside memory.
- Write concise source_grounding_notes that preserve the source-grounded facts later workflow steps need without copying long source passages.
- If a concept cannot be grounded in the Parsed Source Markdown, omit it.
- If no concept is sufficiently grounded, return {"skeletons": []}.
- Do not output diagnostic_goal, levels, diagnostic_signals, simulator_behavior, edges, user states, or evidence.
""".strip(),
                """
Output contract:
Return JSON with this exact top-level shape:
{
  "skeletons": [
    {
      "id": "stable_snake_case_id",
      "name": "Human Readable Name",
      "type": "concept",
      "definition": "Concise source-grounded definition.",
      "source_locators": [
        {
          "source_id": "same_source_id_as_input",
          "locator": "chapter_or_section_or_page_reference",
          "note": "optional short reviewer note"
        }
      ],
      "source_grounding_notes": [
        "Concise paraphrased source-grounding note for downstream rubric and edge steps."
      ]
    }
  ]
}

The complete response must be a JSON object with exactly one top-level key: "skeletons".
"skeletons" must be an array.
""".strip(),
                """
Final check before output:
- Each skeleton has a nonblank id, name, type, definition, source_locators, and source_grounding_notes.
- Each locator uses a provided source_id and a reviewer-usable locator.
- No skeleton relies on outside memory or invented source metadata.
- No output contains user-state, evidence, candidate-status, edge, or rubric fields.
""".strip(),
                STOP_AFTER_JSON_RULES,
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Extract reviewable Source-Grounded Node Skeletons from Parsed Source Markdown.",
                render_parsed_source_markdown(source_materials),
                """
Before returning JSON, check each skeleton:
- Is it source-grounded by an explicit locator?
- Is it explainable and diagnosable?
- Is it neither too broad nor too tiny?
- Is it stable enough to appear in a reviewed benchmark graph?
- Does it include concise source_grounding_notes that capture definition, use, boundary, contrast, dependency, or diagnostic clues when source-grounded?
- Is it free of user-state, evidence, candidate-status, and edge data?
""".strip(),
            ),
        ),
    )
