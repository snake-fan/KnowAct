from backend.knowact.agents.agents.simple_llm import SimpleLLMTestedAgent
from backend.knowact.agents.providers import (
    DEFAULT_TESTED_AGENT_CLIENT_PROVIDER,
    TestedAgentClientProvider,
)
from backend.knowact.llm.client import ModelClient, ModelClientError
from backend.knowact.llm.config import (
    DeepSeekModelConfig,
    OpenAIModelConfig,
    deepseek_config_from_env,
    openai_config_from_env,
)
from backend.knowact.llm.deepseek_client import DeepSeekChatModelClient
from backend.knowact.llm.openai_client import OpenAIChatModelClient
from backend.knowact.logging_config import get_knowact_logger


_LOGGER = get_knowact_logger("agents.llm_agent")


class TestedAgentConfigurationError(RuntimeError):
    """Raised when a provider-backed tested agent cannot be configured."""


def build_simple_llm_tested_agent(
    *,
    model_client: ModelClient,
    temperature: float | None = None,
) -> SimpleLLMTestedAgent:
    metadata = getattr(model_client, "metadata", None)
    _LOGGER.info(
        "Simple LLM tested agent initialized model_provider=%s model_name=%s",
        metadata.provider if metadata is not None else None,
        metadata.model_name if metadata is not None else None,
    )
    return SimpleLLMTestedAgent(
        model_client=model_client,
        temperature=temperature,
    )


def build_simple_llm_tested_agent_for_provider(
    client_provider: TestedAgentClientProvider | None = DEFAULT_TESTED_AGENT_CLIENT_PROVIDER,
    *,
    temperature: float | None = None,
    openai_config: OpenAIModelConfig | None = None,
    deepseek_config: DeepSeekModelConfig | None = None,
) -> SimpleLLMTestedAgent:
    provider = client_provider or DEFAULT_TESTED_AGENT_CLIENT_PROVIDER
    _LOGGER.info(
        "Simple LLM tested agent provider configuration started client_provider=%s",
        provider,
    )
    try:
        if provider == "openai":
            agent = build_simple_llm_tested_agent(
                model_client=OpenAIChatModelClient(
                    openai_config or openai_config_from_env()
                ),
                temperature=temperature,
            )
            _LOGGER.info(
                "Simple LLM tested agent provider configuration succeeded client_provider=%s",
                provider,
            )
            return agent
        if provider == "deepseek":
            agent = build_simple_llm_tested_agent(
                model_client=DeepSeekChatModelClient(
                    deepseek_config or deepseek_config_from_env()
                ),
                temperature=temperature,
            )
            _LOGGER.info(
                "Simple LLM tested agent provider configuration succeeded client_provider=%s",
                provider,
            )
            return agent
    except (ValueError, ModelClientError) as exc:
        _LOGGER.error(
            "Simple LLM tested agent provider configuration failed client_provider=%s error_type=%s",
            provider,
            type(exc).__name__,
        )
        raise TestedAgentConfigurationError(
            "Simple LLM tested agent service is not configured."
        ) from exc

    _LOGGER.error(
        "Simple LLM tested agent provider configuration failed client_provider=%s error_type=%s",
        provider,
        "UnsupportedProvider",
    )
    raise TestedAgentConfigurationError(
        f"Unsupported tested-agent client provider: {provider}"
    )
