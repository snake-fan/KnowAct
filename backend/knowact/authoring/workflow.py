from collections.abc import Callable, Sequence
from typing import TypeVar

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
from backend.knowact.authoring.schemas import GraphAuthoringWorkflowResult, SourceMaterial
from backend.knowact.authoring.steps import (
    EdgeProposalStep,
    NodeExtractionStep,
    NodeRubricAuthoringStep,
    get_authoring_agent_step_trace,
)
from backend.knowact.authoring.validation import (
    canonicalize_candidate_edges,
    validate_candidate_edges,
    validate_complete_candidate_nodes,
    validate_source_grounded_node_skeletons,
)
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.logging_config import get_knowact_logger


T = TypeVar("T")
_LOGGER = get_knowact_logger("authoring.workflow")


class GraphAuthoringAgentWorkflow:
    def __init__(
        self,
        *,
        node_extraction_step: NodeExtractionStep,
        node_rubric_authoring_step: NodeRubricAuthoringStep,
        edge_proposal_step: EdgeProposalStep,
        model_metadata: ModelClientMetadata | None = None,
    ) -> None:
        self._node_extraction_step = node_extraction_step
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
        )

        candidate_nodes = _run_logged_entry(
            builder,
            entry_name="node_rubric_authoring",
            entry_type="agent_step",
            input_counts={"skeletons": len(skeletons), "source_materials": len(source_materials)},
            run_id=run_id,
            operation=lambda: self._node_rubric_authoring_step.run(skeletons, source_materials),
            output_counts=lambda value: {"candidate_nodes": len(value)},
            trace_getter=lambda: get_authoring_agent_step_trace(self._node_rubric_authoring_step),
        )
        _run_logged_entry(
            builder,
            entry_name="validate_complete_candidate_nodes",
            entry_type="validation_checkpoint",
            input_counts={"candidate_nodes": len(candidate_nodes), "skeletons": len(skeletons)},
            run_id=run_id,
            operation=lambda: validate_complete_candidate_nodes(candidate_nodes, skeletons),
            validation_result="passed",
        )

        candidate_edges = _run_logged_entry(
            builder,
            entry_name="edge_proposal",
            entry_type="agent_step",
            input_counts={"candidate_nodes": len(candidate_nodes), "source_materials": len(source_materials)},
            run_id=run_id,
            operation=lambda: self._edge_proposal_step.run(candidate_nodes, source_materials),
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


def _run_logged_entry(
    builder: GraphAuthoringRunLogBuilder,
    *,
    entry_name: str,
    entry_type: WorkflowRunLogEntryType,
    input_counts: dict[str, int],
    run_id: str,
    operation: Callable[[], T],
    output_counts: Callable[[T], dict[str, int]] | None = None,
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
