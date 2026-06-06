from enum import StrEnum
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.core.interaction import (
    CoarseObservationMetadata,
    DiagnosticQuestion,
    VisibleDialogueContext,
    VisibleSimulatorAnswer,
)


_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class SimulatorPreviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    benchmark_domain: str
    map_id: str
    question: DiagnosticQuestion
    visible_dialogue_context: VisibleDialogueContext | None = None

    @field_validator("benchmark_domain", "map_id")
    @classmethod
    def _must_be_safe_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        if not _SAFE_ID_PATTERN.fullmatch(value):
            raise ValueError(
                "must contain only letters, numbers, dots, underscores, or dashes"
            )
        return value


class SimulatorPreviewWarningCode(StrEnum):
    MISSING_PROFILE_CONTEXT = "missing_profile_context"
    PREVIEW_CONFIGURATION = "preview_configuration"
    DEBUG_TRACE_UNAVAILABLE = "debug_trace_unavailable"


class SimulatorPreviewWarning(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: SimulatorPreviewWarningCode
    message: str

    @field_validator("message")
    @classmethod
    def _message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class SimulatorPreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    answer: VisibleSimulatorAnswer
    observation: CoarseObservationMetadata
    warnings: tuple[SimulatorPreviewWarning, ...] = Field(default_factory=tuple)
    debug_trace_id: str | None = None
    debug_trace_available: bool | None = None

    @field_validator("debug_trace_id")
    @classmethod
    def _optional_value_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value
