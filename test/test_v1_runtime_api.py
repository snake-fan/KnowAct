import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
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
        self.assertEqual("episode_a", payload["episode_id"])
        self.assertEqual("classical_supervised_ml_algorithms", payload["benchmark_domain"])
        self.assertEqual("v1", payload["graph_version"])
        self.assertEqual("single_diagnostic_question_per_turn", payload["interaction_rule"])
        self.assertEqual("squared_mastery_distance_v1", payload["scoring_profile"])
        self.assertEqual([], payload["visible_dialogue_context"]["turns"])
        self.assertEqual(2, len(payload["graph"]["nodes"]))
        self.assertEqual(1, len(payload["graph"]["edges"]))
        self.assertEqual(
            "Diagnose understanding of Train/Test Split.",
            payload["graph"]["nodes"][0]["diagnostic_goal"],
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
        response_text = json.dumps(response.json(), sort_keys=True)
        self.assertNotIn("hidden_map_id", response_text)
        self.assertNotIn("profile_context", response_text)


if __name__ == "__main__":
    unittest.main()
