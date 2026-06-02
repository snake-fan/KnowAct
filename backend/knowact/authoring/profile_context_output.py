import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.knowact.authoring.profile_context import (
    PROFILE_CONTEXT_AUTHORING_WORKFLOW_NAME,
    ProfileContextAuthoringWorkflowResult,
)
from backend.knowact.authoring.schemas import CandidateProfileContext


CANDIDATE_PROFILE_CONTEXT_FILENAME = "candidate_profile_context.json"
WORKFLOW_LOG_FILENAME = "workflow_log.json"
AGENT_TRACES_DIRNAME = "agent_traces"
MODEL_RAW_OUTPUT_FILENAME = "model_raw_output.txt"
PARSER_OUTPUT_FILENAME = "parser_output.json"


class CandidateProfileContextArtifactPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir_uri: str
    candidate_profile_context_uri: str
    workflow_log_uri: str
    model_raw_output_uri: str
    parser_output_uri: str


class ProfileContextAuthoringRunLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    workflow_name: str
    status: Literal["succeeded"]
    benchmark_domain: str
    model_provider: str | None = None
    model_name: str | None = None
    message_profile: str | None = None
    artifact_paths: CandidateProfileContextArtifactPaths


class CandidateProfileContextNotFoundError(FileNotFoundError):
    """Raised when a candidate Profile Context run does not exist."""


class CandidateProfileContextArtifactError(RuntimeError):
    """Raised when a saved candidate Profile Context artifact is malformed."""


def write_candidate_profile_context_run(
    *,
    workspace_root: Path,
    output_dir: Path,
    run_id: str,
    result: ProfileContextAuthoringWorkflowResult,
) -> CandidateProfileContextArtifactPaths:
    traces_dir = output_dir / AGENT_TRACES_DIRNAME
    traces_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = output_dir / CANDIDATE_PROFILE_CONTEXT_FILENAME
    workflow_log_path = output_dir / WORKFLOW_LOG_FILENAME
    model_raw_output_path = traces_dir / MODEL_RAW_OUTPUT_FILENAME
    parser_output_path = traces_dir / PARSER_OUTPUT_FILENAME

    _write_json_model(candidate_path, result.candidate_profile_context)
    model_raw_output_path.write_text(result.model_raw_output, encoding="utf-8")
    _write_json_payload(parser_output_path, result.parser_output)

    artifact_paths = _artifact_paths(workspace_root=workspace_root, output_dir=output_dir)
    metadata = result.model_metadata
    _write_json_model(
        workflow_log_path,
        ProfileContextAuthoringRunLog(
            run_id=run_id,
            workflow_name=PROFILE_CONTEXT_AUTHORING_WORKFLOW_NAME,
            status="succeeded",
            benchmark_domain=result.candidate_profile_context.benchmark_domain,
            model_provider=metadata.provider if metadata is not None else None,
            model_name=metadata.model_name if metadata is not None else None,
            message_profile=metadata.message_profile if metadata is not None else None,
            artifact_paths=artifact_paths,
        ),
    )
    return artifact_paths


def read_candidate_profile_context_run(
    *,
    workspace_root: Path,
    output_dir: Path,
) -> tuple[CandidateProfileContext, CandidateProfileContextArtifactPaths]:
    candidate_path = output_dir / CANDIDATE_PROFILE_CONTEXT_FILENAME
    if not candidate_path.exists():
        raise CandidateProfileContextNotFoundError("candidate Profile Context does not exist")
    try:
        with candidate_path.open(encoding="utf-8") as handle:
            candidate = CandidateProfileContext.model_validate(json.load(handle))
    except (OSError, ValueError, ValidationError) as exc:
        raise CandidateProfileContextArtifactError(str(exc)) from exc
    return candidate, _artifact_paths(workspace_root=workspace_root, output_dir=output_dir)


def _artifact_paths(
    *,
    workspace_root: Path,
    output_dir: Path,
) -> CandidateProfileContextArtifactPaths:
    traces_dir = output_dir / AGENT_TRACES_DIRNAME
    return CandidateProfileContextArtifactPaths(
        output_dir_uri=_relative_uri(output_dir, workspace_root),
        candidate_profile_context_uri=_relative_uri(
            output_dir / CANDIDATE_PROFILE_CONTEXT_FILENAME,
            workspace_root,
        ),
        workflow_log_uri=_relative_uri(output_dir / WORKFLOW_LOG_FILENAME, workspace_root),
        model_raw_output_uri=_relative_uri(traces_dir / MODEL_RAW_OUTPUT_FILENAME, workspace_root),
        parser_output_uri=_relative_uri(traces_dir / PARSER_OUTPUT_FILENAME, workspace_root),
    )


def _write_json_model(path: Path, model: BaseModel) -> None:
    _write_json_payload(path, model.model_dump(mode="json", exclude_none=True))


def _write_json_payload(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _relative_uri(path: Path, workspace_root: Path) -> str:
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()
