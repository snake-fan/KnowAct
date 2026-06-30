import unittest

from pydantic import ValidationError

from backend.knowact.simulator.turn import (
    SimulatorTurnRequest,
    SimulatorTurnResponse,
    SimulatorTurnTestResponse,
)


class V1SimulatorTurnContractsTest(unittest.TestCase):
    def test_turn_request_rejects_hidden_state_payload_fields(self):
        base_payload = {
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "map_id": "dev_map_001",
            "question": {"text": "How would you decide whether linear regression is appropriate?"},
        }

        forbidden_fields = {
            "graph_version": "v1",
            "user_id": "synthetic_user_001",
            "mastery_level": "L3",
            "evidence_refs": ["ev_hidden"],
            "evidence_ids": ["ev_hidden"],
            "states": [{"node_id": "linear_regression"}],
            "evidence": [{"id": "ev_hidden"}],
            "grounded_node_ids": ["linear_regression"],
            "profile_context": {"summary": "hidden persona text"},
            "debug_trace": {"grounding": "hidden internals"},
            "debug_trace_payload": {"validator": "hidden internals"},
            "raw_debug_trace": "hidden internals",
        }

        for field, value in forbidden_fields.items():
            with self.subTest(field=field):
                payload = dict(base_payload)
                payload[field] = value

                with self.assertRaises(ValidationError):
                    SimulatorTurnRequest.model_validate(payload)

    def test_turn_request_accepts_only_structured_visible_dialogue_context(self):
        payload = {
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "map_id": "dev_map_001",
            "question": {"text": "When would a test set reveal a linear model problem?"},
            "visible_dialogue_context": {
                "turns": [
                    {
                        "turn_id": "turn_01",
                        "question": {"text": "How do you interpret a regression slope?"},
                        "answer": {"text": "I usually read it as the expected change in the response."},
                        "observation": {"kind": "answer"},
                    }
                ]
            },
        }

        request = SimulatorTurnRequest.model_validate(payload)

        self.assertEqual("turn_01", request.visible_dialogue_context.turns[0].turn_id)
        self.assertEqual("answer", request.visible_dialogue_context.turns[0].observation.kind)

        hidden_question_payload = dict(payload)
        hidden_question_payload["question"] = {
            "text": payload["question"]["text"],
            "mastery_level": "L4",
        }
        with self.assertRaises(ValidationError):
            SimulatorTurnRequest.model_validate(hidden_question_payload)

        hidden_context_payload = dict(payload)
        hidden_context_payload["visible_dialogue_context"] = {
            "turns": [
                {
                    "turn_id": "turn_01",
                    "question": {"text": "How do you interpret a regression slope?"},
                    "answer": {
                        "text": "I usually read it as the expected change in the response.",
                        "evidence_ids": ["ev_hidden"],
                    },
                    "observation": {"kind": "answer"},
                }
            ],
            "states": [{"node_id": "linear_regression"}],
        }
        with self.assertRaises(ValidationError):
            SimulatorTurnRequest.model_validate(hidden_context_payload)

        candidate_path_payload = dict(payload)
        candidate_path_payload["map_id"] = "candidate_maps/dev_map_001"
        with self.assertRaises(ValidationError):
            SimulatorTurnRequest.model_validate(candidate_path_payload)

        invalid_question_id_payload = dict(payload)
        invalid_question_id_payload["question"] = {
            "question_id": "bad/question id",
            "text": payload["question"]["text"],
        }
        with self.assertRaises(ValidationError):
            SimulatorTurnRequest.model_validate(invalid_question_id_payload)

    def test_turn_request_accepts_debug_trace_availability_option_only(self):
        payload = {
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "map_id": "dev_map_001",
            "question": {"text": "How would you decide whether linear regression is appropriate?"},
            "turn_options": {"include_debug_trace": True},
        }

        request = SimulatorTurnRequest.model_validate(payload)

        self.assertEqual("openai", request.client_provider)
        self.assertTrue(request.turn_options.include_debug_trace)

        hidden_options_payload = dict(payload)
        hidden_options_payload["turn_options"] = {
            "include_debug_trace": True,
            "raw_debug_trace": {"grounding": "hidden internals"},
        }
        with self.assertRaises(ValidationError):
            SimulatorTurnRequest.model_validate(hidden_options_payload)

    def test_turn_request_accepts_client_provider_like_authoring_requests(self):
        payload = {
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "map_id": "dev_map_001",
            "client_provider": "deepseek",
            "question": {"text": "How would you decide whether linear regression is appropriate?"},
        }

        request = SimulatorTurnRequest.model_validate(payload)

        self.assertEqual("deepseek", request.client_provider)

        unsupported_provider_payload = dict(payload)
        unsupported_provider_payload["client_provider"] = "unknown"
        with self.assertRaises(ValidationError):
            SimulatorTurnRequest.model_validate(unsupported_provider_payload)

    def test_turn_response_exposes_only_visible_answer_metadata_and_trace_handle(self):
        payload = {
            "answer": {"text": "I can explain the slope, but I am less sure about the assumptions."},
            "observation": {"kind": "answer"},
            "warnings": [
                {
                    "code": "missing_profile_context",
                    "message": "Profile context is unavailable; simulator used neutral wording.",
                }
            ],
            "debug_trace_id": "trace_turn_001",
            "debug_trace_available": True,
        }

        response = SimulatorTurnResponse.model_validate(payload)

        self.assertEqual("answer", response.observation.kind)
        self.assertEqual("trace_turn_001", response.debug_trace_id)

        forbidden_fields = {
            "mastery_level": "L3",
            "evidence_refs": ["ev_hidden"],
            "evidence_ids": ["ev_hidden"],
            "states": [{"node_id": "linear_regression"}],
            "evidence": [{"id": "ev_hidden"}],
            "grounded_node_ids": ["linear_regression"],
            "profile_context": {"summary": "hidden persona text"},
            "debug_trace": {"grounding": "hidden internals"},
            "debug_trace_payload": {"validator": "hidden internals"},
            "raw_debug_trace": "hidden internals",
        }

        for field, value in forbidden_fields.items():
            with self.subTest(field=field):
                hidden_payload = dict(payload)
                hidden_payload[field] = value

                with self.assertRaises(ValidationError):
                    SimulatorTurnResponse.model_validate(hidden_payload)

        hidden_answer_payload = dict(payload)
        hidden_answer_payload["answer"] = {
            "text": payload["answer"]["text"],
            "evidence_refs": ["ev_hidden"],
        }
        with self.assertRaises(ValidationError):
            SimulatorTurnResponse.model_validate(hidden_answer_payload)

    def test_turn_test_response_exposes_only_grounded_node_ids_beyond_turn_response(self):
        payload = {
            "answer": {"text": "I can compare the held-out split with repeated folds."},
            "observation": {"kind": "answer"},
            "warnings": [],
            "debug_trace_id": None,
            "debug_trace_available": None,
            "grounded_node_ids": ["train_test_split", "cross_validation"],
        }

        response = SimulatorTurnTestResponse.model_validate(payload)

        self.assertEqual(
            ("train_test_split", "cross_validation"),
            response.grounded_node_ids,
        )

        forbidden_fields = {
            "mastery_level": "L3",
            "evidence_refs": ["ev_hidden"],
            "evidence_ids": ["ev_hidden"],
            "states": [{"node_id": "linear_regression"}],
            "evidence": [{"id": "ev_hidden"}],
            "profile_context": {"summary": "hidden persona text"},
            "debug_trace": {"grounding": "hidden internals"},
            "debug_trace_payload": {"validator": "hidden internals"},
            "raw_debug_trace": "hidden internals",
        }

        for field, value in forbidden_fields.items():
            with self.subTest(field=field):
                hidden_payload = dict(payload)
                hidden_payload[field] = value

                with self.assertRaises(ValidationError):
                    SimulatorTurnTestResponse.model_validate(hidden_payload)


if __name__ == "__main__":
    unittest.main()
