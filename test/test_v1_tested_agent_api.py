import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.agents.agents.simple_llm import SimpleLLMTestedAgent
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage
from backend.knowact.api.app import create_app
from test.test_v1_runtime_episode_repository import _write_reviewed_graph


class V1TestedAgentApiTest(unittest.TestCase):
    def test_simple_llm_turn_test_initializes_working_map_and_returns_question(self):
        fake_model_client = _FakeModelClient(
            responses=(
                """
                {
                  "action": "ask_diagnostic_question",
                  "question": {
                    "text": "How would you decide whether a held-out test set is needed?",
                    "question_id": "q_train_test_split"
                  },
                  "diagnostic_plan": {
                    "primary_target_node_id": "train_test_split",
                    "secondary_target_node_ids": ["cross_validation"],
                    "target_mastery_boundary": "broad_initial_probe",
                    "selection_reason": "A held-out scenario probes related evaluation concepts."
                  }
                }
                """,
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            client = TestClient(
                create_app(
                    workspace_root=workspace_root,
                    simple_llm_tested_agent_factory=_factory_for(fake_model_client),
                )
            )

            response = client.post(
                "/api/tested-agents/simple-llm/turn-test",
                json={
                    "episode_id": "episode_a",
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "client_provider": "openai",
                    "temperature": 0.2,
                    "decision_context": {
                        "phase": "initial_question",
                        "remaining_diagnostic_turns": 3,
                    },
                },
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("simple_llm", payload["agent_kind"])
        self.assertEqual([], payload["updates"])
        self.assertEqual("ask_diagnostic_question", payload["decision"]["kind"])
        self.assertEqual(
            "How would you decide whether a held-out test set is needed?",
            payload["decision"]["question"]["text"],
        )
        self.assertEqual("episode_a", payload["working_map"]["episode_id"])
        self.assertEqual(2, len(payload["working_map"]["states"]))
        self.assertEqual((0.2,), tuple(fake_model_client.temperatures))
        self.assertEqual(1, len(fake_model_client.messages))
        self.assertIn(
            "Choose the next tested-agent action.",
            fake_model_client.messages[0][1].content,
        )

    def test_simple_llm_turn_test_applies_updates_before_next_question(self):
        fake_model_client = _FakeModelClient(
            responses=(
                """
                {
                  "updates": [
                    {
                      "node_id": "train_test_split",
                      "assessed_mastery_level": "L3",
                      "diagnostic_confidence": "high",
                      "assessment_note": "The answer mentioned held-out data.",
                      "supporting_turn_ids": ["turn_01"]
                    }
                  ]
                }
                """,
                """
                {
                  "action": "ask_diagnostic_question",
                  "question": {
                    "text": "How would leakage affect the test estimate?"
                  },
                  "diagnostic_plan": {
                    "primary_target_node_id": "train_test_split",
                    "secondary_target_node_ids": ["cross_validation"],
                    "target_mastery_boundary": "L2_vs_L3",
                    "selection_reason": "Leakage reasoning distinguishes application from recall."
                  }
                }
                """,
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            client = TestClient(
                create_app(
                    workspace_root=workspace_root,
                    simple_llm_tested_agent_factory=_factory_for(fake_model_client),
                )
            )

            response = client.post(
                "/api/tested-agents/simple-llm/turn-test",
                json={
                    "episode_id": "episode_a",
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "decision_context": {
                        "phase": "after_answer",
                        "remaining_diagnostic_turns": 2,
                    },
                    "visible_dialogue_context": {
                        "turns": [
                            {
                                "turn_id": "turn_01",
                                "question": {
                                    "text": "Why do we keep a test set separate?"
                                },
                                "answer": {
                                    "text": "To evaluate on data the model did not train on."
                                },
                                "observation": {"kind": "answer"},
                            }
                        ]
                    },
                },
            )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, len(payload["updates"]))
        states_by_node_id = {
            state["node_id"]: state for state in payload["working_map"]["states"]
        }
        self.assertEqual(
            "L3",
            states_by_node_id["train_test_split"]["assessed_mastery_level"],
        )
        self.assertEqual(
            ["turn_01"],
            states_by_node_id["train_test_split"]["supporting_turn_ids"],
        )
        self.assertEqual("ask_diagnostic_question", payload["decision"]["kind"])
        self.assertEqual(2, len(fake_model_client.messages))
        second_payload = fake_model_client.messages[1][1].content
        self.assertIn('"assessed_mastery_level": "L3"', second_payload)

    def test_simple_llm_turn_test_rejects_missing_reviewed_graph(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(create_app(workspace_root=Path(temp_dir)))

            response = client.post(
                "/api/tested-agents/simple-llm/turn-test",
                json={
                    "episode_id": "episode_a",
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "missing",
                },
            )

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            "reviewed_graph_not_found",
            response.json()["detail"]["error_code"],
        )

    def test_simple_llm_turn_test_rejects_mismatched_working_map_binding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.post(
                "/api/tested-agents/simple-llm/turn-test",
                json={
                    "episode_id": "episode_a",
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "working_map": {
                        "episode_id": "other_episode",
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "graph_version": "v1",
                        "states": [
                            {"node_id": "train_test_split"},
                            {"node_id": "cross_validation"},
                        ],
                    },
                },
            )

        self.assertEqual(422, response.status_code)
        self.assertEqual(
            "invalid_tested_agent_request",
            response.json()["detail"]["error_code"],
        )

    def test_simple_llm_turn_test_response_exposes_no_hidden_runtime_fields(self):
        fake_model_client = _FakeModelClient(
            responses=(
                """
                {
                  "action": "ask_diagnostic_question",
                  "question": {
                    "text": "How do you interpret a validation split?"
                  },
                  "diagnostic_plan": {
                    "primary_target_node_id": "train_test_split",
                    "secondary_target_node_ids": ["cross_validation"],
                    "target_mastery_boundary": "broad_initial_probe",
                    "selection_reason": "One validation scenario probes related concepts."
                  }
                }
                """,
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            client = TestClient(
                create_app(
                    workspace_root=workspace_root,
                    simple_llm_tested_agent_factory=_factory_for(fake_model_client),
                )
            )

            response = client.post(
                "/api/tested-agents/simple-llm/turn-test",
                json={
                    "episode_id": "episode_a",
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                },
            )

        self.assertEqual(200, response.status_code)
        response_text = json.dumps(response.json(), sort_keys=True)
        for hidden_fragment in (
            "hidden_map_id",
            "map_id",
            "synthetic_user_001",
            "profile_context",
            "simulator_only",
            "answer_blueprint",
            "debug_trace",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, response_text)


class _FakeModelClient:
    message_profile = OPENAI_MESSAGE_PROFILE
    metadata = ModelClientMetadata(
        provider="fake",
        model_name="fake-simple-llm-agent",
        message_profile=OPENAI_MESSAGE_PROFILE.name,
    )

    def __init__(self, *, responses: tuple[str, ...]) -> None:
        self._responses = list(responses)
        self.messages: list[tuple[ModelMessage, ...]] = []
        self.temperatures: list[float | None] = []

    def complete(
        self,
        *,
        messages,
        temperature: float | None = None,
    ) -> str:
        self.messages.append(tuple(messages))
        self.temperatures.append(temperature)
        if not self._responses:
            raise AssertionError("No fake model response configured")
        return self._responses.pop(0)


def _factory_for(fake_model_client: _FakeModelClient):
    def _factory(client_provider, temperature):
        return SimpleLLMTestedAgent(
            model_client=fake_model_client,
            temperature=temperature,
        )

    return _factory


if __name__ == "__main__":
    unittest.main()
