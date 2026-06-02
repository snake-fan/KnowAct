from collections.abc import Sequence

from pydantic import BaseModel

from backend.knowact.llm.client import ModelClientError, ModelClientMetadata
from backend.knowact.llm.config import OpenAIModelConfig
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage, render_messages_for_profile


class OpenAIChatModelClient:
    """OpenAI SDK-backed client that returns raw model text."""

    message_profile = OPENAI_MESSAGE_PROFILE

    def __init__(self, config: OpenAIModelConfig, client: object | None = None) -> None:
        self._config = config
        self.metadata = ModelClientMetadata(
            provider="openai",
            model_name=config.model,
            message_profile=self.message_profile.name,
        )
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
        temperature: float | None = None,
    ) -> str:
        params: dict[str, object] = {
            "model": self._config.model,
            "messages": render_messages_for_profile(messages, self.message_profile),
            "response_format": {"type": "json_object"},
        }
        effective_temperature = (
            temperature if temperature is not None else self._config.temperature
        )
        if effective_temperature is not None:
            params["temperature"] = effective_temperature
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
