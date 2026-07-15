from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.core.episode import SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1
from backend.knowact.core.evidence import EvidenceRecord
from backend.knowact.core.map import MasteryLevel


class SubmittedMasteryLevel(StrEnum):
    UNKNOWN = "unknown"
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"

    def to_mastery_level(self) -> MasteryLevel:
        if self == SubmittedMasteryLevel.UNKNOWN:
            raise ValueError("unknown cannot be converted to a mastery level")
        return MasteryLevel(self.value)


class FinalReconstructionPrediction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    predicted_mastery: SubmittedMasteryLevel = SubmittedMasteryLevel.UNKNOWN
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("node_id")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_refs_must_be_nonblank_unique(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not evidence_ref.strip() for evidence_ref in value):
            raise ValueError("must not contain blank items")
        if len(value) != len(set(value)):
            raise ValueError("must not contain duplicate items")
        return value


class FinalReconstructionSubmission(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    reconstructed_user_id: str
    predictions: tuple[FinalReconstructionPrediction, ...]
    evidence: tuple[EvidenceRecord, ...] = Field(default_factory=tuple)

    @field_validator(
        "episode_id",
        "benchmark_domain",
        "graph_version",
        "reconstructed_user_id",
    )
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @property
    def prediction_by_node_id(self) -> dict[str, FinalReconstructionPrediction]:
        return {prediction.node_id: prediction for prediction in self.predictions}


class NodeComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    ground_truth_mastery: MasteryLevel
    predicted_mastery: MasteryLevel | None = None
    mastery_distance: float = Field(ge=0.0)
    signed_mastery_error: int | None = None
    missing_prediction: bool
    unsupported_inference: bool
    exact_match: bool

    @field_validator("node_id")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class EpisodeScoreReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_id: str
    scoring_profile: Literal["squared_mastery_distance_v1"] = SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1
    per_node: tuple[NodeComparison, ...]
    episode_mastery_distance: float = Field(ge=0.0)
    missing_prediction_rate: float = Field(ge=0.0, le=1.0)
    unsupported_inference_rate: float = Field(ge=0.0, le=1.0)
    exact_match_rate: float = Field(ge=0.0, le=1.0)

    @field_validator("episode_id")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value
