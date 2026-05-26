import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.authoring.openai_workflow import build_openai_graph_authoring_workflow


class V1AuthoringApiTest(unittest.TestCase):
    def test_authoring_api_runs_from_cached_markdown_and_writes_candidate_files_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            markdown_path = _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            fake_parser = FixtureSourceParser("## Should not be used")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, fake_parser)

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
            self.assertEqual("storage/books/isl_python.md", payload["material"]["markdown_storage_uri"])
            self.assertEqual("hit", payload["material"]["markdown_cache_status"])
            self.assertEqual(markdown_path.stat().st_size, payload["material"]["markdown_size_bytes"])
            self.assertEqual([], fake_parser.calls)
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
            self.assertEqual("storage/books/isl_python.md", raw_log["source_materials"][0]["parsed_markdown_uri"])
            self.assertEqual("hit", raw_log["source_materials"][0]["parsed_markdown_cache_status"])
            self.assertEqual(artifact_paths["workflow_log_uri"], raw_log["artifact_paths"]["workflow_log_uri"])
            self.assertEqual(
                {"skeletons": 1, "candidate_nodes": 1, "candidate_edges": 0},
                payload["run_log_summary"]["output_counts"],
            )
            serialized_log = json.dumps(raw_log)
            self.assertNotIn("Cached Markdown", serialized_log)
            self.assertNotIn("Node Extraction Agent Step", serialized_log)

            self.assertEqual(3, len(fake_model_client.calls))
            self.assertIn("Node Extraction Agent Step", fake_model_client.calls[0][0].content)
            self.assertIn("Node Rubric Authoring Agent Step", fake_model_client.calls[1][0].content)
            self.assertIn("Edge Proposal Agent Step", fake_model_client.calls[2][0].content)
            for messages in fake_model_client.calls:
                rendered_prompt = _render_messages(messages)
                self.assertIn("Parsed Source Markdown", rendered_prompt)
                self.assertIn("Cached Markdown", rendered_prompt)
                self.assertIn('source_id "isl_python"', rendered_prompt)
                self.assertNotIn("data:application/pdf;base64", rendered_prompt)
                self.assertNotIn("uploaded original PDF", rendered_prompt)

    def test_authoring_api_generates_markdown_when_cache_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            pdf_path = _write_fixture_pdf(workspace_root)
            fake_parser = FixtureSourceParser("## Generated Markdown\n\nMinerU output.")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, fake_parser)

            response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "pdf_path": "books/isl_python.pdf",
                    "write_artifacts": False,
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("generated", payload["material"]["markdown_cache_status"])
            self.assertEqual("storage/books/isl_python.md", payload["material"]["markdown_storage_uri"])
            self.assertEqual([pdf_path], fake_parser.calls)
            self.assertEqual("## Generated Markdown\n\nMinerU output.", (pdf_path.with_suffix(".md")).read_text())
            self.assertIsNone(payload["artifact_paths"])
            self.assertIn("Generated Markdown", _render_messages(fake_model_client.calls[0]))

    def test_authoring_api_force_reparse_regenerates_existing_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            pdf_path = _write_fixture_pdf(workspace_root)
            markdown_path = pdf_path.with_suffix(".md")
            markdown_path.write_text("## Stale Markdown", encoding="utf-8")
            fake_parser = FixtureSourceParser("## Regenerated Markdown")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, fake_parser)

            response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "pdf_path": "books/isl_python.pdf",
                    "force_reparse": True,
                    "write_artifacts": False,
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("regenerated", payload["material"]["markdown_cache_status"])
            self.assertEqual([pdf_path], fake_parser.calls)
            self.assertEqual("## Regenerated Markdown", markdown_path.read_text(encoding="utf-8"))
            self.assertIn("Regenerated Markdown", _render_messages(fake_model_client.calls[0]))
            self.assertNotIn("Stale Markdown", _render_messages(fake_model_client.calls[0]))

    def test_authoring_api_writes_failed_workflow_log_and_returns_uri(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            fake_model_client = IncompleteNodeGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, FixtureSourceParser("unused"))

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
            self.assertEqual(2, len(fake_model_client.calls))

    def test_authoring_api_rejects_paths_outside_storage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            fake_parser = FixtureSourceParser("unused")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, fake_parser)

            response = client.post(
                "/api/authoring/graph-candidates",
                json={"pdf_path": "../secret.pdf"},
            )

            self.assertEqual(422, response.status_code)
            self.assertEqual([], fake_parser.calls)
            self.assertEqual([], fake_model_client.calls)

    def test_authoring_api_rejects_empty_cached_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "   \n")
            fake_parser = FixtureSourceParser("unused")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, fake_parser)

            response = client.post(
                "/api/authoring/graph-candidates",
                json={"pdf_path": "books/isl_python.pdf"},
            )

            self.assertEqual(422, response.status_code)
            self.assertIn("Parsed Source Markdown is empty", response.json()["detail"])
            self.assertEqual([], fake_parser.calls)
            self.assertEqual([], fake_model_client.calls)

    def test_old_test_api_route_is_not_registered(self):
        client = TestClient(
            create_app(
                graph_authoring_workflow_factory=lambda: build_openai_graph_authoring_workflow(
                    model_client=FixtureGraphModelClient()
                ),
                source_parser=FixtureSourceParser("unused"),
            )
        )

        response = client.get("/test-api/health")

        self.assertEqual(404, response.status_code)


class FixtureGraphModelClient:
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

    def complete(self, *, messages):
        self.calls.append(messages)
        return self._responses[len(self.calls) - 1]


class IncompleteNodeGraphModelClient(FixtureGraphModelClient):
    def __init__(self):
        super().__init__()
        node_payload = json.loads(self._responses[1])
        del node_payload["nodes"][0]["levels"]["L5"]
        self._responses = [
            self._responses[0],
            json.dumps(node_payload),
            self._responses[2],
        ]


class FixtureSourceParser:
    def __init__(self, markdown: str):
        self.markdown = markdown
        self.calls = []

    def parse_pdf_to_markdown(
        self,
        *,
        pdf_path: Path,
        run_id: str | None = None,
        storage_uri: str | None = None,
    ) -> str:
        self.calls.append(pdf_path)
        return self.markdown


def _test_client(workspace_root: Path, model_client: FixtureGraphModelClient, parser: FixtureSourceParser) -> TestClient:
    return TestClient(
        create_app(
            graph_authoring_workflow_factory=lambda: build_openai_graph_authoring_workflow(
                model_client=model_client
            ),
            source_parser=parser,
            workspace_root=workspace_root,
        )
    )


def _write_fixture_pdf(workspace_root: Path) -> Path:
    pdf_path = workspace_root / "storage" / "books" / "isl_python.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\nfixture\n%%EOF")
    return pdf_path


def _write_fixture_markdown(workspace_root: Path, text: str) -> Path:
    markdown_path = workspace_root / "storage" / "books" / "isl_python.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(text, encoding="utf-8")
    return markdown_path


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _render_messages(messages) -> str:
    return "\n\n".join(message.content for message in messages)


if __name__ == "__main__":
    unittest.main()
