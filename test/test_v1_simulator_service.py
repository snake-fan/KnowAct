import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.core.evidence import EvidenceRecord
from backend.knowact.core.graph import KnowledgeNode
from backend.knowact.core.interaction import (
    VisibleObservationKind,
    VisibleSimulatorAnswer,
)
from backend.knowact.core.map import UserKnowledgeState
from backend.knowact.llm.client import ModelClientError, ModelClientMetadata
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE
from backend.knowact.simulator.checks import (
    HeuristicSimulatorAnswerValidator,
    ModelClientAnswerValidator,
    SimulatorAnswerValidationDecision,
)
from backend.knowact.simulator.context_builder import (
    GroundedSimulatorNodeContext,
    SimulatorTurnContext,
)
from backend.knowact.simulator.generators import (
    ModelClientAnswerGenerator,
    RuleBasedAnswerGenerator,
)
from backend.knowact.simulator.grounding import QuestionGroundingResult
from backend.knowact.simulator.policy import (
    ModelClientAnswerPolicy,
    RuleBasedAnswerPolicy,
    SimulatorAnswerStance,
    SimulatorResponseMode,
)
from backend.knowact.simulator.preview import (
    SimulatorPreviewRequest,
    SimulatorPreviewWarningCode,
)
from backend.knowact.simulator.service import SimulatorService


class V1SimulatorServiceTest(unittest.TestCase):
    def test_service_answers_clear_question_from_reviewed_map_manifest_bindings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(workspace_root=workspace_root)
            request = SimulatorPreviewRequest.model_validate(
                {
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "text": "How would you decide whether a train/test split is appropriate?"
                    },
                }
            )

            response = service.answer_preview(request)

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertEqual((), response.warnings)
            self.assertIn("train/test split", response.answer.text.lower())
            self.assertIn("held-out", response.answer.text.lower())
            self.assertNotIn("L4", response.answer.text)
            self.assertNotIn("ev_gt_map_001_train_test_split_001", response.answer.text)
            self.assertNotIn("synthetic_user_001", response.answer.text)

    def test_service_logs_preview_workflow_steps_without_hidden_payloads(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(workspace_root=workspace_root)
            request = SimulatorPreviewRequest.model_validate(
                {
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "text": "How would you decide whether a train/test split is appropriate?"
                    },
                }
            )

            with self.assertLogs("knowact.simulator", level="INFO") as captured_logs:
                response = service.answer_preview(request)

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            log_text = "\n".join(captured_logs.output)
            for expected_fragment in (
                "Simulator preview workflow started",
                "Simulator preview map manifest loaded",
                "Simulator preview reviewed graph loaded",
                "Question grounding succeeded",
                "Simulator preview reviewed map loaded",
                "Simulator profile context loaded",
                "Simulator context built",
                "Answer blueprint derived",
                "Answer generation input prepared",
                "Simulator answer generation started",
                "Rule-based simulator answer generation succeeded",
                "Simulator answer validation completed",
                "Simulator preview workflow succeeded",
            ):
                with self.subTest(expected_fragment=expected_fragment):
                    self.assertIn(expected_fragment, log_text)
            for hidden_fragment in (
                "ev_gt_map_001_train_test_split_001",
                "Can explain why a final held-out evaluation is useful.",
                "A practical beginner with limited statistical foundations.",
                "Has followed introductory sklearn examples.",
                "Can run basic estimator workflows.",
                "Understand model evaluation.",
                "Prefers concrete examples.",
                response.answer.text,
            ):
                with self.subTest(hidden_fragment=hidden_fragment):
                    self.assertNotIn(hidden_fragment, log_text)

    def test_preview_api_answers_reviewed_map_request_without_episode_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            client = _simulator_preview_test_client(workspace_root)

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "text": "How would you decide whether a train/test split is appropriate?"
                    },
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("answer", payload["observation"]["kind"])
            self.assertEqual([], payload["warnings"])
            self.assertIn("held-out", payload["answer"]["text"].lower())
            self.assertNotIn("map_manifest", payload)
            self.assertNotIn("graph_version", payload)
            self.assertNotIn("user_id", payload)

    def test_preview_api_selects_simulator_client_provider_per_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service_factory = RecordingSimulatorServiceFactory()
            client = TestClient(
                create_app(
                    workspace_root=workspace_root,
                    simulator_service_factory=service_factory,
                )
            )

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "client_provider": "deepseek",
                    "question": {
                        "text": "How would you decide whether a train/test split is appropriate?"
                    },
                },
            )

            self.assertEqual(200, response.status_code)
            self.assertEqual(["deepseek"], service_factory.client_providers)

    def test_preview_api_reports_debug_trace_availability_without_inline_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            client = _simulator_preview_test_client(workspace_root)

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "question_id": "q_train_test_split",
                        "text": "How would you decide whether a train/test split is appropriate?"
                    },
                    "preview_options": {"include_debug_trace": True},
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("answer", payload["observation"]["kind"])
            self.assertEqual("q_train_test_split", payload["debug_trace_id"])
            self.assertEqual(True, payload["debug_trace_available"])
            self.assertNotIn(
                "debug_trace_unavailable",
                {warning["code"] for warning in payload["warnings"]},
            )
            response_payload = json.dumps(payload, sort_keys=True)
            for hidden_fragment in (
                "grounded_node_ids",
                "grounding_confidence",
                "debug_trace_payload",
                "raw_debug_trace",
                "ev_gt_map_001_train_test_split_001",
            ):
                with self.subTest(hidden_fragment=hidden_fragment):
                    self.assertNotIn(hidden_fragment, response_payload)

            trace_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "simulator"
                / "gt_map_001"
                / "q_train_test_split"
            )
            trace_payload = _read_json(trace_dir / "debug_trace.json")
            self.assertEqual("succeeded", trace_payload["status"])
            self.assertEqual("q_train_test_split", trace_payload["trace_id"])
            self.assertEqual(
                ["train_test_split"],
                trace_payload["workflow"]["grounding"]["grounded_node_ids"],
            )
            self.assertEqual(
                ["ev_gt_map_001_train_test_split_001"],
                trace_payload["workflow"]["policy"]["decision_trace"][
                    "grounded_node_traces"
                ][0]["evidence_refs"],
            )
            self.assertEqual(
                payload["answer"],
                trace_payload["visible_output"]["answer"],
            )
            self.assertFalse((trace_dir / "map.json").exists())
            self.assertFalse((trace_dir / "profile_context.json").exists())

    def test_preview_api_persists_debug_trace_even_when_handle_is_not_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            client = _simulator_preview_test_client(workspace_root)

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "question_id": "q_without_handle",
                        "text": "How would you decide whether a train/test split is appropriate?",
                    },
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertIsNone(payload["debug_trace_id"])
            self.assertIsNone(payload["debug_trace_available"])
            self.assertTrue(
                (
                    workspace_root
                    / "benchmark"
                    / "domains"
                    / "classical_supervised_ml_algorithms"
                    / "simulator"
                    / "gt_map_001"
                    / "q_without_handle"
                    / "debug_trace.json"
                ).exists()
            )

    def test_preview_api_generates_question_trace_id_when_question_id_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            client = _simulator_preview_test_client(workspace_root)

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "text": "How would you decide whether a train/test split is appropriate?",
                    },
                    "preview_options": {"include_debug_trace": True},
                },
            )

            self.assertEqual(200, response.status_code)
            trace_id = response.json()["debug_trace_id"]
            self.assertTrue(trace_id.startswith("question_"))
            self.assertTrue(
                (
                    workspace_root
                    / "benchmark"
                    / "domains"
                    / "classical_supervised_ml_algorithms"
                    / "simulator"
                    / "gt_map_001"
                    / trace_id
                    / "debug_trace.json"
                ).exists()
            )

    def test_preview_api_rewrites_existing_question_debug_trace_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            trace_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "simulator"
                / "gt_map_001"
                / "q_rewrite"
            )
            stale_path = (
                trace_dir
                / "agent_traces"
                / "answer_generation"
                / "attempt_999"
                / "stale.txt"
            )
            stale_path.parent.mkdir(parents=True)
            stale_path.write_text("stale", encoding="utf-8")
            client = _simulator_preview_test_client(workspace_root)

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "question_id": "q_rewrite",
                        "text": "How would you decide whether a train/test split is appropriate?",
                    },
                    "preview_options": {"include_debug_trace": True},
                },
            )

            self.assertEqual(200, response.status_code)
            self.assertFalse(stale_path.exists())
            self.assertTrue((trace_dir / "debug_trace.json").exists())

    def test_preview_api_returns_no_grounding_non_answer_without_hidden_map_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(
                workspace_root,
                include_profile_context=True,
                include_map_artifact=False,
            )
            client = _simulator_preview_test_client(workspace_root)

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {"text": "What should I study next?"},
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("non_answer", payload["observation"]["kind"])
            self.assertIn("which concept", payload["answer"]["text"].lower())
            response_payload = json.dumps(payload, sort_keys=True)
            self.assertNotIn("ev_gt_map_001", response_payload)
            self.assertNotIn("held-out", response_payload.lower())

    def test_preview_api_returns_multi_question_clarification_without_hidden_map_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(
                workspace_root,
                include_profile_context=True,
                include_map_artifact=False,
            )
            client = _simulator_preview_test_client(workspace_root)

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "text": (
                            "How would you use a train/test split? "
                            "How do cross-validation folds work?"
                        )
                    },
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("clarification", payload["observation"]["kind"])
            self.assertIn("one specific question", payload["answer"]["text"].lower())
            response_payload = json.dumps(payload, sort_keys=True)
            self.assertNotIn("ev_gt_map_001", response_payload)
            self.assertNotIn("final test", response_payload.lower())

    def test_preview_api_returns_missing_profile_context_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=False)
            client = _simulator_preview_test_client(workspace_root)

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "text": "How would you decide whether a train/test split is appropriate?"
                    },
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("answer", payload["observation"]["kind"])
            self.assertIn("held-out", payload["answer"]["text"].lower())
            self.assertEqual(["missing_profile_context"], [
                warning["code"] for warning in payload["warnings"]
            ])
            self.assertNotIn("synthetic_user_001", json.dumps(payload, sort_keys=True))

    def test_service_continues_with_non_leaking_warning_when_profile_context_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=False)
            service = SimulatorService(workspace_root=workspace_root)

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": "How would you decide whether a train/test split is appropriate?"
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("held-out", response.answer.text.lower())
            self.assertEqual(1, len(response.warnings))
            self.assertEqual(
                SimulatorPreviewWarningCode.MISSING_PROFILE_CONTEXT,
                response.warnings[0].code,
            )
            self.assertNotIn("synthetic_user_001", response.warnings[0].message)
            self.assertNotIn("gt_map_001", response.warnings[0].message)

    def test_service_does_not_pull_neighbor_state_or_evidence_from_graph_edges(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(workspace_root=workspace_root)

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": "How would you decide whether a train/test split is appropriate?"
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("train/test split", response.answer.text.lower())
            self.assertNotIn("validation fold", response.answer.text.lower())
            self.assertNotIn("separate final test set", response.answer.text.lower())
            self.assertNotIn("cross-validation", response.answer.text.lower())

    def test_question_grounding_ignores_hidden_map_state_and_evidence_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(workspace_root=workspace_root)

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {"text": "How do folds rotate validation data?"},
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.NON_ANSWER, response.observation.kind)
            self.assertNotIn("fold", response.answer.text.lower())
            self.assertNotIn("validation", response.answer.text.lower())

    def test_no_grounding_preview_does_not_load_hidden_reviewed_map_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(
                workspace_root,
                include_profile_context=True,
                include_map_artifact=False,
            )
            service = SimulatorService(workspace_root=workspace_root)

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {"text": "What should I study next?"},
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.NON_ANSWER, response.observation.kind)
            self.assertIn("which concept", response.answer.text.lower())
            self.assertNotIn("held-out", response.answer.text.lower())
            self.assertNotIn("ev_gt_map_001", response.answer.text)
            self.assertEqual((), response.warnings)
            self.assertEqual(
                {"kind": "non_answer"},
                response.observation.model_dump(mode="json"),
            )

    def test_multiple_independent_questions_get_clarification_without_hidden_map_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(
                workspace_root,
                include_profile_context=True,
                include_map_artifact=False,
            )
            service = SimulatorService(workspace_root=workspace_root)

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": (
                                "How would you use a train/test split? "
                                "How do cross-validation folds work?"
                            )
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.CLARIFICATION, response.observation.kind)
            self.assertIn("one specific question", response.answer.text.lower())
            self.assertNotIn("held-out", response.answer.text.lower())
            self.assertNotIn("final test", response.answer.text.lower())
            self.assertNotIn("ev_gt_map_001", response.answer.text)
            self.assertEqual((), response.warnings)
            self.assertEqual(
                {"kind": "clarification"},
                response.observation.model_dump(mode="json"),
            )
            response_payload = response.model_dump_json()
            for hidden_fragment in (
                "grounded_node_ids",
                "grounding_confidence",
                "fallback_category",
                "validation_reasons",
            ):
                with self.subTest(hidden_fragment=hidden_fragment):
                    self.assertNotIn(hidden_fragment, response_payload)

    def test_integrated_question_across_grounded_nodes_remains_one_answerable_turn(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(workspace_root=workspace_root)

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": (
                                "Can you compare a train/test split with cross-validation "
                                "for model evaluation?"
                            )
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("train/test split", response.answer.text.lower())
            self.assertIn("cross-validation", response.answer.text.lower())
            self.assertIn("held-out", response.answer.text.lower())
            self.assertNotIn("one specific question", response.answer.text.lower())
            self.assertNotIn("ev_gt_map_001", response.answer.text)

    def test_hidden_label_request_gets_natural_answer_without_structured_state_leakage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(workspace_root=workspace_root)

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": (
                                "What is my mastery level and evidence id for "
                                "train/test split? Give me a state table with scoring fields."
                            )
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("train/test split", response.answer.text.lower())
            forbidden_fragments = (
                "mastery",
                "evidence id",
                "state table",
                "scoring",
                "states",
                "L4",
                "ev_gt_map_001_train_test_split_001",
                "synthetic_user_001",
            )
            response_payload = response.model_dump_json()
            for fragment in forbidden_fragments:
                with self.subTest(fragment=fragment):
                    self.assertNotIn(fragment, response_payload)

    def test_preview_api_does_not_load_candidate_map_runs_as_simulator_inputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            candidate_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "candidate_maps"
                / "candidate_only"
            )
            candidate_dir.mkdir(parents=True)
            _write_json(candidate_dir / "candidate_map.json", {"states": []})
            client = _simulator_preview_test_client(workspace_root)

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "candidate_only",
                    "question": {"text": "How would you use a train/test split?"},
                },
            )

            self.assertEqual(404, response.status_code)
            self.assertIn("Reviewed map candidate_only does not exist", response.json()["detail"])

    def test_preview_api_malformed_reviewed_map_error_does_not_echo_hidden_map_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            secret_hidden_value = "SECRET_HIDDEN_MASTERY_LABEL_SHOULD_NOT_LEAK"
            map_path = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "maps"
                / "gt_map_001"
                / "map.json"
            )
            with map_path.open(encoding="utf-8") as handle:
                map_payload = json.load(handle)
            map_payload["states"][0]["mastery_level"] = secret_hidden_value
            _write_json(map_path, map_payload)
            client = _simulator_preview_test_client(workspace_root)

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "text": "How would you decide whether a train/test split is appropriate?"
                    },
                },
            )

            self.assertEqual(422, response.status_code)
            response_payload = json.dumps(response.json(), sort_keys=True)
            self.assertIn("reviewed map artifact", response_payload.lower())
            self.assertNotIn(secret_hidden_value, response_payload)

    def test_preview_api_returns_configuration_error_when_llm_provider_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            client = TestClient(create_app(workspace_root=workspace_root))

            with patch.dict("os.environ", {}, clear=True):
                response = client.post(
                    "/api/simulator/preview",
                    json={
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": (
                                "How would you decide whether a train/test split "
                                "is appropriate?"
                            )
                        },
                    },
                )

            self.assertEqual(503, response.status_code)
            self.assertEqual(
                "Simulator LLM service is not configured.",
                response.json()["detail"],
            )

    def test_policy_intent_and_generator_do_not_expose_raw_hidden_state(self):
        simulator_context = SimulatorTurnContext(
            benchmark_domain="classical_supervised_ml_algorithms",
            map_id="gt_map_001",
            graph_version="v1",
            user_id="synthetic_user_001",
            grounded_nodes=(
                GroundedSimulatorNodeContext(
                    node=KnowledgeNode.model_validate(
                        _knowledge_node("train_test_split", "Train/Test Split")
                    ),
                    state=UserKnowledgeState.model_validate(
                        {
                            "node_id": "train_test_split",
                            "mastery_level": "L2",
                            "evidence_refs": ["ev_hidden_partial"],
                            "misconceptions": [],
                            "unknowns": ["When a separate validation set is needed."],
                        }
                    ),
                    simulator_only_evidence=(
                        EvidenceRecord.model_validate(
                            {
                                "id": "ev_hidden_partial",
                                "node_id": "train_test_split",
                                "evidence_type": "ground_truth_profile",
                                "evidence_kind": "prior_answer",
                                "visibility": "simulator_only",
                                "signal": "Can explain the held-out split idea but mixes up validation and final testing.",
                                "turn_id": None,
                            }
                        ),
                    ),
                ),
            ),
            visible_dialogue_context=None,
        )

        policy_result = RuleBasedAnswerPolicy().derive(
            question_text="How would you use a train/test split?",
            simulator_context=simulator_context,
            grounding=QuestionGroundingResult(grounded_node_ids=("train_test_split",)),
        )
        intent = policy_result.intent
        answer = RuleBasedAnswerGenerator().render(
            intent=intent,
        )

        self.assertEqual(SimulatorAnswerStance.PARTIAL_UNDERSTANDING, intent.primary_stance)
        self.assertIn(
            "ev_hidden_partial",
            policy_result.trace.grounded_node_traces[0].evidence_refs,
        )
        intent_payload = intent.model_dump_json()
        for hidden_fragment in (
            "ev_hidden_partial",
            "L2",
            "mastery_level",
            "evidence_refs",
            "synthetic_user_001",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, intent_payload)
                self.assertNotIn(hidden_fragment, answer.text)
        self.assertIn("partial", answer.text.lower())
        self.assertIn("held-out split", answer.text)

    def test_rule_based_answer_path_expresses_core_fixture_stances(self):
        cases = (
            ("L4", (), (), "correct_understanding", "can explain"),
            ("L2", (), ("When a separate validation set is needed.",), "partial_understanding", "partial"),
            ("L1", (), ("How folds rotate validation data.",), "uncertain_understanding", "not fully sure"),
            ("L0", (), (), "not_knowing", "do not really know"),
            (
                "L1",
                ("Treats each fold as a separate final test set.",),
                (),
                "misconception",
                "tend to think",
            ),
        )
        policy = RuleBasedAnswerPolicy()
        generator = RuleBasedAnswerGenerator()

        for mastery_level, misconceptions, unknowns, stance, answer_fragment in cases:
            with self.subTest(stance=stance):
                simulator_context = _simulator_context_for_state(
                    mastery_level=mastery_level,
                    misconceptions=misconceptions,
                    unknowns=unknowns,
                )

                intent = _derive_rule_based_intent(
                    policy=policy,
                    question_text="How would you use a train/test split?",
                    simulator_context=simulator_context,
                )
                answer = generator.render(intent=intent)

                self.assertEqual(stance, intent.primary_stance)
                self.assertIn(answer_fragment, answer.text.lower())

    def test_service_uses_deidentified_llm_generator_and_validator_for_safe_answers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            fake_model_client = FixtureSimulatorAnswerModelClient(
                json.dumps(
                    {
                        "answer": (
                            "I can explain the held-out split idea, but I would "
                            "be careful about validation details."
                        )
                    }
                )
            )
            fake_validator = PassingSimulatorAnswerValidator()
            service = SimulatorService(
                workspace_root=workspace_root,
                generator=ModelClientAnswerGenerator(model_client=fake_model_client),
                validator=fake_validator,
            )

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": (
                                "How would you decide whether a train/test split "
                                "is appropriate?"
                            )
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("held-out split", response.answer.text.lower())
            self.assertEqual(1, len(fake_model_client.calls))
            self.assertIsNotNone(fake_validator.answer_blueprint_json)
            prompt_text = "\n".join(message.content for message in fake_model_client.calls[0])
            validator_payload = fake_validator.answer_blueprint_json or ""
            for hidden_fragment in (
                "ev_gt_map_001_train_test_split_001",
                "synthetic_user_001",
                "mastery_level",
                "evidence_refs",
                "L4",
                "ground_truth",
                "map_manifest",
                "sklearn examples",
                "basic estimator workflows",
            ):
                with self.subTest(hidden_fragment=hidden_fragment):
                    self.assertNotIn(hidden_fragment, prompt_text)
                    self.assertNotIn(hidden_fragment, validator_payload)
                    self.assertNotIn(hidden_fragment, response.answer.text)

    def test_llm_generation_payload_includes_visible_dialogue_for_continuity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            fake_model_client = FixtureSimulatorAnswerModelClient(
                json.dumps(
                    {
                        "answer": (
                            "I still mix up validation and final testing when I "
                            "explain the split."
                        )
                    }
                )
            )
            service = SimulatorService(
                workspace_root=workspace_root,
                generator=ModelClientAnswerGenerator(model_client=fake_model_client),
                validator=PassingSimulatorAnswerValidator(),
            )

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": "Can you follow up on how you use a train/test split?"
                        },
                        "visible_dialogue_context": {
                            "turns": [
                                {
                                    "turn_id": "visible_turn_001",
                                    "question": {
                                        "text": "What felt uncertain in your previous answer?"
                                    },
                                    "answer": {
                                        "text": "I said I mixed up validation and final testing."
                                    },
                                    "observation": {"kind": "answer"},
                                }
                            ]
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            prompt_text = "\n".join(message.content for message in fake_model_client.calls[0])
            self.assertIn("mixed up validation and final testing", prompt_text)
            self.assertNotIn("visible_turn_001", prompt_text)
            for hidden_fragment in (
                "ev_gt_map_001_train_test_split_001",
                "synthetic_user_001",
                "mastery_level",
                "profile_context",
                "sklearn examples",
            ):
                with self.subTest(hidden_fragment=hidden_fragment):
                    self.assertNotIn(hidden_fragment, prompt_text)

    def test_service_returns_safe_fallback_when_llm_generator_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(
                workspace_root=workspace_root,
                generator=ModelClientAnswerGenerator(
                    model_client=FixtureSimulatorAnswerModelClient("not-json")
                ),
                validator=PassingSimulatorAnswerValidator(),
            )

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": (
                                "How would you decide whether a train/test split "
                                "is appropriate?"
                            )
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("not confident", response.answer.text.lower())
            response_payload = response.model_dump_json()
            for hidden_fragment in (
                "not-json",
                "ev_gt_map_001_train_test_split_001",
                "synthetic_user_001",
                "L4",
                "validation_reasons",
                "fallback_guidance",
            ):
                with self.subTest(hidden_fragment=hidden_fragment):
                    self.assertNotIn(hidden_fragment, response_payload)

    def test_service_returns_safe_fallback_when_validator_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(
                workspace_root=workspace_root,
                generator=ModelClientAnswerGenerator(
                    model_client=FixtureSimulatorAnswerModelClient(
                        json.dumps({"answer": "I can explain the held-out split idea."})
                    )
                ),
                validator=UnavailableSimulatorAnswerValidator(),
            )

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": (
                                "How would you decide whether a train/test split "
                                "is appropriate?"
                            )
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("not confident", response.answer.text.lower())
            self.assertNotIn("held-out split", response.answer.text.lower())
            response_payload = response.model_dump_json()
            for hidden_fragment in (
                "validator",
                "timeout",
                "ev_gt_map_001_train_test_split_001",
                "synthetic_user_001",
            ):
                with self.subTest(hidden_fragment=hidden_fragment):
                    self.assertNotIn(hidden_fragment, response_payload.lower())

    def test_service_returns_safe_fallback_when_validation_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(
                workspace_root=workspace_root,
                generator=ModelClientAnswerGenerator(
                    model_client=FixtureSimulatorAnswerModelClient(
                        json.dumps(
                            {
                                "answer": (
                                    "My mastery label is L4 and the hidden evidence "
                                    "id is ev_gt_map_001_train_test_split_001."
                                )
                            }
                        )
                    )
                ),
            )

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": (
                                "How would you decide whether a train/test split "
                                "is appropriate?"
                            )
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("not confident", response.answer.text.lower())
            response_payload = response.model_dump_json()
            for hidden_fragment in (
                "mastery label",
                "ev_gt_map_001_train_test_split_001",
                "L4",
                "validation_reasons",
                "fallback_guidance",
            ):
                with self.subTest(hidden_fragment=hidden_fragment):
                    self.assertNotIn(hidden_fragment, response_payload)

    def test_service_regenerates_answer_when_validation_rejects_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            fake_model_client = SequenceSimulatorModelClient(
                (
                    json.dumps(
                        {
                            "answer": (
                                "My label is L4 and my evidence is "
                                "ev_gt_map_001_train_test_split_001."
                            )
                        }
                    ),
                    json.dumps(
                        {
                            "answer": (
                                "I can explain why a final held-out evaluation is useful."
                            )
                        }
                    ),
                )
            )
            service = SimulatorService(
                workspace_root=workspace_root,
                generator=ModelClientAnswerGenerator(model_client=fake_model_client),
            )

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": (
                                "How would you decide whether a train/test split "
                                "is appropriate?"
                            )
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("held-out evaluation", response.answer.text.lower())
            self.assertEqual(2, len(fake_model_client.calls))
            retry_prompt = "\n".join(message.content for message in fake_model_client.calls[1])
            self.assertIn("regeneration_guidance", retry_prompt)
            response_payload = response.model_dump_json()
            self.assertNotIn("L4", response_payload)
            self.assertNotIn("ev_gt_map_001_train_test_split_001", response_payload)

    def test_heuristic_validator_returns_structured_blocking_reasons(self):
        simulator_context = _simulator_context_for_state(
            mastery_level="L4",
            misconceptions=(),
            unknowns=(),
        )
        intent = _derive_rule_based_intent(
            policy=RuleBasedAnswerPolicy(),
            question_text="How would you use a train/test split?",
            simulator_context=simulator_context,
        )

        decision = HeuristicSimulatorAnswerValidator().validate(
            candidate_answer=VisibleSimulatorAnswer(
                text=(
                    "My L4 mastery appears in the state table with hidden evidence "
                    "id ev_hidden, scoring fields, and a knowledge map dump."
                )
            ),
            intent=intent,
        )

        self.assertFalse(decision.passed)
        self.assertIsNotNone(decision.fallback_guidance)
        self.assertEqual(
            {
                "mastery label leakage",
                "hidden evidence id leakage",
                "state-table language",
                "benchmark scoring fields",
                "full-map or state dump language",
            },
            set(decision.blocking_safety_reasons),
        )

    def test_model_client_validator_parses_deidentified_structured_decision(self):
        simulator_context = _simulator_context_for_state(
            mastery_level="L2",
            misconceptions=(),
            unknowns=("When a separate validation set is needed.",),
        )
        intent = _derive_rule_based_intent(
            policy=RuleBasedAnswerPolicy(),
            question_text="How would you use a train/test split?",
            simulator_context=simulator_context,
        )
        fake_model_client = FixtureSimulatorAnswerModelClient(
            json.dumps(
                {
                    "passed": True,
                    "blocking_safety_reasons": [],
                    "blueprint_coverage_notes": [
                        "The answer preserves partial understanding."
                    ],
                    "fallback_guidance": None,
                }
            )
        )

        decision = ModelClientAnswerValidator(model_client=fake_model_client).validate(
            candidate_answer=VisibleSimulatorAnswer(
                text="I understand the held-out split idea but still mix up validation."
            ),
            intent=intent,
        )

        self.assertTrue(decision.passed)
        self.assertEqual(
            ("The answer preserves partial understanding.",),
            decision.blueprint_coverage_notes,
        )
        self.assertEqual(1, len(fake_model_client.calls))
        validator_prompt = "\n".join(message.content for message in fake_model_client.calls[0])
        self.assertIn("held-out split idea", validator_prompt)
        for hidden_fragment in (
            "ev_hidden_state",
            "synthetic_user_001",
            "mastery_level",
            "evidence_refs",
            "L2",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, validator_prompt)

    def test_model_client_policy_parses_safe_structured_intent_and_keeps_trace_hidden(self):
        simulator_context = _simulator_context_for_state(
            mastery_level="L2",
            misconceptions=(),
            unknowns=("When a separate validation set is needed.",),
        )
        fake_model_client = FixtureSimulatorAnswerModelClient(
            json.dumps(
                {
                    "primary_stance": "partial_understanding",
                    "answer_shape": {
                        "voice": "first_person",
                        "integration_mode": "single_node",
                        "max_sentences": 2,
                    },
                    "answer_strategy": "Answer with partial understanding.",
                    "content_units": [
                        {
                            "node_name": "Train/Test Split",
                            "stance": "partial_understanding",
                            "core_claim": "Can explain the held-out split idea.",
                            "boundary": "Still checks validation details.",
                            "mistaken_belief": None,
                            "uncertainty": None,
                            "supporting_cues": [],
                            "avoid_overclaiming": [
                                "full confidence about validation details"
                            ],
                        }
                    ],
                }
            )
        )

        result = ModelClientAnswerPolicy(model_client=fake_model_client).derive(
            question_text="How would you use a train/test split?",
            simulator_context=simulator_context,
            grounding=QuestionGroundingResult(grounded_node_ids=("train_test_split",)),
        )

        self.assertEqual(SimulatorResponseMode.ANSWER, result.intent.response_mode)
        self.assertEqual("model_client", result.trace.policy_source)
        self.assertIn("ev_hidden_state", result.trace.grounded_node_traces[0].evidence_refs)
        intent_payload = result.intent.model_dump_json()
        for hidden_fragment in (
            "ev_hidden_state",
            "synthetic_user_001",
            "mastery_level",
            "evidence_refs",
            "L2",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, intent_payload)

    def test_rule_based_policy_intent_does_not_leak_label_examples(self):
        simulator_context = _simulator_context_for_state(
            mastery_level="L2",
            misconceptions=(),
            unknowns=("When a separate validation set is needed.",),
        )

        result = RuleBasedAnswerPolicy().derive(
            question_text="How would you use a train/test split?",
            simulator_context=simulator_context,
            grounding=QuestionGroundingResult(grounded_node_ids=("train_test_split",)),
        )

        intent_payload = result.intent.model_dump_json()
        for hidden_fragment in ("L0", "L1", "L2", "L3", "L4", "L5", "ev_"):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, intent_payload)

    def test_model_client_policy_rejects_unsafe_downstream_intent(self):
        simulator_context = _simulator_context_for_state(
            mastery_level="L2",
            misconceptions=(),
            unknowns=("When a separate validation set is needed.",),
        )
        fake_model_client = FixtureSimulatorAnswerModelClient(
            json.dumps(
                {
                    "primary_stance": "partial_understanding",
                    "answer_shape": {
                        "voice": "first_person",
                        "integration_mode": "single_node",
                        "max_sentences": 2,
                    },
                    "answer_strategy": "Answer with partial understanding.",
                    "content_units": [
                        {
                            "node_name": "Train/Test Split",
                            "stance": "partial_understanding",
                            "core_claim": "The hidden label is L2.",
                            "boundary": "Uses ev_hidden_state.",
                            "mistaken_belief": None,
                            "uncertainty": None,
                            "supporting_cues": [],
                            "avoid_overclaiming": [],
                        }
                    ],
                }
            )
        )

        with self.assertRaises(ModelClientError):
            ModelClientAnswerPolicy(model_client=fake_model_client).derive(
                question_text="How would you use a train/test split?",
                simulator_context=simulator_context,
                grounding=QuestionGroundingResult(grounded_node_ids=("train_test_split",)),
            )

    def test_preview_api_uses_llm_generator_and_llm_validator(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            fake_model_client = SequenceSimulatorModelClient(
                (
                    json.dumps({"answer": "I can explain the held-out split idea."}),
                    json.dumps(
                        {
                            "passed": True,
                            "blocking_safety_reasons": [],
                            "blueprint_coverage_notes": ["Safe and blueprint-covering."],
                            "fallback_guidance": None,
                        }
                    ),
                )
            )
            client = _simulator_preview_test_client(
                workspace_root,
                service=SimulatorService(
                    workspace_root=workspace_root,
                    generator=ModelClientAnswerGenerator(model_client=fake_model_client),
                    validator=ModelClientAnswerValidator(model_client=fake_model_client),
                ),
            )

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "question_id": "q_llm_trace",
                        "text": "How would you decide whether a train/test split is appropriate?"
                    },
                    "preview_options": {"include_debug_trace": True},
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("answer", payload["observation"]["kind"])
            self.assertEqual("q_llm_trace", payload["debug_trace_id"])
            self.assertIn("held-out split", payload["answer"]["text"].lower())
            self.assertEqual(2, len(fake_model_client.calls))
            trace_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "simulator"
                / "gt_map_001"
                / "q_llm_trace"
            )
            generation_raw = (
                trace_dir
                / "agent_traces"
                / "answer_generation"
                / "attempt_001"
                / "model_raw_output.txt"
            )
            validation_raw = (
                trace_dir
                / "agent_traces"
                / "answer_validation"
                / "attempt_001"
                / "model_raw_output.txt"
            )
            self.assertIn("held-out split", generation_raw.read_text(encoding="utf-8"))
            self.assertIn(
                "Safe and blueprint-covering",
                validation_raw.read_text(encoding="utf-8"),
            )
            trace_payload = _read_json(trace_dir / "debug_trace.json")
            self.assertEqual(
                generation_raw.relative_to(workspace_root).as_posix(),
                trace_payload["model_steps"][
                    "answer_generation.attempt_001"
                ]["model_raw_output_uri"],
            )
            self.assertEqual(
                "succeeded",
                trace_payload["model_steps"][
                    "answer_validation.attempt_001"
                ]["parser_status"],
            )


class FixtureSimulatorAnswerModelClient:
    message_profile = OPENAI_MESSAGE_PROFILE

    def __init__(self, raw_output: str) -> None:
        self._raw_output = raw_output
        self.metadata = ModelClientMetadata(
            provider="fixture",
            model_name="simulator-answer-fixture",
            message_profile=self.message_profile.name,
        )
        self.calls = []

    def complete(self, *, messages, temperature=None):
        self.calls.append(tuple(messages))
        return self._raw_output


class PassingSimulatorAnswerValidator:
    def __init__(self) -> None:
        self.answer_blueprint_json: str | None = None

    def validate(
        self,
        *,
        candidate_answer,
        intent,
        visible_dialogue_context=None,
        style_hint=None,
        regeneration_guidance=(),
    ):
        self.answer_blueprint_json = intent.model_dump_json()
        return SimulatorAnswerValidationDecision(
            passed=True,
            blocking_safety_reasons=(),
            blueprint_coverage_notes=("Core stance is covered.",),
            fallback_guidance=None,
        )


class UnavailableSimulatorAnswerValidator:
    def validate(
        self,
        *,
        candidate_answer,
        intent,
        visible_dialogue_context=None,
        style_hint=None,
        regeneration_guidance=(),
    ):
        raise TimeoutError("validator timeout")


class SequenceSimulatorModelClient(FixtureSimulatorAnswerModelClient):
    def __init__(self, raw_outputs: tuple[str, ...]) -> None:
        super().__init__("")
        self._raw_outputs = list(raw_outputs)

    def complete(self, *, messages, temperature=None):
        self.calls.append(tuple(messages))
        return self._raw_outputs.pop(0)


def _simulator_preview_test_client(
    workspace_root: Path,
    *,
    service: SimulatorService | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            workspace_root=workspace_root,
            simulator_service_factory=lambda _client_provider, root: service
            or SimulatorService(workspace_root=root),
        )
    )


class RecordingSimulatorServiceFactory:
    def __init__(self) -> None:
        self.client_providers: list[str] = []

    def __call__(self, client_provider, workspace_root):
        self.client_providers.append(client_provider)
        return SimulatorService(workspace_root=workspace_root)


def _write_reviewed_simulator_fixture(
    workspace_root: Path,
    *,
    include_profile_context: bool,
    include_map_artifact: bool = True,
) -> None:
    graph_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "graphs"
        / "v1"
    )
    graph_dir.mkdir(parents=True)
    _write_json(
        graph_dir / "graph_manifest.json",
        {
            "graph_id": "kg_classical_supervised_ml_algorithms_v1",
            "domain": "classical_supervised_ml_algorithms",
            "version": "v1",
            "promoted_from_candidate_run": "graph_run_001",
            "nodes_file": "authored_nodes.json",
            "edges_file": "authored_edges.json",
        },
    )
    _write_json(
        graph_dir / "authored_nodes.json",
        [
            _knowledge_node("train_test_split", "Train/Test Split"),
            _knowledge_node("cross_validation", "Cross-Validation"),
        ],
    )
    _write_json(
        graph_dir / "authored_edges.json",
        [
            {
                "id": "edge_train_test_split_prerequisite_for_cross_validation",
                "source": "train_test_split",
                "target": "cross_validation",
                "type": "prerequisite_for",
                "rationale": "A held-out split motivates repeated validation splits.",
                "weight": 0.7,
                "curation_confidence": 0.8,
            }
        ],
    )

    map_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "maps"
        / "gt_map_001"
    )
    map_dir.mkdir(parents=True)
    _write_json(
        map_dir / "map_manifest.json",
        {
            "map_id": "gt_map_001",
            "user_id": "synthetic_user_001",
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "graph_version": "v1",
            "promoted_from_candidate_run": "map_run_001",
        },
    )
    if include_map_artifact:
        _write_json(
            map_dir / "map.json",
            {
                "user_id": "synthetic_user_001",
                "kind": "ground_truth",
                "states": [
                    {
                        "node_id": "train_test_split",
                        "mastery_level": "L4",
                        "evidence_refs": ["ev_gt_map_001_train_test_split_001"],
                        "misconceptions": [],
                        "unknowns": [],
                    },
                    {
                        "node_id": "cross_validation",
                        "mastery_level": "L1",
                        "evidence_refs": ["ev_gt_map_001_cross_validation_001"],
                        "misconceptions": ["Treats each fold as a separate final test set."],
                        "unknowns": ["How folds rotate validation data."],
                    },
                ],
                "evidence": [
                    {
                        "id": "ev_gt_map_001_train_test_split_001",
                        "node_id": "train_test_split",
                        "evidence_type": "ground_truth_profile",
                        "evidence_kind": "prior_answer",
                        "visibility": "simulator_only",
                        "signal": "Can explain why a final held-out evaluation is useful.",
                        "turn_id": None,
                    },
                    {
                        "id": "ev_gt_map_001_cross_validation_001",
                        "node_id": "cross_validation",
                        "evidence_type": "ground_truth_profile",
                        "evidence_kind": "misconception_trace",
                        "visibility": "simulator_only",
                        "signal": "Calls each validation fold a final test set.",
                        "turn_id": None,
                    },
                ],
            },
        )

    if include_profile_context:
        profile_path = (
            workspace_root
            / "benchmark"
            / "domains"
            / "classical_supervised_ml_algorithms"
            / "users"
            / "synthetic_user_001"
            / "profile_context.json"
        )
        profile_path.parent.mkdir(parents=True)
        _write_json(
            profile_path,
            {
                "user_id": "synthetic_user_001",
                "benchmark_domain": "classical_supervised_ml_algorithms",
                "summary": "A practical beginner with limited statistical foundations.",
                "background": ["Has followed introductory sklearn examples."],
                "prior_experience": ["Can run basic estimator workflows."],
                "goals": ["Understand model evaluation."],
                "preferences": ["Prefers concrete examples."],
            },
        )


def _simulator_context_for_state(
    *,
    mastery_level: str,
    misconceptions: tuple[str, ...],
    unknowns: tuple[str, ...],
) -> SimulatorTurnContext:
    return SimulatorTurnContext(
        benchmark_domain="classical_supervised_ml_algorithms",
        map_id="gt_map_001",
        graph_version="v1",
        user_id="synthetic_user_001",
        grounded_nodes=(
            GroundedSimulatorNodeContext(
                node=KnowledgeNode.model_validate(
                    _knowledge_node("train_test_split", "Train/Test Split")
                ),
                state=UserKnowledgeState.model_validate(
                    {
                        "node_id": "train_test_split",
                        "mastery_level": mastery_level,
                        "evidence_refs": ["ev_hidden_state"],
                        "misconceptions": misconceptions,
                        "unknowns": unknowns,
                    }
                ),
                simulator_only_evidence=(
                    EvidenceRecord.model_validate(
                        {
                            "id": "ev_hidden_state",
                            "node_id": "train_test_split",
                            "evidence_type": "ground_truth_profile",
                            "evidence_kind": "prior_answer",
                            "visibility": "simulator_only",
                            "signal": "Can explain the held-out split idea.",
                            "turn_id": None,
                        }
                    ),
                ),
            ),
        ),
        visible_dialogue_context=None,
    )


def _derive_rule_based_intent(
    *,
    policy: RuleBasedAnswerPolicy,
    question_text: str,
    simulator_context: SimulatorTurnContext,
):
    return policy.derive(
        question_text=question_text,
        simulator_context=simulator_context,
        grounding=QuestionGroundingResult(
            grounded_node_ids=tuple(
                context.state.node_id
                for context in simulator_context.grounded_nodes
            )
        ),
    ).intent


def _knowledge_node(node_id: str, name: str) -> dict[str, object]:
    return {
        "id": node_id,
        "name": name,
        "type": "concept",
        "definition": f"Definition for {name}.",
        "source_locators": [{"source_id": "isl_python", "locator": "chapter 5"}],
        "diagnostic_goal": f"Diagnose understanding of {name}.",
        "levels": {f"L{index}": f"L{index} rubric for {name}." for index in range(6)},
        "diagnostic_signals": [f"Can discuss {name}."],
        "simulator_behavior": f"Answer consistently about {name}.",
    }


def _write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    unittest.main()
