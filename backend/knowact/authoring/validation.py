from collections.abc import Sequence
import re

from backend.knowact.core.graph import KnowledgeEdge, KnowledgeEdgeType, KnowledgeGraph, KnowledgeNode
from backend.knowact.core.map import MasteryLevel
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.graph import validate_knowledge_graph
from backend.knowact.authoring.schemas import (
    GraphAuthoringScope,
    NodeSkeletonReconciliationResult,
    NodeSkeletonVerificationResult,
    ParsedSourceSegment,
    SegmentNodeExtractionDraft,
    SegmentNodeExtractionDraftPatch,
    SourceGroundedNodeSkeleton,
)


REQUIRED_MASTERY_LEVELS = {level.value for level in MasteryLevel}
MAX_SEGMENT_NODE_EXTRACTION_DRAFTS = 12


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
    draft_counts_by_segment: dict[str, int] = {}
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
        if not _evidence_excerpt_matches(draft.evidence_excerpt, segment.text):
            raise KnowActValidationError(
                f"Segment node extraction draft {draft.draft_id} evidence excerpt was not found in segment {segment.segment_id}"
            )
        draft_counts_by_segment[draft.segment_id] = (
            draft_counts_by_segment.get(draft.segment_id, 0) + 1
        )

    over_budget_segments = {
        segment_id: count
        for segment_id, count in draft_counts_by_segment.items()
        if count > MAX_SEGMENT_NODE_EXTRACTION_DRAFTS
    }
    if over_budget_segments:
        raise KnowActValidationError(
            "Segment node extraction exceeded the per-segment draft limit: "
            f"{over_budget_segments}; maximum={MAX_SEGMENT_NODE_EXTRACTION_DRAFTS}"
        )


def validate_segment_node_extraction_draft_patches(
    patches: Sequence[SegmentNodeExtractionDraftPatch],
    segment: ParsedSourceSegment,
) -> None:
    """Validate one model response before it enters global draft assembly."""

    if len(patches) > MAX_SEGMENT_NODE_EXTRACTION_DRAFTS:
        raise KnowActValidationError(
            f"Segment {segment.segment_id} returned {len(patches)} drafts; "
            f"maximum={MAX_SEGMENT_NODE_EXTRACTION_DRAFTS}"
        )
    for patch_index, patch in enumerate(patches, start=1):
        if not _evidence_excerpt_matches(patch.evidence_excerpt, segment.text):
            raise KnowActValidationError(
                f"Segment {segment.segment_id} draft patch {patch_index} evidence_excerpt "
                f"was not found in the segment: {patch.evidence_excerpt!r}"
            )


def validate_node_skeleton_reconciliation_result(
    result: NodeSkeletonReconciliationResult,
    drafts: Sequence[SegmentNodeExtractionDraft],
    scope: GraphAuthoringScope | None = None,
) -> None:
    validate_source_grounded_node_skeletons(result.source_grounded_node_skeletons)

    if len(result.records) != len(result.source_grounded_node_skeletons):
        raise KnowActValidationError("Node skeleton reconciliation record count must match skeleton count")
    if scope is not None and len(result.records) > scope.max_node_count:
        raise KnowActValidationError(
            "Node skeleton reconciliation exceeded max_node_count: "
            f"{len(result.records)} > {scope.max_node_count}"
        )

    drafts_by_id = {draft.draft_id: draft for draft in drafts}
    draft_ids = set(drafts_by_id)
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
        supporting_drafts = tuple(
            drafts_by_id[draft_id] for draft_id in record.supporting_draft_ids
        )
        unknown_segments = set(record.supporting_segment_ids) - segment_ids
        if unknown_segments:
            raise KnowActValidationError(
                f"Node skeleton reconciliation record {record.id} references unknown segments: {sorted(unknown_segments)}"
            )
        expected_supporting_segments = {draft.segment_id for draft in supporting_drafts}
        if set(record.supporting_segment_ids) != expected_supporting_segments:
            raise KnowActValidationError(
                f"Node skeleton reconciliation record {record.id} segment provenance does not match supporting drafts"
            )
        supporting_evidence = {draft.evidence_excerpt for draft in supporting_drafts}
        unknown_evidence = set(record.evidence_excerpts) - supporting_evidence
        if unknown_evidence:
            raise KnowActValidationError(
                f"Node skeleton reconciliation record {record.id} contains evidence not present in its supporting drafts"
            )
        if record.evidence_excerpts != skeleton.source_evidence_excerpts:
            raise KnowActValidationError(
                f"Node skeleton reconciliation record {record.id} evidence does not match skeleton evidence"
            )


def validate_node_skeleton_verification_result(
    result: NodeSkeletonVerificationResult,
    skeletons: Sequence[SourceGroundedNodeSkeleton],
    scope: GraphAuthoringScope,
) -> None:
    input_ids = [skeleton.id for skeleton in skeletons]
    decision_ids = [decision.id for decision in result.decisions]
    if len(decision_ids) != len(set(decision_ids)):
        raise KnowActValidationError("Node skeleton verification contains duplicate decision ids")
    if set(decision_ids) != set(input_ids):
        missing = set(input_ids) - set(decision_ids)
        extra = set(decision_ids) - set(input_ids)
        raise KnowActValidationError(
            f"Node skeleton verification decisions do not match inputs; missing={sorted(missing)} extra={sorted(extra)}"
        )

    for decision in result.decisions:
        if decision.decision == "keep" and (
            decision.grounding_status != "supported"
            or decision.scope_status != "in_scope"
            or decision.diagnostic_value == "low"
        ):
            raise KnowActValidationError(
                f"Node skeleton verification keep decision for {decision.id} violates keep criteria"
            )

    expected_kept_ids = {
        decision.id for decision in result.decisions if decision.decision == "keep"
    }
    actual_kept_ids = [skeleton.id for skeleton in result.verified_skeletons]
    if set(actual_kept_ids) != expected_kept_ids or len(actual_kept_ids) != len(expected_kept_ids):
        raise KnowActValidationError(
            "Verified skeletons do not match node skeleton verification keep decisions"
        )
    if not result.verified_skeletons:
        raise KnowActValidationError("Node skeleton verification kept no skeletons")
    if len(result.verified_skeletons) > scope.max_node_count:
        raise KnowActValidationError(
            "Node skeleton verification exceeded max_node_count: "
            f"{len(result.verified_skeletons)} > {scope.max_node_count}"
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


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _evidence_excerpt_matches(excerpt: str, segment_text: str) -> bool:
    """Match verbatim evidence while tolerating PDF-to-Markdown line wrapping.

    A PDF line break can split a word as ``func-\ntional`` or wrap a genuine
    compound as ``non-\nparametric``. Both are layout artifacts, so matching
    checks the raw whitespace-normalized text plus the two defensible line-wrap
    interpretations. No general punctuation or word changes are allowed.
    """

    excerpt_variants = _line_wrap_variants(excerpt)
    segment_variants = _line_wrap_variants(segment_text)
    return any(
        excerpt_variant in segment_variant
        for excerpt_variant in excerpt_variants
        for segment_variant in segment_variants
    )


def _line_wrap_variants(value: str) -> set[str]:
    wrapped_hyphen = r"(?<=[A-Za-z])-[ \t]*\r?\n[ \t]*(?=[a-z])"
    values = (value, _strip_pdf_margin_annotations(value))
    return {
        normalized
        for candidate in values
        for normalized in (
            _normalized_text(candidate),
            _normalized_text(re.sub(wrapped_hyphen, "-", candidate)),
            _normalized_text(re.sub(wrapped_hyphen, "", candidate)),
            _normalized_text(
                re.sub(
                    r"(?<=[—–])[ \t]*\r?\n[ \t]*(?=[A-Za-z])",
                    "",
                    candidate,
                )
            ),
        )
    }


def _strip_pdf_margin_annotations(value: str) -> str:
    """Remove narrowly recognizable margin-glossary intrusions for matching.

    Miner-style PDF text sometimes inserts a short, far-right glossary label
    between two prose lines. A continuation can also appear after a word that
    was hyphenated at the physical line boundary. This creates strings such as
    ``sin- regression\ngle``. The rules below target only those layout shapes;
    the stored source and model evidence remain unchanged and auditable.
    """

    lines = value.splitlines()
    kept: list[str] = []
    pending_margin_annotation: str | None = None
    for index, line in enumerate(lines):
        stripped = line.lstrip(" \t")
        indentation = len(line) - len(stripped)
        if indentation >= 40 and len(stripped) <= 80:
            pending_margin_annotation = stripped
            continue

        next_line = lines[index + 1].lstrip(" \t") if index + 1 < len(lines) else ""
        if next_line[:1].islower():
            margin_after_hyphen = re.match(
                r"^(.+[A-Za-z]-)[ \t]+[A-Za-z][A-Za-z -]{0,60}$",
                line,
            )
            if margin_after_hyphen is not None:
                line = margin_after_hyphen.group(1)
            elif pending_margin_annotation:
                for suffix_word_count in range(1, 4):
                    suffix_match = re.search(
                        rf"(?:[ \t]+[A-Za-z-]+){{{suffix_word_count}}}$",
                        line,
                    )
                    if suffix_match is None:
                        continue
                    suffix = " ".join(suffix_match.group(0).split())
                    line_without_suffix = line[: suffix_match.start()]
                    label = _normalized_text(f"{pending_margin_annotation} {suffix}").lower()
                    prose_context = _normalized_text(
                        "\n".join((*kept[-2:], line_without_suffix))
                    ).lower()
                    if label in prose_context:
                        line = line_without_suffix
                        break
        kept.append(line)
        pending_margin_annotation = None
    return "\n".join(kept)
