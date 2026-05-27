from collections.abc import Sequence
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
    parse_node_extraction_output,
    parse_node_rubric_authoring_output,
)
from backend.knowact.authoring.schemas import (
    EdgeProposalInput,
    NodeRubricAuthoringInput,
    NodeRubricAuthoringResult,
    NodeRubricPatch,
    SourceGroundedNodeSkeleton,
    SourceMaterial,
)
from backend.knowact.authoring.templates.edge_proposal import build_edge_proposal_messages
from backend.knowact.authoring.templates.node_extraction import build_node_extraction_messages
from backend.knowact.authoring.templates.node_rubric_authoring import (
    build_node_rubric_authoring_messages,
)
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeNode
from backend.knowact.llm.client import ModelClient
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessageProfile


AgentStepParser = Callable[[str], tuple[BaseModel, ...]]
AgentStepOutputSerializer = Callable[[tuple[BaseModel, ...]], dict[str, object]]


class NodeExtractionStep(Protocol):
    def run(self, source_materials: Sequence[SourceMaterial]) -> tuple[SourceGroundedNodeSkeleton, ...]:
        """Extract source-grounded node skeletons from authoritative source material."""


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
    def __init__(self, model_client: ModelClient) -> None:
        self._model_client = model_client
        self.last_trace: WorkflowRunAgentTrace | None = None

    def run(self, source_materials: Sequence[SourceMaterial]) -> tuple[SourceGroundedNodeSkeleton, ...]:
        return _run_traced_llm_step(
            model_client=self._model_client,
            messages=build_node_extraction_messages(
                source_materials,
                message_profile=_message_profile_for(self._model_client),
            ),
            parser=parse_node_extraction_output,
            output_serializer=lambda skeletons: {
                "skeletons": _dump_models(skeletons),
            },
            step_name="node_extraction",
            trace_setter=self._set_last_trace,
        )

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
