from collections.abc import Sequence

from pydantic import BaseModel

from backend.knowact.llm.client import ModelClientError
from backend.knowact.llm.config import OpenAIModelConfig
from backend.knowact.llm.messages import ModelMessage


class OpenAIChatModelClient:
    """OpenAI SDK-backed client that returns raw model text."""

    def __init__(self, config: OpenAIModelConfig, client: object | None = None) -> None:
        self._config = config
        if client is not None:
            self._client = client
            return

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ModelClientError("The openai package is required for OpenAIChatModelClient") from exc

        kwargs: dict[str, object] = {
            "api_key": config.api_key,
            "timeout": config.timeout_seconds,
        }
        if config.base_url is not None:
            kwargs["base_url"] = config.base_url

        self._client = OpenAI(**kwargs)

    def complete(
        self,
        *,
        messages: Sequence[ModelMessage],
    ) -> str:
        params: dict[str, object] = {
            "model": self._config.model,
            "messages": [message.model_dump(mode="json") for message in messages],
            "response_format": {"type": "json_object"},
        }
        if self._config.temperature is not None:
            params["temperature"] = self._config.temperature
        if self._config.max_completion_tokens is not None:
            params["max_completion_tokens"] = self._config.max_completion_tokens

        completion = self._client.chat.completions.create(**params)
        return _extract_content(completion)


def _extract_content(completion: BaseModel | object) -> str:
    try:
        content = completion.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise ModelClientError("OpenAI response did not include a chat message") from exc

    if not isinstance(content, str) or not content.strip():
        raise ModelClientError("OpenAI response content was empty")
    return content
