from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1 = "squared_mastery_distance_v1"


class ArtifactReviewStatus(StrEnum):
    CANDIDATE = "candidate"
    REVIEWED = "reviewed"


class ArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    uri: str
    review_status: ArtifactReviewStatus

    @field_validator("id", "uri")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class EvaluationEpisodeManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_id: str
    benchmark_domain: str
    graph: ArtifactRef
    hidden_map: ArtifactRef
    max_turns: int = Field(gt=0)
    interaction_rule: Literal["single_diagnostic_question_per_turn"]
    scoring_profile: Literal["squared_mastery_distance_v1"]
    profile_context: ArtifactRef | None = None
    scoring_overrides: dict[str, Any] | None = None

    @field_validator("episode_id", "benchmark_domain")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value
