from collections.abc import Iterator
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import tempfile
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.knowact.authoring.profile_context import (
    PROFILE_CONTEXT_AUTHORING_WORKFLOW_NAME,
    ProfileContextAuthoringWorkflowResult,
)
from backend.knowact.authoring.schemas import CandidateProfileContext, ConfirmedProfileContext


CANDIDATE_PROFILE_CONTEXT_FILENAME = "candidate_profile_context.json"
CONFIRMED_PROFILE_CONTEXT_FILENAME = "profile_context.json"
WORKFLOW_LOG_FILENAME = "workflow_log.json"
AGENT_TRACES_DIRNAME = "agent_traces"
MODEL_RAW_OUTPUT_FILENAME = "model_raw_output.txt"
PARSER_OUTPUT_FILENAME = "parser_output.json"
CONFIRMATION_LOCK_FILENAME = ".confirmation.lock"


class CandidateProfileContextArtifactPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir_uri: str
    candidate_profile_context_uri: str
    workflow_log_uri: str
    model_raw_output_uri: str
    parser_output_uri: str


class ConfirmedProfileContextArtifactPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir_uri: str
    profile_context_uri: str


class ProfileContextAuthoringRunLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    workflow_name: str
    status: Literal["succeeded"]
    benchmark_domain: str
    model_provider: str | None = None
    model_name: str | None = None
    message_profile: str | None = None
    confirmed_user_id: str | None = None
    artifact_paths: CandidateProfileContextArtifactPaths


class CandidateProfileContextNotFoundError(FileNotFoundError):
    """Raised when a candidate Profile Context run does not exist."""


class CandidateProfileContextArtifactError(RuntimeError):
    """Raised when a saved candidate Profile Context artifact is malformed."""


class ConfirmedProfileContextConflictError(FileExistsError):
    """Raised when confirmation would overwrite an immutable synthetic-user snapshot."""


class CandidateProfileContextConfirmationConflictError(RuntimeError):
    """Raised when one candidate Profile Context run is confirmed more than once."""


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
    benchmark_domain: str | None = None,
) -> tuple[CandidateProfileContext, CandidateProfileContextArtifactPaths]:
    candidate_path = output_dir / CANDIDATE_PROFILE_CONTEXT_FILENAME
    if not candidate_path.exists():
        raise CandidateProfileContextNotFoundError("candidate Profile Context does not exist")
    try:
        with candidate_path.open(encoding="utf-8") as handle:
            candidate = CandidateProfileContext.model_validate(json.load(handle))
    except (OSError, ValueError, ValidationError) as exc:
        raise CandidateProfileContextArtifactError(str(exc)) from exc
    if benchmark_domain is not None and candidate.benchmark_domain != benchmark_domain:
        raise CandidateProfileContextArtifactError(
            "candidate Profile Context benchmark_domain does not match artifact path"
        )
    return candidate, _artifact_paths(workspace_root=workspace_root, output_dir=output_dir)


def write_candidate_profile_context(
    *,
    output_dir: Path,
    candidate: CandidateProfileContext,
) -> None:
    _write_json_model(output_dir / CANDIDATE_PROFILE_CONTEXT_FILENAME, candidate)


def confirm_candidate_profile_context(
    *,
    workspace_root: Path,
    output_dir: Path,
    benchmark_domain: str,
    user_id: str,
    candidate: CandidateProfileContext,
) -> tuple[ConfirmedProfileContext, ConfirmedProfileContextArtifactPaths]:
    with _candidate_profile_context_confirmation_lock(output_dir):
        _ensure_candidate_profile_context_not_confirmed(output_dir=output_dir)
        profile_context, artifact_paths = _publish_confirmed_profile_context(
            workspace_root=workspace_root,
            benchmark_domain=benchmark_domain,
            user_id=user_id,
            candidate=candidate,
        )
        try:
            _record_candidate_profile_context_confirmation(
                output_dir=output_dir,
                user_id=user_id,
            )
        except Exception:
            _remove_path(
                _confirmed_profile_context_output_dir(
                    workspace_root=workspace_root,
                    benchmark_domain=benchmark_domain,
                    user_id=user_id,
                )
            )
            raise
        return profile_context, artifact_paths


def _publish_confirmed_profile_context(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    user_id: str,
    candidate: CandidateProfileContext,
) -> tuple[ConfirmedProfileContext, ConfirmedProfileContextArtifactPaths]:
    profile_context = ConfirmedProfileContext(
        user_id=user_id,
        **candidate.model_dump(),
    )
    output_dir = _confirmed_profile_context_output_dir(
        workspace_root=workspace_root,
        benchmark_domain=benchmark_domain,
        user_id=user_id,
    )
    if output_dir.exists():
        raise ConfirmedProfileContextConflictError(
            f"Confirmed Profile Context user_id {user_id} already exists"
        )
    users_dir = output_dir.parent
    users_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{user_id}.", dir=users_dir))
    try:
        _write_json_model(staging_dir / CONFIRMED_PROFILE_CONTEXT_FILENAME, profile_context)
        _publish_staged_directory(staging_dir, output_dir)
    except Exception:
        _remove_path(staging_dir)
        raise
    return profile_context, _confirmed_artifact_paths(
        workspace_root=workspace_root,
        output_dir=output_dir,
    )


def _ensure_candidate_profile_context_not_confirmed(*, output_dir: Path) -> None:
    run_log = _read_profile_context_authoring_run_log(output_dir)
    if run_log.confirmed_user_id is not None:
        raise CandidateProfileContextConfirmationConflictError(
            "candidate Profile Context run has already been confirmed "
            f"as user_id {run_log.confirmed_user_id}"
        )


def _record_candidate_profile_context_confirmation(*, output_dir: Path, user_id: str) -> None:
    run_log = _read_profile_context_authoring_run_log(output_dir)
    if run_log.confirmed_user_id is not None:
        raise CandidateProfileContextConfirmationConflictError(
            "candidate Profile Context run has already been confirmed "
            f"as user_id {run_log.confirmed_user_id}"
        )
    _write_json_model(
        output_dir / WORKFLOW_LOG_FILENAME,
        run_log.model_copy(update={"confirmed_user_id": user_id}),
    )


@contextmanager
def _candidate_profile_context_confirmation_lock(output_dir: Path) -> Iterator[None]:
    lock_path = output_dir / CONFIRMATION_LOCK_FILENAME
    try:
        lock_path.touch(exist_ok=False)
    except FileExistsError as exc:
        raise CandidateProfileContextConfirmationConflictError(
            "candidate Profile Context run is already being confirmed"
        ) from exc
    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def _confirmed_profile_context_output_dir(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    user_id: str,
) -> Path:
    return (
        workspace_root
        / "benchmark"
        / "domains"
        / benchmark_domain
        / "users"
        / user_id
    )


def _publish_staged_directory(staging_dir: Path, output_dir: Path) -> None:
    if output_dir.exists():
        raise ConfirmedProfileContextConflictError(
            f"Confirmed Profile Context user_id {output_dir.name} already exists"
        )
    try:
        staging_dir.replace(output_dir)
    except FileExistsError as exc:
        raise ConfirmedProfileContextConflictError(
            f"Confirmed Profile Context user_id {output_dir.name} already exists"
        ) from exc


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


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


def _read_profile_context_authoring_run_log(output_dir: Path) -> ProfileContextAuthoringRunLog:
    workflow_log_path = output_dir / WORKFLOW_LOG_FILENAME
    try:
        with workflow_log_path.open(encoding="utf-8") as handle:
            return ProfileContextAuthoringRunLog.model_validate(json.load(handle))
    except (OSError, ValueError, ValidationError) as exc:
        raise CandidateProfileContextArtifactError(str(exc)) from exc


def _confirmed_artifact_paths(
    *,
    workspace_root: Path,
    output_dir: Path,
) -> ConfirmedProfileContextArtifactPaths:
    return ConfirmedProfileContextArtifactPaths(
        output_dir_uri=_relative_uri(output_dir, workspace_root),
        profile_context_uri=_relative_uri(
            output_dir / CONFIRMED_PROFILE_CONTEXT_FILENAME,
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
