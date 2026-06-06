import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.core.evidence import EvidenceRecord
from backend.knowact.core.graph import KnowledgeNode
from backend.knowact.core.interaction import VisibleObservationKind
from backend.knowact.core.map import UserKnowledgeState
from backend.knowact.simulator.context_builder import (
    GroundedSimulatorNodeContext,
    SimulatorTurnContext,
)
from backend.knowact.simulator.expression import SimulatorExpressionContextBuilder
from backend.knowact.simulator.generators import RuleBasedAnswerGenerator
from backend.knowact.simulator.policy import RuleBasedAnswerPolicy, SimulatorAnswerStance
from backend.knowact.simulator.preview import (
    SimulatorPreviewRequest,
    SimulatorPreviewWarningCode,
)
from backend.knowact.simulator.service import SimulatorService


class V1SimulatorServiceTest(unittest.TestCase):
    def test_service_answers_clear_question_from_reviewed_map_manifest_bindings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(workspace_root=workspace_root)
            request = SimulatorPreviewRequest.model_validate(
                {
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "text": "How would you decide whether a train/test split is appropriate?"
                    },
                }
            )

            response = service.answer_preview(request)

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertEqual((), response.warnings)
            self.assertIn("train/test split", response.answer.text.lower())
            self.assertIn("held-out", response.answer.text.lower())
            self.assertNotIn("L4", response.answer.text)
            self.assertNotIn("ev_gt_map_001_train_test_split_001", response.answer.text)
            self.assertNotIn("synthetic_user_001", response.answer.text)

    def test_preview_api_answers_reviewed_map_request_without_episode_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "gt_map_001",
                    "question": {
                        "text": "How would you decide whether a train/test split is appropriate?"
                    },
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("answer", payload["observation"]["kind"])
            self.assertEqual([], payload["warnings"])
            self.assertIn("held-out", payload["answer"]["text"].lower())
            self.assertNotIn("map_manifest", payload)
            self.assertNotIn("graph_version", payload)
            self.assertNotIn("user_id", payload)

    def test_service_continues_with_non_leaking_warning_when_profile_context_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=False)
            service = SimulatorService(workspace_root=workspace_root)

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": "How would you decide whether a train/test split is appropriate?"
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("held-out", response.answer.text.lower())
            self.assertEqual(1, len(response.warnings))
            self.assertEqual(
                SimulatorPreviewWarningCode.MISSING_PROFILE_CONTEXT,
                response.warnings[0].code,
            )
            self.assertNotIn("synthetic_user_001", response.warnings[0].message)
            self.assertNotIn("gt_map_001", response.warnings[0].message)

    def test_service_does_not_pull_neighbor_state_or_evidence_from_graph_edges(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(workspace_root=workspace_root)

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {
                            "text": "How would you decide whether a train/test split is appropriate?"
                        },
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.ANSWER, response.observation.kind)
            self.assertIn("train/test split", response.answer.text.lower())
            self.assertNotIn("validation fold", response.answer.text.lower())
            self.assertNotIn("separate final test set", response.answer.text.lower())
            self.assertNotIn("cross-validation", response.answer.text.lower())

    def test_question_grounding_ignores_hidden_map_state_and_evidence_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_simulator_fixture(workspace_root, include_profile_context=True)
            service = SimulatorService(workspace_root=workspace_root)

            response = service.answer_preview(
                SimulatorPreviewRequest.model_validate(
                    {
                        "benchmark_domain": "classical_supervised_ml_algorithms",
                        "map_id": "gt_map_001",
                        "question": {"text": "How do folds rotate validation data?"},
                    }
                )
            )

            self.assertEqual(VisibleObservationKind.NON_ANSWER, response.observation.kind)
            self.assertNotIn("fold", response.answer.text.lower())
            self.assertNotIn("validation", response.answer.text.lower())

    def test_preview_api_does_not_load_candidate_map_runs_as_simulator_inputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            candidate_dir = (
                workspace_root
                / "benchmark"
                / "domains"
                / "classical_supervised_ml_algorithms"
                / "candidate_maps"
                / "candidate_only"
            )
            candidate_dir.mkdir(parents=True)
            _write_json(candidate_dir / "candidate_map.json", {"states": []})
            client = TestClient(create_app(workspace_root=workspace_root))

            response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "map_id": "candidate_only",
                    "question": {"text": "How would you use a train/test split?"},
                },
            )

            self.assertEqual(404, response.status_code)
            self.assertIn("Reviewed map candidate_only does not exist", response.json()["detail"])

    def test_policy_expression_and_generator_do_not_expose_raw_hidden_state(self):
        simulator_context = SimulatorTurnContext(
            benchmark_domain="classical_supervised_ml_algorithms",
            map_id="gt_map_001",
            graph_version="v1",
            user_id="synthetic_user_001",
            grounded_nodes=(
                GroundedSimulatorNodeContext(
                    node=KnowledgeNode.model_validate(
                        _knowledge_node("train_test_split", "Train/Test Split")
                    ),
                    state=UserKnowledgeState.model_validate(
                        {
                            "node_id": "train_test_split",
                            "mastery_level": "L2",
                            "evidence_refs": ["ev_hidden_partial"],
                            "misconceptions": [],
                            "unknowns": ["When a separate validation set is needed."],
                        }
                    ),
                    simulator_only_evidence=(
                        EvidenceRecord.model_validate(
                            {
                                "id": "ev_hidden_partial",
                                "node_id": "train_test_split",
                                "evidence_type": "ground_truth_profile",
                                "evidence_kind": "prior_answer",
                                "visibility": "simulator_only",
                                "signal": "Can explain the held-out split idea but mixes up validation and final testing.",
                                "turn_id": None,
                            }
                        ),
                    ),
                ),
            ),
            visible_dialogue_context=None,
        )

        intent = RuleBasedAnswerPolicy().derive_intent(
            question_text="How would you use a train/test split?",
            simulator_context=simulator_context,
        )
        expression_context = SimulatorExpressionContextBuilder().build(
            intent=intent,
            simulator_context=simulator_context,
        )
        answer = RuleBasedAnswerGenerator().render(expression_context)

        self.assertEqual(SimulatorAnswerStance.PARTIAL_UNDERSTANDING, intent.primary_stance)
        self.assertIn("ev_hidden_partial", intent.hidden_evidence_refs)
        expression_payload = expression_context.model_dump_json()
        for hidden_fragment in (
            "ev_hidden_partial",
            "L2",
            "mastery_level",
            "evidence_refs",
            "synthetic_user_001",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, expression_payload)
                self.assertNotIn(hidden_fragment, answer.text)
        self.assertIn("partial", answer.text.lower())
        self.assertIn("held-out split", answer.text)

    def test_rule_based_answer_path_expresses_core_fixture_stances(self):
        cases = (
            ("L4", (), (), "correct_understanding", "can explain"),
            ("L2", (), ("When a separate validation set is needed.",), "partial_understanding", "partial"),
            ("L1", (), ("How folds rotate validation data.",), "uncertain_understanding", "not fully sure"),
            ("L0", (), (), "not_knowing", "do not really know"),
            (
                "L1",
                ("Treats each fold as a separate final test set.",),
                (),
                "misconception",
                "tend to think",
            ),
        )
        policy = RuleBasedAnswerPolicy()
        expression_builder = SimulatorExpressionContextBuilder()
        generator = RuleBasedAnswerGenerator()

        for mastery_level, misconceptions, unknowns, stance, answer_fragment in cases:
            with self.subTest(stance=stance):
                simulator_context = _simulator_context_for_state(
                    mastery_level=mastery_level,
                    misconceptions=misconceptions,
                    unknowns=unknowns,
                )

                intent = policy.derive_intent(
                    question_text="How would you use a train/test split?",
                    simulator_context=simulator_context,
                )
                answer = generator.render(
                    expression_builder.build(
                        intent=intent,
                        simulator_context=simulator_context,
                    )
                )

                self.assertEqual(stance, intent.primary_stance)
                self.assertIn(answer_fragment, answer.text.lower())


def _write_reviewed_simulator_fixture(
    workspace_root: Path,
    *,
    include_profile_context: bool,
) -> None:
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

    map_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "maps"
        / "gt_map_001"
    )
    map_dir.mkdir(parents=True)
    _write_json(
        map_dir / "map_manifest.json",
        {
            "map_id": "gt_map_001",
            "user_id": "synthetic_user_001",
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "graph_version": "v1",
            "promoted_from_candidate_run": "map_run_001",
        },
    )
    _write_json(
        map_dir / "map.json",
        {
            "user_id": "synthetic_user_001",
            "kind": "ground_truth",
            "states": [
                {
                    "node_id": "train_test_split",
                    "mastery_level": "L4",
                    "evidence_refs": ["ev_gt_map_001_train_test_split_001"],
                    "misconceptions": [],
                    "unknowns": [],
                },
                {
                    "node_id": "cross_validation",
                    "mastery_level": "L1",
                    "evidence_refs": ["ev_gt_map_001_cross_validation_001"],
                    "misconceptions": ["Treats each fold as a separate final test set."],
                    "unknowns": ["How folds rotate validation data."],
                },
            ],
            "evidence": [
                {
                    "id": "ev_gt_map_001_train_test_split_001",
                    "node_id": "train_test_split",
                    "evidence_type": "ground_truth_profile",
                    "evidence_kind": "prior_answer",
                    "visibility": "simulator_only",
                    "signal": "Can explain why a final held-out evaluation is useful.",
                    "turn_id": None,
                },
                {
                    "id": "ev_gt_map_001_cross_validation_001",
                    "node_id": "cross_validation",
                    "evidence_type": "ground_truth_profile",
                    "evidence_kind": "misconception_trace",
                    "visibility": "simulator_only",
                    "signal": "Calls each validation fold a final test set.",
                    "turn_id": None,
                },
            ],
        },
    )

    if include_profile_context:
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


def _simulator_context_for_state(
    *,
    mastery_level: str,
    misconceptions: tuple[str, ...],
    unknowns: tuple[str, ...],
) -> SimulatorTurnContext:
    return SimulatorTurnContext(
        benchmark_domain="classical_supervised_ml_algorithms",
        map_id="gt_map_001",
        graph_version="v1",
        user_id="synthetic_user_001",
        grounded_nodes=(
            GroundedSimulatorNodeContext(
                node=KnowledgeNode.model_validate(
                    _knowledge_node("train_test_split", "Train/Test Split")
                ),
                state=UserKnowledgeState.model_validate(
                    {
                        "node_id": "train_test_split",
                        "mastery_level": mastery_level,
                        "evidence_refs": ["ev_hidden_state"],
                        "misconceptions": misconceptions,
                        "unknowns": unknowns,
                    }
                ),
                simulator_only_evidence=(
                    EvidenceRecord.model_validate(
                        {
                            "id": "ev_hidden_state",
                            "node_id": "train_test_split",
                            "evidence_type": "ground_truth_profile",
                            "evidence_kind": "prior_answer",
                            "visibility": "simulator_only",
                            "signal": "Can explain the held-out split idea.",
                            "turn_id": None,
                        }
                    ),
                ),
            ),
        ),
        visible_dialogue_context=None,
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


if __name__ == "__main__":
    unittest.main()
