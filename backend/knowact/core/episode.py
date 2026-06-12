from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1 = "squared_mastery_distance_v1"
INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN = (
    "single_diagnostic_question_per_turn"
)


class EvaluationEpisodeManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    hidden_map_id: str
    max_turns: int = Field(gt=0)
    interaction_rule: Literal["single_diagnostic_question_per_turn"]
    scoring_profile: Literal["squared_mastery_distance_v1"]
    scoring_overrides: dict[str, Any] | None = None

    @field_validator(
        "episode_id",
        "benchmark_domain",
        "graph_version",
        "hidden_map_id",
    )
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value
