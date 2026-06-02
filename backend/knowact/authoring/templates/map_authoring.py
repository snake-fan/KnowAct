import json

from backend.knowact.authoring.schemas import KnowledgeStateOutline
from backend.knowact.authoring.schemas import ConfirmedProfileContext
from backend.knowact.core.evidence import EvidenceKind
from backend.knowact.core.graph import KnowledgeNode
from backend.knowact.llm.messages import ModelMessage, ModelMessageProfile, OPENAI_MESSAGE_PROFILE


def build_knowledge_state_outline_messages(
    *,
    profile_context: ConfirmedProfileContext,
    nodes: tuple[KnowledgeNode, ...],
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=(
                "You are the Knowledge-State Outline Agent Step. Draft one plausible synthetic "
                "user knowledge state for every supplied reviewed node. Return JSON with a states "
                "array. Each state must contain node_id, mastery_level from L0 through L5, and "
                "explicit misconceptions and unknowns arrays. Do not emit evidence refs, user "
                "identity, lifecycle kind, or graph edges. Avoid blank or exactly duplicated items."
            ),
        ),
        ModelMessage(
            role="user",
            content=_json_context(
                {
                    "confirmed_profile_context": profile_context.model_dump(mode="json"),
                    "reviewed_nodes_with_rubrics": [
                        node.model_dump(mode="json", exclude_none=True) for node in nodes
                    ],
                }
            ),
        ),
    )


def build_ground_truth_evidence_messages(
    *,
    profile_context: ConfirmedProfileContext,
    nodes: tuple[KnowledgeNode, ...],
    state_outlines: tuple[KnowledgeStateOutline, ...],
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    allowed_evidence_kinds = ", ".join(kind.value for kind in EvidenceKind)
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=(
                "You are the Ground-Truth Evidence Authoring Agent Step. Return JSON with an "
                "evidence array for the supplied node batch only. Each record must contain node_id, "
                "evidence_kind, and signal only. Do not emit evidence ids, evidence_type, "
                "visibility, turn_id, lifecycle kind, user identity, mastery updates, graph edges, "
                "scores, or promotion metadata. Only author hidden simulator-support evidence for "
                "the supplied batch nodes; do not reference nodes outside this batch. evidence_kind "
                "is a functional role, not a surface format. It must be exactly one of: "
                f"{allowed_evidence_kinds}. Use prior_answer for answer-like evidence such as "
                "quiz answers, written responses, verbal explanations, discussion comments, "
                "multiple-choice answers, true/false answers, or theorem references. Use "
                "worked_example for evidence where the user applies a concept in an example, "
                "calculation, code sketch, model-selection proposal, diagnostic exercise, pipeline "
                "description, residual-plot interpretation, or example analysis. Use self_report "
                "for the user's own claims about confidence, experience, goals, preferences, or "
                "uncertainty. Use misconception_trace for evidence of a wrong belief, boundary "
                "confusion, faulty assumption, or repeated error pattern. Use background_fact for "
                "stable profile facts or prior exposure that support simulator behavior. Put the "
                "specific surface form in signal; never invent fine-grained evidence_kind values "
                "such as quiz_answer, verbal_explanation, discussion_comment, written_response, "
                "concept_explanation, residual_plot_interpretation, or theorem_reference. Use at "
                "least one record for L0-L1 and L4-L5 states, and at least two records for L2-L3 "
                "states. Avoid exactly duplicated (evidence_kind, signal) pairs for one node."
            ),
        ),
        ModelMessage(
            role="user",
            content=_json_context(
                {
                    "confirmed_profile_context": profile_context.model_dump(mode="json"),
                    "batch_nodes_with_rubrics": [
                        node.model_dump(mode="json", exclude_none=True) for node in nodes
                    ],
                    "batch_state_outlines": [
                        state.model_dump(mode="json") for state in state_outlines
                    ],
                }
            ),
        ),
    )


def _json_context(payload: object) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)
