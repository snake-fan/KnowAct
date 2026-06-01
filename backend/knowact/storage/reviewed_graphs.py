from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import tempfile
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from backend.knowact.core.graph import GraphManifest, GraphManifestSource, KnowledgeEdge, KnowledgeNode


CANDIDATE_NODES_FILENAME = "candidate_nodes.json"
CANDIDATE_EDGES_FILENAME = "candidate_edges.json"
WORKFLOW_LOG_FILENAME = "workflow_log.json"
GRAPH_MANIFEST_FILENAME = "graph_manifest.json"
AUTHORED_NODES_FILENAME = "authored_nodes.json"
AUTHORED_EDGES_FILENAME = "authored_edges.json"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class CandidateGraphNotFoundError(FileNotFoundError):
    """Raised when a candidate graph run does not contain publishable artifacts."""


class CandidateGraphArtifactError(ValueError):
    """Raised when candidate graph artifacts cannot be parsed or validated."""


class ReviewedGraphPromotionConflictError(FileExistsError):
    """Raised when promotion would overwrite a reviewed graph without approval."""


@dataclass(frozen=True)
class ReviewedGraphPromotion:
    manifest: GraphManifest
    output_dir: Path
    graph_manifest_path: Path
    authored_nodes_path: Path
    authored_edges_path: Path


@dataclass(frozen=True)
class CandidateGraphArtifacts:
    nodes: tuple[KnowledgeNode, ...]
    edges: tuple[KnowledgeEdge, ...]
    candidate_dir: Path


def load_candidate_graph(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    run_id: str,
) -> CandidateGraphArtifacts:
    benchmark_domain = _validate_safe_id(benchmark_domain, "benchmark_domain")
    run_id = _validate_safe_id(run_id, "run_id")
    candidate_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / benchmark_domain
        / "candidate_graphs"
        / run_id
    )
    candidate_nodes_path = candidate_dir / CANDIDATE_NODES_FILENAME
    candidate_edges_path = candidate_dir / CANDIDATE_EDGES_FILENAME
    if not candidate_nodes_path.exists() or not candidate_edges_path.exists():
        raise CandidateGraphNotFoundError(f"Candidate graph run {run_id} does not exist")

    try:
        nodes = tuple(KnowledgeNode.model_validate(item) for item in _read_json_list(candidate_nodes_path))
        edges = tuple(KnowledgeEdge.model_validate(item) for item in _read_json_list(candidate_edges_path))
    except (OSError, ValueError, ValidationError) as exc:
        raise CandidateGraphArtifactError(str(exc)) from exc
    return CandidateGraphArtifacts(nodes=nodes, edges=edges, candidate_dir=candidate_dir)


def publish_reviewed_graph(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    version: str,
    manifest: GraphManifest,
    nodes: tuple[KnowledgeNode, ...],
    edges: tuple[KnowledgeEdge, ...],
    overwrite: bool = False,
) -> ReviewedGraphPromotion:
    benchmark_domain = _validate_safe_id(benchmark_domain, "benchmark_domain")
    version = _validate_safe_id(version, "version")
    graph_root = workspace_root / "benchmark" / "domains" / benchmark_domain / "graphs"
    output_dir = graph_root / version
    if output_dir.exists() and not overwrite:
        raise ReviewedGraphPromotionConflictError(f"Reviewed graph version {version} already exists")

    graph_root.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{version}.", dir=graph_root))
    try:
        _write_json_list(staging_dir / AUTHORED_NODES_FILENAME, nodes)
        _write_json_list(staging_dir / AUTHORED_EDGES_FILENAME, edges)
        _write_json_model(staging_dir / GRAPH_MANIFEST_FILENAME, manifest)
        _publish_staged_directory(staging_dir, output_dir)
    except Exception:
        _remove_path(staging_dir)
        raise

    return ReviewedGraphPromotion(
        manifest=manifest,
        output_dir=output_dir,
        graph_manifest_path=output_dir / GRAPH_MANIFEST_FILENAME,
        authored_nodes_path=output_dir / AUTHORED_NODES_FILENAME,
        authored_edges_path=output_dir / AUTHORED_EDGES_FILENAME,
    )


def read_optional_manifest_sources(candidate_dir: Path) -> tuple[GraphManifestSource, ...]:
    workflow_log_path = candidate_dir / WORKFLOW_LOG_FILENAME
    try:
        with workflow_log_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        source_materials = payload["source_materials"]
        if not isinstance(source_materials, list):
            return ()
        return tuple(
            GraphManifestSource.model_validate(
                {
                    "source_id": material["source_id"],
                    "title": material["title"],
                    "citation": material.get("citation"),
                }
            )
            for material in source_materials
            if isinstance(material, dict)
        )
    except (OSError, KeyError, TypeError, ValueError, ValidationError, json.JSONDecodeError):
        return ()


def _publish_staged_directory(staging_dir: Path, output_dir: Path) -> None:
    if not output_dir.exists():
        staging_dir.replace(output_dir)
        return

    backup_dir = output_dir.with_name(f".{output_dir.name}.backup-{uuid4().hex}")
    output_dir.replace(backup_dir)
    try:
        staging_dir.replace(output_dir)
    except Exception:
        backup_dir.replace(output_dir)
        raise
    _remove_path(backup_dir)


def _read_json_list(path: Path) -> list[object]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path.name} must contain a JSON list")
    return payload


def _write_json_list(path: Path, items: tuple[BaseModel, ...]) -> None:
    payload = [item.model_dump(mode="json", exclude_none=True) for item in items]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _write_json_model(path: Path, model: BaseModel) -> None:
    payload = model.model_dump(mode="json", exclude_none=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must contain only letters, numbers, dots, underscores, or dashes")
    return value
