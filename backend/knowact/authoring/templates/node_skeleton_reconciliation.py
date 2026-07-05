from collections.abc import Sequence

from backend.knowact.authoring.schemas import SegmentNodeExtractionDraft
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    INTERMEDIATE_SOURCE_GROUNDING_RULES,
    JSON_ONLY_RULES,
    NODE_DESIGN_RULES,
    STOP_AFTER_JSON_RULES,
    TASK_DATA_BOUNDARY_RULES,
    dump_model_list,
    render_sections,
)
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage, ModelMessageProfile


def build_node_skeleton_reconciliation_messages(
    drafts: Sequence[SegmentNodeExtractionDraft],
    *,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                """
Role:
You are the KnowAct Node Skeleton Reconciliation Agent Step.
""".strip(),
                """
Objective:
Deduplicate, merge, and lightly split Segment Node Extraction Drafts into reviewable source-grounded node skeleton drafts.
Success means the output contains one canonical object per diagnosable concept, with preserved source locators and draft provenance.
""".strip(),
                AUTHORING_CONTEXT,
                TASK_DATA_BOUNDARY_RULES,
                INTERMEDIATE_SOURCE_GROUNDING_RULES,
                NODE_DESIGN_RULES,
                """
Input boundary:
This step receives only Segment Node Extraction Drafts and their source-grounding metadata.
It does not receive original segment text or full source text.
It is not the rubric-writing step and it is not the edge proposal step.
""".strip(),
                """
Process:
1. Merge drafts that refer to the same concept, including duplicates across different source locations.
2. Choose one canonical human-readable name for each merged concept.
3. Preserve all useful source locators and enough grounding notes for downstream rubric authoring.
4. Split an obviously compound draft only when the resulting concepts are already supported by draft notes and locators.
5. Remove weak, duplicate, ungrounded, too broad, or too tiny drafts.
""".strip(),
                """
Decision rules:
- Do not invent a skeleton without support from at least one input draft.
- Do not use outside memory or infer from original book text that is not present in draft definitions, locators, or grounding notes.
- Keep names stable and human-readable. The workflow will derive final node ids from these names.
- supporting_draft_ids must reference existing draft ids.
- supporting_segment_ids must reference segment ids present in supporting drafts.
- merge_split_note should briefly explain whether the output is unchanged, merged, split, or discarded from related drafts.
- Do not output id, diagnostic_goal, levels, diagnostic_signals, simulator_behavior, edges, user states, or evidence.
""".strip(),
                """
Output contract:
Return JSON with this exact top-level shape:
{
  "skeletons": [
    {
      "name": "Canonical Human Readable Name",
      "definition": "Concise source-grounded definition.",
      "source_locators": [
        {
          "source_id": "source_id_from_input_draft",
          "locator": "reviewer-usable source location",
          "note": "optional short reviewer note"
        }
      ],
      "grounding_notes": [
        "Concise paraphrased source-grounding note for downstream rubric and edge steps."
      ],
      "supporting_draft_ids": ["draft_000001"],
      "supporting_segment_ids": ["seg_000001"],
      "merge_split_note": "Short provenance note."
    }
  ]
}

The complete response must be a JSON object with exactly one top-level key: "skeletons".
"skeletons" must be an array.
""".strip(),
                """
Final check before output:
- Every output skeleton has at least one supporting draft id and segment id.
- Every output skeleton has at least one source locator and grounding note.
- No output object includes id, rubric fields, edge fields, user-state fields, evidence, or candidate status.
""".strip(),
                STOP_AFTER_JSON_RULES,
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Reconcile these Segment Node Extraction Drafts into canonical source-grounded node skeleton drafts.",
                f"Segment Node Extraction Drafts:\n\n{dump_model_list(drafts)}",
            ),
        ),
    )
