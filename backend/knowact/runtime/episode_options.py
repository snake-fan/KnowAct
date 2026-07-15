from __future__ import annotations

from collections.abc import Mapping
import os

from pydantic import BaseModel, ConfigDict

from backend.knowact.core.episode import EpisodeExecutionConfiguration


DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
TESTED_AGENT_TEMPERATURE_OPTIONS = (0.0, 0.2, 0.5, 0.7, 1.0)
MAX_TOOL_RETRY_OPTIONS = (1, 2, 3, 5)


class EpisodeModelProviderOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    models: tuple[str, ...]
    default_model: str
    available: bool


class EpisodeModelCatalog(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_kinds: tuple[str, ...] = ("simple_llm_agent",)
    providers: tuple[EpisodeModelProviderOption, ...]
    tested_agent_temperature_options: tuple[float, ...] = (
        TESTED_AGENT_TEMPERATURE_OPTIONS
    )
    max_tool_retry_options: tuple[int, ...] = MAX_TOOL_RETRY_OPTIONS
    default_tested_agent_temperature: float = 0.0
    default_max_tool_retries: int = 3

    def provider(self, name: str) -> EpisodeModelProviderOption | None:
        return next((item for item in self.providers if item.provider == name), None)


class EpisodeExecutionConfigurationError(ValueError):
    """Raised when a new episode selects an unavailable execution option."""


def build_episode_model_catalog(
    environ: Mapping[str, str] | None = None,
    *,
    available_provider_overrides: Mapping[str, bool] | None = None,
) -> EpisodeModelCatalog:
    env = os.environ if environ is None else environ
    overrides = available_provider_overrides or {}
    openai_default = _optional_env(env, "KNOWACT_OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    deepseek_default = (
        _optional_env(env, "KNOWACT_DEEPSEEK_MODEL") or DEFAULT_DEEPSEEK_MODEL
    )
    return EpisodeModelCatalog(
        providers=(
            EpisodeModelProviderOption(
                provider="openai",
                models=_models(
                    _optional_env(env, "KNOWACT_OPENAI_MODELS"),
                    openai_default,
                ),
                default_model=openai_default,
                available=overrides.get("openai", _has_openai_key(env)),
            ),
            EpisodeModelProviderOption(
                provider="deepseek",
                models=_models(
                    _optional_env(env, "KNOWACT_DEEPSEEK_MODELS"),
                    deepseek_default,
                ),
                default_model=deepseek_default,
                available=overrides.get("deepseek", _has_deepseek_key(env)),
            ),
        )
    )


def validate_execution_configuration(
    configuration: EpisodeExecutionConfiguration,
    catalog: EpisodeModelCatalog,
) -> None:
    if configuration.agent_kind not in catalog.agent_kinds:
        raise EpisodeExecutionConfigurationError(
            f"Unsupported episode agent kind: {configuration.agent_kind}"
        )
    _validate_provider_model(
        role="tested agent",
        provider=configuration.tested_agent_client_provider,
        model=configuration.tested_agent_model,
        catalog=catalog,
    )
    _validate_provider_model(
        role="simulator",
        provider=configuration.simulator_client_provider,
        model=configuration.simulator_model,
        catalog=catalog,
    )
    if configuration.tested_agent_temperature not in (
        catalog.tested_agent_temperature_options
    ):
        raise EpisodeExecutionConfigurationError(
            "Tested-agent temperature must be selected from the episode options."
        )
    if configuration.max_tool_retries not in catalog.max_tool_retry_options:
        raise EpisodeExecutionConfigurationError(
            "Maximum tool retries must be selected from the episode options."
        )


def _validate_provider_model(
    *,
    role: str,
    provider: str,
    model: str,
    catalog: EpisodeModelCatalog,
) -> None:
    option = catalog.provider(provider)
    if option is None:
        raise EpisodeExecutionConfigurationError(
            f"Unsupported {role} provider: {provider}"
        )
    if not option.available:
        raise EpisodeExecutionConfigurationError(
            f"The selected {role} provider is not configured."
        )
    if model not in option.models:
        raise EpisodeExecutionConfigurationError(
            f"The selected {role} model is not in the provider catalog."
        )


def _models(raw_value: str | None, default_model: str) -> tuple[str, ...]:
    values = [] if raw_value is None else raw_value.split(",")
    normalized = [value.strip() for value in values if value.strip()]
    return tuple(dict.fromkeys((default_model, *normalized)))


def _has_openai_key(environ: Mapping[str, str]) -> bool:
    return bool(
        _optional_env(environ, "KNOWACT_OPENAI_API_KEY")
        or _optional_env(environ, "OPENAI_API_KEY")
    )


def _has_deepseek_key(environ: Mapping[str, str]) -> bool:
    return bool(
        _optional_env(environ, "KNOWACT_DEEPSEEK_API_KEY")
        or _optional_env(environ, "DEEPSEEK_API_KEY")
    )


def _optional_env(environ: Mapping[str, str], key: str) -> str | None:
    value = environ.get(key)
    if value is None or not value.strip():
        return None
    return value
