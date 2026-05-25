import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OpenAIModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: str = Field(repr=False)
    model: str = "gpt-4.1-mini"
    base_url: str | None = None
    temperature: float | None = Field(default=0.0, ge=0.0)
    timeout_seconds: float = Field(default=120.0, gt=0.0)
    max_completion_tokens: int | None = Field(default=8000, gt=0)

    @field_validator("api_key", "model")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


def openai_config_from_env(environ: Mapping[str, str] | None = None) -> OpenAIModelConfig:
    env = os.environ if environ is None else environ
    api_key = _optional_env(env, "KNOWACT_OPENAI_API_KEY") or _optional_env(env, "OPENAI_API_KEY")
    if api_key is None:
        raise ValueError("OPENAI_API_KEY or KNOWACT_OPENAI_API_KEY is required")

    return OpenAIModelConfig(
        api_key=api_key,
        model=_optional_env(env, "KNOWACT_OPENAI_MODEL") or "gpt-4.1-mini",
        base_url=_optional_env(env, "OPENAI_BASE_URL") or _optional_env(env, "KNOWACT_OPENAI_BASE_URL"),
        temperature=_optional_float_env(env, "KNOWACT_OPENAI_TEMPERATURE", default=0.0),
        timeout_seconds=_float_env(env, "KNOWACT_OPENAI_TIMEOUT_SECONDS", default=120.0),
        max_completion_tokens=_optional_int_env(env, "KNOWACT_OPENAI_MAX_COMPLETION_TOKENS", default=8000),
    )


def load_dotenv_file(dotenv_path: Path | None = None) -> bool:
    """Load local development secrets into the process environment."""

    from dotenv import load_dotenv

    return load_dotenv(dotenv_path=dotenv_path or _default_dotenv_path(), override=False)


def _default_dotenv_path() -> Path:
    return Path(__file__).resolve().parents[3] / ".env"


def _optional_env(environ: Mapping[str, str], key: str) -> str | None:
    value = environ.get(key)
    if value is None or not value.strip():
        return None
    return value


def _float_env(environ: Mapping[str, str], key: str, *, default: float) -> float:
    value = _optional_env(environ, key)
    if value is None:
        return default
    return float(value)


def _optional_float_env(environ: Mapping[str, str], key: str, *, default: float | None) -> float | None:
    value = _optional_env(environ, key)
    if value is None:
        return default
    return float(value)


def _optional_int_env(environ: Mapping[str, str], key: str, *, default: int | None) -> int | None:
    value = _optional_env(environ, key)
    if value is None:
        return default
    return int(value)
