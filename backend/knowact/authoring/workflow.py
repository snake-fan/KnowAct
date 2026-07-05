from collections.abc import Callable, Sequence
from typing import Protocol, TypeVar

from backend.knowact.authoring.logging import (
    GRAPH_AUTHORING_WORKFLOW_NAME,
    GraphAuthoringRunLogBuilder,
    GraphAuthoringWorkflowRunError,
    GraphAuthoringWorkflowRunResult,
    RunLogSourceMaterial,
    WorkflowRunAgentTrace,
    WorkflowRunLogEntryType,
    WorkflowRunValidationResult,
    default_graph_authoring_run_id,
    workflow_run_error_from_exception,
)
from backend.knowact.authoring.schemas import (
    EdgeProposalInput,
    GraphAuthoringWorkflowResult,
    NodeSkeletonReconciliationResult,
    NodeRubricAuthoringInput,
    NodeRubricAuthoringResult,
    ParsedSourceSegment,
    SegmentNodeExtractionDraft,
    SourceMaterial,
)
from backend.knowact.authoring.segments import derive_parsed_source_segments
from backend.knowact.authoring.steps import (
    EdgeProposalStep,
    NodeExtractionStep,
    NodeSkeletonReconciliationStep,
    NodeRubricAuthoringStep,
    SegmentNodeExtractionStep,
    get_authoring_agent_step_trace,
)
from backend.knowact.authoring.validation import (
    canonicalize_candidate_edges,
    validate_candidate_edges,
    validate_complete_candidate_nodes,
    validate_node_skeleton_reconciliation_result,
    validate_parsed_source_segments,
    validate_segment_node_extraction_drafts,
    validate_source_grounded_node_skeletons,
)
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.logging_config import get_knowact_logger


T = TypeVar("T")
_LOGGER = get_knowact_logger("authoring.workflow")


class IntermediateArtifactWriter(Protocol):
    def write_parsed_source_segments(self, items) -> str:
        """Persist validated parsed source segments and return a run-relative URI."""

    def write_segment_node_extraction_drafts(self, items) -> str:
        """Persist validated segment-level node drafts and return a run-relative URI."""

    def write_node_skeleton_reconciliation(self, items) -> str:
        """Persist validated node skeleton reconciliation records and return a run-relative URI."""

    def write_source_grounded_node_skeletons(self, items) -> str:
        """Persist validated source-grounded skeletons and return a run-relative URI."""

    def write_node_rubric_patches(self, items) -> str:
        """Persist validated node rubric patches and return a run-relative URI."""

    def write_candidate_nodes_pre_edge(self, items) -> str:
        """Persist validated candidate nodes before edge proposal and return a run-relative URI."""

    def write_candidate_edges_canonical(self, items) -> str:
        """Persist validated canonical candidate edges and return a run-relative URI."""


class GraphAuthoringAgentWorkflow:
    def __init__(
        self,
        *,
        node_extraction_step: NodeExtractionStep | None = None,
        segment_node_extraction_step: SegmentNodeExtractionStep | None = None,
        node_skeleton_reconciliation_step: NodeSkeletonReconciliationStep | None = None,
        node_rubric_authoring_step: NodeRubricAuthoringStep,
        edge_proposal_step: EdgeProposalStep,
        model_metadata: ModelClientMetadata | None = None,
    ) -> None:
        if node_extraction_step is None and (
            segment_node_extraction_step is None or node_skeleton_reconciliation_step is None
        ):
            raise ValueError(
                "Either node_extraction_step or both segment_node_extraction_step and "
                "node_skeleton_reconciliation_step must be provided"
            )
        self._node_extraction_step = node_extraction_step
        self._segment_node_extraction_step = segment_node_extraction_step
        self._node_skeleton_reconciliation_step = node_skeleton_reconciliation_step
        self._node_rubric_authoring_step = node_rubric_authoring_step
        self._edge_proposal_step = edge_proposal_step
        self._model_metadata = model_metadata

    def run(self, source_materials: Sequence[SourceMaterial]) -> GraphAuthoringWorkflowResult:
        return self.run_with_log(
            source_materials,
            run_id=default_graph_authoring_run_id(),
        ).workflow_result

    def run_with_log(
        self,
        source_materials: Sequence[SourceMaterial],
        *,
        run_id: str,
        source_metadata: Sequence[RunLogSourceMaterial] | None = None,
        intermediate_artifact_writer: IntermediateArtifactWriter | None = None,
    ) -> GraphAuthoringWorkflowRunResult:
        source_materials = tuple(source_materials)
        _LOGGER.info(
            "Graph authoring workflow started run_id=%s source_materials=%d",
            run_id,
            len(source_materials),
        )
        builder = GraphAuthoringRunLogBuilder(
            run_id=run_id,
            workflow_name=GRAPH_AUTHORING_WORKFLOW_NAME,
            source_materials=source_materials,
            source_metadata=source_metadata,
            model_metadata=self._model_metadata,
        )

        skeletons = self._run_source_grounded_node_skeleton_authoring(
            builder=builder,
            source_materials=source_materials,
            run_id=run_id,
            intermediate_artifact_writer=intermediate_artifact_writer,
        )

        rubric_result = _run_logged_entry(
            builder,
            entry_name="node_rubric_authoring",
            entry_type="agent_step",
            input_counts={"skeletons": len(skeletons)},
            run_id=run_id,
            operation=lambda: self._node_rubric_authoring_step.run(
                NodeRubricAuthoringInput(skeletons=tuple(skeletons))
            ),
            output_counts=lambda value: {
                "node_rubric_patches": len(value.rubric_patches),
                "candidate_nodes": len(value.candidate_nodes),
            },
            trace_getter=lambda: get_authoring_agent_step_trace(self._node_rubric_authoring_step),
        )
        candidate_nodes = rubric_result.candidate_nodes
        _run_logged_entry(
            builder,
            entry_name="validate_complete_candidate_nodes",
            entry_type="validation_checkpoint",
            input_counts={"candidate_nodes": len(candidate_nodes), "skeletons": len(skeletons)},
            run_id=run_id,
            operation=lambda: validate_complete_candidate_nodes(candidate_nodes, skeletons),
            validation_result="passed",
            artifact_uris=lambda _: _write_candidate_node_artifacts(
                intermediate_artifact_writer,
                rubric_result,
            ),
        )

        candidate_edges = _run_logged_entry(
            builder,
            entry_name="edge_proposal",
            entry_type="agent_step",
            input_counts={"candidate_nodes": len(candidate_nodes), "skeletons": len(skeletons)},
            run_id=run_id,
            operation=lambda: self._edge_proposal_step.run(
                EdgeProposalInput(
                    candidate_nodes=tuple(candidate_nodes),
                    source_grounded_node_skeletons=tuple(skeletons),
                )
            ),
            output_counts=lambda value: {"candidate_edges": len(value)},
            trace_getter=lambda: get_authoring_agent_step_trace(self._edge_proposal_step),
        )
        candidate_edges = canonicalize_candidate_edges(candidate_edges)
        _run_logged_entry(
            builder,
            entry_name="validate_candidate_edges",
            entry_type="validation_checkpoint",
            input_counts={"candidate_nodes": len(candidate_nodes), "candidate_edges": len(candidate_edges)},
            run_id=run_id,
            operation=lambda: validate_candidate_edges(candidate_nodes, candidate_edges),
            validation_result="passed",
            artifact_uris=lambda _: _write_candidate_edge_artifacts(
                intermediate_artifact_writer,
                candidate_edges,
            ),
        )

        workflow_result = GraphAuthoringWorkflowResult(
            source_grounded_node_skeletons=tuple(skeletons),
            candidate_nodes=tuple(candidate_nodes),
            candidate_edges=tuple(candidate_edges),
        )
        _LOGGER.info(
            "Graph authoring workflow succeeded run_id=%s skeletons=%d candidate_nodes=%d candidate_edges=%d",
            run_id,
            len(skeletons),
            len(candidate_nodes),
            len(candidate_edges),
        )
        return GraphAuthoringWorkflowRunResult(
            workflow_result=workflow_result,
            run_log=builder.succeeded(),
        )

    def _run_source_grounded_node_skeleton_authoring(
        self,
        *,
        builder: GraphAuthoringRunLogBuilder,
        source_materials: tuple[SourceMaterial, ...],
        run_id: str,
        intermediate_artifact_writer: IntermediateArtifactWriter | None,
    ):
        if self._segment_node_extraction_step is None or self._node_skeleton_reconciliation_step is None:
            if self._node_extraction_step is None:
                raise RuntimeError("Graph authoring workflow has no node extraction path")
            return self._run_legacy_node_extraction(
                builder=builder,
                source_materials=source_materials,
                run_id=run_id,
                intermediate_artifact_writer=intermediate_artifact_writer,
            )

        segments = _run_logged_entry(
            builder,
            entry_name="derive_parsed_source_segments",
            entry_type="deterministic_step",
            input_counts={"source_materials": len(source_materials)},
            run_id=run_id,
            operation=lambda: derive_parsed_source_segments(source_materials),
            output_counts=lambda value: {"segments": len(value)},
            artifact_uris=lambda value: _write_parsed_source_segment_artifacts(
                intermediate_artifact_writer,
                value,
            ),
        )
        _run_logged_entry(
            builder,
            entry_name="validate_parsed_source_segments",
            entry_type="validation_checkpoint",
            input_counts={"segments": len(segments)},
            run_id=run_id,
            operation=lambda: validate_parsed_source_segments(segments),
            validation_result="passed",
        )

        drafts = _run_logged_entry(
            builder,
            entry_name="node_extraction",
            entry_type="agent_step",
            input_counts={"segments": len(segments)},
            run_id=run_id,
            operation=lambda: self._segment_node_extraction_step.run(segments),
            output_counts=lambda value: {"segment_node_extraction_drafts": len(value)},
            artifact_uris=lambda value: _write_segment_node_extraction_draft_artifacts(
                intermediate_artifact_writer,
                value,
            ),
            trace_getter=lambda: get_authoring_agent_step_trace(self._segment_node_extraction_step),
        )
        _run_logged_entry(
            builder,
            entry_name="validate_segment_node_extraction_drafts",
            entry_type="validation_checkpoint",
            input_counts={"segments": len(segments), "segment_node_extraction_drafts": len(drafts)},
            run_id=run_id,
            operation=lambda: validate_segment_node_extraction_drafts(drafts, segments),
            validation_result="passed",
        )

        reconciliation_result = _run_logged_entry(
            builder,
            entry_name="node_skeleton_reconciliation",
            entry_type="agent_step",
            input_counts={"segment_node_extraction_drafts": len(drafts)},
            run_id=run_id,
            operation=lambda: self._node_skeleton_reconciliation_step.run(drafts),
            output_counts=lambda value: {"skeletons": len(value.source_grounded_node_skeletons)},
            trace_getter=lambda: get_authoring_agent_step_trace(self._node_skeleton_reconciliation_step),
        )
        skeletons = reconciliation_result.source_grounded_node_skeletons
        _run_logged_entry(
            builder,
            entry_name="validate_source_grounded_node_skeletons",
            entry_type="validation_checkpoint",
            input_counts={"skeletons": len(skeletons), "segment_node_extraction_drafts": len(drafts)},
            run_id=run_id,
            operation=lambda: validate_node_skeleton_reconciliation_result(
                reconciliation_result,
                drafts,
            ),
            validation_result="passed",
            artifact_uris=lambda _: _write_reconciled_node_skeleton_artifacts(
                intermediate_artifact_writer,
                reconciliation_result,
            ),
        )
        return skeletons

    def _run_legacy_node_extraction(
        self,
        *,
        builder: GraphAuthoringRunLogBuilder,
        source_materials: tuple[SourceMaterial, ...],
        run_id: str,
        intermediate_artifact_writer: IntermediateArtifactWriter | None,
    ):
        skeletons = _run_logged_entry(
            builder,
            entry_name="node_extraction",
            entry_type="agent_step",
            input_counts={"source_materials": len(source_materials)},
            run_id=run_id,
            operation=lambda: self._node_extraction_step.run(source_materials),
            output_counts=lambda value: {"skeletons": len(value)},
            trace_getter=lambda: get_authoring_agent_step_trace(self._node_extraction_step),
        )
        _run_logged_entry(
            builder,
            entry_name="validate_source_grounded_node_skeletons",
            entry_type="validation_checkpoint",
            input_counts={"skeletons": len(skeletons)},
            run_id=run_id,
            operation=lambda: validate_source_grounded_node_skeletons(skeletons),
            validation_result="passed",
            artifact_uris=lambda _: _write_source_grounded_node_skeleton_artifacts(
                intermediate_artifact_writer,
                skeletons,
            ),
        )
        return skeletons


def _run_logged_entry(
    builder: GraphAuthoringRunLogBuilder,
    *,
    entry_name: str,
    entry_type: WorkflowRunLogEntryType,
    input_counts: dict[str, int],
    run_id: str,
    operation: Callable[[], T],
    output_counts: Callable[[T], dict[str, int]] | None = None,
    artifact_uris: Callable[[T], dict[str, str]] | None = None,
    validation_result: WorkflowRunValidationResult | None = None,
    trace_getter: Callable[[], WorkflowRunAgentTrace | None] | None = None,
) -> T:
    _LOGGER.info(
        "Graph authoring entry started run_id=%s entry_name=%s entry_type=%s input_counts=%s",
        run_id,
        entry_name,
        entry_type,
        input_counts,
    )
    active_entry = builder.start_entry(
        entry_name=entry_name,
        entry_type=entry_type,
        input_counts=input_counts,
    )
    try:
        value = operation()
        entry_artifact_uris = artifact_uris(value) if artifact_uris is not None else None
    except Exception as exc:
        error = workflow_run_error_from_exception(
            exc,
            checkpoint=entry_name if entry_type == "validation_checkpoint" else None,
            step_name=entry_name if entry_type == "agent_step" else None,
        )
        agent_trace = trace_getter() if trace_getter is not None else None
        builder.fail_entry(active_entry, error, agent_trace=agent_trace)
        run_log = builder.failed(error)
        _LOGGER.error(
            "Graph authoring entry failed run_id=%s entry_name=%s entry_type=%s error_type=%s message=%s",
            run_id,
            entry_name,
            entry_type,
            error.error_type,
            error.message,
        )
        raise GraphAuthoringWorkflowRunError(
            f"{GRAPH_AUTHORING_WORKFLOW_NAME} failed during {entry_name}",
            run_log=run_log,
            cause=exc,
        ) from exc

    entry_output_counts = output_counts(value) if output_counts is not None else None
    builder.finish_entry(
        active_entry,
        output_counts=entry_output_counts,
        artifact_uris=entry_artifact_uris,
        validation_result=validation_result,
        agent_trace=trace_getter() if trace_getter is not None else None,
    )
    _LOGGER.info(
        "Graph authoring entry succeeded run_id=%s entry_name=%s entry_type=%s output_counts=%s validation_result=%s",
        run_id,
        entry_name,
        entry_type,
        entry_output_counts or {},
        validation_result,
    )
    return value


def _write_parsed_source_segment_artifacts(
    writer: IntermediateArtifactWriter | None,
    segments: Sequence[ParsedSourceSegment],
) -> dict[str, str]:
    if writer is None:
        return {}
    return {
        "parsed_source_segments": writer.write_parsed_source_segments(
            tuple(segments)
        )
    }


def _write_segment_node_extraction_draft_artifacts(
    writer: IntermediateArtifactWriter | None,
    drafts: Sequence[SegmentNodeExtractionDraft],
) -> dict[str, str]:
    if writer is None:
        return {}
    return {
        "segment_node_extraction_drafts": writer.write_segment_node_extraction_drafts(
            tuple(drafts)
        )
    }


def _write_reconciled_node_skeleton_artifacts(
    writer: IntermediateArtifactWriter | None,
    reconciliation_result: NodeSkeletonReconciliationResult,
) -> dict[str, str]:
    if writer is None:
        return {}
    return {
        "node_skeleton_reconciliation": writer.write_node_skeleton_reconciliation(
            reconciliation_result.records
        ),
        "source_grounded_node_skeletons": writer.write_source_grounded_node_skeletons(
            reconciliation_result.source_grounded_node_skeletons
        ),
    }


def _write_source_grounded_node_skeleton_artifacts(
    writer: IntermediateArtifactWriter | None,
    skeletons,
) -> dict[str, str]:
    if writer is None:
        return {}
    return {
        "source_grounded_node_skeletons": writer.write_source_grounded_node_skeletons(
            tuple(skeletons)
        )
    }


def _write_candidate_node_artifacts(
    writer: IntermediateArtifactWriter | None,
    result: NodeRubricAuthoringResult,
) -> dict[str, str]:
    if writer is None:
        return {}
    return {
        "node_rubric_patches": writer.write_node_rubric_patches(result.rubric_patches),
        "candidate_nodes_pre_edge": writer.write_candidate_nodes_pre_edge(result.candidate_nodes),
    }


def _write_candidate_edge_artifacts(
    writer: IntermediateArtifactWriter | None,
    candidate_edges,
) -> dict[str, str]:
    if writer is None:
        return {}
    return {
        "candidate_edges_canonical": writer.write_candidate_edges_canonical(
            tuple(candidate_edges)
        )
    }
