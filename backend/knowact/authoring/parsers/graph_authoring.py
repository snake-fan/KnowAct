import json

from pydantic import ValidationError

from backend.knowact.authoring.schemas import (
    KnowledgeEdgeList,
    KnowledgeNodeList,
    SourceGroundedNodeSkeleton,
    SourceGroundedNodeSkeletonList,
)
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeNode


class AuthoringOutputParseError(RuntimeError):
    """Raised when an authoring agent output cannot be parsed into the expected schema."""


def parse_node_extraction_output(raw_output: str) -> tuple[SourceGroundedNodeSkeleton, ...]:
    return _parse_model(raw_output, SourceGroundedNodeSkeletonList).skeletons


def parse_node_rubric_authoring_output(raw_output: str) -> tuple[KnowledgeNode, ...]:
    return _parse_model(raw_output, KnowledgeNodeList).nodes


def parse_edge_proposal_output(raw_output: str) -> tuple[KnowledgeEdge, ...]:
    return _parse_model(raw_output, KnowledgeEdgeList).edges


def _parse_model(raw_output: str, model_type):
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise AuthoringOutputParseError("Authoring agent output was not valid JSON") from exc

    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise AuthoringOutputParseError(
            f"Authoring agent output did not match {model_type.__name__}"
        ) from exc

