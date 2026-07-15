import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.agents.agents.simple_llm import SimpleLLMTestedAgent
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage
from backend.knowact.runtime.episode_repository import RuntimeEpisodeRepository
from backend.knowact.runtime.execution_repository import EpisodeExecutionRepository
from backend.knowact.runtime.runner import EpisodeRunner
from backend.knowact.simulator.service import SimulatorService
from backend.knowact.validation.exceptions import KnowActValidationError
from test.test_v1_runtime_episode_repository import (
    _write_confirmed_profile_context,
    _execution_configuration_payload,
    _write_manifest,
    _write_reviewed_graph,
    _write_reviewed_map,
)


def _configured_client(workspace_root: Path, **app_kwargs) -> TestClient:
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        return TestClient(create_app(workspace_root=workspace_root, **app_kwargs))


def _registration_payload(**overrides) -> dict[str, object]:
    payload: dict[str, object] = {
        "episode_id": "episode_a",
        "benchmark_domain": "classical_supervised_ml_algorithms",
        "graph_version": "v1",
        "hidden_map_id": "gt_map_001",
        "max_turns": 4,
        **_execution_configuration_payload(),
    }
    payload.update(overrides)
    return payload


def _wait_for_status(
    client: TestClient,
    episode_id: str,
    expected_status: str,
) -> dict[str, object]:
    payload: dict[str, object] = {}
    for _ in range(100):
        response = client.get(f"/api/runtime/run-queue/episodes/{episode_id}")
        if response.status_code == 200:
            payload = response.json()
            if payload["episode"]["status"] == expected_status:
                return payload
        time.sleep(0.01)
    raise AssertionError(
        f"Episode {episode_id} did not reach {expected_status}: {payload}"
    )


class V1RuntimeApiTest(unittest.TestCase):
    def test_enqueue_is_per_episode_and_checkpoint_restart_uses_new_run_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            for episode_id in ("episode_a", "episode_b"):
                _write_manifest(
                    workspace_root,
                    episode_id,
                    graph_version="v1",
                    hidden_map_id="gt_map_001",
                    max_turns=1,
                    execution_configuration=True,
                )
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            runner = EpisodeRunner(workspace_root=workspace_root)
            prepared = runner.prepare_registered_episode(
                episode_id="episode_a",
                run_id="run_broken_001",
            )
            episode_repository = RuntimeEpisodeRepository(
                workspace_root=workspace_root
            )
            execution_repository = EpisodeExecutionRepository(
                workspace_root=workspace_root
            )
            execution_repository.initialize(
                tuple(
                    record.manifest for record in episode_repository.list_episodes()
                )
            )
            execution_repository.enqueue(
                episode_id="episode_a",
                run_id=prepared.run_id,
            )
            execution_repository.mark_running("episode_a")
            execution_repository.mark_failed(
                "episode_a",
                code="episode_run_failed",
                message="The run stopped.",
            )
            prepared.artifacts.checkpoint_path.unlink()
            model_client = _FakeModelClient(
                responses=(
                    _ask_train_test_split_question_output(),
                    _train_test_split_l4_update_output(),
                    _ask_train_test_split_question_output(),
                    _train_test_split_l4_update_output(),
                )
            )
            client = TestClient(
                create_app(
                    workspace_root=workspace_root,
                    simple_llm_tested_agent_factory=lambda provider, temperature: SimpleLLMTestedAgent(
                        model_client=model_client,
                        temperature=temperature,
                    ),
                    simulator_service_factory=lambda provider, root: SimulatorService(
                        workspace_root=root
                    ),
                )
            )

            response = client.post(
                "/api/runtime/run-queue/enqueue",
                json={
                    "selections": [
                        {"episode_id": "episode_a"},
                        {"episode_id": "episode_b"},
                    ]
                },
            )
            outcomes = response.json()["outcomes"]
            self.assertFalse(outcomes[0]["accepted"])
            self.assertEqual("checkpoint_invalid", outcomes[0]["error_code"])
            self.assertTrue(outcomes[1]["accepted"])
            _wait_for_status(client, "episode_b", "completed")

            completed_requeue = client.post(
                "/api/runtime/run-queue/enqueue",
                json={"selections": [{"episode_id": "episode_b"}]},
            )
            self.assertFalse(completed_requeue.json()["outcomes"][0]["accepted"])

            restart = client.post(
                "/api/runtime/run-queue/enqueue",
                json={
                    "selections": [
                        {"episode_id": "episode_a", "action": "restart"}
                    ]
                },
            )
            restart_outcome = restart.json()["outcomes"][0]
            self.assertTrue(restart_outcome["accepted"])
            self.assertNotEqual("run_broken_001", restart_outcome["run_id"])
            _wait_for_status(client, "episode_a", "completed")
            old_run_preserved = prepared.artifacts.run_dir.exists()

        self.assertEqual(200, response.status_code)
        self.assertTrue(old_run_preserved)

    def test_list_runtime_episodes_returns_visible_summaries_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(
                workspace_root,
                "episode_a",
                graph_version="v1",
                hidden_map_id="gt_map_001",
            )
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.get("/api/runtime/episodes")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, len(payload))
        self.assertEqual("episode_a", payload[0]["episode_id"])
        self.assertEqual("v1", payload[0]["graph_version"])
        self.assertEqual(3, payload[0]["max_turns"])
        response_text = json.dumps(payload, sort_keys=True)
        self.assertNotIn("hidden_map_id", response_text)
        self.assertNotIn("gt_map_001", response_text)

    def test_read_runtime_episode_returns_tested_agent_visible_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(
                workspace_root,
                "episode_a",
                graph_version="v1",
                hidden_map_id="gt_map_001",
            )
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.get("/api/runtime/episodes/episode_a")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        manifest = payload["manifest"]
        reviewed_artifacts = payload["reviewed_artifacts"]
        preview = payload["tested_agent_visible_context_preview"]

        self.assertEqual("episode_a", manifest["episode_id"])
        self.assertEqual("classical_supervised_ml_algorithms", manifest["benchmark_domain"])
        self.assertEqual("v1", manifest["graph_version"])
        self.assertEqual("gt_map_001", manifest["hidden_map_id"])
        self.assertEqual(3, manifest["max_turns"])
        self.assertEqual("single_diagnostic_question_per_turn", manifest["interaction_rule"])
        self.assertEqual("squared_mastery_distance_v1", manifest["scoring_profile"])

        self.assertEqual("loaded", reviewed_artifacts["graph"]["status"])
        self.assertEqual(
            "kg_classical_supervised_ml_algorithms_v1",
            reviewed_artifacts["graph"]["graph_id"],
        )
        self.assertEqual(2, reviewed_artifacts["graph"]["node_count"])
        self.assertEqual(1, reviewed_artifacts["graph"]["edge_count"])
        self.assertEqual("loaded", reviewed_artifacts["reference_map"]["status"])
        self.assertEqual("gt_map_001", reviewed_artifacts["reference_map"]["map_id"])
        self.assertEqual(
            "synthetic_user_001",
            reviewed_artifacts["reference_map"]["user_id"],
        )
        self.assertEqual("ground_truth", reviewed_artifacts["reference_map"]["kind"])
        self.assertEqual(2, reviewed_artifacts["reference_map"]["covered_node_count"])
        self.assertEqual(
            "loaded",
            reviewed_artifacts["reference_map"]["profile_context_status"],
        )
        self.assertEqual("legacy_missing", manifest["configuration_status"])
        self.assertEqual(
            "execution_configuration_missing",
            payload["warnings"][0]["code"],
        )

        self.assertEqual("episode_a", preview["episode_id"])
        self.assertEqual("classical_supervised_ml_algorithms", preview["benchmark_domain"])
        self.assertEqual("v1", preview["graph_version"])
        self.assertEqual("single_diagnostic_question_per_turn", preview["interaction_rule"])
        self.assertEqual("squared_mastery_distance_v1", preview["scoring_profile"])
        self.assertEqual([], preview["visible_dialogue_context"]["turns"])
        self.assertEqual(2, len(preview["graph"]["nodes"]))
        self.assertEqual(1, len(preview["graph"]["edges"]))
        self.assertEqual(
            "Diagnose understanding of Train/Test Split.",
            preview["graph"]["nodes"][0]["diagnostic_goal"],
        )

        preview_text = json.dumps(preview, sort_keys=True)
        for hidden_fragment in (
            "hidden_map_id",
            "gt_map_001",
            "synthetic_user_001",
            "profile_context_status",
            "warnings",
            "missing_profile_context",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, preview_text)

        response_text = json.dumps(payload, sort_keys=True)
        for hidden_fragment in (
            "ev_gt_map_001",
            "mastery_level",
            "evidence_refs",
            "simulator_only",
            "A practical beginner with limited statistical foundations.",
            "answer_blueprint",
            "debug_trace",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, response_text)

    def test_register_runtime_episode_creates_manifest_and_returns_management_detail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            client = _configured_client(workspace_root)

            response = client.post(
                "/api/runtime/episodes",
                json=_registration_payload(),
            )
            manifest_path = (
                workspace_root
                / "benchmark"
                / "runtime"
                / "episodes"
                / "episode_a"
                / "episode_manifest.json"
            )
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(201, response.status_code)
        self.assertEqual(
            {
                "episode_id": "episode_a",
                "benchmark_domain": "classical_supervised_ml_algorithms",
                "graph_version": "v1",
                "hidden_map_id": "gt_map_001",
                "max_turns": 4,
                "interaction_rule": "single_diagnostic_question_per_turn",
                "scoring_profile": "squared_mastery_distance_v1",
                **_execution_configuration_payload(),
            },
            manifest_payload,
        )
        payload = response.json()
        self.assertEqual("gt_map_001", payload["manifest"]["hidden_map_id"])
        self.assertEqual("gt_map_001", payload["reviewed_artifacts"]["reference_map"]["map_id"])
        self.assertEqual(
            "synthetic_user_001",
            payload["reviewed_artifacts"]["reference_map"]["user_id"],
        )
        self.assertEqual(
            "loaded",
            payload["reviewed_artifacts"]["reference_map"]["profile_context_status"],
        )
        self.assertEqual([], payload["warnings"])

        preview_text = json.dumps(
            payload["tested_agent_visible_context_preview"],
            sort_keys=True,
        )
        for hidden_fragment in (
            "hidden_map_id",
            "gt_map_001",
            "synthetic_user_001",
            "profile_context_status",
            "warnings",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, preview_text)

    def test_register_runtime_episode_allows_missing_profile_context_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root)
            client = _configured_client(workspace_root)

            response = client.post(
                "/api/runtime/episodes",
                json=_registration_payload(),
            )

        self.assertEqual(201, response.status_code)
        payload = response.json()
        self.assertEqual(
            "missing_optional",
            payload["reviewed_artifacts"]["reference_map"]["profile_context_status"],
        )
        self.assertEqual(1, len(payload["warnings"]))
        self.assertEqual("missing_profile_context", payload["warnings"][0]["code"])
        response_text = json.dumps(payload, sort_keys=True)
        self.assertNotIn("A practical beginner with limited statistical foundations.", response_text)

        preview_text = json.dumps(
            payload["tested_agent_visible_context_preview"],
            sort_keys=True,
        )
        self.assertNotIn("missing_profile_context", preview_text)
        self.assertNotIn("profile_context_status", preview_text)

    def test_register_runtime_episode_rejects_duplicate_episode_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(
                workspace_root,
                "episode_a",
                graph_version="v1",
                hidden_map_id="gt_map_001",
            )
            client = _configured_client(workspace_root)

            response = client.post(
                "/api/runtime/episodes",
                json=_registration_payload(),
            )

        self.assertEqual(409, response.status_code)
        self.assertEqual("episode_already_exists", response.json()["detail"]["error_code"])

    def test_register_runtime_episode_rejects_identity_mismatch_without_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root, graph_version="v2")
            client = _configured_client(workspace_root)

            response = client.post(
                "/api/runtime/episodes",
                json=_registration_payload(),
            )
            manifest_path = (
                workspace_root
                / "benchmark"
                / "runtime"
                / "episodes"
                / "episode_a"
                / "episode_manifest.json"
            )

        self.assertEqual(409, response.status_code)
        self.assertEqual("identity_mismatch", response.json()["detail"]["error_code"])
        self.assertFalse(manifest_path.exists())

    def test_register_runtime_episode_rejects_missing_reviewed_artifacts_without_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            client = _configured_client(workspace_root)

            response = client.post(
                "/api/runtime/episodes",
                json=_registration_payload(),
            )
            manifest_path = (
                workspace_root
                / "benchmark"
                / "runtime"
                / "episodes"
                / "episode_a"
                / "episode_manifest.json"
            )

        self.assertEqual(424, response.status_code)
        self.assertEqual(
            "reviewed_artifact_loading_failure",
            response.json()["detail"]["error_code"],
        )
        self.assertFalse(manifest_path.exists())

    def test_register_runtime_episode_rejects_fixed_manifest_fields_in_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.post(
                "/api/runtime/episodes",
                json={
                    "episode_id": "episode_a",
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "hidden_map_id": "gt_map_001",
                    "max_turns": 4,
                    "interaction_rule": "single_diagnostic_question_per_turn",
                    "scoring_profile": "squared_mastery_distance_v1",
                },
            )

        self.assertEqual(422, response.status_code)

    def test_read_runtime_episode_reports_not_found_without_hidden_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(create_app(workspace_root=Path(temp_dir)))

            response = client.get("/api/runtime/episodes/missing_episode")

        self.assertEqual(404, response.status_code)
        self.assertEqual("episode_not_found", response.json()["detail"]["error_code"])
        response_text = json.dumps(response.json(), sort_keys=True)
        self.assertNotIn("hidden_map_id", response_text)
        self.assertNotIn("profile_context", response_text)

    def test_runtime_api_reports_malformed_registry_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            manifest_path = (
                workspace_root
                / "benchmark"
                / "runtime"
                / "episodes"
                / "episode_bad_json"
                / "episode_manifest.json"
            )
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text("{not valid json", encoding="utf-8")
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.get("/api/runtime/episodes")

        self.assertEqual(422, response.status_code)
        self.assertEqual("malformed_manifest", response.json()["detail"]["error_code"])

    def test_read_runtime_episode_reports_malformed_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_bad_manifest", max_turns=0)
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.get("/api/runtime/episodes/episode_bad_manifest")

        self.assertEqual(422, response.status_code)
        self.assertEqual("malformed_manifest", response.json()["detail"]["error_code"])

    def test_read_runtime_episode_reports_reviewed_artifact_loading_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(
                workspace_root,
                "episode_a",
                graph_version="v1",
                hidden_map_id="gt_map_001",
            )
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.get("/api/runtime/episodes/episode_a")

        self.assertEqual(424, response.status_code)
        self.assertEqual(
            "reviewed_artifact_loading_failure",
            response.json()["detail"]["error_code"],
        )
        response_text = json.dumps(response.json(), sort_keys=True)
        self.assertNotIn("gt_map_001", response_text)
        self.assertNotIn("synthetic_user_001", response_text)

    def test_read_runtime_episode_reports_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(
                workspace_root,
                "episode_a",
                graph_version="v1",
                hidden_map_id="gt_map_001",
            )
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root, graph_version="v2")
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.get("/api/runtime/episodes/episode_a")

        self.assertEqual(409, response.status_code)
        self.assertEqual("identity_mismatch", response.json()["detail"]["error_code"])

    def test_read_runtime_episode_reports_visibility_validation_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(
                workspace_root,
                "episode_a",
                graph_version="v1",
                hidden_map_id="gt_map_001",
            )
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root)
            client = TestClient(create_app(workspace_root=workspace_root))

            with patch(
                "backend.knowact.api.runtime.build_tested_agent_visible_episode_context",
                side_effect=KnowActValidationError("leak detected"),
            ):
                response = client.get("/api/runtime/episodes/episode_a")

        self.assertEqual(500, response.status_code)
        self.assertEqual(
            "visibility_validation_failure",
            response.json()["detail"]["error_code"],
        )

    def test_run_queue_executes_episode_and_returns_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(
                workspace_root,
                "episode_a",
                graph_version="v1",
                hidden_map_id="gt_map_001",
                max_turns=1,
                execution_configuration=True,
            )
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            model_client = _FakeModelClient(
                responses=(
                    _ask_train_test_split_question_output(),
                    _train_test_split_l4_update_output(),
                )
            )
            client = TestClient(
                create_app(
                    workspace_root=workspace_root,
                    simple_llm_tested_agent_factory=lambda provider, temperature: SimpleLLMTestedAgent(
                        model_client=model_client,
                        temperature=temperature,
                    ),
                    simulator_service_factory=lambda provider, root: SimulatorService(
                        workspace_root=root
                    ),
                )
            )

            response = client.post(
                "/api/runtime/run-queue/enqueue",
                json={
                    "selections": [
                        {"episode_id": "episode_a", "action": "start_or_resume"}
                    ]
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertTrue(response.json()["outcomes"][0]["accepted"])
            detail_response = None
            for _ in range(100):
                detail_response = client.get(
                    "/api/runtime/run-queue/episodes/episode_a"
                )
                self.assertEqual(200, detail_response.status_code, detail_response.text)
                if detail_response.json()["episode"]["status"] == "completed":
                    break
                time.sleep(0.01)
            self.assertIsNotNone(detail_response)
            payload = detail_response.json()["result"]
            run_id = payload["run_id"]
            transcript_path = workspace_root / payload["artifacts"]["transcript"]
            turns_path = workspace_root / payload["artifacts"]["turns"]
            scoring_report_path = workspace_root / payload["artifacts"]["scoring_report"]
            transcript_exists = transcript_path.exists()
            turn_log_exists = (turns_path / "turn_001.json").exists()
            scoring_report_exists = scoring_report_path.exists()
            transcript_response = client.get(
                f"/api/runtime/runs/{run_id}/transcript"
            )
            transcript_payload = transcript_response.json()

        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["run_id"].startswith("run_"))
        self.assertEqual("episode_a", payload["episode_id"])
        self.assertEqual("simple_llm_agent", payload["agent_kind"])
        self.assertEqual(1, payload["turn_count"])
        self.assertTrue(payload["forced_finalization"])
        self.assertFalse(payload["forced_finalization_fallback"])
        self.assertEqual(
            f"experiments/runs/{payload['run_id']}/scoring_report.json",
            payload["artifacts"]["scoring_report"],
        )
        self.assertEqual(
            "squared_mastery_distance_v1",
            payload["scoring_report"]["scoring_profile"],
        )
        self.assertAlmostEqual(18.0, payload["scoring_report"]["episode_mastery_distance"])
        self.assertTrue(transcript_exists)
        self.assertEqual(
            f"experiments/runs/{payload['run_id']}/turns",
            payload["artifacts"]["turns"],
        )
        self.assertTrue(turn_log_exists)
        self.assertTrue(scoring_report_exists)
        self.assertEqual(200, transcript_response.status_code)
        self.assertEqual(1, len(transcript_payload["turns"]))
        self.assertEqual("turn_001", transcript_payload["turns"][0]["turn_id"])
        self.assertEqual(
            "How would you decide whether a Train/Test Split is appropriate?",
            transcript_payload["turns"][0]["question"]["text"],
        )
        self.assertEqual("answer", transcript_payload["turns"][0]["observation"]["kind"])
        response_text = json.dumps(payload, sort_keys=True)
        for hidden_fragment in (
            "gt_map_001",
            "synthetic_user_001",
            "debug_trace",
            "answer_blueprint",
            "simulator_only",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, response_text)
                self.assertNotIn(
                    hidden_fragment,
                    json.dumps(transcript_payload, sort_keys=True),
                )

    def test_synchronous_episode_run_route_is_not_exposed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            (workspace_root / "experiments" / "runs" / "run_api_001").mkdir(
                parents=True
            )
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.post(
                "/api/runtime/episodes/episode_a/runs",
                json={
                    "run_id": "run_api_001",
                    "agent_kind": "simple_llm_agent",
                },
            )

        self.assertEqual(404, response.status_code)

    def test_read_runtime_run_transcript_reports_missing_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(create_app(workspace_root=Path(temp_dir)))

            response = client.get("/api/runtime/runs/missing_run/transcript")

        self.assertEqual(404, response.status_code)
        self.assertEqual(
            "episode_run_not_found",
            response.json()["detail"]["error_code"],
        )

    def test_read_runtime_run_transcript_rejects_malformed_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            transcript_path = (
                workspace_root
                / "experiments"
                / "runs"
                / "run_bad_transcript"
                / "transcript.json"
            )
            transcript_path.parent.mkdir(parents=True)
            transcript_path.write_text("{not valid json", encoding="utf-8")
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.get("/api/runtime/runs/run_bad_transcript/transcript")

        self.assertEqual(422, response.status_code)
        self.assertEqual(
            "malformed_run_transcript",
            response.json()["detail"]["error_code"],
        )


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


def _ask_train_test_split_question_output() -> str:
    return json.dumps(
        {
            "action": "ask_diagnostic_question",
            "question": {
                "text": "How would you decide whether a Train/Test Split is appropriate?",
                "question_id": "q_train_test_split",
            },
            "diagnostic_plan": {
                "primary_target_node_id": "train_test_split",
                "secondary_target_node_ids": ["cross_validation"],
                "target_mastery_boundary": "broad_initial_probe",
                "selection_reason": "A held-out evaluation scenario probes related validation concepts.",
            },
        }
    )


def _train_test_split_l4_update_output() -> str:
    return json.dumps(
        {
            "updates": [
                {
                    "node_id": "train_test_split",
                    "assessed_mastery_level": "L4",
                    "diagnostic_confidence": "high",
                    "assessment_note": "The user gave a held-out evaluation answer.",
                    "supporting_turn_ids": ["turn_001"],
                }
            ]
        }
    )


if __name__ == "__main__":
    unittest.main()
