import os
from pathlib import Path
from typing import Literal

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
from backend.knowact.simulator.checks import ModelClientAnswerValidator
from backend.knowact.simulator.generators import ModelClientAnswerGenerator
from backend.knowact.simulator.service import SimulatorService


SimulatorClientProvider = Literal["openai", "deepseek"]
DEFAULT_SIMULATOR_CLIENT_PROVIDER: SimulatorClientProvider = "openai"
_LOGGER = get_knowact_logger("simulator.llm_service")


class SimulatorServiceConfigurationError(RuntimeError):
    """Raised when the provider-backed simulator service cannot be configured."""


def build_simulator_service(
    *,
    workspace_root: Path,
    model_client: ModelClient,
) -> SimulatorService:
    metadata = getattr(model_client, "metadata", None)
    _LOGGER.info(
        "Simulator service initialized workspace_root=%s model_provider=%s model_name=%s",
        workspace_root,
        metadata.provider if metadata is not None else None,
        metadata.model_name if metadata is not None else None,
    )
    return SimulatorService(
        workspace_root=workspace_root,
        generator=ModelClientAnswerGenerator(model_client=model_client),
        validator=ModelClientAnswerValidator(model_client=model_client),
    )


def build_simulator_service_for_provider(
    *,
    workspace_root: Path,
    client_provider: SimulatorClientProvider | None = None,
    openai_config: OpenAIModelConfig | None = None,
    deepseek_config: DeepSeekModelConfig | None = None,
) -> SimulatorService:
    provider = client_provider or _simulator_client_provider_from_env()
    _LOGGER.info("Simulator provider configuration started client_provider=%s", provider)
    try:
        if provider == "openai":
            service = build_simulator_service(
                workspace_root=workspace_root,
                model_client=OpenAIChatModelClient(openai_config or openai_config_from_env()),
            )
            _LOGGER.info("Simulator provider configuration succeeded client_provider=%s", provider)
            return service
        if provider == "deepseek":
            service = build_simulator_service(
                workspace_root=workspace_root,
                model_client=DeepSeekChatModelClient(
                    deepseek_config or deepseek_config_from_env()
                ),
            )
            _LOGGER.info("Simulator provider configuration succeeded client_provider=%s", provider)
            return service
    except (ValueError, ModelClientError) as exc:
        _LOGGER.error(
            "Simulator provider configuration failed client_provider=%s error_type=%s",
            provider,
            type(exc).__name__,
        )
        raise SimulatorServiceConfigurationError(
            "Simulator LLM service is not configured."
        ) from exc

    _LOGGER.error(
        "Simulator provider configuration failed client_provider=%s error_type=%s",
        provider,
        "UnsupportedProvider",
    )
    raise SimulatorServiceConfigurationError(
        f"Unsupported simulator client provider: {provider}"
    )


def _simulator_client_provider_from_env() -> SimulatorClientProvider:
    provider = os.environ.get(
        "KNOWACT_SIMULATOR_CLIENT_PROVIDER",
        DEFAULT_SIMULATOR_CLIENT_PROVIDER,
    )
    if provider in ("openai", "deepseek"):
        return provider
    _LOGGER.error(
        "Simulator provider configuration failed client_provider=%s error_type=%s",
        provider,
        "UnsupportedProvider",
    )
    raise SimulatorServiceConfigurationError(
        f"Unsupported simulator client provider: {provider}"
    )
