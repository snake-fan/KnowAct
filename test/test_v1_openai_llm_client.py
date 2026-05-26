import os
import unittest
from types import SimpleNamespace
from pathlib import Path
import tempfile
from unittest.mock import patch

from backend.knowact.llm.config import load_dotenv_file, openai_config_from_env
from backend.knowact.llm.messages import ModelMessage
from backend.knowact.llm.openai_client import OpenAIChatModelClient


class V1OpenAILLMClientTest(unittest.TestCase):
    def test_openai_config_reads_env_without_requiring_dotenv(self):
        config = openai_config_from_env(
            {
                "OPENAI_API_KEY": "test-key",
                "KNOWACT_OPENAI_MODEL": "gpt-test",
                "OPENAI_BASE_URL": "https://example.test/v1",
                "KNOWACT_OPENAI_TEMPERATURE": "0.2",
                "KNOWACT_OPENAI_TIMEOUT_SECONDS": "30",
                "KNOWACT_OPENAI_MAX_COMPLETION_TOKENS": "1234",
            }
        )

        self.assertEqual("test-key", config.api_key)
        self.assertEqual("gpt-test", config.model)
        self.assertEqual("https://example.test/v1", config.base_url)
        self.assertEqual(0.2, config.temperature)
        self.assertEqual(30.0, config.timeout_seconds)
        self.assertEqual(1234, config.max_completion_tokens)

    def test_openai_config_requires_api_key(self):
        with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
            openai_config_from_env({})

    def test_load_dotenv_file_populates_process_environment_without_overriding_existing_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=from-dotenv",
                        "KNOWACT_OPENAI_MODEL=gpt-dotenv",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"OPENAI_API_KEY": "existing-key"}, clear=True):
                loaded = load_dotenv_file(dotenv_path=dotenv_path)
                config = openai_config_from_env()

        self.assertTrue(loaded)
        self.assertEqual("existing-key", config.api_key)
        self.assertEqual("gpt-dotenv", config.model)

    def test_openai_client_uses_sdk_chat_completions_with_json_mode(self):
        fake_completions = FakeCompletions()
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions),
        )
        config = openai_config_from_env({"OPENAI_API_KEY": "test-key", "KNOWACT_OPENAI_MODEL": "gpt-test"})
        client = OpenAIChatModelClient(config, client=fake_client)

        response = client.complete(
            messages=[ModelMessage(role="developer", content="Return candidate nodes as JSON.")],
        )

        self.assertEqual('{"nodes": []}', response)
        self.assertEqual("gpt-test", fake_completions.last_params["model"])
        self.assertEqual({"type": "json_object"}, fake_completions.last_params["response_format"])
        self.assertEqual(8000, fake_completions.last_params["max_completion_tokens"])
        self.assertEqual(
            [{"role": "developer", "content": "Return candidate nodes as JSON."}],
            fake_completions.last_params["messages"],
        )


class FakeCompletions:
    def __init__(self):
        self.last_params = {}

    def create(self, **params):
        self.last_params = params
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"nodes": []}',
                    )
                )
            ]
        )

if __name__ == "__main__":
    unittest.main()
