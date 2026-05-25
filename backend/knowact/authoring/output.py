import json
from pathlib import Path

from pydantic import BaseModel

from backend.knowact.authoring.logging import GraphAuthoringRunLog, WORKFLOW_LOG_FILENAME
from backend.knowact.authoring.schemas import GraphAuthoringWorkflowResult


CANDIDATE_NODES_FILENAME = "candidate_nodes.json"
CANDIDATE_EDGES_FILENAME = "candidate_edges.json"


def write_graph_authoring_output(
    result: GraphAuthoringWorkflowResult,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = output_dir / CANDIDATE_NODES_FILENAME
    edges_path = output_dir / CANDIDATE_EDGES_FILENAME
    _write_json_list(nodes_path, result.candidate_nodes)
    _write_json_list(edges_path, result.candidate_edges)
    return nodes_path, edges_path


def write_graph_authoring_run_log(
    run_log: GraphAuthoringRunLog,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / WORKFLOW_LOG_FILENAME
    _write_json_model(log_path, run_log)
    return log_path


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
