from collections.abc import Sequence

from pydantic import BaseModel

from backend.knowact.llm.client import ModelClientError, ModelClientMetadata
from backend.knowact.llm.config import DeepSeekModelConfig
from backend.knowact.llm.messages import DEEPSEEK_MESSAGE_PROFILE, ModelMessage, render_messages_for_profile


class DeepSeekChatModelClient:
    """DeepSeek SDK-compatible chat client that returns raw model text."""

    message_profile = DEEPSEEK_MESSAGE_PROFILE

    def __init__(self, config: DeepSeekModelConfig, client: object | None = None) -> None:
        self._config = config
        self.metadata = ModelClientMetadata(
            provider="deepseek",
            model_name=config.model,
            message_profile=self.message_profile.name,
        )
        if client is not None:
            self._client = client
            return

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ModelClientError("The openai package is required for DeepSeekChatModelClient") from exc

        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )

    def complete(
        self,
        *,
        messages: Sequence[ModelMessage],
    ) -> str:
        params: dict[str, object] = {
            "model": self._config.model,
            "messages": render_messages_for_profile(tuple(messages), self.message_profile),
            "response_format": {"type": "json_object"},
        }
        completion = self._client.chat.completions.create(**params)
        return _extract_content(completion)


def _extract_content(completion: BaseModel | object) -> str:
    try:
        content = completion.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise ModelClientError("DeepSeek response did not include a chat message") from exc

    if not isinstance(content, str) or not content.strip():
        raise ModelClientError("DeepSeek response content was empty")
    return content
