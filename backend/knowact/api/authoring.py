from collections.abc import Callable
from pathlib import Path
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

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
from backend.knowact.authoring.output import write_graph_authoring_output, write_graph_authoring_run_log
from backend.knowact.authoring.parsers.graph_authoring import AuthoringOutputParseError
from backend.knowact.authoring.schemas import SourceGroundedNodeSkeleton, SourceMaterial
from backend.knowact.authoring.sources import (
    ParsedMarkdownMaterial,
    ParsedMarkdownEmptyError,
    ParsedMarkdownWriteError,
    SourceParser,
    SourcePreparationError,
    resolve_or_create_parsed_markdown,
)
from backend.knowact.authoring.workflow import GraphAuthoringAgentWorkflow
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeNode
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
from backend.knowact.validation.exceptions import KnowActValidationError


_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_DEFAULT_BENCHMARK_DOMAIN = "classical_supervised_ml_algorithms"
_DEFAULT_SOURCE_ID = "isl_python"
_DEFAULT_SOURCE_TITLE = "An Introduction to Statistical Learning with Applications in Python"
GraphAuthoringWorkflowFactory = Callable[[], GraphAuthoringAgentWorkflow]
_LOGGER = get_knowact_logger("api.authoring")


class GraphCandidateAuthoringRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf_path: str = Field(description="Relative path under storage/, for example books/isl_python.pdf.")
    benchmark_domain: str = _DEFAULT_BENCHMARK_DOMAIN
    source_id: str = _DEFAULT_SOURCE_ID
    source_title: str = _DEFAULT_SOURCE_TITLE
    citation: str | None = None
    force_reparse: bool = False
    write_artifacts: bool = True
    run_id: str | None = None

    @field_validator("pdf_path", "source_title")
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


def build_authoring_router(
    *,
    graph_authoring_workflow_factory: GraphAuthoringWorkflowFactory,
    source_parser: SourceParser,
    workspace_root: Path | None = None,
) -> APIRouter:
    root = workspace_root or _default_workspace_root()
    storage_root = root / "storage"
    router = APIRouter()

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
            "Graph candidate authoring request received run_id=%s benchmark_domain=%s pdf_path=%s write_artifacts=%s",
            run_id,
            request.benchmark_domain,
            request.pdf_path,
            request.write_artifacts,
        )

        try:
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
            workflow = _build_graph_authoring_workflow(graph_authoring_workflow_factory)
            source_material = _source_material_from_markdown(parsed_markdown, request)
            run_result = workflow.run_with_log(
                (source_material,),
                run_id=run_id,
                source_metadata=(_run_log_source_material(material, parsed_markdown, request),),
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
                title=request.source_title,
            ),
            run_log_summary=summarize_run_log(run_log),
            source_grounded_node_skeletons=result.source_grounded_node_skeletons,
            candidate_nodes=result.candidate_nodes,
            candidate_edges=result.candidate_edges,
            artifact_paths=artifact_paths,
        )

    return router


def _build_graph_authoring_workflow(
    factory: GraphAuthoringWorkflowFactory,
) -> GraphAuthoringAgentWorkflow:
    try:
        return factory()
    except (ValueError, ModelClientError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _source_material_from_markdown(
    parsed_markdown: ParsedMarkdownMaterial,
    request: GraphCandidateAuthoringRequest,
) -> SourceMaterial:
    return SourceMaterial(
        source_id=request.source_id,
        title=request.source_title,
        citation=request.citation or parsed_markdown.storage_uri,
        text=parsed_markdown.text,
    )


def _run_log_source_material(
    material: LocalPDFMaterial,
    parsed_markdown: ParsedMarkdownMaterial,
    request: GraphCandidateAuthoringRequest,
) -> RunLogSourceMaterial:
    return RunLogSourceMaterial(
        source_id=request.source_id,
        title=request.source_title,
        citation=request.citation or parsed_markdown.storage_uri,
        storage_uri=material.storage_uri,
        filename=material.filename,
        size_bytes=material.size_bytes,
        parsed_markdown_uri=parsed_markdown.storage_uri,
        parsed_markdown_cache_status=parsed_markdown.cache_status,
        parsed_markdown_size_bytes=parsed_markdown.size_bytes,
    )


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _candidate_graph_output_dir(root: Path, benchmark_domain: str, run_id: str) -> Path:
    return root / "benchmark" / "domains" / benchmark_domain / "candidate_graphs" / "api" / run_id


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
