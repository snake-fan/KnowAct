from backend.knowact.authoring.schemas import (
    DEFAULT_GRAPH_AUTHORING_SCOPE,
    GraphAuthoringScope,
    ParsedSourceSegment,
)
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    JSON_ONLY_RULES,
    NODE_DESIGN_RULES,
    SOURCE_READING_RULES,
    STOP_AFTER_JSON_RULES,
    TASK_DATA_BOUNDARY_RULES,
    dump_model,
    render_sections,
)
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage, ModelMessageProfile


def build_node_extraction_messages(
    segment: ParsedSourceSegment,
    *,
    scope: GraphAuthoringScope | None = None,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    scope = scope or DEFAULT_GRAPH_AUTHORING_SCOPE
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
Success means every returned draft is in the declared aspect, source-grounded, useful for representative diagnostic tasks, moderately granular, and parseable by the exact JSON contract.
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
1. Read the segment only through the declared Graph Authoring Scope.
2. Identify stable concepts needed to answer the representative tasks; ignore unrelated book content even when it is important in the wider field.
3. Return only concepts grounded in this segment.
4. Keep drafts thin: name, definition, source_locator, grounding_note, and one short verbatim evidence_excerpt only.
5. Prefer source-grounded definitions, boundaries, contrasts, dependencies, examples, and diagnostic clues over broad headings or isolated notation.
6. Remove anything that belongs to reconciliation, rubric authoring, edge proposal, user-state authoring, or evidence authoring.
""".strip(),
                """
Decision rules:
- Preserve a clear source trail for every draft.
- Prefer stable domain concepts over section headings, implementation details, exercises, examples, named one-off results, proof maneuvers, or isolated formula notation.
- Do not mine every theorem, lemma, proposition, example, exercise, equation, symbol, named algorithm step, or local variation as a separate node.
- Use examples, exercises, formulas, and local results as grounding for broader concepts unless the passage clearly introduces a central domain concept that can support several diagnostic questions.
- A compact relevant segment should usually return 2-6 drafts, and may return zero drafts when it is outside the scope or contains mostly examples, exercises, proofs, front matter, or repeated material.
- A long segment spanning several major in-scope subsections may justify 8-12 drafts so the later graph-wide reconciliation can choose representative coverage. Treat 12 as an upper bound, not a quota: never add incidental concepts merely to approach target_node_count.
- Write definitions from the provided segment text, not from outside memory.
- Write concise grounding_note values that preserve the source-grounded facts later workflow steps need without copying long source passages.
- Copy evidence_excerpt exactly from the segment text. Keep it short but sufficient to support the concept; do not paraphrase or add ellipses.
- If a concept cannot be grounded in the segment text, omit it.
- If the segment contains no sufficiently grounded diagnosable concept, return {"drafts": []}.
- Do not output id, draft_id, segment_id, diagnostic_goal, levels, diagnostic_signals, simulator_behavior, edges, user states, or evidence.
- Do not output source_id. The workflow supplies source_id from the Parsed Source Segment.
- If source_locator.note would be blank, omit the note key entirely.
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
        "locator": "same_or_more_precise_location_as_input"
      },
      "grounding_note": "Concise paraphrased source-grounding note.",
      "evidence_excerpt": "Short exact excerpt copied from the segment text."
    }
  ]
}

The complete response must be a JSON object with exactly one top-level key: "drafts".
"drafts" must be an array.
source_locator.note is optional. Include it only when it is a nonblank reviewer note; otherwise omit the key.
""".strip(),
                """
Final check before output:
- Each draft has nonblank name, definition, source_locator, grounding_note, and evidence_excerpt.
- Every evidence_excerpt is copied exactly from the provided segment text.
- Each source_locator contains a reviewer-usable locator and does not contain source_id.
- No source_locator contains a blank note.
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
                f"Graph Authoring Scope:\n\n{dump_model(scope)}",
                f"Source ID (workflow-supplied; do not output): {segment.source_id}",
                f"Source title: {segment.source_title}",
                f"Location: {segment.location}",
                f"Text:\n\n{segment.text}",
            ),
        ),
    )
