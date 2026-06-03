import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.authoring.map_authoring import build_candidate_map_authoring_workflow
from backend.knowact.authoring.schemas import ConfirmedProfileContext, KnowledgeStateOutline
from backend.knowact.authoring.templates.map_authoring import (
    build_ground_truth_evidence_messages,
    build_knowledge_state_outline_messages,
)
from backend.knowact.core.graph import KnowledgeNode
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.llm.messages import DEEPSEEK_MESSAGE_PROFILE, OPENAI_MESSAGE_PROFILE


class V1CandidateMapAuthoringApiTest(unittest.TestCase):
    def test_map_authoring_templates_use_message_profile_high_priority_role(self):
        profile_context = _confirmed_profile_context()
        nodes = (KnowledgeNode.model_validate(_knowledge_node("train_test_split", "Train/Test Split")),)
        state_outlines = (
            KnowledgeStateOutline(
                node_id="train_test_split",
                mastery_level="L2",
                misconceptions=[],
                unknowns=[],
            ),
        )

        default_outline_messages = build_knowledge_state_outline_messages(
            profile_context=profile_context,
            nodes=nodes,
        )
        deepseek_outline_messages = build_knowledge_state_outline_messages(
            profile_context=profile_context,
            nodes=nodes,
            message_profile=DEEPSEEK_MESSAGE_PROFILE,
        )
        default_evidence_messages = build_ground_truth_evidence_messages(
            profile_context=profile_context,
            nodes=nodes,
            state_outlines=state_outlines,
        )
        deepseek_evidence_messages = build_ground_truth_evidence_messages(
            profile_context=profile_context,
            nodes=nodes,
            state_outlines=state_outlines,
            message_profile=DEEPSEEK_MESSAGE_PROFILE,
        )

        self.assertEqual("developer", default_outline_messages[0].role)
        self.assertEqual("system", deepseek_outline_messages[0].role)
        self.assertEqual("developer", default_evidence_messages[0].role)
        self.assertEqual("system", deepseek_evidence_messages[0].role)
        self.assertEqual("user", deepseek_outline_messages[1].role)
        self.assertEqual("user", deepseek_evidence_messages[1].role)

    def test_authoring_api_generates_single_batch_candidate_map_and_reads_saved_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            fake_model_client = FixtureCandidateMapModelClient()
            client = TestClient(
                create_app(
                    candidate_map_authoring_workflow_factory=lambda client_provider, root: (
                        build_candidate_map_authoring_workflow(
                            workspace_root=root,
                            model_client=fake_model_client,
                        )
                    ),
                    workspace_root=workspace_root,
                )
            )

            with self.assertLogs("knowact.authoring.map_authoring", level="INFO") as logs:
                response = client.post(
                    "/api/authoring/map-candidates",
                    json={
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "graph_version": "v1",
                        "user_id": "synthetic_user_001",
                        "run_id": "map_run_001",
                        "client_provider": "openai",
                    },
                )

            self.assertEqual(200, response.status_code)
            rendered_logs = "\n".join(logs.output)
            self.assertIn("Candidate map authoring workflow started", rendered_logs)
            self.assertIn("Candidate map reviewed graph loaded", rendered_logs)
            self.assertIn("Knowledge-state outline step started", rendered_logs)
            self.assertIn("Ground-truth evidence batch started", rendered_logs)
            self.assertIn("Candidate map authoring workflow succeeded", rendered_logs)
            payload = response.json()
            self.assertEqual("map_run_001", payload["run_id"])
            self.assertEqual(
                {
                    "user_id": "synthetic_user_001",
                    "kind": "candidate",
                    "states": [
                        {
                            "node_id": "train_test_split",
                            "mastery_level": "L2",
                            "evidence_refs": [
                                "ev_map_run_001_train_test_split_001",
                                "ev_map_run_001_train_test_split_002",
                            ],
                            "misconceptions": ["Assumes the held-out set tunes the model."],
                            "unknowns": [],
                        },
                        {
                            "node_id": "cross_validation",
                            "mastery_level": "L1",
                            "evidence_refs": ["ev_map_run_001_cross_validation_001"],
                            "misconceptions": [],
                            "unknowns": ["How folds rotate validation data."],
                        },
                    ],
                    "evidence": [
                        {
                            "id": "ev_map_run_001_train_test_split_001",
                            "node_id": "train_test_split",
                            "evidence_type": "ground_truth_profile",
                            "evidence_kind": "misconception_trace",
                            "visibility": "simulator_only",
                            "signal": "Uses the held-out set while selecting model settings.",
                            "turn_id": None,
                        },
                        {
                            "id": "ev_map_run_001_train_test_split_002",
                            "node_id": "train_test_split",
                            "evidence_type": "ground_truth_profile",
                            "evidence_kind": "prior_answer",
                            "visibility": "simulator_only",
                            "signal": "Can explain why a final held-out evaluation is useful.",
                            "turn_id": None,
                        },
                        {
                            "id": "ev_map_run_001_cross_validation_001",
                            "node_id": "cross_validation",
                            "evidence_type": "ground_truth_profile",
                            "evidence_kind": "self_report",
                            "visibility": "simulator_only",
                            "signal": "Has heard of cross-validation but cannot describe fold rotation.",
                            "turn_id": None,
                        },
                    ],
                },
                payload["candidate_map"],
            )
            artifact_paths = payload["artifact_paths"]
            output_dir = workspace_root / artifact_paths["output_dir_uri"]
            self.assertEqual(
                {
                    "candidate_map.json",
                    "consistency_warnings.json",
                    "workflow_log.json",
                    "intermediate",
                    "agent_traces",
                },
                {path.name for path in output_dir.iterdir()},
            )
            self.assertEqual(
                {"state_outline.json", "ground_truth_evidence.json"},
                {path.name for path in (output_dir / "intermediate").iterdir()},
            )
            self.assertEqual(
                payload["candidate_map"],
                _load_json(workspace_root / artifact_paths["candidate_map_uri"]),
            )
            self.assertEqual(
                {"warnings": []},
                _load_json(workspace_root / artifact_paths["consistency_warnings_uri"]),
            )

            read_response = client.get(
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_run_001"
            )

            self.assertEqual(200, read_response.status_code)
            self.assertEqual(payload, read_response.json())
            self.assertEqual(2, len(fake_model_client.calls))
            outline_prompt = _render_messages(fake_model_client.calls[0])
            evidence_prompt = _render_messages(fake_model_client.calls[1])
            self.assertIn("Knowledge-State Outline Agent Step", outline_prompt)
            self.assertIn("synthetic_user_001", outline_prompt)
            self.assertIn("train_test_split", outline_prompt)
            self.assertIn("cross_validation", outline_prompt)
            self.assertIn("Return JSON with this exact top-level shape:", outline_prompt)
            self.assertIn('"states": [', outline_prompt)
            self.assertIn('"node_id": "node id from reviewed_nodes_with_rubrics"', outline_prompt)
            self.assertIn("Allowed output fields for each state object:", outline_prompt)
            self.assertIn("- mastery_level", outline_prompt)
            self.assertIn("Forbidden output:", outline_prompt)
            self.assertIn("- evidence_refs", outline_prompt)
            self.assertIn("Node coverage:", outline_prompt)
            self.assertIn(
                "Every state.node_id must exactly match one node id from "
                "reviewed_nodes_with_rubrics",
                outline_prompt,
            )
            self.assertIn("Allowed mastery_level values:", outline_prompt)
            for mastery_level in ("L0", "L1", "L2", "L3", "L4", "L5"):
                self.assertIn(f"- {mastery_level}", outline_prompt)
            self.assertIn("Array rules:", outline_prompt)
            self.assertIn("misconceptions must always be present", outline_prompt)
            self.assertIn("unknowns must always be present", outline_prompt)
            self.assertIn("escape them as valid JSON", outline_prompt)
            self.assertNotIn("edge_train_test_split_prerequisite_for_cross_validation", outline_prompt)
            self.assertIn("Ground-Truth Evidence Authoring Agent Step", evidence_prompt)
            self.assertIn("train_test_split", evidence_prompt)
            self.assertIn("cross_validation", evidence_prompt)
            self.assertIn(
                "evidence_kind is a functional role, not a surface format",
                evidence_prompt,
            )
            self.assertIn("Task:", evidence_prompt)
            self.assertIn("Return JSON with this exact top-level shape:", evidence_prompt)
            self.assertIn('"evidence": [', evidence_prompt)
            self.assertIn('"node_id": "node id from this batch"', evidence_prompt)
            self.assertIn("Allowed output fields for each evidence object:", evidence_prompt)
            self.assertIn("Forbidden output:", evidence_prompt)
            self.assertIn("- evidence_type", evidence_prompt)
            self.assertIn("- visibility", evidence_prompt)
            self.assertIn("Node boundary:", evidence_prompt)
            self.assertIn(
                "Every evidence.node_id must exactly match one node_id from "
                "batch_nodes_with_rubrics",
                evidence_prompt,
            )
            self.assertIn("Evidence count per node:", evidence_prompt)
            self.assertIn(
                "For each node, inspect its target mastery_level from batch_state_outlines",
                evidence_prompt,
            )
            self.assertIn("- L0-L1: at least 1 evidence record", evidence_prompt)
            self.assertIn("- L2-L3: at least 2 evidence records", evidence_prompt)
            self.assertIn("- L4-L5: at least 1 evidence record", evidence_prompt)
            for allowed_kind in (
                "prior_answer",
                "worked_example",
                "self_report",
                "misconception_trace",
                "background_fact",
            ):
                self.assertIn(allowed_kind, evidence_prompt)
            for forbidden_surface_kind in (
                "quiz_answer",
                "verbal_explanation",
                "written_response",
                "discussion_comment",
                "residual_plot_interpretation",
                "theorem_reference",
            ):
                self.assertIn(forbidden_surface_kind, evidence_prompt)
            self.assertIn("never invent fine-grained evidence_kind values", evidence_prompt)
            self.assertIn("Put the specific surface form in signal", evidence_prompt)
            self.assertNotIn("edge_train_test_split_prerequisite_for_cross_validation", evidence_prompt)

    def test_authoring_api_lists_review_inputs_and_candidate_map_warnings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            _write_failed_candidate_map_run(workspace_root)
            fake_model_client = EdgeInconsistentCandidateMapModelClient()
            client = _test_client(workspace_root, fake_model_client)

            create_response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_run_with_warning",
                    "client_provider": "openai",
                },
            )

            self.assertEqual(200, create_response.status_code)

            graphs_response = client.get(
                "/api/authoring/graphs/classical_supervised_ml_algorithms"
            )
            self.assertEqual(200, graphs_response.status_code)
            self.assertEqual(
                [
                    {
                        "version": "v1",
                        "graph_id": "kg_classical_supervised_ml_algorithms_v1",
                        "node_count": 2,
                        "edge_count": 1,
                    }
                ],
                graphs_response.json()["graphs"],
            )

            graph_response = client.get(
                "/api/authoring/graphs/classical_supervised_ml_algorithms/v1"
            )
            self.assertEqual(200, graph_response.status_code)
            graph_payload = graph_response.json()
            self.assertEqual("v1", graph_payload["graph_manifest"]["version"])
            self.assertEqual(2, len(graph_payload["authored_nodes"]))
            self.assertEqual(1, len(graph_payload["authored_edges"]))

            users_response = client.get(
                "/api/authoring/users/classical_supervised_ml_algorithms"
            )
            self.assertEqual(200, users_response.status_code)
            self.assertEqual(
                [
                    {
                        "user_id": "synthetic_user_001",
                        "summary": "A practical beginner with limited statistical foundations.",
                    }
                ],
                users_response.json()["users"],
            )

            profile_response = client.get(
                "/api/authoring/users/classical_supervised_ml_algorithms/synthetic_user_001"
            )
            self.assertEqual(200, profile_response.status_code)
            self.assertEqual(
                "synthetic_user_001",
                profile_response.json()["profile_context"]["user_id"],
            )

            maps_response = client.get(
                "/api/authoring/candidate-maps/classical_supervised_ml_algorithms"
            )
            self.assertEqual(200, maps_response.status_code)
            map_summaries = {
                summary["run_id"]: summary
                for summary in maps_response.json()["runs"]
            }
            self.assertEqual(
                {
                    "run_id": "map_run_with_warning",
                    "status": "succeeded",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "has_candidate_map": True,
                    "warning_count": 1,
                    "error": None,
                },
                map_summaries["map_run_with_warning"],
            )
            self.assertEqual(
                {
                    "run_id": "failed_map_run",
                    "status": "failed",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "has_candidate_map": False,
                    "warning_count": 0,
                    "error": "second batch failed",
                },
                map_summaries["failed_map_run"],
            )

            warnings_response = client.get(
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_run_with_warning/warnings"
            )
            self.assertEqual(200, warnings_response.status_code)
            self.assertEqual(
                [
                    {
                        "edge_id": "edge_train_test_split_prerequisite_for_cross_validation",
                        "source_node_id": "train_test_split",
                        "source_mastery_level": "L1",
                        "target_node_id": "cross_validation",
                        "target_mastery_level": "L3",
                        "rule": "prerequisite_target_mastery_exceeds_source_by_at_least_two_levels",
                    }
                ],
                warnings_response.json()["warnings"],
            )

    def test_authoring_api_omits_already_promoted_candidate_map_runs_from_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            client = _test_client(workspace_root, FixtureCandidateMapModelClient())
            create_response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "stale_promoted_run",
                    "client_provider": "openai",
                },
            )
            self.assertEqual(200, create_response.status_code)
            map_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "maps"
                / "published_stale"
            )
            map_dir.mkdir(parents=True)
            _write_json(
                map_dir / "map_manifest.json",
                {
                    "map_id": "published_stale",
                    "user_id": "synthetic_user_001",
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "promoted_from_candidate_run": "stale_promoted_run",
                },
            )

            list_response = client.get(
                "/api/authoring/candidate-maps/classical_supervised_ml_algorithms"
            )

            self.assertEqual(200, list_response.status_code)
            self.assertNotIn(
                "stale_promoted_run",
                [run["run_id"] for run in list_response.json()["runs"]],
            )

    def test_authoring_api_promotes_candidate_map_into_reviewed_ground_truth_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            client = _test_client(workspace_root, FixtureCandidateMapModelClient())
            candidate_response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_promotion_run_001",
                },
            )
            self.assertEqual(200, candidate_response.status_code)
            candidate_payload = candidate_response.json()
            candidate_output_dir = workspace_root / candidate_payload["artifact_paths"]["output_dir_uri"]
            self.assertTrue(candidate_output_dir.exists())

            response = client.post(
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_promotion_run_001/promotion",
                json={"map_id": "gt_map_001"},
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            expected_manifest = {
                "map_id": "gt_map_001",
                "user_id": "synthetic_user_001",
                "benchmark_domain": "classical_supervised_ml_algorithms",
                "graph_version": "v1",
                "promoted_from_candidate_run": "map_promotion_run_001",
            }
            self.assertEqual("classical_supervised_ml_algorithms", payload["benchmark_domain"])
            self.assertEqual("map_promotion_run_001", payload["run_id"])
            self.assertEqual(expected_manifest, payload["map_manifest"])
            reviewed_map = {
                **candidate_payload["candidate_map"],
                "kind": "ground_truth",
            }
            self.assertEqual(reviewed_map, payload["map"])
            self.assertEqual(
                [
                    evidence["id"]
                    for evidence in candidate_payload["candidate_map"]["evidence"]
                ],
                [evidence["id"] for evidence in payload["map"]["evidence"]],
            )

            artifact_paths = payload["artifact_paths"]
            self.assertEqual(
                "benchmark/domains/classical_supervised_ml_algorithms/maps/gt_map_001",
                artifact_paths["output_dir_uri"],
            )
            self.assertEqual(
                reviewed_map,
                _load_json(workspace_root / artifact_paths["map_uri"]),
            )
            self.assertEqual(
                expected_manifest,
                _load_json(workspace_root / artifact_paths["map_manifest_uri"]),
            )
            published_dir = workspace_root / artifact_paths["output_dir_uri"]
            self.assertEqual(
                {"map.json", "map_manifest.json"},
                {path.name for path in published_dir.iterdir()},
            )
            self.assertFalse(candidate_output_dir.exists())
            list_response = client.get(
                "/api/authoring/candidate-maps/classical_supervised_ml_algorithms"
            )
            self.assertEqual(200, list_response.status_code)
            self.assertNotIn(
                "map_promotion_run_001",
                [run["run_id"] for run in list_response.json()["runs"]],
            )
            reviewed_list_response = client.get(
                "/api/authoring/maps/classical_supervised_ml_algorithms"
            )
            self.assertEqual(200, reviewed_list_response.status_code)
            self.assertEqual(
                [
                    {
                        "map_id": "gt_map_001",
                        "user_id": "synthetic_user_001",
                        "graph_version": "v1",
                        "state_count": 2,
                        "evidence_count": 3,
                    }
                ],
                reviewed_list_response.json()["maps"],
            )

            reviewed_read_response = client.get(
                "/api/authoring/maps/classical_supervised_ml_algorithms/gt_map_001"
            )
            self.assertEqual(200, reviewed_read_response.status_code)
            reviewed_read_payload = reviewed_read_response.json()
            self.assertEqual("classical_supervised_ml_algorithms", reviewed_read_payload["benchmark_domain"])
            self.assertEqual(expected_manifest, reviewed_read_payload["map_manifest"])
            self.assertEqual(reviewed_map, reviewed_read_payload["map"])
            self.assertEqual(artifact_paths, reviewed_read_payload["artifact_paths"])

    def test_authoring_api_rejects_map_promotion_conflicts_without_overwrite_escape_hatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            client = _test_client(workspace_root, FixtureCandidateMapModelClient())
            create_response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_conflict_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)
            first_promotion_url = (
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_conflict_run_001/promotion"
            )
            first_promotion_response = client.post(
                first_promotion_url,
                json={"map_id": "gt_map_001"},
            )
            self.assertEqual(200, first_promotion_response.status_code)
            second_client = _test_client(workspace_root, FixtureCandidateMapModelClient())
            second_create_response = second_client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_conflict_run_002",
                },
            )
            self.assertEqual(200, second_create_response.status_code)
            second_candidate_dir = (
                workspace_root
                / second_create_response.json()["artifact_paths"]["output_dir_uri"]
            )
            second_promotion_url = (
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_conflict_run_002/promotion"
            )

            same_map_id_response = second_client.post(
                second_promotion_url,
                json={"map_id": "gt_map_001"},
            )
            unsupported_overwrite_response = second_client.post(
                second_promotion_url,
                json={"map_id": "gt_map_001", "overwrite": True},
            )

            self.assertEqual(409, same_map_id_response.status_code)
            self.assertEqual(422, unsupported_overwrite_response.status_code)
            self.assertTrue(second_candidate_dir.exists())

            second_map_id_response = second_client.post(
                second_promotion_url,
                json={"map_id": "gt_map_002"},
            )

            self.assertEqual(200, second_map_id_response.status_code)
            self.assertFalse(second_candidate_dir.exists())
            self.assertTrue(
                (
                    workspace_root
                    / "benchmark"
                    / "domains"
                    / "classical_supervised_ml_algorithms"
                    / "maps"
                    / "gt_map_002"
                ).exists()
            )

    def test_authoring_api_removes_candidate_map_run_after_promotion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            client = _test_client(workspace_root, FixtureCandidateMapModelClient())
            create_response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_cleanup_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)
            candidate_dir = (
                workspace_root
                / create_response.json()["artifact_paths"]["output_dir_uri"]
            )
            self.assertTrue(candidate_dir.exists())
            promotion_url = (
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_cleanup_run_001/promotion"
            )

            promotion_response = client.post(
                promotion_url,
                json={"map_id": "gt_cleanup_map_001"},
            )
            read_after_promotion_response = client.get(
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_cleanup_run_001"
            )
            promote_again_response = client.post(
                promotion_url,
                json={"map_id": "gt_cleanup_map_002"},
            )

            self.assertEqual(200, promotion_response.status_code)
            self.assertFalse(candidate_dir.exists())
            self.assertEqual(404, read_after_promotion_response.status_code)
            self.assertEqual(404, promote_again_response.status_code)
            self.assertTrue(
                (
                    workspace_root
                    / "benchmark"
                    / "domains"
                    / "classical_supervised_ml_algorithms"
                    / "maps"
                    / "gt_cleanup_map_001"
                    / "map.json"
                ).exists()
            )

    def test_authoring_api_revalidates_candidate_map_before_promotion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            client = _test_client(workspace_root, FixtureCandidateMapModelClient())
            create_response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_invalid_promotion_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)
            candidate_path = (
                workspace_root
                / create_response.json()["artifact_paths"]["candidate_map_uri"]
            )
            candidate_map = _load_json(candidate_path)
            candidate_map["states"][0]["evidence_refs"] = candidate_map["states"][0]["evidence_refs"][:1]
            _write_json(candidate_path, candidate_map)

            response = client.post(
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_invalid_promotion_run_001/promotion",
                json={"map_id": "gt_invalid_map_001"},
            )

            self.assertEqual(422, response.status_code)
            self.assertIn(
                "requires at least 2 simulator-only evidence records",
                response.json()["detail"],
            )
            self.assertFalse(
                (
                    workspace_root
                    / "benchmark"
                    / "domains"
                    / "classical_supervised_ml_algorithms"
                    / "maps"
                    / "gt_invalid_map_001"
                ).exists()
            )

    def test_authoring_api_promotes_candidate_map_without_reading_consistency_warnings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            client = _test_client(workspace_root, EdgeInconsistentCandidateMapModelClient())
            create_response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_warning_promotion_run_001",
                },
            )
            self.assertEqual(200, create_response.status_code)
            candidate_dir = (
                workspace_root
                / create_response.json()["artifact_paths"]["output_dir_uri"]
            )
            warnings_path = (
                workspace_root
                / create_response.json()["artifact_paths"]["consistency_warnings_uri"]
            )
            warnings_path.write_text("not json", encoding="utf-8")

            response = client.post(
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_warning_promotion_run_001/promotion",
                json={"map_id": "gt_warning_map_001"},
            )

            self.assertEqual(200, response.status_code)
            published_dir = workspace_root / response.json()["artifact_paths"]["output_dir_uri"]
            self.assertEqual(
                {"map.json", "map_manifest.json"},
                {path.name for path in published_dir.iterdir()},
            )
            self.assertFalse(candidate_dir.exists())

    def test_authoring_api_allows_multiple_reviewed_map_samples_for_one_user_basis(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            first_client = _test_client(workspace_root, FixtureCandidateMapModelClient())
            first_create_response = first_client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_sample_run_001",
                },
            )
            self.assertEqual(200, first_create_response.status_code)
            first_promotion_response = first_client.post(
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_sample_run_001/promotion",
                json={"map_id": "gt_sample_map_001"},
            )
            self.assertEqual(200, first_promotion_response.status_code)
            second_client = _test_client(workspace_root, FixtureCandidateMapModelClient())
            second_create_response = second_client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_sample_run_002",
                },
            )
            self.assertEqual(200, second_create_response.status_code)

            second_promotion_response = second_client.post(
                "/api/authoring/candidate-maps/"
                "classical_supervised_ml_algorithms/map_sample_run_002/promotion",
                json={"map_id": "gt_sample_map_002"},
            )

            self.assertEqual(200, second_promotion_response.status_code)
            first_manifest = first_promotion_response.json()["map_manifest"]
            second_manifest = second_promotion_response.json()["map_manifest"]
            self.assertEqual("synthetic_user_001", first_manifest["user_id"])
            self.assertEqual("synthetic_user_001", second_manifest["user_id"])
            self.assertEqual("v1", first_manifest["graph_version"])
            self.assertEqual("v1", second_manifest["graph_version"])
            self.assertEqual("map_sample_run_001", first_manifest["promoted_from_candidate_run"])
            self.assertEqual("map_sample_run_002", second_manifest["promoted_from_candidate_run"])
            self.assertTrue(
                (
                    workspace_root
                    / "benchmark"
                    / "domains"
                    / "classical_supervised_ml_algorithms"
                    / "maps"
                    / "gt_sample_map_001"
                    / "map.json"
                ).exists()
            )
            self.assertTrue(
                (
                    workspace_root
                    / "benchmark"
                    / "domains"
                    / "classical_supervised_ml_algorithms"
                    / "maps"
                    / "gt_sample_map_002"
                    / "map.json"
                ).exists()
            )

    def test_authoring_api_generates_evidence_in_contiguous_reviewed_node_batches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            nodes_path = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "graphs"
                / "v1"
                / "authored_nodes.json"
            )
            nodes = _load_json(nodes_path)
            nodes.extend(
                _knowledge_node(f"extra_node_{index}", f"Extra Node {index}")
                for index in range(1, 5)
            )
            _write_json(nodes_path, nodes)
            _write_confirmed_profile_context(workspace_root)
            fake_model_client = MultiBatchCandidateMapModelClient()
            client = _test_client(workspace_root, fake_model_client)

            response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_multi_batch_run_001",
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            candidate_map = payload["candidate_map"]
            expected_node_ids = [
                "train_test_split",
                "cross_validation",
                "extra_node_1",
                "extra_node_2",
                "extra_node_3",
                "extra_node_4",
            ]
            self.assertEqual(
                expected_node_ids,
                [state["node_id"] for state in candidate_map["states"]],
            )
            self.assertEqual(
                expected_node_ids,
                [evidence["node_id"] for evidence in candidate_map["evidence"]],
            )
            self.assertEqual(
                [
                    "ev_map_multi_batch_run_001_train_test_split_001",
                    "ev_map_multi_batch_run_001_cross_validation_001",
                    "ev_map_multi_batch_run_001_extra_node_1_001",
                    "ev_map_multi_batch_run_001_extra_node_2_001",
                    "ev_map_multi_batch_run_001_extra_node_3_001",
                    "ev_map_multi_batch_run_001_extra_node_4_001",
                ],
                [evidence["id"] for evidence in candidate_map["evidence"]],
            )
            self.assertEqual(3, len(fake_model_client.calls))
            self.assertEqual(
                ["batch_001", "batch_002"],
                [
                    batch["batch_name"]
                    for batch in payload["artifact_paths"]["evidence_batch_artifacts"]
                ],
            )
            first_batch_prompt = _render_messages(fake_model_client.calls[1])
            second_batch_prompt = _render_messages(fake_model_client.calls[2])
            self.assertIn("extra_node_3", first_batch_prompt)
            self.assertNotIn("extra_node_4", first_batch_prompt)
            self.assertIn("extra_node_4", second_batch_prompt)
            self.assertNotIn("train_test_split", second_batch_prompt)
            output_dir = workspace_root / payload["artifact_paths"]["output_dir_uri"]
            self.assertEqual(
                {"batch_001", "batch_002"},
                {
                    path.name
                    for path in (
                        output_dir / "agent_traces" / "ground_truth_evidence"
                    ).iterdir()
                },
            )
            self.assertEqual(
                expected_node_ids,
                [
                    evidence["node_id"]
                    for evidence in _load_json(
                        output_dir / "intermediate" / "ground_truth_evidence.json"
                    )["evidence"]
                ],
            )

    def test_authoring_api_rejects_incomplete_outline_before_evidence_authoring_and_retains_debug_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            fake_model_client = MissingNodeOutlineCandidateMapModelClient()
            client = _test_client(workspace_root, fake_model_client)

            response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_missing_outline_run_001",
                },
            )

            self.assertEqual(422, response.status_code)
            self.assertIn("missing node ids", response.json()["detail"])
            self.assertEqual(1, len(fake_model_client.calls))
            output_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "candidate_maps"
                / "map_missing_outline_run_001"
            )
            self.assertFalse((output_dir / "candidate_map.json").exists())
            self.assertTrue((output_dir / "workflow_log.json").exists())
            self.assertTrue((output_dir / "intermediate" / "state_outline.json").exists())
            self.assertTrue(
                (
                    output_dir
                    / "agent_traces"
                    / "knowledge_state_outline"
                    / "model_raw_output.txt"
                ).exists()
            )
            self.assertEqual("failed", _load_json(output_dir / "workflow_log.json")["status"])

    def test_authoring_api_rejects_evidence_below_mastery_sensitive_minimum_and_retains_debug_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            fake_model_client = InsufficientEvidenceCandidateMapModelClient()
            client = _test_client(workspace_root, fake_model_client)

            response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_insufficient_evidence_run_001",
                },
            )

            self.assertEqual(422, response.status_code)
            self.assertIn("requires at least 2 simulator-only records", response.json()["detail"])
            self.assertEqual(2, len(fake_model_client.calls))
            output_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "candidate_maps"
                / "map_insufficient_evidence_run_001"
            )
            self.assertFalse((output_dir / "candidate_map.json").exists())
            self.assertTrue(
                (output_dir / "intermediate" / "ground_truth_evidence.json").exists()
            )
            self.assertTrue(
                (
                    output_dir
                    / "agent_traces"
                    / "ground_truth_evidence"
                    / "batch_001"
                    / "parser_output.json"
                ).exists()
            )
            self.assertEqual("failed", _load_json(output_dir / "workflow_log.json")["status"])

    def test_authoring_api_fails_fast_on_invalid_evidence_batch_and_retains_debug_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            nodes_path = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "graphs"
                / "v1"
                / "authored_nodes.json"
            )
            nodes = _load_json(nodes_path)
            nodes.extend(
                _knowledge_node(f"extra_node_{index}", f"Extra Node {index}")
                for index in range(1, 10)
            )
            _write_json(nodes_path, nodes)
            fake_model_client = FailingSecondBatchCandidateMapModelClient()
            client = _test_client(workspace_root, fake_model_client)

            response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_failed_second_batch_run_001",
                },
            )

            self.assertEqual(422, response.status_code)
            self.assertIn("nodes outside the batch", response.json()["detail"])
            self.assertEqual(3, len(fake_model_client.calls))
            output_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "candidate_maps"
                / "map_failed_second_batch_run_001"
            )
            self.assertFalse((output_dir / "candidate_map.json").exists())
            self.assertEqual(
                {"batch_001", "batch_002"},
                {
                    path.name
                    for path in (
                        output_dir / "agent_traces" / "ground_truth_evidence"
                    ).iterdir()
                },
            )
            self.assertTrue(
                (output_dir / "intermediate" / "ground_truth_evidence.json").exists()
            )
            self.assertEqual("failed", _load_json(output_dir / "workflow_log.json")["status"])

    def test_authoring_api_applies_request_level_batch_size_and_shared_sampling_temperature(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            nodes_path = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "graphs"
                / "v1"
                / "authored_nodes.json"
            )
            nodes = _load_json(nodes_path)
            nodes.extend(
                _knowledge_node(f"extra_node_{index}", f"Extra Node {index}")
                for index in range(1, 5)
            )
            _write_json(nodes_path, nodes)
            _write_confirmed_profile_context(workspace_root)
            fake_model_client = TemperatureRecordingCandidateMapModelClient()
            client = _test_client(workspace_root, fake_model_client)

            response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_tuned_run_001",
                    "evidence_batch_size": 2,
                    "sampling_temperature": 0.85,
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual([0.85, 0.85, 0.85, 0.85], fake_model_client.temperatures)
            output_dir = workspace_root / payload["artifact_paths"]["output_dir_uri"]
            self.assertEqual(
                {"batch_001", "batch_002", "batch_003"},
                {
                    path.name
                    for path in (
                        output_dir / "agent_traces" / "ground_truth_evidence"
                    ).iterdir()
                },
            )
            workflow_log = _load_json(output_dir / "workflow_log.json")
            self.assertEqual(2, workflow_log["evidence_batch_size"])
            self.assertEqual(0.85, workflow_log["sampling_temperature"])

    def test_authoring_api_rejects_non_positive_evidence_batch_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            fake_model_client = FixtureCandidateMapModelClient()
            client = _test_client(workspace_root, fake_model_client)

            response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "evidence_batch_size": 0,
                },
            )

            self.assertEqual(422, response.status_code)
            self.assertEqual([], fake_model_client.calls)

    def test_authoring_api_rejects_model_client_that_cannot_apply_sampling_temperature(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            client = _test_client(
                workspace_root,
                UnsupportedTemperatureCandidateMapModelClient(),
            )

            response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_unsupported_temperature_run_001",
                },
            )

            self.assertEqual(502, response.status_code)
            self.assertIn(
                "does not support sampling_temperature",
                response.json()["detail"],
            )

    def test_authoring_api_writes_non_blocking_prerequisite_edge_consistency_warnings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            fake_model_client = EdgeInconsistentCandidateMapModelClient()
            client = _test_client(workspace_root, fake_model_client)

            response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_warning_run_001",
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            output_dir = workspace_root / payload["artifact_paths"]["output_dir_uri"]
            self.assertEqual(
                {
                    "warnings": [
                        {
                            "edge_id": "edge_train_test_split_prerequisite_for_cross_validation",
                            "source_node_id": "train_test_split",
                            "source_mastery_level": "L1",
                            "target_node_id": "cross_validation",
                            "target_mastery_level": "L3",
                            "rule": "prerequisite_target_mastery_exceeds_source_by_at_least_two_levels",
                        }
                    ]
                },
                _load_json(output_dir / "consistency_warnings.json"),
            )

    def test_authoring_api_rejects_inline_graph_or_profile_context_payloads(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            fake_model_client = FixtureCandidateMapModelClient()
            client = _test_client(workspace_root, fake_model_client)

            response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "graph_nodes": [{"id": "train_test_split"}],
                    "edges": [],
                    "profile_context": {"summary": "Inline payload must not be accepted."},
                },
            )

            self.assertEqual(422, response.status_code)
            self.assertEqual([], fake_model_client.calls)
            self.assertEqual(
                {"edges", "graph_nodes", "profile_context"},
                {
                    item["loc"][-1]
                    for item in response.json()["detail"]
                    if item["type"] == "extra_forbidden"
                },
            )

    def test_authoring_api_rejects_evidence_for_nodes_outside_the_single_batch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            fake_model_client = OutsideBatchEvidenceCandidateMapModelClient()
            client = _test_client(workspace_root, fake_model_client)

            response = client.post(
                "/api/authoring/map-candidates",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "user_id": "synthetic_user_001",
                    "run_id": "map_outside_batch_evidence_run_001",
                },
            )

            self.assertEqual(422, response.status_code)
            self.assertIn("nodes outside the batch", response.json()["detail"])
            output_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "candidate_maps"
                / "map_outside_batch_evidence_run_001"
            )
            self.assertFalse((output_dir / "candidate_map.json").exists())
            self.assertEqual("failed", _load_json(output_dir / "workflow_log.json")["status"])

    def test_authoring_api_rejects_reusing_candidate_map_run_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            _write_confirmed_profile_context(workspace_root)
            run_request = {
                "benchmark_domain": "classical_supervised_ml_algorithms",
                "graph_version": "v1",
                "user_id": "synthetic_user_001",
                "run_id": "map_unique_run_001",
            }
            first_client = _test_client(workspace_root, FixtureCandidateMapModelClient())
            first_response = first_client.post("/api/authoring/map-candidates", json=run_request)
            self.assertEqual(200, first_response.status_code)
            candidate_path = (
                workspace_root / first_response.json()["artifact_paths"]["candidate_map_uri"]
            )
            original_candidate = _load_json(candidate_path)
            second_model_client = InsufficientEvidenceCandidateMapModelClient()
            second_client = _test_client(workspace_root, second_model_client)

            response = second_client.post("/api/authoring/map-candidates", json=run_request)

            self.assertEqual(409, response.status_code)
            self.assertEqual([], second_model_client.calls)
            self.assertEqual(original_candidate, _load_json(candidate_path))


class FixtureCandidateMapModelClient:
    def __init__(self):
        self.calls = []
        self.message_profile = OPENAI_MESSAGE_PROFILE
        self.metadata = ModelClientMetadata(
            provider="openai",
            model_name="fixture-map-model",
            message_profile=OPENAI_MESSAGE_PROFILE.name,
        )

    def complete(self, *, messages, temperature=None):
        del temperature
        self.calls.append(messages)
        if len(self.calls) == 1:
            return json.dumps(
                {
                    "states": [
                        {
                            "node_id": "cross_validation",
                            "mastery_level": "L1",
                            "misconceptions": [],
                            "unknowns": ["How folds rotate validation data."],
                        },
                        {
                            "node_id": "train_test_split",
                            "mastery_level": "L2",
                            "misconceptions": ["Assumes the held-out set tunes the model."],
                            "unknowns": [],
                        },
                    ]
                }
            )
        return json.dumps(
            {
                "evidence": [
                    {
                        "node_id": "cross_validation",
                        "evidence_kind": "self_report",
                        "signal": "Has heard of cross-validation but cannot describe fold rotation.",
                    },
                    {
                        "node_id": "train_test_split",
                        "evidence_kind": "misconception_trace",
                        "signal": "Uses the held-out set while selecting model settings.",
                    },
                    {
                        "node_id": "train_test_split",
                        "evidence_kind": "prior_answer",
                        "signal": "Can explain why a final held-out evaluation is useful.",
                    },
                ]
            }
        )


class MissingNodeOutlineCandidateMapModelClient(FixtureCandidateMapModelClient):
    def complete(self, *, messages, temperature=None):
        raw_output = super().complete(messages=messages, temperature=temperature)
        if len(self.calls) == 1:
            payload = json.loads(raw_output)
            payload["states"] = payload["states"][:1]
            return json.dumps(payload)
        return raw_output


class InsufficientEvidenceCandidateMapModelClient(FixtureCandidateMapModelClient):
    def complete(self, *, messages, temperature=None):
        raw_output = super().complete(messages=messages, temperature=temperature)
        if len(self.calls) == 2:
            payload = json.loads(raw_output)
            payload["evidence"] = [
                evidence
                for evidence in payload["evidence"]
                if evidence["signal"] != "Can explain why a final held-out evaluation is useful."
            ]
            return json.dumps(payload)
        return raw_output


class OutsideBatchEvidenceCandidateMapModelClient(FixtureCandidateMapModelClient):
    def complete(self, *, messages, temperature=None):
        raw_output = super().complete(messages=messages, temperature=temperature)
        if len(self.calls) == 2:
            payload = json.loads(raw_output)
            payload["evidence"].append(
                {
                    "node_id": "outside_batch_node",
                    "evidence_kind": "self_report",
                    "signal": "This node is not part of the supplied evidence batch.",
                }
            )
            return json.dumps(payload)
        return raw_output


class MultiBatchCandidateMapModelClient(FixtureCandidateMapModelClient):
    def complete(self, *, messages, temperature=None):
        del temperature
        self.calls.append(messages)
        prompt_payload = json.loads(messages[-1].content)
        if len(self.calls) == 1:
            return json.dumps(
                {
                    "states": [
                        {
                            "node_id": node["id"],
                            "mastery_level": "L1",
                            "misconceptions": [],
                            "unknowns": [],
                        }
                        for node in prompt_payload["reviewed_nodes_with_rubrics"]
                    ]
                }
            )
        return json.dumps(
            {
                "evidence": [
                    {
                        "node_id": node["id"],
                        "evidence_kind": "self_report",
                        "signal": f"Signal for {node['id']}.",
                    }
                    for node in reversed(prompt_payload["batch_nodes_with_rubrics"])
                ]
            }
        )


class FailingSecondBatchCandidateMapModelClient(MultiBatchCandidateMapModelClient):
    def complete(self, *, messages, temperature=None):
        raw_output = super().complete(messages=messages, temperature=temperature)
        if len(self.calls) == 3:
            payload = json.loads(raw_output)
            payload["evidence"].append(
                {
                    "node_id": "outside_batch_node",
                    "evidence_kind": "self_report",
                    "signal": "This node is not part of the supplied evidence batch.",
                }
            )
            return json.dumps(payload)
        return raw_output


class TemperatureRecordingCandidateMapModelClient(MultiBatchCandidateMapModelClient):
    def __init__(self):
        super().__init__()
        self.temperatures = []

    def complete(self, *, messages, temperature=None):
        self.temperatures.append(temperature)
        return super().complete(messages=messages)


class UnsupportedTemperatureCandidateMapModelClient(FixtureCandidateMapModelClient):
    def complete(self, *, messages):
        return super().complete(messages=messages)


class EdgeInconsistentCandidateMapModelClient(FixtureCandidateMapModelClient):
    def complete(self, *, messages, temperature=None):
        raw_output = super().complete(messages=messages, temperature=temperature)
        payload = json.loads(raw_output)
        if len(self.calls) == 1:
            for state in payload["states"]:
                state["mastery_level"] = (
                    "L1" if state["node_id"] == "train_test_split" else "L3"
                )
            return json.dumps(payload)
        payload["evidence"].append(
            {
                "node_id": "cross_validation",
                "evidence_kind": "prior_answer",
                "signal": "Can discuss fold rotation but not why repeats reduce variance.",
            }
        )
        return json.dumps(payload)


def _write_reviewed_graph(workspace_root: Path) -> None:
    graph_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "graphs"
        / "v1"
    )
    graph_dir.mkdir(parents=True)
    _write_json(
        graph_dir / "graph_manifest.json",
        {
            "graph_id": "kg_classical_supervised_ml_algorithms_v1",
            "domain": "classical_supervised_ml_algorithms",
            "version": "v1",
            "promoted_from_candidate_run": "graph_run_001",
            "nodes_file": "authored_nodes.json",
            "edges_file": "authored_edges.json",
        },
    )
    _write_json(
        graph_dir / "authored_nodes.json",
        [
            _knowledge_node("train_test_split", "Train/Test Split"),
            _knowledge_node("cross_validation", "Cross-Validation"),
        ],
    )
    _write_json(
        graph_dir / "authored_edges.json",
        [
            {
                "id": "edge_train_test_split_prerequisite_for_cross_validation",
                "source": "train_test_split",
                "target": "cross_validation",
                "type": "prerequisite_for",
                "rationale": "A held-out split motivates repeated validation splits.",
                "weight": 0.7,
                "curation_confidence": 0.8,
            }
        ],
    )


def _test_client(workspace_root: Path, model_client: FixtureCandidateMapModelClient) -> TestClient:
    return TestClient(
        create_app(
            candidate_map_authoring_workflow_factory=lambda client_provider, root: (
                build_candidate_map_authoring_workflow(
                    workspace_root=root,
                    model_client=model_client,
                )
            ),
            workspace_root=workspace_root,
        )
    )


def _write_confirmed_profile_context(workspace_root: Path) -> None:
    profile_path = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "users"
        / "synthetic_user_001"
        / "profile_context.json"
    )
    profile_path.parent.mkdir(parents=True)
    _write_json(
        profile_path,
        {
            "user_id": "synthetic_user_001",
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "summary": "A practical beginner with limited statistical foundations.",
            "background": ["Has followed introductory sklearn examples."],
            "prior_experience": ["Can run basic estimator workflows."],
            "goals": ["Understand model evaluation."],
            "preferences": ["Prefers concrete examples."],
        },
    )


def _write_failed_candidate_map_run(workspace_root: Path) -> None:
    run_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "candidate_maps"
        / "failed_map_run"
    )
    run_dir.mkdir(parents=True)
    artifact_root = (
        "benchmark/domains/classical_supervised_ml_algorithms/"
        "candidate_maps/failed_map_run"
    )
    _write_json(
        run_dir / "workflow_log.json",
        {
            "run_id": "failed_map_run",
            "workflow_name": "Candidate Knowledge Map Authoring Workflow",
            "status": "failed",
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "graph_version": "v1",
            "user_id": "synthetic_user_001",
            "evidence_batch_size": 5,
            "sampling_temperature": 0.7,
            "error": "second batch failed",
            "artifact_paths": {
                "output_dir_uri": artifact_root,
                "candidate_map_uri": f"{artifact_root}/candidate_map.json",
                "consistency_warnings_uri": f"{artifact_root}/consistency_warnings.json",
                "workflow_log_uri": f"{artifact_root}/workflow_log.json",
                "state_outline_uri": f"{artifact_root}/intermediate/state_outline.json",
                "ground_truth_evidence_uri": f"{artifact_root}/intermediate/ground_truth_evidence.json",
                "outline_model_raw_output_uri": (
                    f"{artifact_root}/agent_traces/knowledge_state_outline/model_raw_output.txt"
                ),
                "outline_parser_output_uri": (
                    f"{artifact_root}/agent_traces/knowledge_state_outline/parser_output.json"
                ),
                "evidence_model_raw_output_uri": (
                    f"{artifact_root}/agent_traces/ground_truth_evidence/batch_001/model_raw_output.txt"
                ),
                "evidence_parser_output_uri": (
                    f"{artifact_root}/agent_traces/ground_truth_evidence/batch_001/parser_output.json"
                ),
                "evidence_batch_artifacts": [],
            },
        },
    )


def _confirmed_profile_context() -> ConfirmedProfileContext:
    return ConfirmedProfileContext(
        user_id="synthetic_user_001",
        benchmark_domain="classical_supervised_ml_algorithms",
        summary="A practical beginner with limited statistical foundations.",
        background=("Has followed introductory sklearn examples.",),
        prior_experience=("Can run basic estimator workflows.",),
        goals=("Understand model evaluation.",),
        preferences=("Prefers concrete examples.",),
    )


def _knowledge_node(node_id: str, name: str) -> dict[str, object]:
    return {
        "id": node_id,
        "name": name,
        "type": "concept",
        "definition": f"Definition for {name}.",
        "source_locators": [{"source_id": "isl_python", "locator": "chapter 5"}],
        "diagnostic_goal": f"Diagnose understanding of {name}.",
        "levels": {f"L{index}": f"L{index} rubric for {name}." for index in range(6)},
        "diagnostic_signals": [f"Can discuss {name}."],
        "simulator_behavior": f"Answer consistently about {name}.",
    }


def _write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _render_messages(messages) -> str:
    return "\n\n".join(message.content for message in messages)


if __name__ == "__main__":
    unittest.main()
