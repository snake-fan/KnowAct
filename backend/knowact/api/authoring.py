from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.authoring.output import write_graph_authoring_output
from backend.knowact.authoring.parsers.graph_authoring import AuthoringOutputParseError
from backend.knowact.authoring.schemas import SourceGroundedNodeSkeleton, SourceMaterial
from backend.knowact.authoring.workflow import GraphAuthoringAgentWorkflow
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeNode
from backend.knowact.llm.client import ModelClientError
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
PDFGraphAuthoringWorkflowFactory = Callable[[Path, str | None], GraphAuthoringAgentWorkflow]


class GraphCandidateAuthoringRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf_path: str = Field(description="Relative path under storage/, for example books/isl_python.pdf.")
    benchmark_domain: str = _DEFAULT_BENCHMARK_DOMAIN
    source_id: str = _DEFAULT_SOURCE_ID
    source_title: str = _DEFAULT_SOURCE_TITLE
    citation: str | None = None
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
    source_id: str
    title: str


class GraphCandidateArtifactPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir_uri: str
    candidate_nodes_uri: str
    candidate_edges_uri: str


class GraphCandidateAuthoringResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow: str
    material: SourceMaterialInfo
    source_grounded_node_skeletons: tuple[SourceGroundedNodeSkeleton, ...]
    candidate_nodes: tuple[KnowledgeNode, ...]
    candidate_edges: tuple[KnowledgeEdge, ...]
    artifact_paths: GraphCandidateArtifactPaths | None = None


def build_authoring_router(
    *,
    pdf_graph_authoring_workflow_factory: PDFGraphAuthoringWorkflowFactory,
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
        try:
            material = resolve_pdf_material(storage_root=storage_root, storage_path=request.pdf_path)
            workflow = _build_pdf_graph_authoring_workflow(
                pdf_graph_authoring_workflow_factory,
                material.path,
                material.filename,
            )
            result = workflow.run((_source_material_from_pdf(material, request),))
        except MaterialFileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except MaterialFileTypeError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        except MaterialFileSizeError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except MaterialFileError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except KnowActValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except AuthoringOutputParseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ModelClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        artifact_paths = None
        if request.write_artifacts:
            run_id = request.run_id or _default_run_id()
            output_dir = (
                root
                / "benchmark"
                / "domains"
                / request.benchmark_domain
                / "candidate_graphs"
                / "api"
                / run_id
            )
            nodes_path, edges_path = write_graph_authoring_output(result, output_dir)
            artifact_paths = GraphCandidateArtifactPaths(
                output_dir_uri=_relative_uri(output_dir, root),
                candidate_nodes_uri=_relative_uri(nodes_path, root),
                candidate_edges_uri=_relative_uri(edges_path, root),
            )

        return GraphCandidateAuthoringResponse(
            workflow="Graph Authoring Agent Workflow",
            material=SourceMaterialInfo(
                storage_uri=material.storage_uri,
                filename=material.filename,
                size_bytes=material.size_bytes,
                source_id=request.source_id,
                title=request.source_title,
            ),
            source_grounded_node_skeletons=result.source_grounded_node_skeletons,
            candidate_nodes=result.candidate_nodes,
            candidate_edges=result.candidate_edges,
            artifact_paths=artifact_paths,
        )

    return router


def _build_pdf_graph_authoring_workflow(
    factory: PDFGraphAuthoringWorkflowFactory,
    pdf_path: Path,
    filename: str,
) -> GraphAuthoringAgentWorkflow:
    try:
        return factory(pdf_path, filename)
    except (ValueError, ModelClientError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _source_material_from_pdf(
    material: LocalPDFMaterial,
    request: GraphCandidateAuthoringRequest,
) -> SourceMaterial:
    return SourceMaterial(
        source_id=request.source_id,
        title=request.source_title,
        citation=request.citation or material.storage_uri,
        text=(
            "Uploaded original PDF content is provided through the OpenAI Responses "
            "input_file attachment, not embedded in the prompt."
        ),
    )


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_run_id() -> str:
    return f"run_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"


def _relative_uri(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must contain only letters, numbers, dots, underscores, or dashes")
    return value
