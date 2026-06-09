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
from backend.knowact.simulator.checks import ModelClientAnswerValidator
from backend.knowact.simulator.generators import ModelClientAnswerGenerator
from backend.knowact.simulator.service import SimulatorService


SimulatorClientProvider = Literal["openai", "deepseek"]
DEFAULT_SIMULATOR_CLIENT_PROVIDER: SimulatorClientProvider = "openai"


class SimulatorServiceConfigurationError(RuntimeError):
    """Raised when the provider-backed simulator service cannot be configured."""


def build_simulator_service(
    *,
    workspace_root: Path,
    model_client: ModelClient,
) -> SimulatorService:
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
    try:
        if provider == "openai":
            return build_simulator_service(
                workspace_root=workspace_root,
                model_client=OpenAIChatModelClient(openai_config or openai_config_from_env()),
            )
        if provider == "deepseek":
            return build_simulator_service(
                workspace_root=workspace_root,
                model_client=DeepSeekChatModelClient(
                    deepseek_config or deepseek_config_from_env()
                ),
            )
    except (ValueError, ModelClientError) as exc:
        raise SimulatorServiceConfigurationError(
            "Simulator LLM service is not configured."
        ) from exc

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
    raise SimulatorServiceConfigurationError(
        f"Unsupported simulator client provider: {provider}"
    )
