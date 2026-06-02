import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.authoring.profile_context import build_profile_context_authoring_workflow
from backend.knowact.authoring.schemas import ProfileContextAuthoringInput
from backend.knowact.authoring.templates.profile_context import (
    build_profile_context_authoring_messages,
)
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE


class V1ProfileContextAuthoringApiTest(unittest.TestCase):
    def test_profile_context_prompt_is_standalone_and_task_specific(self):
        messages = build_profile_context_authoring_messages(
            ProfileContextAuthoringInput(
                benchmark_domain="classical_supervised_ml_algorithms",
                rough_description="A practical beginner.",
                domain_summary="Classical supervised machine learning algorithms.",
            )
        )
        instruction_prompt = messages[0].content
        user_prompt = messages[1].content
        complete_prompt = "\n".join(message.content for message in messages)

        self.assertNotIn("KnowAct", complete_prompt)
        self.assertNotIn("workflow", complete_prompt.lower())
        self.assertNotIn("benchmark author", complete_prompt.lower())
        self.assertNotIn("Knowledge Map", complete_prompt)
        self.assertIn("topic-by-topic knowledge assessment", instruction_prompt)
        self.assertIn("Do not invent specific institutions", instruction_prompt)
        self.assertIn("Subject area: classical_supervised_ml_algorithms", user_prompt)
        self.assertIn("Rough person description: A practical beginner.", user_prompt)

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

            with self.assertLogs("knowact.authoring.profile_context", level="INFO") as logs:
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
            rendered_logs = "\n".join(logs.output)
            self.assertIn("Profile context authoring workflow started", rendered_logs)
            self.assertIn("Profile context authoring model call started", rendered_logs)
            self.assertIn("Profile context authoring parser succeeded", rendered_logs)
            self.assertIn("Profile context authoring workflow succeeded", rendered_logs)
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

    def test_authoring_api_edits_saved_profile_context_candidate(self):
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
                    "run_id": "profile_edit_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)

            response = client.put(
                "/api/authoring/candidate-profile-contexts/"
                "classical_supervised_ml_algorithms/profile_edit_run_001",
                json={
                    "summary": "A careful learner revising a generated persona.",
                    "background": ["Has written small Python scripts."],
                    "prior_experience": [],
                    "goals": ["Understand supervised learning evaluation."],
                    "preferences": [],
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("profile_edit_run_001", payload["run_id"])
            self.assertEqual(
                {
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "summary": "A careful learner revising a generated persona.",
                    "background": ["Has written small Python scripts."],
                    "prior_experience": [],
                    "goals": ["Understand supervised learning evaluation."],
                    "preferences": [],
                },
                payload["candidate_profile_context"],
            )
            self.assertEqual(
                payload["candidate_profile_context"],
                _load_json(
                    workspace_root
                    / payload["artifact_paths"]["candidate_profile_context_uri"]
                ),
            )

    def test_authoring_api_rejects_invalid_profile_context_edits_without_overwriting_draft(self):
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
                    "run_id": "profile_invalid_edit_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)
            candidate_path = (
                workspace_root
                / create_response.json()["artifact_paths"]["candidate_profile_context_uri"]
            )
            original_candidate = _load_json(candidate_path)
            valid_edit = {
                "summary": "A careful learner.",
                "background": ["Has written small Python scripts."],
                "prior_experience": [],
                "goals": ["Understand supervised learning evaluation."],
                "preferences": [],
            }
            invalid_edits = (
                {**valid_edit, "summary": "  "},
                {**valid_edit, "background": []},
                {key: value for key, value in valid_edit.items() if key != "prior_experience"},
                {**valid_edit, "goals": []},
                {key: value for key, value in valid_edit.items() if key != "preferences"},
                {
                    **valid_edit,
                    "benchmark_domain": "another_domain",
                },
            )

            for invalid_edit in invalid_edits:
                with self.subTest(invalid_edit=invalid_edit):
                    response = client.put(
                        "/api/authoring/candidate-profile-contexts/"
                        "classical_supervised_ml_algorithms/profile_invalid_edit_run_001",
                        json=invalid_edit,
                    )

                    self.assertEqual(422, response.status_code)
                    self.assertEqual(original_candidate, _load_json(candidate_path))

    def test_authoring_api_confirms_profile_context_as_immutable_user_snapshot(self):
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
                    "run_id": "profile_confirmation_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)

            response = client.post(
                "/api/authoring/candidate-profile-contexts/"
                "classical_supervised_ml_algorithms/profile_confirmation_run_001/confirmation",
                json={"user_id": "synthetic_user_001"},
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("profile_confirmation_run_001", payload["run_id"])
            self.assertEqual(
                {
                    "user_id": "synthetic_user_001",
                    **create_response.json()["candidate_profile_context"],
                },
                payload["profile_context"],
            )
            artifact_paths = payload["artifact_paths"]
            self.assertEqual(
                "benchmark/domains/classical_supervised_ml_algorithms/users/synthetic_user_001",
                artifact_paths["output_dir_uri"],
            )
            output_dir = workspace_root / artifact_paths["output_dir_uri"]
            self.assertEqual({"profile_context.json"}, {path.name for path in output_dir.iterdir()})
            self.assertEqual(
                payload["profile_context"],
                _load_json(workspace_root / artifact_paths["profile_context_uri"]),
            )

    def test_authoring_api_rejects_overwriting_confirmed_profile_context_user_id(self):
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
            for run_id in ("profile_first_run_001", "profile_second_run_001"):
                create_response = client.post(
                    "/api/authoring/profile-context-candidates",
                    json={
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "rough_description": "A practical beginner.",
                        "run_id": run_id,
                    },
                )
                self.assertEqual(200, create_response.status_code)

            confirmation_url = (
                "/api/authoring/candidate-profile-contexts/"
                "classical_supervised_ml_algorithms/profile_first_run_001/confirmation"
            )
            first_response = client.post(
                confirmation_url,
                json={"user_id": "synthetic_user_001"},
            )
            self.assertEqual(200, first_response.status_code)
            profile_context_path = (
                workspace_root
                / first_response.json()["artifact_paths"]["profile_context_uri"]
            )
            published_snapshot = _load_json(profile_context_path)

            edit_response = client.put(
                "/api/authoring/candidate-profile-contexts/"
                "classical_supervised_ml_algorithms/profile_second_run_001",
                json={
                    "summary": "A different synthetic user.",
                    "background": ["Has stronger Python experience."],
                    "prior_experience": [],
                    "goals": ["Compare model evaluation strategies."],
                    "preferences": [],
                },
            )
            self.assertEqual(200, edit_response.status_code)
            second_confirmation_url = (
                "/api/authoring/candidate-profile-contexts/"
                "classical_supervised_ml_algorithms/profile_second_run_001/confirmation"
            )

            conflict_response = client.post(
                second_confirmation_url,
                json={"user_id": "synthetic_user_001"},
            )

            self.assertEqual(409, conflict_response.status_code)
            self.assertEqual(published_snapshot, _load_json(profile_context_path))

            overwrite_response = client.post(
                second_confirmation_url,
                json={"user_id": "synthetic_user_001", "overwrite": True},
            )

            self.assertEqual(422, overwrite_response.status_code)
            self.assertEqual(published_snapshot, _load_json(profile_context_path))

    def test_authoring_api_rejects_confirming_one_profile_context_candidate_twice(self):
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
                    "run_id": "profile_confirm_once_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)
            confirmation_url = (
                "/api/authoring/candidate-profile-contexts/"
                "classical_supervised_ml_algorithms/profile_confirm_once_run_001/confirmation"
            )
            self.assertEqual(
                200,
                client.post(
                    confirmation_url,
                    json={"user_id": "synthetic_user_001"},
                ).status_code,
            )

            response = client.post(
                confirmation_url,
                json={"user_id": "synthetic_user_002"},
            )

            self.assertEqual(409, response.status_code)
            self.assertFalse(
                (
                    workspace_root
                    / "benchmark"
                    / "domains"
                    / "classical_supervised_ml_algorithms"
                    / "users"
                    / "synthetic_user_002"
                ).exists()
            )

    def test_authoring_api_revalidates_saved_profile_context_candidate_before_confirmation(self):
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
            invalid_candidates = (
                {"summary": "  "},
                {"benchmark_domain": "another_domain"},
                {"mastery_levels": {"train_test_split": "L2"}},
            )

            for index, invalid_fields in enumerate(invalid_candidates, start=1):
                with self.subTest(invalid_fields=invalid_fields):
                    run_id = f"profile_invalid_confirmation_run_{index:03d}"
                    user_id = f"synthetic_invalid_user_{index:03d}"
                    create_response = client.post(
                        "/api/authoring/profile-context-candidates",
                        json={
                            "benchmark_domain": "classical_supervised_ml_algorithms",
                            "rough_description": "A practical beginner.",
                            "run_id": run_id,
                        },
                    )
                    self.assertEqual(200, create_response.status_code)
                    candidate_path = (
                        workspace_root
                        / create_response.json()["artifact_paths"]["candidate_profile_context_uri"]
                    )
                    candidate_path.write_text(
                        json.dumps(
                            {
                                **create_response.json()["candidate_profile_context"],
                                **invalid_fields,
                            }
                        ),
                        encoding="utf-8",
                    )

                    response = client.post(
                        "/api/authoring/candidate-profile-contexts/"
                        f"classical_supervised_ml_algorithms/{run_id}/confirmation",
                        json={"user_id": user_id},
                    )

                    self.assertEqual(422, response.status_code)
                    self.assertFalse(
                        (
                            workspace_root
                            / "benchmark"
                            / "domains"
                            / "classical_supervised_ml_algorithms"
                            / "users"
                            / user_id
                        ).exists()
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
