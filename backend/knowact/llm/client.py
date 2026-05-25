from collections.abc import Sequence
from pathlib import Path
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


class PDFModelClient(Protocol):
    def complete_with_pdf(
        self,
        *,
        messages: Sequence[ModelMessage],
        pdf_path: Path,
        filename: str | None = None,
        json_mode: bool = False,
    ) -> str:
        """Return raw model text for a rendered message list plus one local PDF."""
