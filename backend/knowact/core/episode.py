from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1 = "squared_mastery_distance_v1"
INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN = (
    "single_diagnostic_question_per_turn"
)

EpisodeAgentKind = Literal["simple_llm_agent"]
EpisodeClientProvider = Literal["openai", "deepseek"]


class EpisodeExecutionConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_kind: EpisodeAgentKind
    tested_agent_client_provider: EpisodeClientProvider
    tested_agent_model: str
    simulator_client_provider: EpisodeClientProvider
    simulator_model: str
    tested_agent_temperature: float = Field(ge=0.0)
    max_tool_retries: int = Field(ge=1)

    @field_validator("tested_agent_model", "simulator_model")
    @classmethod
    def _model_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


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
    agent_kind: EpisodeAgentKind | None = None
    tested_agent_client_provider: EpisodeClientProvider | None = None
    tested_agent_model: str | None = None
    simulator_client_provider: EpisodeClientProvider | None = None
    simulator_model: str | None = None
    tested_agent_temperature: float | None = Field(default=None, ge=0.0)
    max_tool_retries: int | None = Field(default=None, ge=1)

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

    @field_validator("tested_agent_model", "simulator_model")
    @classmethod
    def _optional_model_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def _execution_configuration_is_complete_or_legacy(
        self,
    ) -> "EvaluationEpisodeManifest":
        values = (
            self.agent_kind,
            self.tested_agent_client_provider,
            self.tested_agent_model,
            self.simulator_client_provider,
            self.simulator_model,
            self.tested_agent_temperature,
            self.max_tool_retries,
        )
        configured_count = sum(value is not None for value in values)
        if configured_count not in (0, len(values)):
            raise ValueError(
                "episode execution configuration must be fully specified or fully absent"
            )
        return self

    @property
    def is_legacy(self) -> bool:
        return self.agent_kind is None

    def execution_configuration(self) -> EpisodeExecutionConfiguration | None:
        if self.is_legacy:
            return None
        return EpisodeExecutionConfiguration(
            agent_kind=self.agent_kind,
            tested_agent_client_provider=self.tested_agent_client_provider,
            tested_agent_model=self.tested_agent_model,
            simulator_client_provider=self.simulator_client_provider,
            simulator_model=self.simulator_model,
            tested_agent_temperature=self.tested_agent_temperature,
            max_tool_retries=self.max_tool_retries,
        )
