from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.core.episode import SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1
from backend.knowact.core.map import MasteryLevel


class NodeComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    ground_truth_mastery: MasteryLevel
    predicted_mastery: MasteryLevel | None
    mastery_distance: float = Field(ge=0.0)
    missing_prediction: bool
    unsupported_inference: bool

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

    @field_validator("episode_id")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value
