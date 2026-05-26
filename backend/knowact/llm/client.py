from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict, field_validator

from backend.knowact.llm.messages import ModelMessage, ModelMessageProfile


class ModelClientError(RuntimeError):
    """Raised when an LLM client cannot return usable model output."""


class ModelClientMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    model_name: str
    message_profile: str | None = None

    @field_validator("provider", "model_name", "message_profile")
    @classmethod
    def _values_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class ModelClient(Protocol):
    message_profile: ModelMessageProfile
    metadata: ModelClientMetadata

    def complete(
        self,
        *,
        messages: Sequence[ModelMessage],
    ) -> str:
        """Return raw model text for a rendered message list."""
