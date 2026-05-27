import json
import re
from pathlib import Path

from pydantic import BaseModel

from backend.knowact.authoring.logging import GraphAuthoringRunLog, WORKFLOW_LOG_FILENAME
from backend.knowact.authoring.schemas import GraphAuthoringWorkflowResult


CANDIDATE_NODES_FILENAME = "candidate_nodes.json"
CANDIDATE_EDGES_FILENAME = "candidate_edges.json"
AGENT_TRACE_DIRNAME = "agent_traces"
INTERMEDIATE_DIRNAME = "intermediate"
MODEL_RAW_OUTPUT_FILENAME = "model_raw_output.txt"
PARSER_OUTPUT_FILENAME = "parser_output.json"
SOURCE_GROUNDED_NODE_SKELETONS_FILENAME = "source_grounded_node_skeletons.json"
NODE_RUBRIC_PATCHES_FILENAME = "node_rubric_patches.json"
CANDIDATE_NODES_PRE_EDGE_FILENAME = "candidate_nodes_pre_edge.json"
CANDIDATE_EDGES_CANONICAL_FILENAME = "candidate_edges_canonical.json"
_SAFE_ARTIFACT_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


class GraphAuthoringIntermediateArtifactWriter:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def write_source_grounded_node_skeletons(self, items: tuple[BaseModel, ...]) -> str:
        return self._write_json_list(SOURCE_GROUNDED_NODE_SKELETONS_FILENAME, items)

    def write_node_rubric_patches(self, items: tuple[BaseModel, ...]) -> str:
        return self._write_json_list(NODE_RUBRIC_PATCHES_FILENAME, items)

    def write_candidate_nodes_pre_edge(self, items: tuple[BaseModel, ...]) -> str:
        return self._write_json_list(CANDIDATE_NODES_PRE_EDGE_FILENAME, items)

    def write_candidate_edges_canonical(self, items: tuple[BaseModel, ...]) -> str:
        return self._write_json_list(CANDIDATE_EDGES_CANONICAL_FILENAME, items)

    def _write_json_list(self, filename: str, items: tuple[BaseModel, ...]) -> str:
        artifact_uri = f"{INTERMEDIATE_DIRNAME}/{filename}"
        path = self._output_dir / artifact_uri
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_list(path, items)
        return artifact_uri


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
    run_log = _write_agent_trace_artifacts(run_log, output_dir)
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


def _write_agent_trace_artifacts(
    run_log: GraphAuthoringRunLog,
    output_dir: Path,
) -> GraphAuthoringRunLog:
    entries = []
    for entry in run_log.entries:
        trace = entry.agent_trace
        if trace is None:
            entries.append(entry)
            continue

        trace_dir_uri = f"{AGENT_TRACE_DIRNAME}/{_safe_artifact_name(entry.entry_name)}"
        trace_dir = output_dir / trace_dir_uri
        trace_dir.mkdir(parents=True, exist_ok=True)

        externalized_trace = _externalize_agent_trace(trace, output_dir, trace_dir_uri)
        entries.append(entry.model_copy(update={"agent_trace": externalized_trace}))

    return run_log.model_copy(update={"entries": tuple(entries)})


def _externalize_agent_trace(
    trace,
    output_dir: Path,
    trace_dir_uri: str,
):
    model_raw_output_uri = _write_optional_text_artifact(
        output_dir,
        trace_dir_uri,
        trace.model_raw_output,
        trace.model_raw_output_uri,
    )
    externalized_parser_result = _externalize_parser_result(
        trace.parser_result,
        output_dir,
        trace_dir_uri,
    )
    externalized_batches = tuple(
        _externalize_agent_trace_batch(batch_trace, output_dir, trace_dir_uri)
        for batch_trace in trace.batch_traces
    )
    return trace.model_copy(
        update={
            "model_raw_output": None,
            "model_raw_output_uri": model_raw_output_uri,
            "parser_result": externalized_parser_result,
            "batch_traces": externalized_batches,
        }
    )


def _externalize_agent_trace_batch(
    batch_trace,
    output_dir: Path,
    trace_dir_uri: str,
):
    batch_dir_uri = f"{trace_dir_uri}/{_safe_artifact_name(batch_trace.batch_name)}"
    (output_dir / batch_dir_uri).mkdir(parents=True, exist_ok=True)
    model_raw_output_uri = _write_optional_text_artifact(
        output_dir,
        batch_dir_uri,
        batch_trace.model_raw_output,
        batch_trace.model_raw_output_uri,
    )
    externalized_parser_result = _externalize_parser_result(
        batch_trace.parser_result,
        output_dir,
        batch_dir_uri,
    )
    return batch_trace.model_copy(
        update={
            "model_raw_output": None,
            "model_raw_output_uri": model_raw_output_uri,
            "parser_result": externalized_parser_result,
        }
    )


def _write_optional_text_artifact(
    output_dir: Path,
    artifact_dir_uri: str,
    content: str | None,
    existing_uri: str | None,
) -> str | None:
    if content is None:
        return existing_uri
    artifact_uri = f"{artifact_dir_uri}/{MODEL_RAW_OUTPUT_FILENAME}"
    (output_dir / artifact_uri).write_text(content, encoding="utf-8")
    return artifact_uri


def _externalize_parser_result(
    parser_result,
    output_dir: Path,
    artifact_dir_uri: str,
):
    parser_output_uri = parser_result.output_uri
    if parser_result.output is not None:
        parser_output_uri = f"{artifact_dir_uri}/{PARSER_OUTPUT_FILENAME}"
        with (output_dir / parser_output_uri).open("w", encoding="utf-8") as handle:
            json.dump(parser_result.output, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    return parser_result.model_copy(
        update={
            "output": None,
            "output_uri": parser_output_uri,
        }
    )


def _safe_artifact_name(value: str) -> str:
    name = _SAFE_ARTIFACT_NAME_PATTERN.sub("_", value.strip())
    return name.strip("._") or "entry"
