from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiagnosticQuestion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    question_id: str | None = None

    @field_validator("text")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("question_id")
    @classmethod
    def _optional_value_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class VisibleObservationKind(StrEnum):
    ANSWER = "answer"
    CLARIFICATION = "clarification"
    NON_ANSWER = "non_answer"


class VisibleSimulatorAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str

    @field_validator("text")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class CoarseObservationMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: VisibleObservationKind


class VisibleDialogueTurn(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question: DiagnosticQuestion
    answer: VisibleSimulatorAnswer
    observation: CoarseObservationMetadata
    turn_id: str | None = None

    @field_validator("turn_id")
    @classmethod
    def _optional_value_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class VisibleDialogueContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    turns: tuple[VisibleDialogueTurn, ...] = Field(default_factory=tuple)
