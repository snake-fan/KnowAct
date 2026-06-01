from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class EvidenceType(StrEnum):
    GROUND_TRUTH_PROFILE = "ground_truth_profile"
    INTERACTION_OBSERVATION = "interaction_observation"


class EvidenceKind(StrEnum):
    PRIOR_ANSWER = "prior_answer"
    WORKED_EXAMPLE = "worked_example"
    SELF_REPORT = "self_report"
    MISCONCEPTION_TRACE = "misconception_trace"
    BACKGROUND_FACT = "background_fact"


class EvidenceVisibility(StrEnum):
    SIMULATOR_ONLY = "simulator_only"
    TESTED_AGENT = "tested_agent"


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    node_id: str
    evidence_type: EvidenceType
    evidence_kind: EvidenceKind
    visibility: EvidenceVisibility
    signal: str
    turn_id: str | None = None

    @field_validator("id", "node_id", "signal")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("turn_id")
    @classmethod
    def _optional_value_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value
