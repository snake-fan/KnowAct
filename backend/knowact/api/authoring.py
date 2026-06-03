from collections.abc import Callable
import json
from pathlib import Path
import re
import shutil

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.knowact.authoring.openai_workflow import (
    DEFAULT_GRAPH_AUTHORING_CLIENT_PROVIDER,
    GraphAuthoringClientProvider,
)
from backend.knowact.authoring.logging import (
    GraphAuthoringLogArtifactPaths,
    GraphAuthoringRunLogSummary,
    GraphAuthoringWorkflowRunError,
    RunLogSourceMaterial,
    WORKFLOW_LOG_FILENAME,
    default_graph_authoring_run_id,
    summarize_run_log,
    with_artifact_paths,
)
from backend.knowact.authoring.map_authoring import (
    CandidateMapAuthoringInput,
    CandidateMapAuthoringWorkflow,
)
from backend.knowact.authoring.map_authoring_output import (
    CANDIDATE_MAP_FILENAME,
    CONSISTENCY_WARNINGS_FILENAME,
    CandidateMapAuthoringRunLog,
    CandidateMapArtifactError,
    CandidateMapArtifactPaths,
    CandidateMapNotFoundError,
    CandidateMapRunConflictError,
    WORKFLOW_LOG_FILENAME as CANDIDATE_MAP_WORKFLOW_LOG_FILENAME,
    read_candidate_map_run,
)
from backend.knowact.authoring.output import (
    GraphAuthoringIntermediateArtifactWriter,
    write_graph_authoring_output,
    write_graph_authoring_run_log,
)
from backend.knowact.authoring.parsers.graph_authoring import AuthoringOutputParseError
from backend.knowact.authoring.parsers.map_authoring import CandidateMapOutputParseError
from backend.knowact.authoring.parsers.profile_context import ProfileContextOutputParseError
from backend.knowact.authoring.profile_context import (
    ProfileContextAuthoringWorkflow,
)
from backend.knowact.authoring.profile_context_output import (
    CandidateProfileContextArtifactError,
    CandidateProfileContextArtifactPaths,
    CandidateProfileContextConfirmationConflictError,
    CandidateProfileContextNotFoundError,
    ConfirmedProfileContextArtifactPaths,
    ConfirmedProfileContextConflictError,
    confirm_candidate_profile_context,
    read_candidate_profile_context_run,
    write_candidate_profile_context,
    write_candidate_profile_context_run,
)
from backend.knowact.authoring.review_promotion import promote_candidate_graph, promote_candidate_map
from backend.knowact.authoring.schemas import (
    CandidateProfileContext,
    ConfirmedProfileContext,
    GeneratedProfileContext,
    GraphAuthoringWorkflowResult,
    MapEdgeConsistencyWarningList,
    ProfileContextAuthoringInput,
    SourceGroundedNodeSkeleton,
    SourceMaterial,
)
from backend.knowact.authoring.sources import (
    ParsedMarkdownMaterial,
    ParsedMarkdownEmptyError,
    ParsedMarkdownWriteError,
    SourceParser,
    SourcePreparationError,
    resolve_or_create_parsed_markdown,
)
from backend.knowact.authoring.validation import validate_candidate_edges, validate_complete_candidate_nodes
from backend.knowact.authoring.workflow import GraphAuthoringAgentWorkflow
from backend.knowact.core.graph import GraphManifest, KnowledgeEdge, KnowledgeNode
from backend.knowact.core.map import GroundTruthMapManifest, KnowledgeMap
from backend.knowact.llm.client import ModelClientError
from backend.knowact.logging_config import get_knowact_logger
from backend.knowact.storage.materials import (
    LocalPDFMaterial,
    MaterialFileError,
    MaterialFileNotFoundError,
    MaterialFileSizeError,
    MaterialFileTypeError,
    resolve_pdf_material,
)
from backend.knowact.storage.source_material_catalog import (
    SourceMaterialRecord,
    get_source_material,
    list_source_materials,
    save_pdf_source_material,
)
from backend.knowact.storage.reviewed_graphs import (
    AUTHORED_EDGES_FILENAME,
    AUTHORED_NODES_FILENAME,
    CandidateGraphArtifactError,
    CandidateGraphNotFoundError,
    GRAPH_MANIFEST_FILENAME,
    ReviewedGraphArtifactError,
    ReviewedGraphNotFoundError,
    ReviewedGraphPromotionConflictError,
    load_reviewed_graph,
)
from backend.knowact.storage.reviewed_maps import ReviewedMapPromotionConflictError
from backend.knowact.storage.profile_contexts import (
    CONFIRMED_PROFILE_CONTEXT_FILENAME,
    ConfirmedProfileContextArtifactError,
    ConfirmedProfileContextNotFoundError,
    load_confirmed_profile_context,
)
from backend.knowact.validation.exceptions import KnowActValidationError


_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_DEFAULT_BENCHMARK_DOMAIN = "classical_supervised_ml_algorithms"
_DEFAULT_SOURCE_ID = "isl_python"
_DEFAULT_SOURCE_TITLE = "An Introduction to Statistical Learning with Applications in Python"
GraphAuthoringWorkflowFactory = Callable[[GraphAuthoringClientProvider], GraphAuthoringAgentWorkflow]
ProfileContextAuthoringWorkflowFactory = Callable[
    [GraphAuthoringClientProvider],
    ProfileContextAuthoringWorkflow,
]
CandidateMapAuthoringWorkflowFactory = Callable[
    [GraphAuthoringClientProvider, Path],
    CandidateMapAuthoringWorkflow,
]
_LOGGER = get_knowact_logger("api.authoring")


class GraphCandidateAuthoringRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf_path: str | None = Field(
        default=None,
        description="Relative path under storage/, for example books/isl_python.pdf.",
    )
    benchmark_domain: str = _DEFAULT_BENCHMARK_DOMAIN
    source_id: str = _DEFAULT_SOURCE_ID
    source_title: str = _DEFAULT_SOURCE_TITLE
    citation: str | None = None
    force_reparse: bool = False
    write_artifacts: bool = True
    run_id: str | None = None
    client_provider: GraphAuthoringClientProvider = DEFAULT_GRAPH_AUTHORING_CLIENT_PROVIDER

    @field_validator("pdf_path")
    @classmethod
    def _pdf_path_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("source_title")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("benchmark_domain", "source_id")
    @classmethod
    def _safe_ids_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "id")

    @field_validator("run_id")
    @classmethod
    def _run_id_must_be_safe(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_safe_id(value, "run_id")


class ProfileContextCandidateAuthoringRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    benchmark_domain: str
    rough_description: str
    domain_summary: str | None = None
    run_id: str | None = None
    client_provider: GraphAuthoringClientProvider = DEFAULT_GRAPH_AUTHORING_CLIENT_PROVIDER

    @field_validator("benchmark_domain")
    @classmethod
    def _benchmark_domain_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "benchmark_domain")

    @field_validator("rough_description", "domain_summary")
    @classmethod
    def _text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("run_id")
    @classmethod
    def _run_id_must_be_safe(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_safe_id(value, "run_id")


class ProfileContextCandidateAuthoringResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    candidate_profile_context: CandidateProfileContext
    artifact_paths: CandidateProfileContextArtifactPaths


class ProfileContextCandidateSaveRequest(GeneratedProfileContext):
    pass


class ProfileContextConfirmationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: str

    @field_validator("user_id")
    @classmethod
    def _user_id_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "user_id")


class ProfileContextConfirmationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    profile_context: ConfirmedProfileContext
    artifact_paths: ConfirmedProfileContextArtifactPaths


class CandidateMapAuthoringRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    benchmark_domain: str
    graph_version: str
    user_id: str
    run_id: str | None = None
    client_provider: GraphAuthoringClientProvider = DEFAULT_GRAPH_AUTHORING_CLIENT_PROVIDER
    evidence_batch_size: int = Field(default=5, gt=0)
    sampling_temperature: float = Field(default=0.7, ge=0.0)

    @field_validator("benchmark_domain", "graph_version", "user_id")
    @classmethod
    def _ids_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "id")

    @field_validator("run_id")
    @classmethod
    def _run_id_must_be_safe(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_safe_id(value, "run_id")


class CandidateMapAuthoringResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    candidate_map: KnowledgeMap
    artifact_paths: CandidateMapArtifactPaths


class CandidateMapPromotionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    map_id: str

    @field_validator("map_id")
    @classmethod
    def _map_id_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "map_id")


class ReviewedMapArtifactPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir_uri: str
    ground_truth_map_uri: str
    map_manifest_uri: str


class CandidateMapPromotionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_domain: str
    run_id: str
    ground_truth_map: KnowledgeMap
    map_manifest: GroundTruthMapManifest
    artifact_paths: ReviewedMapArtifactPaths


class ReviewedGraphVersionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    graph_id: str | None = None
    node_count: int | None = None
    edge_count: int | None = None


class ReviewedGraphVersionListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_domain: str
    graphs: tuple[ReviewedGraphVersionSummary, ...]


class ReviewedGraphArtifactPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir_uri: str
    graph_manifest_uri: str
    authored_nodes_uri: str
    authored_edges_uri: str


class ReviewedGraphArtifactsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_domain: str
    graph_manifest: GraphManifest
    authored_nodes: tuple[KnowledgeNode, ...]
    authored_edges: tuple[KnowledgeEdge, ...]
    artifact_paths: ReviewedGraphArtifactPaths


class ConfirmedProfileContextSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: str
    summary: str | None = None


class ConfirmedProfileContextListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_domain: str
    users: tuple[ConfirmedProfileContextSummary, ...]


class ConfirmedProfileContextResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_domain: str
    user_id: str
    profile_context: ConfirmedProfileContext
    artifact_paths: ConfirmedProfileContextArtifactPaths


class CandidateMapRunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    status: str
    graph_version: str | None = None
    user_id: str | None = None
    has_candidate_map: bool
    warning_count: int | None = None
    error: str | None = None


class CandidateMapRunListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_domain: str
    runs: tuple[CandidateMapRunSummary, ...]


class BenchmarkDomainListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_domains: tuple[str, ...]


class SourceMaterialInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    storage_uri: str
    filename: str
    size_bytes: int
    markdown_storage_uri: str
    markdown_filename: str
    markdown_size_bytes: int
    markdown_cache_status: str
    source_id: str
    title: str


class SourceMaterialListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_materials: tuple[SourceMaterialRecord, ...]


class GraphCandidateArtifactPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir_uri: str
    candidate_nodes_uri: str
    candidate_edges_uri: str
    workflow_log_uri: str


class GraphCandidateAuthoringResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow: str
    material: SourceMaterialInfo
    run_log_summary: GraphAuthoringRunLogSummary
    source_grounded_node_skeletons: tuple[SourceGroundedNodeSkeleton, ...]
    candidate_nodes: tuple[KnowledgeNode, ...]
    candidate_edges: tuple[KnowledgeEdge, ...]
    artifact_paths: GraphCandidateArtifactPaths | None = None


class CandidateGraphArtifactsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_domain: str
    run_id: str
    candidate_nodes: tuple[KnowledgeNode, ...]
    candidate_edges: tuple[KnowledgeEdge, ...]
    artifact_paths: GraphCandidateArtifactPaths


class CandidateGraphRunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str


class CandidateGraphRunListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_domain: str
    runs: tuple[CandidateGraphRunSummary, ...]


class CandidateGraphSaveRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_nodes: tuple[KnowledgeNode, ...]
    candidate_edges: tuple[KnowledgeEdge, ...] = Field(default_factory=tuple)


class CandidateGraphPromotionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str

    @field_validator("version")
    @classmethod
    def _version_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "version")


class CandidateGraphPromotionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_domain: str
    run_id: str
    graph_manifest: GraphManifest
    artifact_paths: ReviewedGraphArtifactPaths


def build_authoring_router(
    *,
    graph_authoring_workflow_factory: GraphAuthoringWorkflowFactory,
    profile_context_authoring_workflow_factory: ProfileContextAuthoringWorkflowFactory,
    candidate_map_authoring_workflow_factory: CandidateMapAuthoringWorkflowFactory,
    source_parser: SourceParser,
    workspace_root: Path | None = None,
) -> APIRouter:
    root = workspace_root or _default_workspace_root()
    storage_root = root / "storage"
    router = APIRouter()

    @router.get(
        "/benchmark-domains",
        response_model=BenchmarkDomainListResponse,
        summary="List existing benchmark domains available for authoring.",
    )
    def list_benchmark_domains() -> BenchmarkDomainListResponse:
        domains_dir = root / "benchmark" / "domains"
        if not domains_dir.exists():
            return BenchmarkDomainListResponse(benchmark_domains=())
        return BenchmarkDomainListResponse(
            benchmark_domains=tuple(
                entry.name
                for entry in sorted(domains_dir.iterdir())
                if entry.is_dir() and _SAFE_ID_PATTERN.fullmatch(entry.name)
            )
        )

    @router.get(
        "/graphs/{benchmark_domain}",
        response_model=ReviewedGraphVersionListResponse,
        summary="List reviewed graph versions for a benchmark domain.",
    )
    def list_reviewed_graph_versions(
        benchmark_domain: str,
    ) -> ReviewedGraphVersionListResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        graphs_dir = root / "benchmark" / "domains" / benchmark_domain / "graphs"
        summaries: list[ReviewedGraphVersionSummary] = []
        if graphs_dir.exists() and graphs_dir.is_dir():
            for entry in sorted(graphs_dir.iterdir(), reverse=True):
                if not entry.is_dir():
                    continue
                try:
                    version = _validate_safe_id(entry.name, "version")
                except ValueError:
                    continue
                summaries.append(
                    _reviewed_graph_summary(
                        workspace_root=root,
                        benchmark_domain=benchmark_domain,
                        version=version,
                    )
                )
        return ReviewedGraphVersionListResponse(
            benchmark_domain=benchmark_domain,
            graphs=tuple(summaries),
        )

    @router.get(
        "/graphs/{benchmark_domain}/{version}",
        response_model=ReviewedGraphArtifactsResponse,
        summary="Read one reviewed authored graph version.",
    )
    def read_reviewed_graph_version(
        benchmark_domain: str,
        version: str,
    ) -> ReviewedGraphArtifactsResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        version = _validate_safe_id_or_422(version, "version")
        try:
            artifacts = load_reviewed_graph(
                workspace_root=root,
                benchmark_domain=benchmark_domain,
                version=version,
            )
        except ReviewedGraphNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ReviewedGraphArtifactError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return ReviewedGraphArtifactsResponse(
            benchmark_domain=benchmark_domain,
            graph_manifest=artifacts.manifest,
            authored_nodes=artifacts.graph.nodes,
            authored_edges=artifacts.graph.edges,
            artifact_paths=ReviewedGraphArtifactPaths(
                output_dir_uri=_relative_uri(artifacts.graph_dir, root),
                graph_manifest_uri=_relative_uri(
                    artifacts.graph_dir / GRAPH_MANIFEST_FILENAME,
                    root,
                ),
                authored_nodes_uri=_relative_uri(
                    artifacts.graph_dir / AUTHORED_NODES_FILENAME,
                    root,
                ),
                authored_edges_uri=_relative_uri(
                    artifacts.graph_dir / AUTHORED_EDGES_FILENAME,
                    root,
                ),
            ),
        )

    @router.get(
        "/users/{benchmark_domain}",
        response_model=ConfirmedProfileContextListResponse,
        summary="List confirmed Profile Context snapshots for a benchmark domain.",
    )
    def list_confirmed_profile_contexts(
        benchmark_domain: str,
    ) -> ConfirmedProfileContextListResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        users_dir = root / "benchmark" / "domains" / benchmark_domain / "users"
        summaries: list[ConfirmedProfileContextSummary] = []
        if users_dir.exists() and users_dir.is_dir():
            for entry in sorted(users_dir.iterdir()):
                if not entry.is_dir():
                    continue
                try:
                    user_id = _validate_safe_id(entry.name, "user_id")
                    profile_context = load_confirmed_profile_context(
                        workspace_root=root,
                        benchmark_domain=benchmark_domain,
                        user_id=user_id,
                    )
                except (
                    ValueError,
                    ConfirmedProfileContextNotFoundError,
                    ConfirmedProfileContextArtifactError,
                ):
                    continue
                summaries.append(
                    ConfirmedProfileContextSummary(
                        user_id=user_id,
                        summary=profile_context.summary,
                    )
                )
        return ConfirmedProfileContextListResponse(
            benchmark_domain=benchmark_domain,
            users=tuple(summaries),
        )

    @router.get(
        "/users/{benchmark_domain}/{user_id}",
        response_model=ConfirmedProfileContextResponse,
        summary="Read one confirmed Profile Context snapshot.",
    )
    def read_confirmed_profile_context(
        benchmark_domain: str,
        user_id: str,
    ) -> ConfirmedProfileContextResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        user_id = _validate_safe_id_or_422(user_id, "user_id")
        try:
            profile_context = load_confirmed_profile_context(
                workspace_root=root,
                benchmark_domain=benchmark_domain,
                user_id=user_id,
            )
        except ConfirmedProfileContextNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ConfirmedProfileContextArtifactError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        output_dir = (
            root
            / "benchmark"
            / "domains"
            / benchmark_domain
            / "users"
            / user_id
        )
        return ConfirmedProfileContextResponse(
            benchmark_domain=benchmark_domain,
            user_id=user_id,
            profile_context=profile_context,
            artifact_paths=ConfirmedProfileContextArtifactPaths(
                output_dir_uri=_relative_uri(output_dir, root),
                profile_context_uri=_relative_uri(
                    output_dir / CONFIRMED_PROFILE_CONTEXT_FILENAME,
                    root,
                ),
            ),
        )

    @router.post(
        "/profile-context-candidates",
        response_model=ProfileContextCandidateAuthoringResponse,
        summary="Generate one reviewable Profile Context candidate.",
    )
    def create_profile_context_candidate(
        request: ProfileContextCandidateAuthoringRequest,
    ) -> ProfileContextCandidateAuthoringResponse:
        run_id = request.run_id or default_graph_authoring_run_id()
        output_dir = _candidate_profile_context_output_dir(root, request.benchmark_domain, run_id)
        try:
            workflow = _build_profile_context_authoring_workflow(
                profile_context_authoring_workflow_factory,
                client_provider=request.client_provider,
            )
            result = workflow.run(
                ProfileContextAuthoringInput(
                    benchmark_domain=request.benchmark_domain,
                    rough_description=request.rough_description,
                    domain_summary=request.domain_summary,
                )
            )
            artifact_paths = write_candidate_profile_context_run(
                workspace_root=root,
                output_dir=output_dir,
                run_id=run_id,
                result=result,
            )
        except ProfileContextOutputParseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ModelClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return ProfileContextCandidateAuthoringResponse(
            run_id=run_id,
            candidate_profile_context=result.candidate_profile_context,
            artifact_paths=artifact_paths,
        )

    @router.get(
        "/candidate-profile-contexts/{benchmark_domain}/{run_id}",
        response_model=ProfileContextCandidateAuthoringResponse,
        summary="Read one saved Profile Context candidate.",
    )
    def read_profile_context_candidate(
        benchmark_domain: str,
        run_id: str,
    ) -> ProfileContextCandidateAuthoringResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        run_id = _validate_safe_id_or_422(run_id, "run_id")
        try:
            candidate, artifact_paths = read_candidate_profile_context_run(
                workspace_root=root,
                output_dir=_candidate_profile_context_output_dir(root, benchmark_domain, run_id),
                benchmark_domain=benchmark_domain,
            )
        except CandidateProfileContextNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CandidateProfileContextArtifactError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return ProfileContextCandidateAuthoringResponse(
            run_id=run_id,
            candidate_profile_context=candidate,
            artifact_paths=artifact_paths,
        )

    @router.put(
        "/candidate-profile-contexts/{benchmark_domain}/{run_id}",
        response_model=ProfileContextCandidateAuthoringResponse,
        summary="Validate and overwrite one Profile Context candidate draft.",
    )
    def save_profile_context_candidate(
        benchmark_domain: str,
        run_id: str,
        request: ProfileContextCandidateSaveRequest,
    ) -> ProfileContextCandidateAuthoringResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        run_id = _validate_safe_id_or_422(run_id, "run_id")
        output_dir = _candidate_profile_context_output_dir(root, benchmark_domain, run_id)
        try:
            _, artifact_paths = read_candidate_profile_context_run(
                workspace_root=root,
                output_dir=output_dir,
                benchmark_domain=benchmark_domain,
            )
            candidate = CandidateProfileContext(
                benchmark_domain=benchmark_domain,
                **request.model_dump(),
            )
            write_candidate_profile_context(output_dir=output_dir, candidate=candidate)
        except CandidateProfileContextNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CandidateProfileContextArtifactError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return ProfileContextCandidateAuthoringResponse(
            run_id=run_id,
            candidate_profile_context=candidate,
            artifact_paths=artifact_paths,
        )

    @router.post(
        "/candidate-profile-contexts/{benchmark_domain}/{run_id}/confirmation",
        response_model=ProfileContextConfirmationResponse,
        summary="Confirm one Profile Context candidate as an immutable synthetic-user snapshot.",
    )
    def confirm_profile_context_candidate(
        benchmark_domain: str,
        run_id: str,
        request: ProfileContextConfirmationRequest,
    ) -> ProfileContextConfirmationResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        run_id = _validate_safe_id_or_422(run_id, "run_id")
        output_dir = _candidate_profile_context_output_dir(root, benchmark_domain, run_id)
        try:
            candidate, _ = read_candidate_profile_context_run(
                workspace_root=root,
                output_dir=output_dir,
                benchmark_domain=benchmark_domain,
            )
            profile_context, artifact_paths = confirm_candidate_profile_context(
                workspace_root=root,
                output_dir=output_dir,
                benchmark_domain=benchmark_domain,
                user_id=request.user_id,
                candidate=candidate,
            )
        except CandidateProfileContextNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (
            CandidateProfileContextConfirmationConflictError,
            ConfirmedProfileContextConflictError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except CandidateProfileContextArtifactError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return ProfileContextConfirmationResponse(
            run_id=run_id,
            profile_context=profile_context,
            artifact_paths=artifact_paths,
        )

    @router.post(
        "/source-materials",
        response_model=SourceMaterialRecord,
        summary="Upload one PDF source material for graph authoring.",
    )
    def upload_source_material(
        file: UploadFile = File(...),
        source_id: str = Form(...),
        title: str = Form(...),
        citation: str | None = Form(None),
    ) -> SourceMaterialRecord:
        try:
            safe_source_id = _validate_safe_id_or_422(source_id, "source_id")
            return save_pdf_source_material(
                storage_root=storage_root,
                source_id=safe_source_id,
                title=title,
                citation=citation,
                filename=file.filename or "",
                content=file.file,
            )
        except MaterialFileTypeError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        except MaterialFileSizeError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except MaterialFileError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get(
        "/candidate-maps/{benchmark_domain}",
        response_model=CandidateMapRunListResponse,
        summary="List candidate map runs for a benchmark domain.",
    )
    def list_candidate_map_runs(
        benchmark_domain: str,
    ) -> CandidateMapRunListResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        runs_dir = root / "benchmark" / "domains" / benchmark_domain / "candidate_maps"
        summaries: list[CandidateMapRunSummary] = []
        if runs_dir.exists() and runs_dir.is_dir():
            for entry in sorted(runs_dir.iterdir(), reverse=True):
                if not entry.is_dir():
                    continue
                try:
                    run_id = _validate_safe_id(entry.name, "run_id")
                except ValueError:
                    continue
                summaries.append(
                    _candidate_map_run_summary(
                        run_dir=entry,
                        run_id=run_id,
                    )
                )
        return CandidateMapRunListResponse(
            benchmark_domain=benchmark_domain,
            runs=tuple(summaries),
        )

    @router.post(
        "/map-candidates",
        response_model=CandidateMapAuthoringResponse,
        summary="Generate one Candidate Knowledge Map over a reviewed graph.",
    )
    def create_candidate_map(
        request: CandidateMapAuthoringRequest,
    ) -> CandidateMapAuthoringResponse:
        run_id = request.run_id or default_graph_authoring_run_id()
        try:
            workflow = _build_candidate_map_authoring_workflow(
                candidate_map_authoring_workflow_factory,
                client_provider=request.client_provider,
                workspace_root=root,
            )
            result = workflow.run(
                CandidateMapAuthoringInput(
                    benchmark_domain=request.benchmark_domain,
                    graph_version=request.graph_version,
                    user_id=request.user_id,
                    run_id=run_id,
                    evidence_batch_size=request.evidence_batch_size,
                    sampling_temperature=request.sampling_temperature,
                )
            )
        except (ReviewedGraphNotFoundError, ConfirmedProfileContextNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CandidateMapRunConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (
            ReviewedGraphArtifactError,
            ConfirmedProfileContextArtifactError,
            KnowActValidationError,
        ) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (CandidateMapOutputParseError, ModelClientError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return CandidateMapAuthoringResponse(
            run_id=run_id,
            candidate_map=result.candidate_map,
            artifact_paths=result.artifact_paths,
        )

    @router.get(
        "/candidate-maps/{benchmark_domain}/{run_id}",
        response_model=CandidateMapAuthoringResponse,
        summary="Read one saved Candidate Knowledge Map.",
    )
    def read_candidate_map(
        benchmark_domain: str,
        run_id: str,
    ) -> CandidateMapAuthoringResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        run_id = _validate_safe_id_or_422(run_id, "run_id")
        try:
            candidate_map, artifact_paths = read_candidate_map_run(
                workspace_root=root,
                benchmark_domain=benchmark_domain,
                run_id=run_id,
            )
        except CandidateMapNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CandidateMapArtifactError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return CandidateMapAuthoringResponse(
            run_id=run_id,
            candidate_map=candidate_map,
            artifact_paths=artifact_paths,
        )

    @router.get(
        "/candidate-maps/{benchmark_domain}/{run_id}/warnings",
        response_model=MapEdgeConsistencyWarningList,
        summary="Read generation-time consistency warnings for one candidate map run.",
    )
    def read_candidate_map_warnings(
        benchmark_domain: str,
        run_id: str,
    ) -> MapEdgeConsistencyWarningList:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        run_id = _validate_safe_id_or_422(run_id, "run_id")
        output_dir = root / "benchmark" / "domains" / benchmark_domain / "candidate_maps" / run_id
        if not output_dir.exists() or not output_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Candidate map run {run_id} does not exist")
        warnings_path = output_dir / CONSISTENCY_WARNINGS_FILENAME
        if not warnings_path.exists():
            return MapEdgeConsistencyWarningList(warnings=())
        try:
            return MapEdgeConsistencyWarningList.model_validate(_read_json_payload(warnings_path))
        except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post(
        "/candidate-maps/{benchmark_domain}/{run_id}/promotion",
        response_model=CandidateMapPromotionResponse,
        summary="Promote one accepted Candidate Knowledge Map into an immutable ground-truth snapshot.",
    )
    def promote_candidate_map_artifacts(
        benchmark_domain: str,
        run_id: str,
        request: CandidateMapPromotionRequest,
    ) -> CandidateMapPromotionResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        run_id = _validate_safe_id_or_422(run_id, "run_id")
        try:
            promotion = promote_candidate_map(
                workspace_root=root,
                benchmark_domain=benchmark_domain,
                run_id=run_id,
                map_id=request.map_id,
            )
        except (CandidateMapNotFoundError, ReviewedGraphNotFoundError, ConfirmedProfileContextNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ReviewedMapPromotionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (
            CandidateMapArtifactError,
            ReviewedGraphArtifactError,
            ConfirmedProfileContextArtifactError,
        ) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return CandidateMapPromotionResponse(
            benchmark_domain=benchmark_domain,
            run_id=run_id,
            ground_truth_map=promotion.ground_truth_map,
            map_manifest=promotion.manifest,
            artifact_paths=ReviewedMapArtifactPaths(
                output_dir_uri=_relative_uri(promotion.output_dir, root),
                ground_truth_map_uri=_relative_uri(promotion.ground_truth_map_path, root),
                map_manifest_uri=_relative_uri(promotion.map_manifest_path, root),
            ),
        )

    @router.get(
        "/source-materials",
        response_model=SourceMaterialListResponse,
        summary="List uploaded source materials available for graph authoring.",
    )
    def list_uploaded_source_materials() -> SourceMaterialListResponse:
        return SourceMaterialListResponse(source_materials=list_source_materials(storage_root=storage_root))

    @router.get(
        "/candidate-graphs/{benchmark_domain}",
        response_model=CandidateGraphRunListResponse,
        summary="List candidate graph runs for a benchmark domain.",
    )
    def list_candidate_graph_runs(
        benchmark_domain: str,
    ) -> CandidateGraphRunListResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        runs_dir = root / "benchmark" / "domains" / benchmark_domain / "candidate_graphs"
        runs: list[CandidateGraphRunSummary] = []
        if runs_dir.exists() and runs_dir.is_dir():
            for entry in sorted(runs_dir.iterdir(), reverse=True):
                if not entry.is_dir():
                    continue
                run_id = entry.name
                try:
                    _validate_safe_id(run_id, "run_id")
                except ValueError:
                    continue
                runs.append(CandidateGraphRunSummary(run_id=run_id))
        return CandidateGraphRunListResponse(
            benchmark_domain=benchmark_domain,
            runs=tuple(runs),
        )

    @router.get(
        "/candidate-graphs/{benchmark_domain}/{run_id}",
        response_model=CandidateGraphArtifactsResponse,
        summary="Read one candidate graph run's node and edge artifacts.",
    )
    def read_candidate_graph_artifacts(
        benchmark_domain: str,
        run_id: str,
    ) -> CandidateGraphArtifactsResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        run_id = _validate_safe_id_or_422(run_id, "run_id")
        output_dir = _candidate_graph_output_dir(root, benchmark_domain, run_id)
        nodes_path = output_dir / "candidate_nodes.json"
        edges_path = output_dir / "candidate_edges.json"
        workflow_log_path = output_dir / WORKFLOW_LOG_FILENAME
        if not nodes_path.exists() or not edges_path.exists():
            raise HTTPException(status_code=404, detail="candidate graph artifacts do not exist")

        try:
            candidate_nodes = tuple(KnowledgeNode.model_validate(item) for item in _read_json_list(nodes_path))
            candidate_edges = tuple(KnowledgeEdge.model_validate(item) for item in _read_json_list(edges_path))
        except (OSError, ValueError, ValidationError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return CandidateGraphArtifactsResponse(
            benchmark_domain=benchmark_domain,
            run_id=run_id,
            candidate_nodes=candidate_nodes,
            candidate_edges=candidate_edges,
            artifact_paths=GraphCandidateArtifactPaths(
                output_dir_uri=_relative_uri(output_dir, root),
                candidate_nodes_uri=_relative_uri(nodes_path, root),
                candidate_edges_uri=_relative_uri(edges_path, root),
                workflow_log_uri=_relative_uri(workflow_log_path, root),
            ),
        )

    @router.put(
        "/candidate-graphs/{benchmark_domain}/{run_id}",
        response_model=CandidateGraphArtifactsResponse,
        summary="Validate and overwrite one candidate graph run's node and edge artifacts.",
    )
    def save_candidate_graph_artifacts(
        benchmark_domain: str,
        run_id: str,
        request: CandidateGraphSaveRequest,
    ) -> CandidateGraphArtifactsResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        run_id = _validate_safe_id_or_422(run_id, "run_id")
        output_dir = _candidate_graph_output_dir(root, benchmark_domain, run_id)
        nodes_path = output_dir / "candidate_nodes.json"
        edges_path = output_dir / "candidate_edges.json"
        if not nodes_path.exists() or not edges_path.exists():
            raise HTTPException(status_code=404, detail="candidate graph artifacts do not exist")

        try:
            validate_complete_candidate_nodes(request.candidate_nodes)
            validate_candidate_edges(request.candidate_nodes, request.candidate_edges)
        except KnowActValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        result = GraphAuthoringWorkflowResult(
            source_grounded_node_skeletons=(),
            candidate_nodes=request.candidate_nodes,
            candidate_edges=request.candidate_edges,
        )
        write_graph_authoring_output(result, output_dir)
        workflow_log_path = output_dir / WORKFLOW_LOG_FILENAME

        return CandidateGraphArtifactsResponse(
            benchmark_domain=benchmark_domain,
            run_id=run_id,
            candidate_nodes=request.candidate_nodes,
            candidate_edges=request.candidate_edges,
            artifact_paths=GraphCandidateArtifactPaths(
                output_dir_uri=_relative_uri(output_dir, root),
                candidate_nodes_uri=_relative_uri(nodes_path, root),
                candidate_edges_uri=_relative_uri(edges_path, root),
                workflow_log_uri=_relative_uri(workflow_log_path, root),
            ),
        )

    @router.post(
        "/candidate-graphs/{benchmark_domain}/{run_id}/promotion",
        response_model=CandidateGraphPromotionResponse,
        summary="Promote one validated candidate graph run into a reviewed authored graph version.",
    )
    def promote_candidate_graph_artifacts(
        benchmark_domain: str,
        run_id: str,
        request: CandidateGraphPromotionRequest,
    ) -> CandidateGraphPromotionResponse:
        benchmark_domain = _validate_safe_id_or_422(benchmark_domain, "benchmark_domain")
        run_id = _validate_safe_id_or_422(run_id, "run_id")
        try:
            promotion = promote_candidate_graph(
                workspace_root=root,
                benchmark_domain=benchmark_domain,
                run_id=run_id,
                version=request.version,
            )
        except CandidateGraphNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ReviewedGraphPromotionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except CandidateGraphArtifactError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return CandidateGraphPromotionResponse(
            benchmark_domain=benchmark_domain,
            run_id=run_id,
            graph_manifest=promotion.manifest,
            artifact_paths=ReviewedGraphArtifactPaths(
                output_dir_uri=_relative_uri(promotion.output_dir, root),
                graph_manifest_uri=_relative_uri(promotion.graph_manifest_path, root),
                authored_nodes_uri=_relative_uri(promotion.authored_nodes_path, root),
                authored_edges_uri=_relative_uri(promotion.authored_edges_path, root),
            ),
        )

    @router.post(
        "/graph-candidates",
        response_model=GraphCandidateAuthoringResponse,
        summary="Run the Graph Authoring Agent Workflow from one local PDF source material.",
    )
    def create_graph_candidates(
        request: GraphCandidateAuthoringRequest,
    ) -> GraphCandidateAuthoringResponse:
        run_id = request.run_id or default_graph_authoring_run_id()
        output_dir = _candidate_graph_output_dir(root, request.benchmark_domain, run_id)
        _LOGGER.info(
            "Graph candidate authoring request received run_id=%s benchmark_domain=%s pdf_path=%s source_id=%s client_provider=%s write_artifacts=%s",
            run_id,
            request.benchmark_domain,
            request.pdf_path,
            request.source_id,
            request.client_provider,
            request.write_artifacts,
        )

        try:
            material_record = None
            if request.pdf_path is None:
                material_record = get_source_material(storage_root=storage_root, source_id=request.source_id)
                material = resolve_pdf_material(storage_root=storage_root, storage_path=material_record.storage_path)
            else:
                material = resolve_pdf_material(storage_root=storage_root, storage_path=request.pdf_path)
            _LOGGER.info(
                "Graph candidate authoring source resolved run_id=%s storage_uri=%s filename=%s size_bytes=%d",
                run_id,
                material.storage_uri,
                material.filename,
                material.size_bytes,
            )
            parsed_markdown = resolve_or_create_parsed_markdown(
                pdf_path=material.path,
                storage_root=storage_root,
                parser=source_parser,
                force_reparse=request.force_reparse,
                run_id=run_id,
                storage_uri=material.storage_uri,
            )
            _LOGGER.info(
                "Graph candidate authoring markdown resolved run_id=%s markdown_uri=%s cache_status=%s size_bytes=%d",
                run_id,
                parsed_markdown.storage_uri,
                parsed_markdown.cache_status,
                parsed_markdown.size_bytes,
            )
            sources_md_path = _copy_markdown_to_domain_sources(
                markdown_text=parsed_markdown.text,
                root=root,
                benchmark_domain=request.benchmark_domain,
                source_filename=material.filename,
            )
            _LOGGER.info(
                "Markdown copied to domain sources run_id=%s path=%s",
                run_id,
                _relative_uri(sources_md_path, root),
            )
            workflow = _build_graph_authoring_workflow(
                graph_authoring_workflow_factory,
                client_provider=request.client_provider,
            )
            source_material = _source_material_from_markdown(parsed_markdown, request, material_record)
            run_result = workflow.run_with_log(
                (source_material,),
                run_id=run_id,
                source_metadata=(_run_log_source_material(material, parsed_markdown, request, material_record),),
                intermediate_artifact_writer=(
                    GraphAuthoringIntermediateArtifactWriter(output_dir)
                    if request.write_artifacts
                    else None
                ),
            )
        except MaterialFileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except MaterialFileTypeError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        except MaterialFileSizeError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except MaterialFileError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ParsedMarkdownEmptyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ParsedMarkdownWriteError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except SourcePreparationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except GraphAuthoringWorkflowRunError as exc:
            workflow_log_uri = None
            if request.write_artifacts:
                workflow_log_uri = _write_failed_workflow_log(
                    exc,
                    output_dir=output_dir,
                    root=root,
                )
            error = exc.run_log.error
            _LOGGER.error(
                "Graph candidate authoring failed run_id=%s error_type=%s message=%s workflow_log_uri=%s",
                run_id,
                error.error_type if error is not None else type(exc.cause).__name__,
                error.message if error is not None else str(exc.cause),
                workflow_log_uri,
            )
            raise _http_exception_from_workflow_run_error(exc, workflow_log_uri=workflow_log_uri) from exc
        except KnowActValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except AuthoringOutputParseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ModelClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        result = run_result.workflow_result
        run_log = run_result.run_log
        artifact_paths = None
        if request.write_artifacts:
            nodes_path, edges_path = write_graph_authoring_output(result, output_dir)
            _LOGGER.info(
                "Graph candidate artifacts written run_id=%s candidate_nodes_uri=%s candidate_edges_uri=%s",
                run_id,
                _relative_uri(nodes_path, root),
                _relative_uri(edges_path, root),
            )
            workflow_log_path = output_dir / WORKFLOW_LOG_FILENAME
            log_artifact_paths = GraphAuthoringLogArtifactPaths(
                output_dir_uri=_relative_uri(output_dir, root),
                candidate_nodes_uri=_relative_uri(nodes_path, root),
                candidate_edges_uri=_relative_uri(edges_path, root),
                workflow_log_uri=_relative_uri(workflow_log_path, root),
            )
            run_log = with_artifact_paths(run_log, log_artifact_paths)
            log_path = write_graph_authoring_run_log(run_log, output_dir)
            _LOGGER.info(
                "Graph authoring run log written run_id=%s workflow_log_uri=%s",
                run_id,
                _relative_uri(log_path, root),
            )
            artifact_paths = GraphCandidateArtifactPaths(
                output_dir_uri=_relative_uri(output_dir, root),
                candidate_nodes_uri=_relative_uri(nodes_path, root),
                candidate_edges_uri=_relative_uri(edges_path, root),
                workflow_log_uri=_relative_uri(log_path, root),
            )

        _LOGGER.info(
            "Graph candidate authoring succeeded run_id=%s skeletons=%d candidate_nodes=%d candidate_edges=%d write_artifacts=%s",
            run_id,
            len(result.source_grounded_node_skeletons),
            len(result.candidate_nodes),
            len(result.candidate_edges),
            request.write_artifacts,
        )
        return GraphCandidateAuthoringResponse(
            workflow="Graph Authoring Agent Workflow",
            material=SourceMaterialInfo(
                storage_uri=material.storage_uri,
                filename=material.filename,
                size_bytes=material.size_bytes,
                markdown_storage_uri=parsed_markdown.storage_uri,
                markdown_filename=parsed_markdown.filename,
                markdown_size_bytes=parsed_markdown.size_bytes,
                markdown_cache_status=parsed_markdown.cache_status,
                source_id=request.source_id,
                title=_effective_source_title(request, material_record),
            ),
            run_log_summary=summarize_run_log(run_log),
            source_grounded_node_skeletons=result.source_grounded_node_skeletons,
            candidate_nodes=result.candidate_nodes,
            candidate_edges=result.candidate_edges,
            artifact_paths=artifact_paths,
        )

    return router


def _reviewed_graph_summary(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    version: str,
) -> ReviewedGraphVersionSummary:
    try:
        artifacts = load_reviewed_graph(
            workspace_root=workspace_root,
            benchmark_domain=benchmark_domain,
            version=version,
        )
    except (ReviewedGraphNotFoundError, ReviewedGraphArtifactError):
        return ReviewedGraphVersionSummary(version=version)
    return ReviewedGraphVersionSummary(
        version=version,
        graph_id=artifacts.manifest.graph_id,
        node_count=len(artifacts.graph.nodes),
        edge_count=len(artifacts.graph.edges),
    )


def _candidate_map_run_summary(
    *,
    run_dir: Path,
    run_id: str,
) -> CandidateMapRunSummary:
    has_candidate_map = (run_dir / CANDIDATE_MAP_FILENAME).exists()
    run_log = _read_candidate_map_workflow_log(run_dir / CANDIDATE_MAP_WORKFLOW_LOG_FILENAME)
    if run_log is None:
        return CandidateMapRunSummary(
            run_id=run_id,
            status="unknown" if has_candidate_map else "missing_log",
            has_candidate_map=has_candidate_map,
            warning_count=_candidate_map_warning_count(run_dir / CONSISTENCY_WARNINGS_FILENAME),
        )
    return CandidateMapRunSummary(
        run_id=run_id,
        status=run_log.status,
        graph_version=run_log.graph_version,
        user_id=run_log.user_id,
        has_candidate_map=has_candidate_map,
        warning_count=_candidate_map_warning_count(run_dir / CONSISTENCY_WARNINGS_FILENAME),
        error=run_log.error,
    )


def _read_candidate_map_workflow_log(
    workflow_log_path: Path,
) -> CandidateMapAuthoringRunLog | None:
    if not workflow_log_path.exists():
        return None
    try:
        return CandidateMapAuthoringRunLog.model_validate(_read_json_payload(workflow_log_path))
    except (OSError, ValueError, ValidationError, json.JSONDecodeError):
        return None


def _candidate_map_warning_count(warnings_path: Path) -> int | None:
    if not warnings_path.exists():
        return 0
    try:
        return len(MapEdgeConsistencyWarningList.model_validate(_read_json_payload(warnings_path)).warnings)
    except (OSError, ValueError, ValidationError, json.JSONDecodeError):
        return None


def _build_graph_authoring_workflow(
    factory: GraphAuthoringWorkflowFactory,
    *,
    client_provider: GraphAuthoringClientProvider,
) -> GraphAuthoringAgentWorkflow:
    try:
        return factory(client_provider)
    except (ValueError, ModelClientError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _build_profile_context_authoring_workflow(
    factory: ProfileContextAuthoringWorkflowFactory,
    *,
    client_provider: GraphAuthoringClientProvider,
) -> ProfileContextAuthoringWorkflow:
    try:
        return factory(client_provider)
    except (ValueError, ModelClientError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _build_candidate_map_authoring_workflow(
    factory: CandidateMapAuthoringWorkflowFactory,
    *,
    client_provider: GraphAuthoringClientProvider,
    workspace_root: Path,
) -> CandidateMapAuthoringWorkflow:
    try:
        return factory(client_provider, workspace_root)
    except (ValueError, ModelClientError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _source_material_from_markdown(
    parsed_markdown: ParsedMarkdownMaterial,
    request: GraphCandidateAuthoringRequest,
    material_record: SourceMaterialRecord | None = None,
) -> SourceMaterial:
    return SourceMaterial(
        source_id=request.source_id,
        title=_effective_source_title(request, material_record),
        citation=_effective_citation(request, material_record, parsed_markdown),
        text=parsed_markdown.text,
    )


def _run_log_source_material(
    material: LocalPDFMaterial,
    parsed_markdown: ParsedMarkdownMaterial,
    request: GraphCandidateAuthoringRequest,
    material_record: SourceMaterialRecord | None = None,
) -> RunLogSourceMaterial:
    return RunLogSourceMaterial(
        source_id=request.source_id,
        title=_effective_source_title(request, material_record),
        citation=_effective_citation(request, material_record, parsed_markdown),
        storage_uri=material.storage_uri,
        filename=material.filename,
        size_bytes=material.size_bytes,
        parsed_markdown_uri=parsed_markdown.storage_uri,
        parsed_markdown_cache_status=parsed_markdown.cache_status,
        parsed_markdown_size_bytes=parsed_markdown.size_bytes,
    )


def _effective_source_title(
    request: GraphCandidateAuthoringRequest,
    material_record: SourceMaterialRecord | None,
) -> str:
    if material_record is not None and request.source_title == _DEFAULT_SOURCE_TITLE:
        return material_record.title
    return request.source_title


def _effective_citation(
    request: GraphCandidateAuthoringRequest,
    material_record: SourceMaterialRecord | None,
    parsed_markdown: ParsedMarkdownMaterial,
) -> str:
    return request.citation or (material_record.citation if material_record is not None else None) or parsed_markdown.storage_uri


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _candidate_graph_output_dir(root: Path, benchmark_domain: str, run_id: str) -> Path:
    return root / "benchmark" / "domains" / benchmark_domain / "candidate_graphs" / run_id


def _candidate_profile_context_output_dir(root: Path, benchmark_domain: str, run_id: str) -> Path:
    return root / "benchmark" / "domains" / benchmark_domain / "candidate_profile_contexts" / run_id


def _copy_markdown_to_domain_sources(
    *,
    markdown_text: str,
    root: Path,
    benchmark_domain: str,
    source_filename: str,
) -> Path:
    """Copy parsed markdown to the domain's sources/ directory, backing up any existing copy."""
    sources_dir = root / "benchmark" / "domains" / benchmark_domain / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    md_filename = Path(source_filename).stem + ".md"
    target_path = sources_dir / md_filename
    if target_path.exists():
        backup_path = sources_dir / (md_filename + ".bak")
        shutil.copy2(target_path, backup_path)
    target_path.write_text(markdown_text, encoding="utf-8")
    return target_path


def _write_failed_workflow_log(
    exc: GraphAuthoringWorkflowRunError,
    *,
    output_dir: Path,
    root: Path,
) -> str:
    workflow_log_path = output_dir / WORKFLOW_LOG_FILENAME
    artifact_paths = GraphAuthoringLogArtifactPaths(
        output_dir_uri=_relative_uri(output_dir, root),
        workflow_log_uri=_relative_uri(workflow_log_path, root),
    )
    run_log = with_artifact_paths(exc.run_log, artifact_paths)
    log_path = write_graph_authoring_run_log(run_log, output_dir)
    _LOGGER.info(
        "Failed graph authoring run log written run_id=%s workflow_log_uri=%s",
        exc.run_log.run_id,
        _relative_uri(log_path, root),
    )
    return _relative_uri(log_path, root)


def _http_exception_from_workflow_run_error(
    exc: GraphAuthoringWorkflowRunError,
    *,
    workflow_log_uri: str | None,
) -> HTTPException:
    cause = exc.cause
    if isinstance(cause, KnowActValidationError):
        status_code = 422
    elif isinstance(cause, (AuthoringOutputParseError, ModelClientError)):
        status_code = 502
    else:
        status_code = 500

    message = exc.run_log.error.message if exc.run_log.error is not None else str(cause)
    detail: str | dict[str, str] = message
    if workflow_log_uri is not None:
        detail = {
            "message": message,
            "workflow_log_uri": workflow_log_uri,
        }
    return HTTPException(status_code=status_code, detail=detail)


def _relative_uri(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must contain only letters, numbers, dots, underscores, or dashes")
    return value


def _validate_safe_id_or_422(value: str, field_name: str) -> str:
    try:
        return _validate_safe_id(value, field_name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _read_json_list(path: Path) -> list[object]:
    payload = _read_json_payload(path)
    if not isinstance(payload, list):
        raise ValueError(f"{path.name} must contain a JSON list")
    return payload


def _read_json_payload(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
