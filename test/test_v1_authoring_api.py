import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.authoring.openai_workflow import build_openai_graph_authoring_workflow
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.llm.messages import DEEPSEEK_MESSAGE_PROFILE, OPENAI_MESSAGE_PROFILE


SOURCE_TEXT = "# Model Assessment\n\nTrain test split estimates out-of-sample performance."


class V1AuthoringApiTest(unittest.TestCase):
    def test_authoring_api_lists_existing_benchmark_domains(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            domains_dir = workspace_root / "benchmark" / "domains"
            (domains_dir / "statistical_learning").mkdir(parents=True)
            (domains_dir / "research_methods").mkdir()
            (domains_dir / "invalid domain").mkdir()
            client = _test_client(workspace_root)

            response = client.get("/api/authoring/benchmark-domains")

            self.assertEqual(200, response.status_code)
            self.assertEqual(
                {"benchmark_domains": ["research_methods", "statistical_learning"]},
                response.json(),
            )

    def test_authoring_api_lists_filesystem_configured_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            configured = _configure_source(workspace_root)
            client = _test_client(workspace_root)

            response = client.get("/api/authoring/source-materials")

            self.assertEqual(200, response.status_code)
            self.assertEqual([configured], response.json()["source_materials"])
            self.assertEqual(
                SOURCE_TEXT,
                (workspace_root / "storage/source_materials/ISLP/source.md").read_text(
                    encoding="utf-8"
                ),
            )
            upload_response = client.post(
                "/api/authoring/source-materials",
                files={"file": ("source.md", SOURCE_TEXT.encode(), "text/markdown")},
            )
            self.assertEqual(405, upload_response.status_code)

    def test_authoring_api_rejects_invalid_filesystem_configuration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _configure_source(workspace_root, representative_task_count=49)
            client = _test_client(workspace_root)

            response = client.get("/api/authoring/source-materials")

            self.assertEqual(422, response.status_code)
            self.assertIn("at least 50 representative tasks", response.json()["detail"])

    def test_authoring_api_runs_scoped_markdown_workflow_and_writes_auditable_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            model_client = FixtureGraphModelClient()
            _configure_source(workspace_root)
            client = _test_client(workspace_root, model_client)

            response = _generate_fixture_candidate_response(client, run_id="scoped_run_001")

            self.assertEqual(200, response.status_code, response.text)
            payload = response.json()
            self.assertEqual("ISLP", payload["benchmark_domain"])
            self.assertEqual("Model flexibility and generalization", payload["scope"]["aspect_name"])
            self.assertEqual(20, payload["scope"]["target_node_count"])
            self.assertEqual(24, payload["scope"]["max_node_count"])
            self.assertEqual(["train_test_split"], [node["id"] for node in payload["candidate_nodes"]])
            self.assertEqual(5, len(model_client.calls))
            self.assertIn("Graph Authoring Scope", _render_messages(model_client.calls[0]))
            self.assertIn("target_node_count", _render_messages(model_client.calls[1]))
            self.assertIn("Node Skeleton Verification Agent Step", model_client.calls[2][0].content)

            output_dir = workspace_root / payload["artifact_paths"]["output_dir_uri"]
            raw_log = _load_json(output_dir / "workflow_log.json")
            self.assertEqual("succeeded", raw_log["status"])
            self.assertEqual(12, len(raw_log["entries"]))
            entries = {entry["entry_name"]: entry for entry in raw_log["entries"]}
            reconciliation_artifacts = entries["validate_source_grounded_node_skeletons"]["artifact_uris"]
            self.assertEqual(
                "intermediate/graph_authoring_scope.json",
                reconciliation_artifacts["graph_authoring_scope"],
            )
            verification_artifacts = entries["validate_node_skeleton_verification"]["artifact_uris"]
            self.assertTrue((output_dir / verification_artifacts["node_skeleton_verification_decisions"]).exists())
            self.assertTrue((output_dir / verification_artifacts["verified_node_skeletons"]).exists())
            draft = _load_json(output_dir / "intermediate/segment_node_extraction_drafts.json")[0]
            self.assertEqual(
                "Train test split estimates out-of-sample performance.",
                draft["evidence_excerpt"],
            )

    def test_authoring_api_derives_scope_and_rejects_legacy_request_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _configure_source(workspace_root)
            client = _test_client(workspace_root)
            missing_source = client.post(
                "/api/authoring/graph-candidates",
                json={"source_id": "missing"},
            )
            legacy_fields = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "benchmark_domain": "statistical_learning",
                    "source_id": "ISLP",
                    "scope": _scope_payload(),
                },
            )

            self.assertEqual(404, missing_source.status_code)
            self.assertEqual(422, legacy_fields.status_code)

    def test_authoring_api_reads_and_saves_candidate_graph_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _configure_source(workspace_root)
            client = _test_client(workspace_root)
            created = _generate_fixture_candidate(client, run_id="edit_run_001")

            read_response = client.get(
                "/api/authoring/candidate-graphs/ISLP/edit_run_001"
            )
            self.assertEqual(200, read_response.status_code)
            graph = read_response.json()
            graph["candidate_nodes"][0]["definition"] = "Reviewed definition."
            save_response = client.put(
                "/api/authoring/candidate-graphs/ISLP/edit_run_001",
                json={
                    "candidate_nodes": graph["candidate_nodes"],
                    "candidate_edges": graph["candidate_edges"],
                },
            )

            self.assertEqual(200, save_response.status_code)
            self.assertEqual("Reviewed definition.", save_response.json()["candidate_nodes"][0]["definition"])
            nodes_path = workspace_root / created["artifact_paths"]["candidate_nodes_uri"]
            self.assertEqual("Reviewed definition.", _load_json(nodes_path)[0]["definition"])

    def test_authoring_api_rejects_invalid_candidate_edit_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _configure_source(workspace_root)
            client = _test_client(workspace_root)
            created = _generate_fixture_candidate(client, run_id="invalid_edit_001")
            nodes_path = workspace_root / created["artifact_paths"]["candidate_nodes_uri"]
            before = nodes_path.read_bytes()
            invalid_node = dict(created["candidate_nodes"][0])
            invalid_node["levels"] = {"L0": "Only one level"}

            response = client.put(
                "/api/authoring/candidate-graphs/ISLP/invalid_edit_001",
                json={"candidate_nodes": [invalid_node], "candidate_edges": []},
            )

            self.assertEqual(422, response.status_code)
            self.assertEqual(before, nodes_path.read_bytes())

    def test_authoring_api_promotes_once_to_immutable_reviewed_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _configure_source(workspace_root)
            client = _test_client(workspace_root)
            _generate_fixture_candidate(client, run_id="promotion_run_001")
            url = "/api/authoring/candidate-graphs/ISLP/promotion_run_001/promotion"

            first = client.post(url, json={"version": "v1"})
            second = client.post(url, json={"version": "v1"})

            self.assertEqual(200, first.status_code)
            self.assertEqual(409, second.status_code)
            manifest = first.json()["graph_manifest"]
            self.assertEqual("promotion_run_001", manifest["promoted_from_candidate_run"])
            self.assertEqual("ISLP", manifest["source"][0]["source_id"])

    def test_authoring_api_selects_deepseek_provider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            factory = ProviderRecordingWorkflowFactory()
            client = TestClient(
                create_app(
                    graph_authoring_workflow_factory=factory,
                    workspace_root=workspace_root,
                )
            )
            _configure_source(workspace_root)

            response = _generate_fixture_candidate_response(
                client,
                run_id="deepseek_run_001",
                client_provider="deepseek",
            )

            self.assertEqual(200, response.status_code, response.text)
            self.assertEqual(["deepseek"], factory.client_providers)
            self.assertEqual("system", factory.model_client.calls[0][0].role)

    def test_authoring_api_writes_failed_workflow_log_with_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            model_client = IncompleteNodeGraphModelClient()
            _configure_source(workspace_root)
            client = _test_client(workspace_root, model_client)

            response = _generate_fixture_candidate_response(client, run_id="bad_run_001")

            self.assertEqual(422, response.status_code)
            detail = response.json()["detail"]
            log_path = workspace_root / detail["workflow_log_uri"]
            raw_log = _load_json(log_path)
            self.assertEqual("failed", raw_log["status"])
            self.assertEqual("validate_complete_candidate_nodes", raw_log["entries"][-1]["entry_name"])
            self.assertTrue((log_path.parent / "agent_traces/node_rubric_authoring").exists())

    def test_old_test_api_route_is_not_registered(self):
        response = _test_client(Path(tempfile.mkdtemp())).get("/test-api/health")
        self.assertEqual(404, response.status_code)


class FixtureGraphModelClient:
    def __init__(self):
        self.calls = []
        self._last_source_id = "ISLP"
        self.message_profile = OPENAI_MESSAGE_PROFILE
        self.metadata = ModelClientMetadata(
            provider="openai",
            model_name="fixture-model",
            message_profile=OPENAI_MESSAGE_PROFILE.name,
        )
        self._responses = [
            {
                "drafts": [
                    {
                        "name": "Train Test Split",
                        "definition": "Separating data into training and test sets to estimate out-of-sample performance.",
                        "source_locator": {"locator": "Model Assessment"},
                        "grounding_note": "The source presents a held-out split as an estimate of out-of-sample performance.",
                        "evidence_excerpt": "Train test split estimates out-of-sample performance.",
                    }
                ]
            },
            {
                "skeletons": [
                    {
                        "name": "Train Test Split",
                        "definition": "Separating data into training and test sets to estimate out-of-sample performance.",
                        "source_locators": [
                            {"source_id": "ISLP", "locator": "Model Assessment"}
                        ],
                        "grounding_notes": [
                            "The source presents a held-out split as an estimate of out-of-sample performance."
                        ],
                        "evidence_excerpts": [
                            "Train test split estimates out-of-sample performance."
                        ],
                        "supporting_draft_ids": ["draft_000001"],
                        "supporting_segment_ids": ["seg_000001"],
                        "merge_split_note": "Single draft retained.",
                    }
                ]
            },
            {
                "decisions": [
                    {
                        "id": "train_test_split",
                        "decision": "keep",
                        "grounding_status": "supported",
                        "scope_status": "in_scope",
                        "diagnostic_value": "high",
                        "rationale": "Directly supported and useful for representative generalization tasks.",
                    }
                ]
            },
            {
                "nodes": [
                    {
                        "id": "train_test_split",
                        "diagnostic_goal": "Assess whether the user can explain why held-out data estimates generalization.",
                        "levels": {
                            "L0": "Does not recognize train/test split.",
                            "L1": "Recognizes the term but cannot explain its purpose.",
                            "L2": "Can describe a basic holdout split.",
                            "L3": "Explains why test data must be held out.",
                            "L4": "Applies split reasoning to new model assessment cases.",
                            "L5": "Critiques split design and proposes alternatives.",
                        },
                        "diagnostic_signals": [
                            "Connects held-out testing to out-of-sample performance."
                        ],
                        "simulator_behavior": "Answer naturally without naming mastery labels.",
                    }
                ]
            },
            {"edges": []},
        ]

    def complete(self, *, messages):
        self.calls.append(messages)
        response_index = len(self.calls) - 1
        payload = json.loads(json.dumps(self._responses[response_index]))
        if response_index == 0:
            self._last_source_id = _source_id_from_prompt(_render_messages(messages))
        if response_index == 1:
            payload["skeletons"][0]["source_locators"][0]["source_id"] = self._last_source_id
        return json.dumps(payload)


class IncompleteNodeGraphModelClient(FixtureGraphModelClient):
    def __init__(self):
        super().__init__()
        del self._responses[3]["nodes"][0]["levels"]["L5"]


class ProviderRecordingWorkflowFactory:
    def __init__(self):
        self.client_providers = []
        self.model_client = FixtureGraphModelClient()
        self.model_client.message_profile = DEEPSEEK_MESSAGE_PROFILE
        self.model_client.metadata = ModelClientMetadata(
            provider="deepseek",
            model_name="deepseek-fixture",
            message_profile=DEEPSEEK_MESSAGE_PROFILE.name,
        )

    def __call__(self, client_provider):
        self.client_providers.append(client_provider)
        return build_openai_graph_authoring_workflow(model_client=self.model_client)


def _test_client(
    workspace_root: Path,
    model_client: FixtureGraphModelClient | None = None,
) -> TestClient:
    model_client = model_client or FixtureGraphModelClient()
    return TestClient(
        create_app(
            graph_authoring_workflow_factory=lambda client_provider: build_openai_graph_authoring_workflow(
                model_client=model_client
            ),
            workspace_root=workspace_root,
        )
    )


def _configure_source(
    workspace_root: Path,
    *,
    representative_task_count: int = 50,
) -> dict[str, object]:
    material_dir = workspace_root / "storage/source_materials/ISLP"
    material_dir.mkdir(parents=True)
    source_path = material_dir / "source.md"
    source_path.write_text(SOURCE_TEXT, encoding="utf-8")
    source_bytes = SOURCE_TEXT.encode()
    record = {
        "source_id": "ISLP",
        "title": "ISL Scoped Source",
        "citation": "development fixture",
        "storage_path": "source_materials/ISLP/source.md",
        "storage_uri": "storage/source_materials/ISLP/source.md",
        "filename": "source.md",
        "size_bytes": len(source_bytes),
        "content_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "uploaded_at": "2026-07-30T00:00:00Z",
    }
    metadata = {
        **record,
        "metadata_version": "1.0",
        "benchmark_domain": "ISLP",
        "question_bank_method": "reference_grounded_original_questions",
        "question_bank_sources": [
            {
                "title": "Fixture reference",
                "url": "https://example.com/reference",
                "scope_note": "Supports the test question bank.",
            }
        ],
        "graph_authoring_scope": _scope_payload(representative_task_count),
    }
    (material_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def _scope_payload(representative_task_count: int = 50):
    return {
        "aspect_name": "Model flexibility and generalization",
        "aspect_description": "Concepts needed to reason about training/test performance and overfitting.",
        "representative_tasks": [
            f"Diagnostic question {index}: explain a model-assessment decision."
            for index in range(1, representative_task_count + 1)
        ],
        "excluded_topics": ["Unrelated classification algorithms"],
        "target_node_count": 20,
        "max_node_count": 24,
    }


def _generate_fixture_candidate_response(
    client: TestClient,
    *,
    run_id: str,
    client_provider: str = "openai",
):
    return client.post(
        "/api/authoring/graph-candidates",
        json={
            "source_id": "ISLP",
            "client_provider": client_provider,
            "run_id": run_id,
        },
    )


def _generate_fixture_candidate(client: TestClient, *, run_id: str):
    response = _generate_fixture_candidate_response(client, run_id=run_id)
    if response.status_code != 200:
        raise AssertionError(f"candidate generation failed: {response.text}")
    return response.json()


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _render_messages(messages) -> str:
    return "\n\n".join(message.content for message in messages)


def _source_id_from_prompt(prompt: str) -> str:
    marker = "Source ID (workflow-supplied; do not output): "
    for line in prompt.splitlines():
        if line.startswith(marker):
            return line[len(marker):].strip()
    return "ISLP"


if __name__ == "__main__":
    unittest.main()
