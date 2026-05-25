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
            self.assertEqual(
                "benchmark/domains/classical_supervised_ml_algorithms/candidate_graphs/api/dev_run_001",
                artifact_paths["output_dir_uri"],
            )
            self.assertEqual("candidate_nodes.json", nodes_path.name)
            self.assertEqual("candidate_edges.json", edges_path.name)
            self.assertEqual(["train_test_split"], [node["id"] for node in _load_json(nodes_path)])
            self.assertEqual([], _load_json(edges_path))

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
            self.assertIsNone(response.json()["artifact_paths"])

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
