import json
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.knowact.authoring.schemas import (
    GroundTruthEvidenceDraftList,
    KnowledgeStateOutlineList,
)
from backend.knowact.core.map import KnowledgeMap
from backend.knowact.core.map import KnowledgeMapKind
from backend.knowact.llm.client import ModelClientMetadata


CANDIDATE_MAP_FILENAME = "candidate_map.json"
WORKFLOW_LOG_FILENAME = "workflow_log.json"
INTERMEDIATE_DIRNAME = "intermediate"
STATE_OUTLINE_FILENAME = "state_outline.json"
GROUND_TRUTH_EVIDENCE_FILENAME = "ground_truth_evidence.json"
AGENT_TRACES_DIRNAME = "agent_traces"
KNOWLEDGE_STATE_OUTLINE_STEP = "knowledge_state_outline"
GROUND_TRUTH_EVIDENCE_STEP = "ground_truth_evidence"
SINGLE_BATCH_NAME = "batch_001"
MODEL_RAW_OUTPUT_FILENAME = "model_raw_output.txt"
PARSER_OUTPUT_FILENAME = "parser_output.json"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class CandidateMapArtifactPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir_uri: str
    candidate_map_uri: str
    workflow_log_uri: str
    state_outline_uri: str
    ground_truth_evidence_uri: str
    outline_model_raw_output_uri: str
    outline_parser_output_uri: str
    evidence_model_raw_output_uri: str
    evidence_parser_output_uri: str


class CandidateMapAuthoringRunLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    workflow_name: str
    status: Literal["succeeded", "failed"]
    benchmark_domain: str
    graph_version: str
    user_id: str
    model_provider: str | None = None
    model_name: str | None = None
    message_profile: str | None = None
    error: str | None = None
    artifact_paths: CandidateMapArtifactPaths


class CandidateMapNotFoundError(FileNotFoundError):
    """Raised when a candidate-map run does not contain a promotable map."""


class CandidateMapArtifactError(ValueError):
    """Raised when a saved candidate-map artifact is malformed."""


class CandidateMapRunConflictError(FileExistsError):
    """Raised when generation would overwrite an existing candidate-map run."""


class CandidateMapArtifactWriter:
    def __init__(self, *, workspace_root: Path, benchmark_domain: str, run_id: str) -> None:
        self._workspace_root = workspace_root
        self._output_dir = (
            workspace_root
            / "benchmark"
            / "domains"
            / benchmark_domain
            / "candidate_maps"
            / run_id
        )
        if self._output_dir.exists():
            raise CandidateMapRunConflictError(f"Candidate map run {run_id} already exists")
        self._intermediate_dir = self._output_dir / INTERMEDIATE_DIRNAME
        self._outline_trace_dir = (
            self._output_dir / AGENT_TRACES_DIRNAME / KNOWLEDGE_STATE_OUTLINE_STEP
        )
        self._evidence_trace_dir = (
            self._output_dir
            / AGENT_TRACES_DIRNAME
            / GROUND_TRUTH_EVIDENCE_STEP
            / SINGLE_BATCH_NAME
        )
        self._intermediate_dir.mkdir(parents=True, exist_ok=True)
        self._outline_trace_dir.mkdir(parents=True, exist_ok=True)
        self._evidence_trace_dir.mkdir(parents=True, exist_ok=True)

    @property
    def artifact_paths(self) -> CandidateMapArtifactPaths:
        return _artifact_paths(
            workspace_root=self._workspace_root,
            output_dir=self._output_dir,
        )

    def write_outline_raw_output(self, raw_output: str) -> None:
        (self._outline_trace_dir / MODEL_RAW_OUTPUT_FILENAME).write_text(
            raw_output,
            encoding="utf-8",
        )

    def write_outline_parser_output(self, outlines: KnowledgeStateOutlineList) -> None:
        payload = outlines.model_dump(mode="json")
        _write_json_payload(self._outline_trace_dir / PARSER_OUTPUT_FILENAME, payload)
        _write_json_payload(self._intermediate_dir / STATE_OUTLINE_FILENAME, payload)

    def write_evidence_raw_output(self, raw_output: str) -> None:
        (self._evidence_trace_dir / MODEL_RAW_OUTPUT_FILENAME).write_text(
            raw_output,
            encoding="utf-8",
        )

    def write_evidence_parser_output(self, drafts: GroundTruthEvidenceDraftList) -> None:
        payload = drafts.model_dump(mode="json")
        _write_json_payload(self._evidence_trace_dir / PARSER_OUTPUT_FILENAME, payload)
        _write_json_payload(self._intermediate_dir / GROUND_TRUTH_EVIDENCE_FILENAME, payload)

    def write_candidate_map(self, candidate_map: KnowledgeMap) -> None:
        _write_json_payload(
            self._output_dir / CANDIDATE_MAP_FILENAME,
            candidate_map.model_dump(mode="json"),
        )

    def write_workflow_log(
        self,
        *,
        run_id: str,
        workflow_name: str,
        status: Literal["succeeded", "failed"],
        benchmark_domain: str,
        graph_version: str,
        user_id: str,
        model_metadata: ModelClientMetadata | None,
        error: str | None = None,
    ) -> None:
        _write_json_model(
            self._output_dir / WORKFLOW_LOG_FILENAME,
            CandidateMapAuthoringRunLog(
                run_id=run_id,
                workflow_name=workflow_name,
                status=status,
                benchmark_domain=benchmark_domain,
                graph_version=graph_version,
                user_id=user_id,
                model_provider=model_metadata.provider if model_metadata is not None else None,
                model_name=model_metadata.model_name if model_metadata is not None else None,
                message_profile=(
                    model_metadata.message_profile if model_metadata is not None else None
                ),
                error=error,
                artifact_paths=self.artifact_paths,
            ),
        )


def read_candidate_map_run(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    run_id: str,
) -> tuple[KnowledgeMap, CandidateMapArtifactPaths]:
    benchmark_domain = _validate_safe_id(benchmark_domain, "benchmark_domain")
    run_id = _validate_safe_id(run_id, "run_id")
    output_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / benchmark_domain
        / "candidate_maps"
        / run_id
    )
    candidate_path = output_dir / CANDIDATE_MAP_FILENAME
    if not candidate_path.exists():
        raise CandidateMapNotFoundError(f"Candidate map run {run_id} does not exist")
    try:
        with candidate_path.open(encoding="utf-8") as handle:
            candidate_map = KnowledgeMap.model_validate(json.load(handle))
        if candidate_map.kind != KnowledgeMapKind.CANDIDATE:
            raise ValueError("candidate_map.json must use kind candidate")
    except (OSError, ValueError, ValidationError) as exc:
        raise CandidateMapArtifactError(str(exc)) from exc
    return candidate_map, _artifact_paths(
        workspace_root=workspace_root,
        output_dir=output_dir,
    )


def _artifact_paths(*, workspace_root: Path, output_dir: Path) -> CandidateMapArtifactPaths:
    traces_dir = output_dir / AGENT_TRACES_DIRNAME
    outline_trace_dir = traces_dir / KNOWLEDGE_STATE_OUTLINE_STEP
    evidence_trace_dir = traces_dir / GROUND_TRUTH_EVIDENCE_STEP / SINGLE_BATCH_NAME
    return CandidateMapArtifactPaths(
        output_dir_uri=_relative_uri(output_dir, workspace_root),
        candidate_map_uri=_relative_uri(output_dir / CANDIDATE_MAP_FILENAME, workspace_root),
        workflow_log_uri=_relative_uri(output_dir / WORKFLOW_LOG_FILENAME, workspace_root),
        state_outline_uri=_relative_uri(
            output_dir / INTERMEDIATE_DIRNAME / STATE_OUTLINE_FILENAME,
            workspace_root,
        ),
        ground_truth_evidence_uri=_relative_uri(
            output_dir / INTERMEDIATE_DIRNAME / GROUND_TRUTH_EVIDENCE_FILENAME,
            workspace_root,
        ),
        outline_model_raw_output_uri=_relative_uri(
            outline_trace_dir / MODEL_RAW_OUTPUT_FILENAME,
            workspace_root,
        ),
        outline_parser_output_uri=_relative_uri(
            outline_trace_dir / PARSER_OUTPUT_FILENAME,
            workspace_root,
        ),
        evidence_model_raw_output_uri=_relative_uri(
            evidence_trace_dir / MODEL_RAW_OUTPUT_FILENAME,
            workspace_root,
        ),
        evidence_parser_output_uri=_relative_uri(
            evidence_trace_dir / PARSER_OUTPUT_FILENAME,
            workspace_root,
        ),
    )


def _write_json_model(path: Path, model: BaseModel) -> None:
    _write_json_payload(path, model.model_dump(mode="json", exclude_none=True))


def _write_json_payload(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _relative_uri(path: Path, workspace_root: Path) -> str:
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} must contain only letters, numbers, dots, underscores, or dashes"
        )
    return value
