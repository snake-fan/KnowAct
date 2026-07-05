from collections.abc import Sequence

from backend.knowact.core.graph import KnowledgeEdge, KnowledgeEdgeType, KnowledgeGraph, KnowledgeNode
from backend.knowact.core.map import MasteryLevel
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.graph import validate_knowledge_graph
from backend.knowact.authoring.schemas import (
    NodeSkeletonReconciliationResult,
    ParsedSourceSegment,
    SegmentNodeExtractionDraft,
    SourceGroundedNodeSkeleton,
)


REQUIRED_MASTERY_LEVELS = {level.value for level in MasteryLevel}


def validate_parsed_source_segments(
    segments: Sequence[ParsedSourceSegment],
) -> None:
    if not segments:
        raise KnowActValidationError("Parsed source segmentation produced no segments")

    segment_ids = [segment.segment_id for segment in segments]
    duplicate_ids = _duplicates(segment_ids)
    if duplicate_ids:
        raise KnowActValidationError(f"Duplicate parsed source segment ids: {sorted(duplicate_ids)}")

    for segment in segments:
        if len(segment.heading_path) > 3:
            raise KnowActValidationError(
                f"Parsed source segment {segment.segment_id} has heading_path deeper than three levels"
            )
        if segment.source_locator.source_id != segment.source_id:
            raise KnowActValidationError(
                f"Parsed source segment {segment.segment_id} source locator source_id does not match segment source_id"
            )
        if segment.char_count != len(segment.text):
            raise KnowActValidationError(
                f"Parsed source segment {segment.segment_id} char_count does not match text length"
            )


def validate_segment_node_extraction_drafts(
    drafts: Sequence[SegmentNodeExtractionDraft],
    segments: Sequence[ParsedSourceSegment],
) -> None:
    if not drafts:
        raise KnowActValidationError("Segment node extraction produced no drafts")

    draft_ids = [draft.draft_id for draft in drafts]
    duplicate_ids = _duplicates(draft_ids)
    if duplicate_ids:
        raise KnowActValidationError(f"Duplicate segment node extraction draft ids: {sorted(duplicate_ids)}")

    segments_by_id = {segment.segment_id: segment for segment in segments}
    for draft in drafts:
        segment = segments_by_id.get(draft.segment_id)
        if segment is None:
            raise KnowActValidationError(
                f"Segment node extraction draft {draft.draft_id} references unknown segment {draft.segment_id}"
            )
        if draft.source_locator.source_id != segment.source_id:
            raise KnowActValidationError(
                f"Segment node extraction draft {draft.draft_id} source locator source_id does not match segment source_id"
            )


def validate_node_skeleton_reconciliation_result(
    result: NodeSkeletonReconciliationResult,
    drafts: Sequence[SegmentNodeExtractionDraft],
) -> None:
    validate_source_grounded_node_skeletons(result.source_grounded_node_skeletons)

    if len(result.records) != len(result.source_grounded_node_skeletons):
        raise KnowActValidationError("Node skeleton reconciliation record count must match skeleton count")

    draft_ids = {draft.draft_id for draft in drafts}
    segment_ids = {draft.segment_id for draft in drafts}
    skeleton_ids = [record.id for record in result.records]
    duplicate_ids = _duplicates(skeleton_ids)
    if duplicate_ids:
        raise KnowActValidationError(f"Duplicate reconciled node skeleton ids: {sorted(duplicate_ids)}")

    for record, skeleton in zip(result.records, result.source_grounded_node_skeletons, strict=True):
        if record.id != skeleton.id:
            raise KnowActValidationError(
                f"Node skeleton reconciliation record {record.id} does not match skeleton {skeleton.id}"
            )
        unknown_drafts = set(record.supporting_draft_ids) - draft_ids
        if unknown_drafts:
            raise KnowActValidationError(
                f"Node skeleton reconciliation record {record.id} references unknown drafts: {sorted(unknown_drafts)}"
            )
        unknown_segments = set(record.supporting_segment_ids) - segment_ids
        if unknown_segments:
            raise KnowActValidationError(
                f"Node skeleton reconciliation record {record.id} references unknown segments: {sorted(unknown_segments)}"
            )


def validate_source_grounded_node_skeletons(
    skeletons: Sequence[SourceGroundedNodeSkeleton],
) -> None:
    if not skeletons:
        raise KnowActValidationError("Source-grounded node skeleton validation received no skeletons")

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


def canonicalize_candidate_edges(edges: Sequence[KnowledgeEdge]) -> tuple[KnowledgeEdge, ...]:
    return tuple(_canonicalize_candidate_edge(edge) for edge in edges)


def _duplicates(values: Sequence[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _canonicalize_candidate_edge(edge: KnowledgeEdge) -> KnowledgeEdge:
    if edge.type != KnowledgeEdgeType.CONTRASTS_WITH:
        return edge

    source, target = sorted((edge.source, edge.target))
    return edge.model_copy(
        update={
            "id": f"edge_{source}_{edge.type.value}_{target}",
            "source": source,
            "target": target,
        }
    )


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()
