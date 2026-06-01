import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.authoring.profile_context import build_profile_context_authoring_workflow
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE


class V1ProfileContextAuthoringApiTest(unittest.TestCase):
    def test_authoring_api_generates_reviewable_profile_context_candidate_with_minimal_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            fake_model_client = FixtureProfileContextModelClient()
            client = TestClient(
                create_app(
                    profile_context_authoring_workflow_factory=lambda client_provider: (
                        build_profile_context_authoring_workflow(model_client=fake_model_client)
                    ),
                    workspace_root=workspace_root,
                )
            )

            response = client.post(
                "/api/authoring/profile-context-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "rough_description": (
                        "A beginner who can follow sklearn examples but has weak statistical foundations."
                    ),
                    "domain_summary": "Classical supervised machine learning algorithms.",
                    "run_id": "profile_run_001",
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("profile_run_001", payload["run_id"])
            self.assertEqual(
                {
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "summary": "A practical beginner with limited statistical foundations.",
                    "background": ["Has followed introductory sklearn examples."],
                    "prior_experience": ["Can run basic estimator workflows."],
                    "goals": ["Build a clearer conceptual understanding of supervised learning."],
                    "preferences": ["Prefers concrete examples before formal explanations."],
                },
                payload["candidate_profile_context"],
            )
            self.assertNotIn("user_id", payload["candidate_profile_context"])

            artifact_paths = payload["artifact_paths"]
            output_dir = workspace_root / artifact_paths["output_dir_uri"]
            self.assertEqual(
                {
                    "candidate_profile_context.json",
                    "workflow_log.json",
                    "agent_traces",
                },
                {path.name for path in output_dir.iterdir()},
            )
            self.assertEqual(
                {"model_raw_output.txt", "parser_output.json"},
                {path.name for path in (output_dir / "agent_traces").iterdir()},
            )
            self.assertEqual(
                payload["candidate_profile_context"],
                _load_json(workspace_root / artifact_paths["candidate_profile_context_uri"]),
            )
            self.assertEqual(
                {
                    key: value
                    for key, value in payload["candidate_profile_context"].items()
                    if key != "benchmark_domain"
                },
                _load_json(workspace_root / artifact_paths["parser_output_uri"]),
            )
            raw_log = _load_json(workspace_root / artifact_paths["workflow_log_uri"])
            self.assertEqual("profile_run_001", raw_log["run_id"])
            self.assertEqual("Profile Context Authoring Workflow", raw_log["workflow_name"])
            self.assertEqual("succeeded", raw_log["status"])
            self.assertEqual("openai", raw_log["model_provider"])
            self.assertEqual("fixture-profile-model", raw_log["model_name"])
            self.assertEqual(artifact_paths, raw_log["artifact_paths"])

    def test_authoring_api_reads_saved_profile_context_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            client = TestClient(
                create_app(
                    profile_context_authoring_workflow_factory=lambda client_provider: (
                        build_profile_context_authoring_workflow(
                            model_client=FixtureProfileContextModelClient()
                        )
                    ),
                    workspace_root=workspace_root,
                )
            )
            create_response = client.post(
                "/api/authoring/profile-context-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "rough_description": "A practical beginner.",
                    "run_id": "profile_read_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)

            response = client.get(
                "/api/authoring/candidate-profile-contexts/"
                "classical_supervised_ml_algorithms/profile_read_run_001"
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("profile_read_run_001", payload["run_id"])
            self.assertEqual(
                create_response.json()["candidate_profile_context"],
                payload["candidate_profile_context"],
            )
            self.assertEqual(
                create_response.json()["artifact_paths"],
                payload["artifact_paths"],
            )

    def test_authoring_api_rejects_graph_data_in_profile_context_authoring_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_model_client = FixtureProfileContextModelClient()
            client = TestClient(
                create_app(
                    profile_context_authoring_workflow_factory=lambda client_provider: (
                        build_profile_context_authoring_workflow(model_client=fake_model_client)
                    ),
                    workspace_root=Path(temp_dir),
                )
            )

            response = client.post(
                "/api/authoring/profile-context-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "rough_description": "A practical beginner.",
                    "graph_nodes": [{"id": "train_test_split"}],
                    "node_rubrics": [{"id": "train_test_split", "levels": {}}],
                    "edges": [],
                },
            )

            self.assertEqual(422, response.status_code)
            self.assertEqual([], fake_model_client.calls)
            self.assertEqual(
                {"edges", "graph_nodes", "node_rubrics"},
                {
                    item["loc"][-1]
                    for item in response.json()["detail"]
                    if item["type"] == "extra_forbidden"
                },
            )

    def test_authoring_api_selects_profile_context_client_provider_per_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workflow_factory = ProviderRecordingProfileContextWorkflowFactory()
            client = TestClient(
                create_app(
                    profile_context_authoring_workflow_factory=workflow_factory,
                    workspace_root=Path(temp_dir),
                )
            )

            response = client.post(
                "/api/authoring/profile-context-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "rough_description": "A practical beginner.",
                    "client_provider": "deepseek",
                    "run_id": "profile_deepseek_run_001",
                },
            )

            self.assertEqual(200, response.status_code)
            self.assertEqual(["deepseek"], workflow_factory.client_providers)

    def test_authoring_api_rejects_profile_context_output_with_identity_or_node_level_mastery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            client = TestClient(
                create_app(
                    profile_context_authoring_workflow_factory=lambda client_provider: (
                        build_profile_context_authoring_workflow(
                            model_client=ProfileContextModelClientWithForbiddenFields()
                        )
                    ),
                    workspace_root=workspace_root,
                )
            )

            response = client.post(
                "/api/authoring/profile-context-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "rough_description": "A practical beginner.",
                    "run_id": "profile_invalid_output_run_001",
                },
            )

            self.assertEqual(502, response.status_code)
            self.assertIn("extra_forbidden", response.json()["detail"])
            self.assertFalse(
                (
                    workspace_root
                    / "benchmark"
                    / "domains"
                    / "classical_supervised_ml_algorithms"
                    / "candidate_profile_contexts"
                    / "profile_invalid_output_run_001"
                    / "candidate_profile_context.json"
                ).exists()
            )


class FixtureProfileContextModelClient:
    def __init__(self):
        self.calls = []
        self.message_profile = OPENAI_MESSAGE_PROFILE
        self.metadata = ModelClientMetadata(
            provider="openai",
            model_name="fixture-profile-model",
            message_profile=OPENAI_MESSAGE_PROFILE.name,
        )

    def complete(self, *, messages):
        self.calls.append(messages)
        return json.dumps(
            {
                "summary": "A practical beginner with limited statistical foundations.",
                "background": ["Has followed introductory sklearn examples."],
                "prior_experience": ["Can run basic estimator workflows."],
                "goals": ["Build a clearer conceptual understanding of supervised learning."],
                "preferences": ["Prefers concrete examples before formal explanations."],
            }
        )


class ProfileContextModelClientWithForbiddenFields(FixtureProfileContextModelClient):
    def complete(self, *, messages):
        payload = json.loads(super().complete(messages=messages))
        payload["user_id"] = "must_not_be_assigned_during_generation"
        payload["mastery_levels"] = {"train_test_split": "L2"}
        return json.dumps(payload)


class ProviderRecordingProfileContextWorkflowFactory:
    def __init__(self):
        self.client_providers = []

    def __call__(self, client_provider):
        self.client_providers.append(client_provider)
        return build_profile_context_authoring_workflow(
            model_client=FixtureProfileContextModelClient()
        )


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    unittest.main()
