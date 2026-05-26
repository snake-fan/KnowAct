from collections.abc import Sequence
from typing import Protocol

from backend.knowact.llm.messages import ModelMessage


class ModelClientError(RuntimeError):
    """Raised when an LLM client cannot return usable model output."""


class ModelClient(Protocol):
    def complete(
        self,
        *,
        messages: Sequence[ModelMessage],
    ) -> str:
        """Return raw model text for a rendered message list."""
