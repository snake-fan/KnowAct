import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.authoring.openai_workflow import build_openai_graph_authoring_workflow
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.llm.messages import DEEPSEEK_MESSAGE_PROFILE, OPENAI_MESSAGE_PROFILE


class V1AuthoringApiTest(unittest.TestCase):
    def test_authoring_api_uploads_pdf_source_material_and_lists_catalog(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            fake_parser = FixtureSourceParser("unused")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, fake_parser)
            pdf_bytes = b"%PDF-1.4\nuploaded fixture\n%%EOF"

            response = client.post(
                "/api/authoring/source-materials",
                data={
                    "source_id": "isl_python_upload",
                    "title": "ISL Python Upload",
                    "citation": "local upload fixture",
                },
                files={"file": ("isl_python.pdf", pdf_bytes, "application/pdf")},
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("isl_python_upload", payload["source_id"])
            self.assertEqual("ISL Python Upload", payload["title"])
            self.assertEqual("local upload fixture", payload["citation"])
            self.assertEqual("source_materials/isl_python_upload/original.pdf", payload["storage_path"])
            self.assertEqual(
                "storage/source_materials/isl_python_upload/original.pdf",
                payload["storage_uri"],
            )
            self.assertEqual("isl_python.pdf", payload["filename"])
            self.assertEqual(len(pdf_bytes), payload["size_bytes"])
            self.assertIn("uploaded_at", payload)

            material_path = workspace_root / "storage" / payload["storage_path"]
            self.assertEqual(pdf_bytes, material_path.read_bytes())
            metadata = _load_json(material_path.parent / "metadata.json")
            self.assertEqual("isl_python_upload", metadata["source_id"])

            list_response = client.get("/api/authoring/source-materials")

            self.assertEqual(200, list_response.status_code)
            self.assertEqual([payload], list_response.json()["source_materials"])
            self.assertEqual([], fake_parser.calls)
            self.assertEqual([], fake_model_client.calls)

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
                "benchmark/domains/classical_supervised_ml_algorithms/candidate_graphs/dev_run_001",
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
            self.assertEqual("openai", raw_log["model_provider"])
            self.assertEqual("fixture-model", raw_log["model_name"])
            self.assertEqual("openai", raw_log["message_profile"])
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
            entries_by_name = {entry["entry_name"]: entry for entry in raw_log["entries"]}
            node_trace = entries_by_name["node_extraction"]["agent_trace"]
            self.assertNotIn("model_raw_output", node_trace)
            self.assertNotIn("output", node_trace["parser_result"])
            self.assertEqual(
                "agent_traces/node_extraction/model_raw_output.txt",
                node_trace["model_raw_output_uri"],
            )
            self.assertEqual(
                "agent_traces/node_extraction/parser_output.json",
                node_trace["parser_result"]["output_uri"],
            )
            self.assertIn(
                '"skeletons"',
                (log_path.parent / node_trace["model_raw_output_uri"]).read_text(encoding="utf-8"),
            )
            self.assertEqual(
                ["train_test_split"],
                [
                    node["id"]
                    for node in _load_json(log_path.parent / node_trace["parser_result"]["output_uri"])[
                        "skeletons"
                    ]
                ],
            )

            self.assertEqual(3, len(fake_model_client.calls))
            self.assertIn("Node Extraction Agent Step", fake_model_client.calls[0][0].content)
            self.assertIn("Node Rubric Authoring Agent Step", fake_model_client.calls[1][0].content)
            self.assertIn("Edge Proposal Agent Step", fake_model_client.calls[2][0].content)
            extraction_prompt = _render_messages(fake_model_client.calls[0])
            self.assertIn("Parsed Source Markdown", extraction_prompt)
            self.assertIn("Cached Markdown", extraction_prompt)
            self.assertIn('source_id "isl_python"', extraction_prompt)
            self.assertNotIn("data:application/pdf;base64", extraction_prompt)
            self.assertNotIn("uploaded original PDF", extraction_prompt)
            for messages in fake_model_client.calls[1:]:
                rendered_prompt = _render_messages(messages)
                self.assertNotIn("Cached Markdown", rendered_prompt)
                self.assertNotIn("Parsed Source Markdown for source_id", rendered_prompt)
                self.assertIn("source_grounding_notes", rendered_prompt)
                self.assertIn("isl_python", rendered_prompt)
            self.assertNotIn("data:application/pdf;base64", rendered_prompt)
            self.assertNotIn("uploaded original PDF", rendered_prompt)

    def test_authoring_api_runs_graph_candidates_from_source_material_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            fake_parser = FixtureSourceParser("## Generated From Catalog\n\nCatalog Markdown.")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, fake_parser)
            pdf_bytes = b"%PDF-1.4\ncatalog fixture\n%%EOF"
            upload_response = client.post(
                "/api/authoring/source-materials",
                data={
                    "source_id": "catalog_source",
                    "title": "Catalog Source",
                    "citation": "catalog fixture citation",
                },
                files={"file": ("catalog.pdf", pdf_bytes, "application/pdf")},
            )
            self.assertEqual(200, upload_response.status_code)

            response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "source_id": "catalog_source",
                    "run_id": "catalog_run_001",
                    "write_artifacts": False,
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("catalog_source", payload["material"]["source_id"])
            self.assertEqual("Catalog Source", payload["material"]["title"])
            self.assertEqual(
                "storage/source_materials/catalog_source/original.pdf",
                payload["material"]["storage_uri"],
            )
            self.assertEqual("generated", payload["material"]["markdown_cache_status"])
            self.assertIn("Generated From Catalog", _render_messages(fake_model_client.calls[0]))

    def test_authoring_api_reads_candidate_graph_run_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, FixtureSourceParser("unused"))
            create_response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "pdf_path": "books/isl_python.pdf",
                    "run_id": "read_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)

            response = client.get(
                "/api/authoring/candidate-graphs/classical_supervised_ml_algorithms/read_run_001"
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("classical_supervised_ml_algorithms", payload["benchmark_domain"])
            self.assertEqual("read_run_001", payload["run_id"])
            self.assertEqual(["train_test_split"], [node["id"] for node in payload["candidate_nodes"]])
            self.assertEqual([], payload["candidate_edges"])
            self.assertEqual(
                "benchmark/domains/classical_supervised_ml_algorithms/candidate_graphs/read_run_001/candidate_nodes.json",
                payload["artifact_paths"]["candidate_nodes_uri"],
            )

    def test_authoring_api_saves_valid_candidate_graph_edits_by_overwriting_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, FixtureSourceParser("unused"))
            create_response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "pdf_path": "books/isl_python.pdf",
                    "run_id": "save_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)
            graph_payload = client.get(
                "/api/authoring/candidate-graphs/classical_supervised_ml_algorithms/save_run_001"
            ).json()
            edited_node = {
                **graph_payload["candidate_nodes"][0],
                "name": "Train/Test Split Reviewed",
            }

            response = client.put(
                "/api/authoring/candidate-graphs/classical_supervised_ml_algorithms/save_run_001",
                json={
                    "candidate_nodes": [edited_node],
                    "candidate_edges": [],
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual(["Train/Test Split Reviewed"], [node["name"] for node in payload["candidate_nodes"]])
            nodes_path = workspace_root / payload["artifact_paths"]["candidate_nodes_uri"]
            self.assertEqual("Train/Test Split Reviewed", _load_json(nodes_path)[0]["name"])

    def test_authoring_api_rejects_invalid_candidate_graph_edits_without_overwriting_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, FixtureSourceParser("unused"))
            create_response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "pdf_path": "books/isl_python.pdf",
                    "run_id": "invalid_save_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)
            graph_payload = client.get(
                "/api/authoring/candidate-graphs/classical_supervised_ml_algorithms/invalid_save_run_001"
            ).json()
            nodes_path = workspace_root / graph_payload["artifact_paths"]["candidate_nodes_uri"]
            original_nodes = _load_json(nodes_path)

            response = client.put(
                "/api/authoring/candidate-graphs/classical_supervised_ml_algorithms/invalid_save_run_001",
                json={
                    "candidate_nodes": graph_payload["candidate_nodes"],
                    "candidate_edges": [
                        {
                            "id": "edge_train_test_split_supports_missing_node",
                            "source": "train_test_split",
                            "target": "missing_node",
                            "type": "supports",
                            "rationale": "Invalid edge for regression coverage.",
                            "weight": 0.5,
                            "curation_confidence": 0.5,
                        }
                    ],
                },
            )

            self.assertEqual(422, response.status_code)
            self.assertIn("unknown target node", response.json()["detail"])
            self.assertEqual(original_nodes, _load_json(nodes_path))

    def test_authoring_api_promotes_candidate_graph_into_reviewed_version_with_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, FixtureSourceParser("unused"))
            candidate_payload = _generate_fixture_candidate(client, run_id="promote_run_001")

            response = client.post(
                "/api/authoring/candidate-graphs/classical_supervised_ml_algorithms/promote_run_001/promotion",
                json={"version": "v1"},
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("classical_supervised_ml_algorithms", payload["benchmark_domain"])
            self.assertEqual("promote_run_001", payload["run_id"])
            self.assertEqual(
                {
                    "graph_id": "kg_classical_supervised_ml_algorithms_v1",
                    "domain": "classical_supervised_ml_algorithms",
                    "version": "v1",
                    "promoted_from_candidate_run": "promote_run_001",
                    "nodes_file": "authored_nodes.json",
                    "edges_file": "authored_edges.json",
                    "source": [
                        {
                            "source_id": "isl_python",
                            "title": "An Introduction to Statistical Learning with Applications in Python",
                            "citation": "storage/books/isl_python.md",
                        }
                    ],
                },
                payload["graph_manifest"],
            )
            artifact_paths = payload["artifact_paths"]
            self.assertEqual(
                "benchmark/domains/classical_supervised_ml_algorithms/graphs/v1",
                artifact_paths["output_dir_uri"],
            )
            self.assertEqual(
                payload["graph_manifest"],
                _load_json(workspace_root / artifact_paths["graph_manifest_uri"]),
            )
            self.assertEqual(
                candidate_payload["candidate_nodes"],
                _load_json(workspace_root / artifact_paths["authored_nodes_uri"]),
            )
            self.assertEqual(
                candidate_payload["candidate_edges"],
                _load_json(workspace_root / artifact_paths["authored_edges_uri"]),
            )
            self.assertTrue(
                (
                    workspace_root
                    / candidate_payload["artifact_paths"]["candidate_nodes_uri"]
                ).exists()
            )

    def test_authoring_api_requires_explicit_confirmation_before_overwriting_reviewed_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, FixtureSourceParser("unused"))
            graph_payload = _generate_fixture_candidate(client, run_id="overwrite_run_001")
            promotion_url = (
                "/api/authoring/candidate-graphs/"
                "classical_supervised_ml_algorithms/overwrite_run_001/promotion"
            )
            self.assertEqual(200, client.post(promotion_url, json={"version": "v1"}).status_code)
            authored_nodes_path = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "graphs"
                / "v1"
                / "authored_nodes.json"
            )
            edited_node = {
                **graph_payload["candidate_nodes"][0],
                "name": "Train/Test Split Reviewed Again",
            }
            save_response = client.put(
                "/api/authoring/candidate-graphs/classical_supervised_ml_algorithms/overwrite_run_001",
                json={
                    "candidate_nodes": [edited_node],
                    "candidate_edges": [],
                },
            )
            self.assertEqual(200, save_response.status_code)

            conflict_response = client.post(promotion_url, json={"version": "v1"})

            self.assertEqual(409, conflict_response.status_code)
            self.assertEqual("Train Test Split", _load_json(authored_nodes_path)[0]["name"])

            overwrite_response = client.post(
                promotion_url,
                json={"version": "v1", "overwrite": True},
            )

            self.assertEqual(200, overwrite_response.status_code)
            self.assertEqual("Train/Test Split Reviewed Again", _load_json(authored_nodes_path)[0]["name"])

    def test_authoring_api_revalidates_candidate_graph_before_promotion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, FixtureSourceParser("unused"))
            graph_payload = _generate_fixture_candidate(client, run_id="invalid_promotion_run_001")
            edges_path = workspace_root / graph_payload["artifact_paths"]["candidate_edges_uri"]
            edges_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "edge_train_test_split_supports_missing_node",
                            "source": "train_test_split",
                            "target": "missing_node",
                            "type": "supports",
                            "rationale": "Invalid edge for promotion regression coverage.",
                            "weight": 0.5,
                            "curation_confidence": 0.5,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            response = client.post(
                "/api/authoring/candidate-graphs/classical_supervised_ml_algorithms/invalid_promotion_run_001/promotion",
                json={"version": "v1"},
            )

            self.assertEqual(422, response.status_code)
            self.assertIn("unknown target node", response.json()["detail"])
            self.assertFalse(
                (
                    workspace_root
                    / "benchmark"
                    / "domains"
                    / "classical_supervised_ml_algorithms"
                    / "graphs"
                    / "v1"
                ).exists()
            )

    def test_authoring_api_allows_promotion_without_readable_optional_workflow_log(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, FixtureSourceParser("unused"))
            graph_payload = _generate_fixture_candidate(client, run_id="auditless_run_001")
            workflow_log_path = workspace_root / graph_payload["artifact_paths"]["workflow_log_uri"]
            workflow_log_path.write_text("not json", encoding="utf-8")

            response = client.post(
                "/api/authoring/candidate-graphs/classical_supervised_ml_algorithms/auditless_run_001/promotion",
                json={"version": "v1"},
            )

            self.assertEqual(200, response.status_code)
            self.assertEqual([], response.json()["graph_manifest"]["source"])

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

    def test_authoring_api_selects_deepseek_provider_per_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            workflow_factory = ProviderRecordingWorkflowFactory()
            client = TestClient(
                create_app(
                    graph_authoring_workflow_factory=workflow_factory,
                    source_parser=FixtureSourceParser("unused"),
                    workspace_root=workspace_root,
                )
            )

            response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "pdf_path": "books/isl_python.pdf",
                    "client_provider": "deepseek",
                    "write_artifacts": True,
                    "run_id": "deepseek_run_001",
                },
            )

            self.assertEqual(200, response.status_code)
            self.assertEqual(["deepseek"], workflow_factory.client_providers)
            self.assertEqual("system", workflow_factory.model_client.calls[0][0].role)
            log_path = workspace_root / response.json()["artifact_paths"]["workflow_log_uri"]
            raw_log = _load_json(log_path)
            self.assertEqual("deepseek", raw_log["model_provider"])
            self.assertEqual("deepseek-fixture", raw_log["model_name"])
            self.assertEqual("deepseek", raw_log["message_profile"])

    def test_authoring_api_rejects_unknown_client_provider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_fixture_pdf(workspace_root)
            _write_fixture_markdown(workspace_root, "## Train Test Split\n\nCached Markdown.")
            fake_model_client = FixtureGraphModelClient()
            client = _test_client(workspace_root, fake_model_client, FixtureSourceParser("unused"))

            response = client.post(
                "/api/authoring/graph-candidates",
                json={
                    "pdf_path": "books/isl_python.pdf",
                    "client_provider": "unknown",
                },
            )

            self.assertEqual(422, response.status_code)
            self.assertEqual([], fake_model_client.calls)

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
                "benchmark/domains/classical_supervised_ml_algorithms/candidate_graphs/bad_run_001/workflow_log.json",
                detail["workflow_log_uri"],
            )
            self.assertIn("exactly L0-L5", detail["message"])

            output_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "candidate_graphs"
                / "bad_run_001"
            )
            self.assertEqual(
                {"workflow_log.json", "agent_traces", "intermediate"},
                {path.name for path in output_dir.iterdir()},
            )
            raw_log = _load_json(output_dir / "workflow_log.json")
            self.assertEqual("failed", raw_log["status"])
            self.assertEqual("openai", raw_log["model_provider"])
            self.assertEqual("fixture-model", raw_log["model_name"])
            self.assertEqual("openai", raw_log["message_profile"])
            self.assertEqual(detail["workflow_log_uri"], raw_log["artifact_paths"]["workflow_log_uri"])
            failed_entry = raw_log["entries"][-1]
            self.assertEqual("validate_complete_candidate_nodes", failed_entry["entry_name"])
            self.assertEqual("failed", failed_entry["validation_result"])
            self.assertEqual("KnowActValidationError", failed_entry["error"]["error_type"])
            self.assertIn("exactly L0-L5", failed_entry["error"]["message"])
            entries_by_name = {entry["entry_name"]: entry for entry in raw_log["entries"]}
            rubric_trace = entries_by_name["node_rubric_authoring"]["agent_trace"]
            self.assertNotIn("output", rubric_trace["parser_result"])
            self.assertTrue((output_dir / rubric_trace["parser_result"]["output_uri"]).exists())
            rubric_batch_trace = rubric_trace["batch_traces"][0]
            self.assertNotIn("model_raw_output", rubric_batch_trace)
            self.assertNotIn("output", rubric_batch_trace["parser_result"])
            self.assertTrue((output_dir / rubric_batch_trace["model_raw_output_uri"]).exists())
            self.assertTrue((output_dir / rubric_batch_trace["parser_result"]["output_uri"]).exists())
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
                graph_authoring_workflow_factory=lambda client_provider: build_openai_graph_authoring_workflow(
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
        self.message_profile = OPENAI_MESSAGE_PROFILE
        self.metadata = ModelClientMetadata(
            provider="openai",
            model_name="fixture-model",
            message_profile=OPENAI_MESSAGE_PROFILE.name,
        )
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
                            "source_grounding_notes": [
                                "The fixture source introduces train/test split for estimating out-of-sample performance."
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
            graph_authoring_workflow_factory=lambda client_provider: build_openai_graph_authoring_workflow(
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


def _generate_fixture_candidate(client: TestClient, *, run_id: str):
    response = client.post(
        "/api/authoring/graph-candidates",
        json={
            "pdf_path": "books/isl_python.pdf",
            "run_id": run_id,
        },
    )
    if response.status_code != 200:
        raise AssertionError(f"candidate generation failed: {response.text}")
    return response.json()


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _render_messages(messages) -> str:
    return "\n\n".join(message.content for message in messages)


if __name__ == "__main__":
    unittest.main()
