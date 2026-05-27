import json
import re
from pathlib import Path

from pydantic import BaseModel

from backend.knowact.authoring.logging import GraphAuthoringRunLog, WORKFLOW_LOG_FILENAME
from backend.knowact.authoring.schemas import GraphAuthoringWorkflowResult


CANDIDATE_NODES_FILENAME = "candidate_nodes.json"
CANDIDATE_EDGES_FILENAME = "candidate_edges.json"
AGENT_TRACE_DIRNAME = "agent_traces"
MODEL_RAW_OUTPUT_FILENAME = "model_raw_output.txt"
PARSER_OUTPUT_FILENAME = "parser_output.json"
_SAFE_ARTIFACT_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


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

        model_raw_output_uri = trace.model_raw_output_uri
        if trace.model_raw_output is not None:
            model_raw_output_uri = f"{trace_dir_uri}/{MODEL_RAW_OUTPUT_FILENAME}"
            (output_dir / model_raw_output_uri).write_text(
                trace.model_raw_output,
                encoding="utf-8",
            )

        parser_result = trace.parser_result
        parser_output_uri = parser_result.output_uri
        if parser_result.output is not None:
            parser_output_uri = f"{trace_dir_uri}/{PARSER_OUTPUT_FILENAME}"
            with (output_dir / parser_output_uri).open("w", encoding="utf-8") as handle:
                json.dump(parser_result.output, handle, indent=2, ensure_ascii=False)
                handle.write("\n")

        externalized_parser_result = parser_result.model_copy(
            update={
                "output": None,
                "output_uri": parser_output_uri,
            }
        )
        externalized_trace = trace.model_copy(
            update={
                "model_raw_output": None,
                "model_raw_output_uri": model_raw_output_uri,
                "parser_result": externalized_parser_result,
            }
        )
        entries.append(entry.model_copy(update={"agent_trace": externalized_trace}))

    return run_log.model_copy(update={"entries": tuple(entries)})


def _safe_artifact_name(value: str) -> str:
    name = _SAFE_ARTIFACT_NAME_PATTERN.sub("_", value.strip())
    return name.strip("._") or "entry"
