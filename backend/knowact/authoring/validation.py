from collections.abc import Sequence

from backend.knowact.core.graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode
from backend.knowact.core.map import MasteryLevel
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.graph import validate_knowledge_graph
from backend.knowact.authoring.schemas import SourceGroundedNodeSkeleton


REQUIRED_MASTERY_LEVELS = {level.value for level in MasteryLevel}


def validate_source_grounded_node_skeletons(
    skeletons: Sequence[SourceGroundedNodeSkeleton],
) -> None:
    skeleton_ids = [skeleton.id for skeleton in skeletons]
    duplicate_ids = _duplicates(skeleton_ids)
    if duplicate_ids:
        raise KnowActValidationError(f"Duplicate source-grounded node skeleton ids: {sorted(duplicate_ids)}")

    for skeleton in skeletons:
        if not skeleton.source_locators:
            raise KnowActValidationError(f"Node skeleton {skeleton.id} must include source locators")


def validate_complete_candidate_nodes(
    nodes: Sequence[KnowledgeNode],
    skeletons: Sequence[SourceGroundedNodeSkeleton] | None = None,
) -> None:
    node_ids = [node.id for node in nodes]
    duplicate_ids = _duplicates(node_ids)
    if duplicate_ids:
        raise KnowActValidationError(f"Duplicate candidate knowledge node ids: {sorted(duplicate_ids)}")

    if skeletons is not None:
        skeleton_ids = {skeleton.id for skeleton in skeletons}
        missing_nodes = skeleton_ids - set(node_ids)
        extra_nodes = set(node_ids) - skeleton_ids
        if missing_nodes:
            raise KnowActValidationError(f"Missing candidate nodes for skeletons: {sorted(missing_nodes)}")
        if extra_nodes:
            raise KnowActValidationError(f"Candidate nodes not grounded in skeletons: {sorted(extra_nodes)}")

    for node in nodes:
        if _is_blank(node.definition):
            raise KnowActValidationError(f"Candidate node {node.id} must include a definition")
        if not node.source_locators:
            raise KnowActValidationError(f"Candidate node {node.id} must include source locators")
        if _is_blank(node.diagnostic_goal):
            raise KnowActValidationError(f"Candidate node {node.id} must include a diagnostic goal")
        if set(node.levels.keys()) != REQUIRED_MASTERY_LEVELS:
            raise KnowActValidationError(f"Candidate node {node.id} must include exactly L0-L5 levels")
        if any(_is_blank(description) for description in node.levels.values()):
            raise KnowActValidationError(f"Candidate node {node.id} contains a blank level description")
        if not node.diagnostic_signals:
            raise KnowActValidationError(f"Candidate node {node.id} must include diagnostic signals")
        if any(_is_blank(signal) for signal in node.diagnostic_signals):
            raise KnowActValidationError(f"Candidate node {node.id} contains a blank diagnostic signal")
        if _is_blank(node.simulator_behavior):
            raise KnowActValidationError(f"Candidate node {node.id} must include simulator behavior")


def validate_candidate_edges(
    nodes: Sequence[KnowledgeNode],
    edges: Sequence[KnowledgeEdge],
) -> None:
    validate_knowledge_graph(KnowledgeGraph(nodes=tuple(nodes), edges=tuple(edges)))


def _duplicates(values: Sequence[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()

