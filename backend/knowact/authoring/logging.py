from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.authoring.schemas import GraphAuthoringWorkflowResult, SourceMaterial
from backend.knowact.llm.client import ModelClientMetadata


GRAPH_AUTHORING_WORKFLOW_NAME = "Graph Authoring Agent Workflow"
WORKFLOW_LOG_FILENAME = "workflow_log.json"
MAX_ERROR_MESSAGE_CHARS = 500

RunLogStatus = Literal["running", "succeeded", "failed"]
RunLogCompletedStatus = Literal["succeeded", "failed"]
WorkflowRunLogEntryType = Literal["agent_step", "validation_checkpoint", "artifact_write", "deterministic_step"]
WorkflowRunValidationResult = Literal["passed", "failed"]
WorkflowRunParserResultStatus = Literal["succeeded", "failed"]

_OPENAI_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{8,}")
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|bearer)\b\s*[:=]\s*\S+"
)


class RunLogSourceMaterial(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    title: str
    citation: str | None = None
    storage_uri: str | None = None
    filename: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    parsed_markdown_uri: str | None = None
    parsed_markdown_cache_status: str | None = None
    parsed_markdown_size_bytes: int | None = Field(default=None, ge=0)

    @classmethod
    def from_source_material(cls, source_material: SourceMaterial) -> "RunLogSourceMaterial":
        return cls(
            source_id=source_material.source_id,
            title=source_material.title,
            citation=source_material.citation,
        )

    @field_validator("source_id", "title")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("citation", "storage_uri", "filename", "parsed_markdown_uri", "parsed_markdown_cache_status")
    @classmethod
    def _optional_values_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class GraphAuthoringLogArtifactPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir_uri: str | None = None
    candidate_nodes_uri: str | None = None
    candidate_edges_uri: str | None = None
    workflow_log_uri: str | None = None

    @field_validator("output_dir_uri", "candidate_nodes_uri", "candidate_edges_uri", "workflow_log_uri")
    @classmethod
    def _optional_values_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class WorkflowRunError(BaseModel):
    model_config = ConfigDict(frozen=True)

    error_type: str
    message: str
    checkpoint: str | None = None
    step_name: str | None = None

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        *,
        checkpoint: str | None = None,
        step_name: str | None = None,
    ) -> "WorkflowRunError":
        return cls(
            error_type=type(exc).__name__,
            message=redact_error_message(str(exc)),
            checkpoint=checkpoint,
            step_name=step_name,
        )

    @field_validator("error_type", "message")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class WorkflowRunParserResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: WorkflowRunParserResultStatus
    output: dict[str, Any] | None = None
    output_uri: str | None = None
    error: WorkflowRunError | None = None


class WorkflowRunAgentTraceBatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    batch_name: str
    input_counts: dict[str, int] = Field(default_factory=dict)
    model_raw_output: str | None = None
    model_raw_output_uri: str | None = None
    parser_result: WorkflowRunParserResult

    @field_validator("batch_name")
    @classmethod
    def _batch_name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class WorkflowRunAgentTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_raw_output: str | None = None
    model_raw_output_uri: str | None = None
    parser_result: WorkflowRunParserResult
    batch_traces: tuple[WorkflowRunAgentTraceBatch, ...] = ()


class WorkflowRunLogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_name: str
    entry_type: WorkflowRunLogEntryType
    started_at: datetime
    completed_at: datetime
    status: RunLogCompletedStatus
    input_counts: dict[str, int] = Field(default_factory=dict)
    output_counts: dict[str, int] = Field(default_factory=dict)
    artifact_uris: dict[str, str] = Field(default_factory=dict)
    validation_result: WorkflowRunValidationResult | None = None
    agent_trace: WorkflowRunAgentTrace | None = None
    error: WorkflowRunError | None = None

    @field_validator("entry_name")
    @classmethod
    def _entry_name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class GraphAuthoringRunLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    workflow_name: str
    model_provider: str | None = None
    model_name: str | None = None
    message_profile: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    status: RunLogStatus
    source_materials: tuple[RunLogSourceMaterial, ...]
    entries: tuple[WorkflowRunLogEntry, ...]
    artifact_paths: GraphAuthoringLogArtifactPaths | None = None
    error: WorkflowRunError | None = None

    @field_validator("run_id", "workflow_name", "model_provider", "model_name", "message_profile")
    @classmethod
    def _must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class GraphAuthoringRunLogSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    workflow_name: str
    status: RunLogStatus
    started_at: datetime
    completed_at: datetime | None = None
    output_counts: dict[str, int] = Field(default_factory=dict)


class GraphAuthoringWorkflowRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow_result: GraphAuthoringWorkflowResult
    run_log: GraphAuthoringRunLog


class GraphAuthoringWorkflowRunError(RuntimeError):
    def __init__(self, message: str, *, run_log: GraphAuthoringRunLog, cause: Exception) -> None:
        super().__init__(message)
        self.run_log = run_log
        self.cause = cause


@dataclass(frozen=True)
class _ActiveRunLogEntry:
    entry_name: str
    entry_type: WorkflowRunLogEntryType
    started_at: datetime
    input_counts: dict[str, int]


class GraphAuthoringRunLogBuilder:
    def __init__(
        self,
        *,
        run_id: str,
        workflow_name: str = GRAPH_AUTHORING_WORKFLOW_NAME,
        source_materials: Sequence[SourceMaterial],
        source_metadata: Sequence[RunLogSourceMaterial] | None = None,
        model_metadata: ModelClientMetadata | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._run_id = run_id
        self._workflow_name = workflow_name
        self._source_materials = (
            tuple(source_metadata)
            if source_metadata is not None
            else tuple(RunLogSourceMaterial.from_source_material(material) for material in source_materials)
        )
        self._clock = clock or _utc_now
        self._started_at = self._clock()
        self._entries: list[WorkflowRunLogEntry] = []
        self._model_metadata = model_metadata

    def start_entry(
        self,
        *,
        entry_name: str,
        entry_type: WorkflowRunLogEntryType,
        input_counts: dict[str, int] | None = None,
    ) -> _ActiveRunLogEntry:
        return _ActiveRunLogEntry(
            entry_name=entry_name,
            entry_type=entry_type,
            started_at=self._clock(),
            input_counts=dict(input_counts or {}),
        )

    def finish_entry(
        self,
        active_entry: _ActiveRunLogEntry,
        *,
        output_counts: dict[str, int] | None = None,
        artifact_uris: dict[str, str] | None = None,
        validation_result: WorkflowRunValidationResult | None = None,
        agent_trace: WorkflowRunAgentTrace | None = None,
    ) -> None:
        self._entries.append(
            WorkflowRunLogEntry(
                entry_name=active_entry.entry_name,
                entry_type=active_entry.entry_type,
                started_at=active_entry.started_at,
                completed_at=self._clock(),
                status="succeeded",
                input_counts=active_entry.input_counts,
                output_counts=dict(output_counts or {}),
                artifact_uris=dict(artifact_uris or {}),
                validation_result=validation_result,
                agent_trace=agent_trace,
            )
        )

    def fail_entry(
        self,
        active_entry: _ActiveRunLogEntry,
        error: WorkflowRunError,
        *,
        output_counts: dict[str, int] | None = None,
        artifact_uris: dict[str, str] | None = None,
        agent_trace: WorkflowRunAgentTrace | None = None,
    ) -> None:
        validation_result: WorkflowRunValidationResult | None = None
        if active_entry.entry_type == "validation_checkpoint":
            validation_result = "failed"

        self._entries.append(
            WorkflowRunLogEntry(
                entry_name=active_entry.entry_name,
                entry_type=active_entry.entry_type,
                started_at=active_entry.started_at,
                completed_at=self._clock(),
                status="failed",
                input_counts=active_entry.input_counts,
                output_counts=dict(output_counts or {}),
                artifact_uris=dict(artifact_uris or {}),
                validation_result=validation_result,
                agent_trace=agent_trace,
                error=error,
            )
        )

    def succeeded(self) -> GraphAuthoringRunLog:
        return GraphAuthoringRunLog(
            run_id=self._run_id,
            workflow_name=self._workflow_name,
            **_model_metadata_fields(self._model_metadata),
            started_at=self._started_at,
            completed_at=self._clock(),
            status="succeeded",
            source_materials=self._source_materials,
            entries=tuple(self._entries),
        )

    def failed(self, error: WorkflowRunError) -> GraphAuthoringRunLog:
        return GraphAuthoringRunLog(
            run_id=self._run_id,
            workflow_name=self._workflow_name,
            **_model_metadata_fields(self._model_metadata),
            started_at=self._started_at,
            completed_at=self._clock(),
            status="failed",
            source_materials=self._source_materials,
            entries=tuple(self._entries),
            error=error,
        )


def default_graph_authoring_run_id() -> str:
    return f"run_{_utc_now().strftime('%Y%m%dT%H%M%S%fZ')}"


def _model_metadata_fields(model_metadata: ModelClientMetadata | None) -> dict[str, str | None]:
    if model_metadata is None:
        return {}
    return {
        "model_provider": model_metadata.provider,
        "model_name": model_metadata.model_name,
        "message_profile": model_metadata.message_profile,
    }


def workflow_run_error_from_exception(
    exc: Exception,
    *,
    checkpoint: str | None = None,
    step_name: str | None = None,
) -> WorkflowRunError:
    return WorkflowRunError.from_exception(exc, checkpoint=checkpoint, step_name=step_name)


def with_artifact_paths(
    run_log: GraphAuthoringRunLog,
    artifact_paths: GraphAuthoringLogArtifactPaths,
) -> GraphAuthoringRunLog:
    return run_log.model_copy(update={"artifact_paths": artifact_paths})


def summarize_run_log(run_log: GraphAuthoringRunLog) -> GraphAuthoringRunLogSummary:
    output_counts: dict[str, int] = {}
    for entry in run_log.entries:
        for key in ("skeletons", "candidate_nodes", "candidate_edges"):
            if key in entry.output_counts:
                output_counts[key] = entry.output_counts[key]

    return GraphAuthoringRunLogSummary(
        run_id=run_log.run_id,
        workflow_name=run_log.workflow_name,
        status=run_log.status,
        started_at=run_log.started_at,
        completed_at=run_log.completed_at,
        output_counts=output_counts,
    )


def redact_error_message(message: str) -> str:
    redacted = _OPENAI_KEY_PATTERN.sub("sk-[REDACTED]", message)
    redacted = _SENSITIVE_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    redacted = " ".join(redacted.split())
    if not redacted:
        return "No error message provided"
    if len(redacted) > MAX_ERROR_MESSAGE_CHARS:
        return f"{redacted[: MAX_ERROR_MESSAGE_CHARS - 3]}..."
    return redacted


def redact_logged_text(text: str) -> str:
    redacted = _OPENAI_KEY_PATTERN.sub("sk-[REDACTED]", text)
    return _SENSITIVE_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)


def _utc_now() -> datetime:
    return datetime.now(UTC)
