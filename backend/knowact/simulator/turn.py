from enum import StrEnum
import re

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from backend.knowact.core.interaction import (
    CoarseObservationMetadata,
    DiagnosticQuestion,
    VisibleDialogueContext,
    VisibleSimulatorAnswer,
)
from backend.knowact.simulator.providers import (
    DEFAULT_SIMULATOR_CLIENT_PROVIDER,
    SimulatorClientProvider,
)


_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class SimulatorTurnOptions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    include_debug_trace: bool = False


class SimulatorTurnRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    benchmark_domain: str
    map_id: str
    client_provider: SimulatorClientProvider = DEFAULT_SIMULATOR_CLIENT_PROVIDER
    question: DiagnosticQuestion
    visible_dialogue_context: VisibleDialogueContext | None = None
    turn_options: SimulatorTurnOptions = Field(
        default_factory=SimulatorTurnOptions,
        validation_alias=AliasChoices("turn_options", "preview_options"),
    )

    @property
    def preview_options(self) -> SimulatorTurnOptions:
        return self.turn_options

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

    @model_validator(mode="after")
    def _question_id_must_be_safe_id(self) -> "SimulatorTurnRequest":
        question_id = self.question.question_id
        if question_id is not None and not _SAFE_ID_PATTERN.fullmatch(question_id):
            raise ValueError(
                "question.question_id must contain only letters, numbers, dots, "
                "underscores, or dashes"
            )
        return self


class SimulatorTurnWarningCode(StrEnum):
    MISSING_PROFILE_CONTEXT = "missing_profile_context"
    SIMULATOR_CONFIGURATION = "simulator_configuration"


class SimulatorTurnWarning(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: SimulatorTurnWarningCode
    message: str

    @field_validator("message")
    @classmethod
    def _message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class SimulatorTurnResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    answer: VisibleSimulatorAnswer
    observation: CoarseObservationMetadata
    warnings: tuple[SimulatorTurnWarning, ...] = Field(default_factory=tuple)
    debug_trace_id: str | None = None
    debug_trace_available: bool | None = None

    @field_validator("debug_trace_id")
    @classmethod
    def _optional_value_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value
