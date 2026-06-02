from collections.abc import Hashable
from pathlib import Path
import re
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, field_validator

from backend.knowact.authoring.logging import redact_logged_text
from backend.knowact.authoring.map_authoring_output import (
    CandidateMapArtifactPaths,
    CandidateMapArtifactWriter,
)
from backend.knowact.authoring.openai_workflow import (
    DEFAULT_GRAPH_AUTHORING_CLIENT_PROVIDER,
    GraphAuthoringClientProvider,
)
from backend.knowact.authoring.parsers.map_authoring import (
    parse_ground_truth_evidence_output,
    parse_knowledge_state_outline_output,
)
from backend.knowact.authoring.schemas import (
    GroundTruthEvidenceDraft,
    KnowledgeStateOutline,
)
from backend.knowact.authoring.templates.map_authoring import (
    build_ground_truth_evidence_messages,
    build_knowledge_state_outline_messages,
)
from backend.knowact.core.evidence import EvidenceRecord, EvidenceType, EvidenceVisibility
from backend.knowact.core.graph import KnowledgeGraph, KnowledgeNode
from backend.knowact.core.map import (
    KnowledgeMap,
    KnowledgeMapKind,
    MasteryLevel,
    UserKnowledgeState,
)
from backend.knowact.llm.client import ModelClient, ModelClientMetadata
from backend.knowact.llm.config import deepseek_config_from_env, openai_config_from_env
from backend.knowact.llm.deepseek_client import DeepSeekChatModelClient
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE
from backend.knowact.llm.openai_client import OpenAIChatModelClient
from backend.knowact.storage.profile_contexts import load_confirmed_profile_context
from backend.knowact.storage.reviewed_graphs import load_reviewed_graph
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.map import validate_knowledge_map


CANDIDATE_MAP_AUTHORING_WORKFLOW_NAME = "Candidate Knowledge Map Authoring Workflow"
MAX_SINGLE_BATCH_NODES = 5
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class CandidateMapAuthoringInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    benchmark_domain: str
    graph_version: str
    user_id: str
    run_id: str

    @field_validator("benchmark_domain", "graph_version", "user_id", "run_id")
    @classmethod
    def _ids_must_be_safe(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        if not _SAFE_ID_PATTERN.fullmatch(value):
            raise ValueError("must contain only letters, numbers, dots, underscores, or dashes")
        return value


class CandidateMapAuthoringWorkflowResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_map: KnowledgeMap
    artifact_paths: CandidateMapArtifactPaths


class CandidateMapAuthoringWorkflow:
    def __init__(self, *, workspace_root: Path, model_client: ModelClient) -> None:
        self._workspace_root = workspace_root
        self._model_client = model_client

    def run(self, input_data: CandidateMapAuthoringInput) -> CandidateMapAuthoringWorkflowResult:
        writer = CandidateMapArtifactWriter(
            workspace_root=self._workspace_root,
            benchmark_domain=input_data.benchmark_domain,
            run_id=input_data.run_id,
        )
        metadata = getattr(self._model_client, "metadata", None)
        try:
            reviewed_graph = load_reviewed_graph(
                workspace_root=self._workspace_root,
                benchmark_domain=input_data.benchmark_domain,
                version=input_data.graph_version,
            )
            profile_context = load_confirmed_profile_context(
                workspace_root=self._workspace_root,
                benchmark_domain=input_data.benchmark_domain,
                user_id=input_data.user_id,
            )
            nodes = reviewed_graph.graph.nodes
            if len(nodes) > MAX_SINGLE_BATCH_NODES:
                raise KnowActValidationError(
                    "Candidate-map tracer bullet supports at most "
                    f"{MAX_SINGLE_BATCH_NODES} reviewed nodes in one evidence batch"
                )

            message_profile = getattr(self._model_client, "message_profile", OPENAI_MESSAGE_PROFILE)
            outline_raw_output = self._model_client.complete(
                messages=build_knowledge_state_outline_messages(
                    profile_context=profile_context,
                    nodes=nodes,
                    message_profile=message_profile,
                )
            )
            writer.write_outline_raw_output(redact_logged_text(outline_raw_output))
            outline_list = parse_knowledge_state_outline_output(outline_raw_output)
            writer.write_outline_parser_output(outline_list)
            outlines = _validate_and_order_outlines(
                graph=reviewed_graph.graph,
                outlines=outline_list.states,
            )

            evidence_raw_output = self._model_client.complete(
                messages=build_ground_truth_evidence_messages(
                    profile_context=profile_context,
                    nodes=nodes,
                    state_outlines=outlines,
                    message_profile=message_profile,
                )
            )
            writer.write_evidence_raw_output(redact_logged_text(evidence_raw_output))
            evidence_draft_list = parse_ground_truth_evidence_output(evidence_raw_output)
            writer.write_evidence_parser_output(evidence_draft_list)
            evidence = _assemble_evidence(
                run_id=input_data.run_id,
                nodes=nodes,
                outlines=outlines,
                drafts=evidence_draft_list.evidence,
            )
            candidate_map = _assemble_candidate_map(
                user_id=input_data.user_id,
                graph=reviewed_graph.graph,
                outlines=outlines,
                evidence=evidence,
            )
            writer.write_candidate_map(candidate_map)
            writer.write_workflow_log(
                run_id=input_data.run_id,
                workflow_name=CANDIDATE_MAP_AUTHORING_WORKFLOW_NAME,
                status="succeeded",
                benchmark_domain=input_data.benchmark_domain,
                graph_version=input_data.graph_version,
                user_id=input_data.user_id,
                model_metadata=metadata,
            )
            return CandidateMapAuthoringWorkflowResult(
                candidate_map=candidate_map,
                artifact_paths=writer.artifact_paths,
            )
        except Exception as exc:
            writer.write_workflow_log(
                run_id=input_data.run_id,
                workflow_name=CANDIDATE_MAP_AUTHORING_WORKFLOW_NAME,
                status="failed",
                benchmark_domain=input_data.benchmark_domain,
                graph_version=input_data.graph_version,
                user_id=input_data.user_id,
                model_metadata=metadata,
                error=str(exc),
            )
            raise


def build_candidate_map_authoring_workflow(
    *,
    workspace_root: Path,
    model_client: ModelClient,
) -> CandidateMapAuthoringWorkflow:
    return CandidateMapAuthoringWorkflow(
        workspace_root=workspace_root,
        model_client=model_client,
    )


def build_candidate_map_authoring_workflow_for_provider(
    *,
    workspace_root: Path,
    client_provider: GraphAuthoringClientProvider = DEFAULT_GRAPH_AUTHORING_CLIENT_PROVIDER,
) -> CandidateMapAuthoringWorkflow:
    if client_provider == "openai":
        return build_candidate_map_authoring_workflow(
            workspace_root=workspace_root,
            model_client=OpenAIChatModelClient(openai_config_from_env()),
        )
    if client_provider == "deepseek":
        return build_candidate_map_authoring_workflow(
            workspace_root=workspace_root,
            model_client=DeepSeekChatModelClient(deepseek_config_from_env()),
        )
    raise ValueError(f"Unsupported candidate-map authoring client provider: {client_provider}")


def _validate_and_order_outlines(
    *,
    graph: KnowledgeGraph,
    outlines: tuple[KnowledgeStateOutline, ...],
) -> tuple[KnowledgeStateOutline, ...]:
    outline_node_ids = [outline.node_id for outline in outlines]
    duplicate_node_ids = _duplicates(outline_node_ids)
    if duplicate_node_ids:
        raise KnowActValidationError(
            f"Knowledge-State Outline contains duplicate node ids: {sorted(duplicate_node_ids)}"
        )
    unknown_node_ids = set(outline_node_ids) - graph.node_ids
    if unknown_node_ids:
        raise KnowActValidationError(
            f"Knowledge-State Outline references unknown node ids: {sorted(unknown_node_ids)}"
        )
    missing_node_ids = graph.node_ids - set(outline_node_ids)
    if missing_node_ids:
        raise KnowActValidationError(
            f"Knowledge-State Outline is missing node ids: {sorted(missing_node_ids)}"
        )
    outline_by_node_id = {outline.node_id: outline for outline in outlines}
    return tuple(outline_by_node_id[node.id] for node in graph.nodes)


def _assemble_evidence(
    *,
    run_id: str,
    nodes: tuple[KnowledgeNode, ...],
    outlines: tuple[KnowledgeStateOutline, ...],
    drafts: tuple[GroundTruthEvidenceDraft, ...],
) -> tuple[EvidenceRecord, ...]:
    node_ids = {node.id for node in nodes}
    unknown_node_ids = {draft.node_id for draft in drafts} - node_ids
    if unknown_node_ids:
        raise KnowActValidationError(
            f"Ground-Truth Evidence batch references nodes outside the batch: {sorted(unknown_node_ids)}"
        )
    duplicate_signatures = _duplicates(
        [(draft.node_id, draft.evidence_kind.value, draft.signal) for draft in drafts]
    )
    if duplicate_signatures:
        duplicate_nodes = {node_id for node_id, _, _ in duplicate_signatures}
        raise KnowActValidationError(
            "Ground-Truth Evidence batch contains duplicate evidence entries for nodes: "
            f"{sorted(duplicate_nodes)}"
        )

    outline_by_node_id = {outline.node_id: outline for outline in outlines}
    evidence: list[EvidenceRecord] = []
    for node in nodes:
        node_drafts = tuple(draft for draft in drafts if draft.node_id == node.id)
        required_count = _minimum_evidence_count(outline_by_node_id[node.id].mastery_level)
        if len(node_drafts) < required_count:
            raise KnowActValidationError(
                f"Ground-Truth Evidence batch requires at least {required_count} "
                f"simulator-only records for node {node.id}"
            )
        for ordinal, draft in enumerate(node_drafts, start=1):
            evidence.append(
                EvidenceRecord(
                    id=f"ev_{run_id}_{node.id}_{ordinal:03d}",
                    node_id=node.id,
                    evidence_type=EvidenceType.GROUND_TRUTH_PROFILE,
                    evidence_kind=draft.evidence_kind,
                    visibility=EvidenceVisibility.SIMULATOR_ONLY,
                    signal=draft.signal,
                )
            )
    return tuple(evidence)


def _assemble_candidate_map(
    *,
    user_id: str,
    graph: KnowledgeGraph,
    outlines: tuple[KnowledgeStateOutline, ...],
    evidence: tuple[EvidenceRecord, ...],
) -> KnowledgeMap:
    evidence_refs_by_node_id: dict[str, list[str]] = {}
    for record in evidence:
        evidence_refs_by_node_id.setdefault(record.node_id, []).append(record.id)
    candidate_map = KnowledgeMap(
        user_id=user_id,
        kind=KnowledgeMapKind.CANDIDATE,
        states=tuple(
            UserKnowledgeState(
                node_id=outline.node_id,
                mastery_level=outline.mastery_level,
                evidence_refs=tuple(evidence_refs_by_node_id.get(outline.node_id, ())),
                misconceptions=outline.misconceptions,
                unknowns=outline.unknowns,
            )
            for outline in outlines
        ),
        evidence=evidence,
    )
    _validate_candidate_map(candidate_map, graph)
    return candidate_map


def _validate_candidate_map(candidate_map: KnowledgeMap, graph: KnowledgeGraph) -> None:
    validate_knowledge_map(candidate_map, graph)
    state_node_ids = {state.node_id for state in candidate_map.states}
    missing_node_ids = graph.node_ids - state_node_ids
    if missing_node_ids:
        raise KnowActValidationError(
            f"Candidate knowledge map is missing nodes: {sorted(missing_node_ids)}"
        )
    for evidence in candidate_map.evidence:
        if evidence.evidence_type != EvidenceType.GROUND_TRUTH_PROFILE:
            raise KnowActValidationError(
                f"Candidate-map evidence {evidence.id} must have evidence type ground_truth_profile"
            )
        if evidence.visibility != EvidenceVisibility.SIMULATOR_ONLY:
            raise KnowActValidationError(
                f"Candidate-map evidence {evidence.id} must use simulator_only visibility"
            )
    for state in candidate_map.states:
        required_count = _minimum_evidence_count(state.mastery_level)
        if len(state.evidence_refs) < required_count:
            raise KnowActValidationError(
                f"Candidate state for node {state.node_id} requires at least {required_count} "
                "simulator-only evidence records"
            )


def _minimum_evidence_count(mastery_level: MasteryLevel) -> int:
    if mastery_level in (MasteryLevel.L2, MasteryLevel.L3):
        return 2
    return 1


_DuplicateValue = TypeVar("_DuplicateValue", bound=Hashable)


def _duplicates(values: list[_DuplicateValue]) -> set[_DuplicateValue]:
    seen: set[_DuplicateValue] = set()
    duplicates: set[_DuplicateValue] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
