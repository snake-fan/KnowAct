from backend.knowact.authoring.schemas import EdgeProposalInput
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    EDGE_SCHEMA_CONTRACT,
    EDGE_TYPE_RULES,
    INTERMEDIATE_SOURCE_GROUNDING_RULES,
    JSON_ONLY_RULES,
    STOP_AFTER_JSON_RULES,
    TASK_DATA_BOUNDARY_RULES,
    dump_model_list,
    render_sections,
)
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage, ModelMessageProfile


def build_edge_proposal_messages(
    input_data: EdgeProposalInput,
    *,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                """
Role:
You are the KnowAct Edge Proposal Agent Step.
""".strip(),
                """
Objective:
Propose precision-first candidate Knowledge Edges between already-authored candidate nodes.
Success means every returned edge has a clear canonical type, valid endpoints, correct direction, and an objective rationale worth benchmark-author review.
""".strip(),
                AUTHORING_CONTEXT,
                TASK_DATA_BOUNDARY_RULES,
                INTERMEDIATE_SOURCE_GROUNDING_RULES,
                EDGE_TYPE_RULES,
                EDGE_SCHEMA_CONTRACT,
                """
Input boundary:
This step proposes precision-first candidate Knowledge Edges after complete candidate nodes exist.
- You may use complete candidate nodes, including diagnostic_goal, L0-L5 levels, diagnostic_signals, simulator_behavior, source_locators, and source_grounding_notes from earlier workflow artifacts.
- Do not change node objects.
- Do not add node fields to edge objects.
- Do not use edge objects to express user knowledge state, evidence, diagnostic questions, scoring, or probe strategy.
""".strip(),
                """
Process:
1. Compare candidate nodes for objective conceptual relationships, not user-state relationships.
2. Choose an edge only when exactly one canonical type fits clearly.
3. Check direction for part_of, prerequisite_for, and supports.
4. Write a concise rationale that explains the knowledge relationship.
5. Assign weight and curation_confidence from the strength and clarity of the relationship, not from how useful it might be for a question.
""".strip(),
                """
Decision rules:
- Include an edge only when the relation has a clear canonical type and a clear rationale.
- Omit weak, speculative, merely related, same-topic, same-chapter, or type-ambiguous pairs.
- Do not invent related_to, used_for, similar_to, enables, or other free-form edge types.
- Use supports only when the source gives a specific explanatory, transfer, or diagnostic contribution to the target.
- For prerequisite_for, ask whether missing the source would usually prevent stable L3+ understanding of the target.
- For contrasts_with, normally output one directional record for the canonical pair rather than duplicate reciprocal edges.
- If source and target direction is uncertain, omit the edge.
- It is acceptable to return an empty edges list when no pair is clear enough.
""".strip(),
                """
Output contract:
Return JSON with this exact top-level shape:
{
  "edges": [
    {
      "id": "edge_source_type_target",
      "source": "source_node_id",
      "target": "target_node_id",
      "type": "part_of",
      "rationale": "Why this objective relationship holds.",
      "weight": 0.8,
      "curation_confidence": 0.9
    }
  ]
}

The complete response must be a JSON object with exactly one top-level key: "edges".
"edges" must be an array. When no edge is clear enough, return exactly {"edges": []}.
Every edge object must include only the fields shown above and must reference existing candidate node ids.
""".strip(),
                """
Final check before output:
- Every source and target is an existing node id.
- Every type is one of part_of, prerequisite_for, supports, or contrasts_with.
- Every rationale describes an objective relationship rather than a user-state, evidence, score, or question-design idea.
- No weak relatedness edge remains in the output.
""".strip(),
                STOP_AFTER_JSON_RULES,
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Propose precision-first candidate Knowledge Edges for the complete candidate node list.",
                """
Review each proposed edge before output:
- Are source and target valid node ids from the candidate node list?
- Is the edge type one of the four canonical types?
- Is the direction correct for part_of, prerequisite_for, and supports?
- Does the rationale explain the objective knowledge relationship rather than a user-state or question-design idea?
- Would a benchmark author prefer reviewing this edge over omitting it as weak relatedness?
""".strip(),
                f"Source-grounded node context:\n\n{dump_model_list(input_data.source_grounded_node_skeletons)}",
                f"Complete candidate nodes:\n\n{dump_model_list(input_data.candidate_nodes)}",
            ),
        ),
    )
