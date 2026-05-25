import base64
from collections.abc import Sequence
from pathlib import Path

from backend.knowact.llm.client import ModelClientError
from backend.knowact.llm.config import OpenAIModelConfig
from backend.knowact.llm.messages import ModelMessage


class OpenAIResponsesPDFClient:
    """OpenAI Responses API client for prompts that include one local PDF input."""

    def __init__(self, config: OpenAIModelConfig, client: object | None = None) -> None:
        self._config = config
        if client is not None:
            self._client = client
            return

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ModelClientError("The openai package is required for OpenAIResponsesPDFClient") from exc

        kwargs: dict[str, object] = {
            "api_key": config.api_key,
            "timeout": config.timeout_seconds,
        }
        if config.base_url is not None:
            kwargs["base_url"] = config.base_url

        self._client = OpenAI(**kwargs)

    def complete_with_pdf(
        self,
        *,
        messages: Sequence[ModelMessage],
        pdf_path: Path,
        filename: str | None = None,
        json_mode: bool = False,
    ) -> str:
        if not messages:
            raise ModelClientError("at least one message is required")

        params: dict[str, object] = {
            "model": self._config.model,
            "input": _build_response_input(
                messages=messages,
                pdf_file_input=build_base64_pdf_file_input(
                    pdf_path=pdf_path,
                    filename=filename,
                ),
            ),
        }
        if json_mode:
            params["text"] = {"format": {"type": "json_object"}}
        if self._config.temperature is not None:
            params["temperature"] = self._config.temperature
        if self._config.max_completion_tokens is not None:
            params["max_output_tokens"] = self._config.max_completion_tokens

        response = self._client.responses.create(**params)
        return _extract_response_output_text(response)


def build_base64_pdf_file_input(
    *,
    pdf_path: Path,
    filename: str | None = None,
) -> dict[str, object]:
    encoded_pdf = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
    return {
        "type": "input_file",
        "filename": filename or pdf_path.name,
        "file_data": f"data:application/pdf;base64,{encoded_pdf}",
    }


def _build_response_input(
    *,
    messages: Sequence[ModelMessage],
    pdf_file_input: dict[str, object],
) -> list[dict[str, object]]:
    response_input: list[dict[str, object]] = []
    attached_pdf = False

    for message in messages:
        if message.role not in {"developer", "system", "user"}:
            raise ModelClientError("Responses PDF inputs only support developer, system, and user messages")
        content: list[dict[str, object]] = [{"type": "input_text", "text": message.content}]
        if message.role == "user" and not attached_pdf:
            content = [pdf_file_input, *content]
            attached_pdf = True
        response_input.append({"role": message.role, "content": content})

    if not attached_pdf:
        response_input.append({"role": "user", "content": [pdf_file_input]})

    return response_input


def _extract_response_output_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    text_parts: list[str] = []
    for output_item in getattr(response, "output", []) or []:
        for content_item in getattr(output_item, "content", []) or []:
            text = getattr(content_item, "text", None)
            if isinstance(text, str) and text:
                text_parts.append(text)

    content = "".join(text_parts)
    if not content.strip():
        raise ModelClientError("OpenAI response output text was empty")
    return content
