import json

from backend.knowact.authoring.schemas import KnowledgeStateOutline
from backend.knowact.authoring.schemas import ConfirmedProfileContext
from backend.knowact.core.graph import KnowledgeNode
from backend.knowact.llm.messages import ModelMessage, ModelMessageProfile, OPENAI_MESSAGE_PROFILE


def build_knowledge_state_outline_messages(
    *,
    profile_context: ConfirmedProfileContext,
    nodes: tuple[KnowledgeNode, ...],
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    del message_profile
    return (
        ModelMessage(
            role="developer",
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
    del message_profile
    return (
        ModelMessage(
            role="developer",
            content=(
                "You are the Ground-Truth Evidence Authoring Agent Step. Return JSON with an "
                "evidence array for the supplied node batch only. Each record must contain node_id, "
                "evidence_kind, and signal only. Use at least one record for L0-L1 and L4-L5 states, "
                "and at least two records for L2-L3 states. Avoid exactly duplicated "
                "(evidence_kind, signal) pairs for one node."
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
