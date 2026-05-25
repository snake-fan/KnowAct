from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceType(StrEnum):
    GROUND_TRUTH = "ground_truth"
    INTERACTION_OBSERVATION = "interaction_observation"
    SYNTHETIC = "synthetic"


class EvidenceKind(StrEnum):
    PRIOR_ANSWER = "prior_answer"
    WORKED_EXAMPLE = "worked_example"
    SELF_REPORT = "self_report"
    MISCONCEPTION_TRACE = "misconception_trace"
    BACKGROUND_FACT = "background_fact"


class EvidenceVisibility(StrEnum):
    HIDDEN = "hidden"
    VISIBLE = "visible"


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    node_id: str
    type: EvidenceType
    kind: EvidenceKind
    visibility: EvidenceVisibility
    summary: str
    source_turn_id: str | None = None

    @field_validator("id", "node_id", "summary")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value
