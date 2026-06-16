import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.validation.exceptions import KnowActValidationError
from test.test_v1_runtime_episode_repository import (
    _write_confirmed_profile_context,
    _write_manifest,
    _write_reviewed_graph,
    _write_reviewed_map,
)


class V1RuntimeApiTest(unittest.TestCase):
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
        self.assertEqual("ground_truth", reviewed_artifacts["reference_map"]["kind"])
        self.assertEqual(2, reviewed_artifacts["reference_map"]["covered_node_count"])

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

        response_text = json.dumps(payload, sort_keys=True)
        for hidden_fragment in (
            "hidden_map_id",
            "gt_map_001",
            "synthetic_user_001",
            "ev_gt_map_001",
            "mastery_level",
            "evidence_refs",
            "simulator_only",
            "profile_context",
            "A practical beginner with limited statistical foundations.",
            "answer_blueprint",
            "debug_trace",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, response_text)

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

    def test_runtime_api_does_not_expose_episode_run_trigger(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(create_app(workspace_root=Path(temp_dir)))

            collection_response = client.post("/api/runtime/episodes")
            run_response = client.post("/api/runtime/episodes/episode_a/runs")

        self.assertEqual(405, collection_response.status_code)
        self.assertEqual(404, run_response.status_code)


if __name__ == "__main__":
    unittest.main()
