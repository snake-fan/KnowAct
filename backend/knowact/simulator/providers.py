from typing import Literal


SimulatorClientProvider = Literal["openai", "deepseek"]
DEFAULT_SIMULATOR_CLIENT_PROVIDER: SimulatorClientProvider = "openai"
