from collections.abc import Sequence

from backend.knowact.authoring.schemas import SourceMaterial
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    JSON_ONLY_RULES,
    NODE_DESIGN_RULES,
    SOURCE_GROUNDING_RULES,
    render_parsed_source_markdown,
    render_sections,
)
from backend.knowact.llm.messages import ModelMessage


def build_node_extraction_messages(
    source_materials: Sequence[SourceMaterial],
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role="developer",
            content=render_sections(
                "You are the KnowAct Node Extraction Agent Step.",
                AUTHORING_CONTEXT,
                SOURCE_GROUNDING_RULES,
                NODE_DESIGN_RULES,
                """
This step extracts only Source-Grounded Node Skeletons from Parsed Source Markdown.
It is not the rubric-writing step and it is not the edge proposal step.

Extract skeletons that can later become benchmark Knowledge Nodes:
- Preserve a clear source trail for every skeleton.
- Prefer stable domain concepts over section headings, implementation details, examples, or isolated formula notation.
- Merge obvious duplicates and near-synonyms into one canonical skeleton id.
- Use snake_case ids that are stable and meaningful.
- Write definitions from the Parsed Source Markdown, not from outside memory.
- Do not output diagnostic_goal, levels, diagnostic_signals, simulator_behavior, edges, user states, or evidence.
""".strip(),
                """
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
                "Extract reviewable Source-Grounded Node Skeletons from Parsed Source Markdown.",
                render_parsed_source_markdown(source_materials),
                """
Before returning JSON, check each skeleton:
- Is it source-grounded by an explicit locator?
- Is it explainable and diagnosable?
- Is it neither too broad nor too tiny?
- Is it stable enough to appear in a reviewed benchmark graph?
- Is it free of user-state, evidence, candidate-status, and edge data?
""".strip(),
            ),
        ),
    )
