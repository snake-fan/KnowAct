import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.authoring.openai_workflow import build_openai_pdf_graph_authoring_workflow


class V1AuthoringApiTest(unittest.TestCase):
    def test_authoring_api_runs_pdf_graph_workflow_and_writes_candidate_files_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            pdf_path = _write_fixture_pdf(workspace_root)
            fake_pdf_client = FixturePDFGraphClient()
            client = TestClient(
                create_app(
                    pdf_graph_authoring_workflow_factory=lambda path, filename: (
                        build_openai_pdf_graph_authoring_workflow(
                            pdf_path=path,
                            filename=filename,
                            pdf_client=fake_pdf_client,
                        )
                    ),
                    workspace_root=workspace_root,
                )
            )

            response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "pdf_path": "books/isl_python.pdf",
                    "run_id": "dev_run_001",
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("Graph Authoring Agent Workflow", payload["workflow"])
            self.assertEqual("storage/books/isl_python.pdf", payload["material"]["storage_uri"])
            self.assertEqual(["train_test_split"], [node["id"] for node in payload["candidate_nodes"]])
            self.assertEqual([], payload["candidate_edges"])

            artifact_paths = payload["artifact_paths"]
            nodes_path = workspace_root / artifact_paths["candidate_nodes_uri"]
            edges_path = workspace_root / artifact_paths["candidate_edges_uri"]
            log_path = workspace_root / artifact_paths["workflow_log_uri"]
            self.assertEqual(
                "benchmark/domains/classical_supervised_ml_algorithms/candidate_graphs/api/dev_run_001",
                artifact_paths["output_dir_uri"],
            )
            self.assertEqual("candidate_nodes.json", nodes_path.name)
            self.assertEqual("candidate_edges.json", edges_path.name)
            self.assertEqual("workflow_log.json", log_path.name)
            self.assertEqual(["train_test_split"], [node["id"] for node in _load_json(nodes_path)])
            self.assertEqual([], _load_json(edges_path))
            raw_log = _load_json(log_path)
            self.assertEqual("dev_run_001", raw_log["run_id"])
            self.assertEqual("succeeded", raw_log["status"])
            self.assertEqual(6, len(raw_log["entries"]))
            self.assertEqual(artifact_paths["workflow_log_uri"], raw_log["artifact_paths"]["workflow_log_uri"])
            self.assertEqual(
                {"skeletons": 1, "candidate_nodes": 1, "candidate_edges": 0},
                payload["run_log_summary"]["output_counts"],
            )
            serialized_log = json.dumps(raw_log)
            self.assertNotIn("Uploaded original PDF content", serialized_log)
            self.assertNotIn("Node Extraction Agent Step", serialized_log)

            self.assertEqual(3, len(fake_pdf_client.calls))
            self.assertEqual([pdf_path, pdf_path, pdf_path], [call["pdf_path"] for call in fake_pdf_client.calls])
            self.assertEqual(["isl_python.pdf"] * 3, [call["filename"] for call in fake_pdf_client.calls])
            self.assertEqual([True, True, True], [call["json_mode"] for call in fake_pdf_client.calls])
            self.assertIn("Node Extraction Agent Step", fake_pdf_client.calls[0]["messages"][0].content)
            self.assertIn("Node Rubric Authoring Agent Step", fake_pdf_client.calls[1]["messages"][0].content)
            self.assertIn("Edge Proposal Agent Step", fake_pdf_client.calls[2]["messages"][0].content)
            for call in fake_pdf_client.calls:
                rendered_prompt = _render_messages(call["messages"])
                self.assertIn("uploaded original PDF", rendered_prompt)
                self.assertIn('source_id "isl_python"', rendered_prompt)
                self.assertNotIn("The authoritative source material is attached", rendered_prompt)
                self.assertNotIn("storage/books/isl_python.pdf", rendered_prompt)

    def test_authoring_api_can_run_without_writing_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            fake_pdf_client = FixturePDFGraphClient()
            client = TestClient(
                create_app(
                    pdf_graph_authoring_workflow_factory=lambda path, filename: (
                        build_openai_pdf_graph_authoring_workflow(
                            pdf_path=path,
                            filename=filename,
                            pdf_client=fake_pdf_client,
                        )
                    ),
                    workspace_root=workspace_root,
                )
            )

            response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "pdf_path": "books/isl_python.pdf",
                    "write_artifacts": False,
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertIsNone(payload["artifact_paths"])
            self.assertEqual(
                {"skeletons": 1, "candidate_nodes": 1, "candidate_edges": 0},
                payload["run_log_summary"]["output_counts"],
            )

    def test_authoring_api_writes_failed_workflow_log_and_returns_uri(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            fake_pdf_client = IncompleteNodePDFGraphClient()
            client = TestClient(
                create_app(
                    pdf_graph_authoring_workflow_factory=lambda path, filename: (
                        build_openai_pdf_graph_authoring_workflow(
                            pdf_path=path,
                            filename=filename,
                            pdf_client=fake_pdf_client,
                        )
                    ),
                    workspace_root=workspace_root,
                )
            )

            response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "pdf_path": "books/isl_python.pdf",
                    "run_id": "bad_run_001",
                },
            )

            self.assertEqual(422, response.status_code)
            detail = response.json()["detail"]
            self.assertEqual(
                "benchmark/domains/classical_supervised_ml_algorithms/candidate_graphs/api/bad_run_001/workflow_log.json",
                detail["workflow_log_uri"],
            )
            self.assertIn("exactly L0-L5", detail["message"])

            output_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "candidate_graphs"
                / "api"
                / "bad_run_001"
            )
            self.assertEqual({"workflow_log.json"}, {path.name for path in output_dir.iterdir()})
            raw_log = _load_json(output_dir / "workflow_log.json")
            self.assertEqual("failed", raw_log["status"])
            self.assertEqual(detail["workflow_log_uri"], raw_log["artifact_paths"]["workflow_log_uri"])
            failed_entry = raw_log["entries"][-1]
            self.assertEqual("validate_complete_candidate_nodes", failed_entry["entry_name"])
            self.assertEqual("failed", failed_entry["validation_result"])
            self.assertEqual("KnowActValidationError", failed_entry["error"]["error_type"])
            self.assertIn("exactly L0-L5", failed_entry["error"]["message"])
            self.assertEqual(2, len(fake_pdf_client.calls))

    def test_authoring_api_rejects_paths_outside_storage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            fake_pdf_client = FixturePDFGraphClient()
            client = TestClient(
                create_app(
                    pdf_graph_authoring_workflow_factory=lambda path, filename: (
                        build_openai_pdf_graph_authoring_workflow(
                            pdf_path=path,
                            filename=filename,
                            pdf_client=fake_pdf_client,
                        )
                    ),
                    workspace_root=workspace_root,
                )
            )

            response = client.post(
                "/api/authoring/graph-candidates",
                json={"pdf_path": "../secret.pdf"},
            )

            self.assertEqual(422, response.status_code)
            self.assertEqual([], fake_pdf_client.calls)

    def test_old_test_api_route_is_not_registered(self):
        client = TestClient(
            create_app(
                pdf_graph_authoring_workflow_factory=lambda path, filename: (
                    build_openai_pdf_graph_authoring_workflow(
                        pdf_path=path,
                        filename=filename,
                        pdf_client=FixturePDFGraphClient(),
                    )
                )
            )
        )

        response = client.get("/test-api/health")

        self.assertEqual(404, response.status_code)


class FixturePDFGraphClient:
    def __init__(self):
        self.calls = []
        self._responses = [
            json.dumps(
                {
                    "skeletons": [
                        {
                            "id": "train_test_split",
                            "name": "Train Test Split",
                            "type": "concept",
                            "definition": (
                                "Separating data into training and test sets to estimate "
                                "out-of-sample performance."
                            ),
                            "source_locators": [
                                {
                                    "source_id": "isl_python",
                                    "locator": "chapter_2",
                                    "note": "Development fixture locator",
                                }
                            ],
                        }
                    ]
                }
            ),
            json.dumps(
                {
                    "nodes": [
                        {
                            "id": "train_test_split",
                            "name": "Train Test Split",
                            "type": "concept",
                            "definition": (
                                "Separating data into training and test sets to estimate "
                                "out-of-sample performance."
                            ),
                            "source_locators": [
                                {
                                    "source_id": "isl_python",
                                    "locator": "chapter_2",
                                    "note": "Development fixture locator",
                                }
                            ],
                            "diagnostic_goal": (
                                "Assess whether the user can explain and apply Train Test Split."
                            ),
                            "levels": {
                                "L0": "Does not recognize train/test split.",
                                "L1": "Recognizes the term but cannot explain its purpose.",
                                "L2": "Can describe a basic holdout split.",
                                "L3": "Can explain why held-out testing estimates generalization.",
                                "L4": "Can apply split reasoning to model assessment scenarios.",
                                "L5": "Can critique split design and generate nuanced alternatives.",
                            },
                            "diagnostic_signals": [
                                "Explains the purpose of separating training and test data.",
                                "Connects held-out testing to out-of-sample performance.",
                            ],
                            "simulator_behavior": (
                                "Answer naturally about train/test split without naming mastery labels."
                            ),
                        }
                    ]
                }
            ),
            json.dumps({"edges": []}),
        ]

    def complete_with_pdf(self, *, messages, pdf_path, filename=None, json_mode=False):
        self.calls.append(
            {
                "messages": messages,
                "pdf_path": pdf_path,
                "filename": filename,
                "json_mode": json_mode,
            }
        )
        return self._responses[len(self.calls) - 1]


class IncompleteNodePDFGraphClient(FixturePDFGraphClient):
    def __init__(self):
        super().__init__()
        node_payload = json.loads(self._responses[1])
        del node_payload["nodes"][0]["levels"]["L5"]
        self._responses = [
            self._responses[0],
            json.dumps(node_payload),
            self._responses[2],
        ]


def _write_fixture_pdf(workspace_root: Path) -> Path:
    pdf_path = workspace_root / "storage" / "books" / "isl_python.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\nfixture\n%%EOF")
    return pdf_path


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _render_messages(messages) -> str:
    return "\n\n".join(message.content for message in messages)


if __name__ == "__main__":
    unittest.main()
