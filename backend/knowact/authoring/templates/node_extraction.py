from backend.knowact.authoring.schemas import ParsedSourceSegment
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    JSON_ONLY_RULES,
    NODE_DESIGN_RULES,
    SOURCE_READING_RULES,
    STOP_AFTER_JSON_RULES,
    TASK_DATA_BOUNDARY_RULES,
    render_sections,
)
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage, ModelMessageProfile


def build_node_extraction_messages(
    segment: ParsedSourceSegment,
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
Extract thin Segment Node Extraction Drafts from one bounded Parsed Source Segment.
Success means every returned draft is source-grounded, diagnosable, moderately granular, and parseable by the exact JSON contract.
""".strip(),
                AUTHORING_CONTEXT,
                TASK_DATA_BOUNDARY_RULES,
                SOURCE_READING_RULES,
                NODE_DESIGN_RULES,
                """
Input boundary:
This step reads exactly one Parsed Source Segment.
It is not the reconciliation step, rubric-writing step, or edge proposal step.
The segment text is the only source-material text available to this call.
""".strip(),
                """
Process:
1. Read the segment text and identify stable concepts that matter for active knowledge-state diagnosis.
2. Return only concepts grounded in this segment.
3. Keep drafts thin: name, definition, source_locator, and grounding_note only.
4. Prefer source-grounded definitions, boundaries, contrasts, dependencies, examples, and diagnostic clues over broad headings or isolated notation.
5. Remove anything that belongs to reconciliation, rubric authoring, edge proposal, user-state authoring, or evidence authoring.
""".strip(),
                """
Decision rules:
- Preserve a clear source trail for every draft.
- Prefer stable domain concepts over section headings, implementation details, examples, or isolated formula notation.
- Write definitions from the provided segment text, not from outside memory.
- Write concise grounding_note values that preserve the source-grounded facts later workflow steps need without copying long source passages.
- If a concept cannot be grounded in the segment text, omit it.
- If the segment contains no sufficiently grounded diagnosable concept, return {"drafts": []}.
- A soft target is 8-12 drafts or fewer for this segment, but include more if the segment clearly supports them.
- Do not output id, draft_id, segment_id, diagnostic_goal, levels, diagnostic_signals, simulator_behavior, edges, user states, or evidence.
""".strip(),
                """
Output contract:
Return JSON with this exact top-level shape:
{
  "drafts": [
    {
      "name": "Human Readable Name",
      "definition": "Concise source-grounded definition.",
      "source_locator": {
        "source_id": "same_source_id_as_input",
        "locator": "same_or_more_precise_location_as_input",
        "note": "optional short reviewer note"
      },
      "grounding_note": "Concise paraphrased source-grounding note."
    }
  ]
}

The complete response must be a JSON object with exactly one top-level key: "drafts".
"drafts" must be an array.
""".strip(),
                """
Final check before output:
- Each draft has nonblank name, definition, source_locator, and grounding_note.
- Each locator uses the provided source id and a reviewer-usable locator.
- No draft relies on outside memory or invented source metadata.
- No output contains ids, user-state, evidence, candidate-status, edge, or rubric fields.
""".strip(),
                STOP_AFTER_JSON_RULES,
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Extract reviewable Segment Node Extraction Drafts from this Parsed Source Segment.",
                f"Source: {segment.source_id} - {segment.source_title}",
                f"Location: {segment.location}",
                f"Text:\n\n{segment.text}",
            ),
        ),
    )
