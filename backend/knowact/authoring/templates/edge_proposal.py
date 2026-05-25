from collections.abc import Sequence

from backend.knowact.authoring.schemas import SourceMaterial
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    EDGE_SCHEMA_CONTRACT,
    EDGE_TYPE_RULES,
    JSON_ONLY_RULES,
    SOURCE_GROUNDING_RULES,
    dump_model_list,
    render_uploaded_pdf_source_reference,
    render_sections,
)
from backend.knowact.core.graph import KnowledgeNode
from backend.knowact.llm.messages import ModelMessage


def build_edge_proposal_messages(
    candidate_nodes: Sequence[KnowledgeNode],
    source_materials: Sequence[SourceMaterial],
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role="developer",
            content=render_sections(
                "You are the KnowAct Edge Proposal Agent Step.",
                AUTHORING_CONTEXT,
                SOURCE_GROUNDING_RULES,
                EDGE_TYPE_RULES,
                EDGE_SCHEMA_CONTRACT,
                """
This step proposes precision-first candidate Knowledge Edges after complete candidate nodes exist.

Input boundary:
- You may use complete candidate nodes, including diagnostic_goal, L0-L5 levels, diagnostic_signals, simulator_behavior, source_locators, and relevant passages from the uploaded original PDF.
- Do not change node objects.
- Do not add node fields to edge objects.
- Do not use edge objects to express user knowledge state, evidence, diagnostic questions, scoring, or probe strategy.

Precision-first policy:
- Include an edge only when the relation has a clear canonical type and a clear rationale.
- Omit weak, speculative, merely related, same-topic, same-chapter, or type-ambiguous pairs.
- Do not invent related_to, used_for, similar_to, enables, or other free-form edge types.
- Use supports only when the source gives a specific explanatory, transfer, or diagnostic contribution to the target.
- For prerequisite_for, ask whether missing the source would usually prevent stable L3+ understanding of the target.
- For contrasts_with, store only one edge and order source/target lexicographically by node id.
- It is acceptable to return an empty edges list when no pair is clear enough.
""".strip(),
                """
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
""".strip(),
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Propose precision-first candidate Knowledge Edges for the complete candidate node list.",
                render_uploaded_pdf_source_reference(source_materials),
                """
Review each proposed edge before output:
- Are source and target valid node ids from the candidate node list?
- Is the edge type one of the four canonical types?
- Is the direction correct for part_of, prerequisite_for, and supports?
- Is contrasts_with stored in lexicographic node-id order?
- Does the rationale explain the objective knowledge relationship rather than a user-state or question-design idea?
- Would a benchmark author prefer reviewing this edge over omitting it as weak relatedness?
""".strip(),
                f"Complete candidate nodes:\n\n{dump_model_list(candidate_nodes)}",
            ),
        ),
    )
