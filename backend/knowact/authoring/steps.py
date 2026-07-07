from collections.abc import Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
import re
from time import monotonic
from typing import Callable
from typing import Protocol

from pydantic import BaseModel

from backend.knowact.authoring.logging import (
    WorkflowRunAgentTrace,
    WorkflowRunAgentTraceBatch,
    WorkflowRunParserResult,
    redact_logged_text,
    workflow_run_error_from_exception,
)
from backend.knowact.authoring.parsers.graph_authoring import (
    AuthoringOutputParseError,
    parse_edge_proposal_output,
    parse_node_skeleton_reconciliation_output,
    parse_node_rubric_authoring_output,
    parse_segment_node_extraction_output,
)
from backend.knowact.authoring.segments import derive_parsed_source_segments
from backend.knowact.authoring.schemas import (
    EdgeProposalInput,
    NodeSkeletonReconciliationRecord,
    NodeSkeletonReconciliationResult,
    NodeRubricAuthoringInput,
    NodeRubricAuthoringResult,
    NodeRubricPatch,
    ParsedSourceSegment,
    ReconciledNodeSkeletonDraft,
    SegmentNodeExtractionDraft,
    SegmentNodeExtractionDraftPatch,
    SourceGroundedNodeSkeleton,
    SourceMaterial,
)
from backend.knowact.authoring.templates.edge_proposal import build_edge_proposal_messages
from backend.knowact.authoring.templates.node_extraction import build_node_extraction_messages
from backend.knowact.authoring.templates.node_skeleton_reconciliation import (
    build_node_skeleton_reconciliation_messages,
)
from backend.knowact.authoring.templates.node_rubric_authoring import (
    build_node_rubric_authoring_messages,
)
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeNode, SourceLocator
from backend.knowact.llm.client import ModelClient
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessageProfile
from backend.knowact.logging_config import get_knowact_logger


AgentStepParser = Callable[[str], tuple[BaseModel, ...]]
AgentStepOutputSerializer = Callable[[tuple[BaseModel, ...]], dict[str, object]]
DEFAULT_SEGMENT_NODE_EXTRACTION_MAX_CONCURRENT_REQUESTS = 8
SEGMENT_NODE_EXTRACTION_PROGRESS_LOG_INTERVAL_SECONDS = 30.0
_LOGGER = get_knowact_logger("authoring.steps")


class NodeExtractionStep(Protocol):
    def run(self, source_materials: Sequence[SourceMaterial]) -> tuple[SourceGroundedNodeSkeleton, ...]:
        """Extract source-grounded node skeletons from authoritative source material."""


class SegmentNodeExtractionStep(Protocol):
    def run(self, segments: Sequence[ParsedSourceSegment]) -> tuple[SegmentNodeExtractionDraft, ...]:
        """Extract thin node drafts from parsed source segments."""


class NodeSkeletonReconciliationStep(Protocol):
    def run(
        self,
        drafts: Sequence[SegmentNodeExtractionDraft],
    ) -> NodeSkeletonReconciliationResult:
        """Reconcile segment-level node drafts into source-grounded node skeletons."""


class NodeRubricAuthoringStep(Protocol):
    def run(
        self,
        input_data: NodeRubricAuthoringInput,
    ) -> NodeRubricAuthoringResult:
        """Turn node skeletons into complete candidate Knowledge Nodes."""


class EdgeProposalStep(Protocol):
    def run(
        self,
        input_data: EdgeProposalInput,
    ) -> tuple[KnowledgeEdge, ...]:
        """Propose precision-first candidate Knowledge Edges."""


class LLMNodeExtractionStep:
    def __init__(
        self,
        model_client: ModelClient,
        *,
        segment_max_concurrent_requests: int = DEFAULT_SEGMENT_NODE_EXTRACTION_MAX_CONCURRENT_REQUESTS,
    ) -> None:
        self._model_client = model_client
        self._segment_max_concurrent_requests = _validate_positive_int(
            segment_max_concurrent_requests,
            "segment_max_concurrent_requests",
        )
        self.last_trace: WorkflowRunAgentTrace | None = None

    def run(self, source_materials: Sequence[SourceMaterial]) -> tuple[SourceGroundedNodeSkeleton, ...]:
        segment_step = LLMSegmentNodeExtractionStep(
            self._model_client,
            max_concurrent_requests=self._segment_max_concurrent_requests,
        )
        reconciliation_step = LLMNodeSkeletonReconciliationStep(self._model_client)
        drafts = segment_step.run(derive_parsed_source_segments(source_materials))
        result = reconciliation_step.run(drafts)
        self.last_trace = reconciliation_step.last_trace
        return result.source_grounded_node_skeletons

    def _set_last_trace(self, trace: WorkflowRunAgentTrace | None) -> None:
        self.last_trace = trace


class LLMSegmentNodeExtractionStep:
    def __init__(
        self,
        model_client: ModelClient,
        *,
        max_concurrent_requests: int = DEFAULT_SEGMENT_NODE_EXTRACTION_MAX_CONCURRENT_REQUESTS,
    ) -> None:
        self._model_client = model_client
        self._max_concurrent_requests = _validate_positive_int(
            max_concurrent_requests,
            "max_concurrent_requests",
        )
        self.last_trace: WorkflowRunAgentTrace | None = None

    def run(self, segments: Sequence[ParsedSourceSegment]) -> tuple[SegmentNodeExtractionDraft, ...]:
        return _run_traced_segment_node_extraction_step(
            model_client=self._model_client,
            segments=tuple(segments),
            trace_setter=self._set_last_trace,
            message_profile=_message_profile_for(self._model_client),
            max_concurrent_requests=self._max_concurrent_requests,
        )

    def _set_last_trace(self, trace: WorkflowRunAgentTrace | None) -> None:
        self.last_trace = trace


class LLMNodeSkeletonReconciliationStep:
    def __init__(self, model_client: ModelClient) -> None:
        self._model_client = model_client
        self.last_trace: WorkflowRunAgentTrace | None = None

    def run(
        self,
        drafts: Sequence[SegmentNodeExtractionDraft],
    ) -> NodeSkeletonReconciliationResult:
        reconciled_drafts = _run_traced_llm_step(
            model_client=self._model_client,
            messages=build_node_skeleton_reconciliation_messages(
                drafts,
                message_profile=_message_profile_for(self._model_client),
            ),
            parser=parse_node_skeleton_reconciliation_output,
            output_serializer=lambda skeletons: {
                "skeletons": _dump_models(skeletons),
            },
            step_name="node_skeleton_reconciliation",
            trace_setter=self._set_last_trace,
        )
        return _build_node_skeleton_reconciliation_result(reconciled_drafts)

    def _set_last_trace(self, trace: WorkflowRunAgentTrace | None) -> None:
        self.last_trace = trace


class LLMNodeRubricAuthoringStep:
    def __init__(self, model_client: ModelClient, *, batch_size: int = 8) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self._model_client = model_client
        self._batch_size = batch_size
        self.last_trace: WorkflowRunAgentTrace | None = None

    def run(
        self,
        input_data: NodeRubricAuthoringInput,
    ) -> NodeRubricAuthoringResult:
        rubric_patches = _run_traced_batched_node_rubric_authoring_step(
            model_client=self._model_client,
            input_data=input_data,
            batch_size=self._batch_size,
            trace_setter=self._set_last_trace,
            message_profile=_message_profile_for(self._model_client),
        )
        candidate_nodes = _complete_candidate_nodes_from_rubrics(
            rubric_patches,
            input_data.skeletons,
        )
        return NodeRubricAuthoringResult(
            rubric_patches=tuple(rubric_patches),
            candidate_nodes=candidate_nodes,
        )

    def _set_last_trace(self, trace: WorkflowRunAgentTrace | None) -> None:
        self.last_trace = trace


class LLMEdgeProposalStep:
    def __init__(self, model_client: ModelClient) -> None:
        self._model_client = model_client
        self.last_trace: WorkflowRunAgentTrace | None = None

    def run(
        self,
        input_data: EdgeProposalInput,
    ) -> tuple[KnowledgeEdge, ...]:
        return _run_traced_llm_step(
            model_client=self._model_client,
            messages=build_edge_proposal_messages(
                input_data,
                message_profile=_message_profile_for(self._model_client),
            ),
            parser=parse_edge_proposal_output,
            output_serializer=lambda edges: {
                "edges": _dump_models(edges),
            },
            step_name="edge_proposal",
            trace_setter=self._set_last_trace,
        )

    def _set_last_trace(self, trace: WorkflowRunAgentTrace | None) -> None:
        self.last_trace = trace


def get_authoring_agent_step_trace(step: object) -> WorkflowRunAgentTrace | None:
    trace = getattr(step, "last_trace", None)
    if isinstance(trace, WorkflowRunAgentTrace):
        return trace
    return None


def _message_profile_for(model_client: ModelClient) -> ModelMessageProfile:
    return getattr(model_client, "message_profile", OPENAI_MESSAGE_PROFILE)


def _validate_positive_int(value: int, name: str) -> int:
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def _run_traced_llm_step(
    *,
    model_client: ModelClient,
    messages,
    parser: AgentStepParser,
    output_serializer: AgentStepOutputSerializer,
    step_name: str,
    trace_setter: Callable[[WorkflowRunAgentTrace | None], None],
) -> tuple[BaseModel, ...]:
    trace_setter(None)
    raw_output = model_client.complete(messages=messages)
    redacted_raw_output = redact_logged_text(raw_output)

    try:
        parsed_output = parser(raw_output)
    except Exception as exc:
        trace_setter(
            WorkflowRunAgentTrace(
                model_raw_output=redacted_raw_output,
                parser_result=WorkflowRunParserResult(
                    status="failed",
                    error=workflow_run_error_from_exception(exc, step_name=step_name),
                ),
            )
        )
        raise

    trace_setter(
        WorkflowRunAgentTrace(
            model_raw_output=redacted_raw_output,
            parser_result=WorkflowRunParserResult(
                status="succeeded",
                output=output_serializer(parsed_output),
            ),
        )
    )
    return parsed_output


def _run_traced_segment_node_extraction_step(
    *,
    model_client: ModelClient,
    segments: tuple[ParsedSourceSegment, ...],
    trace_setter: Callable[[WorkflowRunAgentTrace | None], None],
    message_profile: ModelMessageProfile,
    max_concurrent_requests: int,
) -> tuple[SegmentNodeExtractionDraft, ...]:
    trace_setter(None)
    total_segments = len(segments)
    max_workers = min(max_concurrent_requests, total_segments) if total_segments else 1
    step_started_at = monotonic()

    _LOGGER.info(
        "Segment node extraction started segments=%s total_char_count=%s max_concurrent_requests=%s",
        total_segments,
        sum(segment.char_count for segment in segments),
        max_workers,
    )

    completed_results: dict[int, _SegmentNodeExtractionResult] = {}
    completed_draft_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: dict[Future[_SegmentNodeExtractionResult], int] = {
            executor.submit(
                _extract_segment_node_patches,
                model_client=model_client,
                message_profile=message_profile,
                segment=segment,
                segment_index=segment_index,
                total_segments=total_segments,
            ): segment_index
            for segment_index, segment in enumerate(segments, start=1)
        }
        pending_futures = set(futures)

        try:
            while pending_futures:
                done_futures, pending_futures = wait(
                    pending_futures,
                    timeout=SEGMENT_NODE_EXTRACTION_PROGRESS_LOG_INTERVAL_SECONDS,
                    return_when=FIRST_COMPLETED,
                )
                if not done_futures:
                    _log_segment_node_extraction_progress(
                        total_segments=total_segments,
                        completed_segments=len(completed_results),
                        active_or_queued_segments=len(pending_futures),
                        total_drafts=completed_draft_count,
                        max_concurrent_requests=max_workers,
                        elapsed_seconds=monotonic() - step_started_at,
                    )
                    continue

                for future in done_futures:
                    result = future.result()
                    completed_results[result.segment_index] = result
                    completed_draft_count += len(result.parsed_patches)
                    remaining_segments = total_segments - len(completed_results)
                    _LOGGER.info(
                        "Segment node extraction segment succeeded segment_index=%s segment_total=%s segment_id=%s draft_count=%s total_drafts=%s completed_segments=%s remaining_segments=%s active_or_queued_segments=%s elapsed_seconds=%.3f",
                        result.segment_index,
                        total_segments,
                        result.segment.segment_id,
                        len(result.parsed_patches),
                        completed_draft_count,
                        len(completed_results),
                        remaining_segments,
                        len(pending_futures),
                        result.elapsed_seconds,
                    )
        except _SegmentNodeExtractionFailure as failure:
            for pending_future in pending_futures:
                pending_future.cancel()
            _LOGGER.error(
                "Segment node extraction segment failed segment_index=%s segment_total=%s segment_id=%s completed_segments=%s remaining_segments=%s elapsed_seconds=%.3f error_type=%s message=%s",
                failure.segment_index,
                total_segments,
                failure.segment.segment_id,
                len(completed_results),
                total_segments - len(completed_results),
                failure.elapsed_seconds,
                failure.cause.__class__.__name__,
                str(failure.cause),
            )
            failed_trace = _segment_failure_batch_trace(failure)
            trace_setter(
                WorkflowRunAgentTrace(
                    parser_result=WorkflowRunParserResult(
                        status="failed",
                        error=workflow_run_error_from_exception(
                            failure.cause,
                            step_name="node_extraction",
                        ),
                    ),
                    batch_traces=(
                        *_build_segment_batch_traces(
                            segments=segments,
                            completed_results=completed_results,
                        ),
                        failed_trace,
                    ),
                )
            )
            raise failure.cause from failure

    drafts = _build_segment_drafts_in_order(
        segments=segments,
        completed_results=completed_results,
    )
    batch_traces = _build_segment_batch_traces(
        segments=segments,
        completed_results=completed_results,
    )
    trace_setter(
        WorkflowRunAgentTrace(
            parser_result=WorkflowRunParserResult(
                status="succeeded",
                output={"drafts": _dump_models(tuple(drafts))},
            ),
            batch_traces=tuple(batch_traces),
        )
    )
    _LOGGER.info(
        "Segment node extraction succeeded segments=%s total_drafts=%s elapsed_seconds=%.3f",
        total_segments,
        len(drafts),
        monotonic() - step_started_at,
    )
    return tuple(drafts)


def _log_segment_node_extraction_progress(
    *,
    total_segments: int,
    completed_segments: int,
    active_or_queued_segments: int,
    total_drafts: int,
    max_concurrent_requests: int,
    elapsed_seconds: float,
) -> None:
    _LOGGER.info(
        "Segment node extraction progress completed_segments=%s segment_total=%s remaining_segments=%s active_or_queued_segments=%s total_drafts=%s max_concurrent_requests=%s elapsed_seconds=%.3f",
        completed_segments,
        total_segments,
        total_segments - completed_segments,
        active_or_queued_segments,
        total_drafts,
        max_concurrent_requests,
        elapsed_seconds,
    )


@dataclass(frozen=True)
class _SegmentNodeExtractionResult:
    segment_index: int
    segment: ParsedSourceSegment
    redacted_raw_output: str
    parsed_patches: tuple[SegmentNodeExtractionDraftPatch, ...]
    elapsed_seconds: float


class _SegmentNodeExtractionFailure(Exception):
    def __init__(
        self,
        *,
        segment_index: int,
        segment: ParsedSourceSegment,
        redacted_raw_output: str | None,
        elapsed_seconds: float,
        cause: Exception,
    ) -> None:
        super().__init__(str(cause))
        self.segment_index = segment_index
        self.segment = segment
        self.redacted_raw_output = redacted_raw_output
        self.elapsed_seconds = elapsed_seconds
        self.cause = cause


def _extract_segment_node_patches(
    *,
    model_client: ModelClient,
    message_profile: ModelMessageProfile,
    segment: ParsedSourceSegment,
    segment_index: int,
    total_segments: int,
) -> _SegmentNodeExtractionResult:
    segment_started_at = monotonic()
    _LOGGER.info(
        "Segment node extraction segment started segment_index=%s segment_total=%s segment_id=%s source_id=%s char_count=%s location=%s",
        segment_index,
        total_segments,
        segment.segment_id,
        segment.source_id,
        segment.char_count,
        segment.location,
    )

    redacted_raw_output: str | None = None
    try:
        raw_output = model_client.complete(
            messages=build_node_extraction_messages(
                segment,
                message_profile=message_profile,
            )
        )
        redacted_raw_output = redact_logged_text(raw_output)
        parsed_patches = parse_segment_node_extraction_output(raw_output)
    except Exception as exc:
        raise _SegmentNodeExtractionFailure(
            segment_index=segment_index,
            segment=segment,
            redacted_raw_output=redacted_raw_output,
            elapsed_seconds=monotonic() - segment_started_at,
            cause=exc,
        ) from exc

    return _SegmentNodeExtractionResult(
        segment_index=segment_index,
        segment=segment,
        redacted_raw_output=redacted_raw_output,
        parsed_patches=tuple(parsed_patches),
        elapsed_seconds=monotonic() - segment_started_at,
    )


def _build_segment_drafts_in_order(
    *,
    segments: tuple[ParsedSourceSegment, ...],
    completed_results: dict[int, _SegmentNodeExtractionResult],
) -> tuple[SegmentNodeExtractionDraft, ...]:
    drafts: list[SegmentNodeExtractionDraft] = []
    for segment_index, segment in enumerate(segments, start=1):
        result = completed_results[segment_index]
        drafts.extend(
            _segment_drafts_from_patches(
                result.parsed_patches,
                segment=segment,
                start_index=len(drafts) + 1,
            )
        )
    return tuple(drafts)


def _build_segment_batch_traces(
    *,
    segments: tuple[ParsedSourceSegment, ...],
    completed_results: dict[int, _SegmentNodeExtractionResult],
) -> tuple[WorkflowRunAgentTraceBatch, ...]:
    traces: list[WorkflowRunAgentTraceBatch] = []
    draft_start_index = 1
    for segment_index, segment in enumerate(segments, start=1):
        result = completed_results.get(segment_index)
        if result is None:
            continue
        segment_drafts = _segment_drafts_from_patches(
            result.parsed_patches,
            segment=segment,
            start_index=draft_start_index,
        )
        draft_start_index += len(segment_drafts)
        traces.append(
            WorkflowRunAgentTraceBatch(
                batch_name=segment.segment_id,
                input_counts={"segments": 1, "char_count": segment.char_count},
                model_raw_output=result.redacted_raw_output,
                parser_result=WorkflowRunParserResult(
                    status="succeeded",
                    output={"drafts": _dump_models(tuple(segment_drafts))},
                ),
            )
        )
    return tuple(traces)


def _segment_failure_batch_trace(
    failure: _SegmentNodeExtractionFailure,
) -> WorkflowRunAgentTraceBatch:
    return WorkflowRunAgentTraceBatch(
        batch_name=failure.segment.segment_id,
        input_counts={"segments": 1, "char_count": failure.segment.char_count},
        model_raw_output=failure.redacted_raw_output,
        parser_result=WorkflowRunParserResult(
            status="failed",
            error=workflow_run_error_from_exception(
                failure.cause,
                step_name="node_extraction",
            ),
        ),
    )


def _segment_drafts_from_patches(
    patches: Sequence[SegmentNodeExtractionDraftPatch],
    *,
    segment: ParsedSourceSegment,
    start_index: int,
) -> tuple[SegmentNodeExtractionDraft, ...]:
    return tuple(
        SegmentNodeExtractionDraft(
            draft_id=f"draft_{index:06d}",
            segment_id=segment.segment_id,
            name=patch.name,
            definition=patch.definition,
            source_locator=SourceLocator(
                source_id=segment.source_id,
                locator=patch.source_locator.locator,
                note=patch.source_locator.note,
            ),
            grounding_note=patch.grounding_note,
        )
        for index, patch in enumerate(patches, start=start_index)
    )


def _build_node_skeleton_reconciliation_result(
    skeleton_drafts: Sequence[ReconciledNodeSkeletonDraft],
) -> NodeSkeletonReconciliationResult:
    records: list[NodeSkeletonReconciliationRecord] = []
    skeletons: list[SourceGroundedNodeSkeleton] = []
    for draft in skeleton_drafts:
        node_id = _node_id_from_name(draft.name)
        records.append(
            NodeSkeletonReconciliationRecord(
                id=node_id,
                name=draft.name,
                definition=draft.definition,
                source_locators=draft.source_locators,
                grounding_notes=draft.grounding_notes,
                supporting_draft_ids=draft.supporting_draft_ids,
                supporting_segment_ids=draft.supporting_segment_ids,
                merge_split_note=draft.merge_split_note,
            )
        )
        skeletons.append(
            SourceGroundedNodeSkeleton(
                id=node_id,
                name=draft.name,
                definition=draft.definition,
                source_locators=draft.source_locators,
                source_grounding_notes=draft.grounding_notes,
            )
        )
    return NodeSkeletonReconciliationResult(
        records=tuple(records),
        source_grounded_node_skeletons=tuple(skeletons),
    )


def _run_traced_batched_node_rubric_authoring_step(
    *,
    model_client: ModelClient,
    input_data: NodeRubricAuthoringInput,
    batch_size: int,
    trace_setter: Callable[[WorkflowRunAgentTrace | None], None],
    message_profile: ModelMessageProfile,
) -> tuple[NodeRubricPatch, ...]:
    trace_setter(None)
    rubric_patches: list[NodeRubricPatch] = []
    batch_traces: list[WorkflowRunAgentTraceBatch] = []

    for batch_index, skeleton_batch in enumerate(
        _batches(input_data.skeletons, batch_size),
        start=1,
    ):
        batch_name = f"batch_{batch_index:03d}"
        raw_output = model_client.complete(
            messages=build_node_rubric_authoring_messages(
                NodeRubricAuthoringInput(skeletons=skeleton_batch),
                message_profile=message_profile,
            )
        )
        redacted_raw_output = redact_logged_text(raw_output)

        try:
            parsed_batch = parse_node_rubric_authoring_output(raw_output)
        except Exception as exc:
            batch_traces.append(
                WorkflowRunAgentTraceBatch(
                    batch_name=batch_name,
                    input_counts={"skeletons": len(skeleton_batch)},
                    model_raw_output=redacted_raw_output,
                    parser_result=WorkflowRunParserResult(
                        status="failed",
                        error=workflow_run_error_from_exception(
                            exc,
                            step_name="node_rubric_authoring",
                        ),
                    ),
                )
            )
            trace_setter(
                WorkflowRunAgentTrace(
                    parser_result=WorkflowRunParserResult(
                        status="failed",
                        error=workflow_run_error_from_exception(
                            exc,
                            step_name="node_rubric_authoring",
                        ),
                    ),
                    batch_traces=tuple(batch_traces),
                )
            )
            raise

        rubric_patches.extend(parsed_batch)
        batch_traces.append(
            WorkflowRunAgentTraceBatch(
                batch_name=batch_name,
                input_counts={"skeletons": len(skeleton_batch)},
                model_raw_output=redacted_raw_output,
                parser_result=WorkflowRunParserResult(
                    status="succeeded",
                    output={"nodes": _dump_models(parsed_batch)},
                ),
            )
        )

    trace_setter(
        WorkflowRunAgentTrace(
            parser_result=WorkflowRunParserResult(
                status="succeeded",
                output={"nodes": _dump_models(tuple(rubric_patches))},
            ),
            batch_traces=tuple(batch_traces),
        )
    )
    return tuple(rubric_patches)


def _dump_models(items: tuple[BaseModel, ...]) -> list[dict[str, object]]:
    return [item.model_dump(mode="json", exclude_none=True) for item in items]


def _batches(
    items: Sequence[SourceGroundedNodeSkeleton],
    batch_size: int,
) -> tuple[tuple[SourceGroundedNodeSkeleton, ...], ...]:
    return tuple(
        tuple(items[index : index + batch_size])
        for index in range(0, len(items), batch_size)
    )


def _complete_candidate_nodes_from_rubrics(
    rubric_patches: Sequence[NodeRubricPatch],
    skeletons: Sequence[SourceGroundedNodeSkeleton],
) -> tuple[KnowledgeNode, ...]:
    duplicate_skeleton_ids = _duplicates([skeleton.id for skeleton in skeletons])
    if duplicate_skeleton_ids:
        raise AuthoringOutputParseError(
            f"Duplicate input skeleton ids: {sorted(duplicate_skeleton_ids)}"
        )

    duplicate_rubric_ids = _duplicates([rubric.id for rubric in rubric_patches])
    if duplicate_rubric_ids:
        raise AuthoringOutputParseError(
            f"Duplicate node rubric ids: {sorted(duplicate_rubric_ids)}"
        )

    skeleton_by_id = {skeleton.id: skeleton for skeleton in skeletons}
    rubric_by_id = {rubric.id: rubric for rubric in rubric_patches}
    missing_rubrics = set(skeleton_by_id) - set(rubric_by_id)
    extra_rubrics = set(rubric_by_id) - set(skeleton_by_id)
    if missing_rubrics:
        raise AuthoringOutputParseError(
            f"Missing node rubrics for skeletons: {sorted(missing_rubrics)}"
        )
    if extra_rubrics:
        raise AuthoringOutputParseError(
            f"Node rubrics not grounded in skeletons: {sorted(extra_rubrics)}"
        )

    nodes: list[KnowledgeNode] = []
    for skeleton in skeletons:
        rubric = rubric_by_id[skeleton.id]
        nodes.append(
            KnowledgeNode(
                id=skeleton.id,
                name=skeleton.name,
                type=skeleton.type,
                definition=skeleton.definition,
                source_locators=skeleton.source_locators,
                diagnostic_goal=rubric.diagnostic_goal,
                levels=rubric.levels,
                diagnostic_signals=rubric.diagnostic_signals,
                simulator_behavior=rubric.simulator_behavior,
            )
        )
    return tuple(nodes)


def _duplicates(values: Sequence[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _node_id_from_name(name: str) -> str:
    node_id = re.sub(r"[^A-Za-z0-9]+", "_", name.strip().lower()).strip("_")
    node_id = re.sub(r"_+", "_", node_id)
    if not node_id:
        raise AuthoringOutputParseError(f"Could not derive node id from name: {name!r}")
    return node_id
