import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.core.interaction import VisibleObservationKind
from backend.knowact.simulator.service import SimulatorService
from backend.knowact.simulator.turn import SimulatorTurnRequest


BENCHMARK_DOMAIN = "classical_supervised_ml_algorithms"
GRAPH_VERSION = "grounded_ambiguity_v1"
MAP_ID = "grounded_ambiguity_map"
USER_ID = "synthetic_grounded_ambiguity_user"


class V1SimulatorGroundedAmbiguityRegressionTest(unittest.TestCase):
    def test_direct_grounding_answers_follow_reviewed_state_and_simulator_only_evidence(self):
        cases = (
            {
                "node_id": "train_test_split",
                "question": "How would you use a train/test split for model evaluation?",
                "kind": VisibleObservationKind.ANSWER,
                "expected_fragments": ("can explain", "final held-out evaluation"),
            },
            {
                "node_id": "bias_variance_tradeoff",
                "question": "How do you reason about the bias-variance tradeoff?",
                "kind": VisibleObservationKind.ANSWER,
                "expected_fragments": ("partial", "learning curve", "regularization changes"),
            },
            {
                "node_id": "regularization",
                "question": "How does regularization affect a fitted model?",
                "kind": VisibleObservationKind.ANSWER,
                "expected_fragments": ("partial", "corrects themself", "penalties"),
            },
            {
                "node_id": "cross_validation",
                "question": "How do cross-validation folds work?",
                "kind": VisibleObservationKind.ANSWER,
                "expected_fragments": ("not fully sure", "folds rotate validation data"),
            },
            {
                "node_id": "decision_tree_overfitting",
                "question": "How would you control decision tree overfitting?",
                "kind": VisibleObservationKind.ANSWER,
                "expected_fragments": ("do not really know", "decision tree overfitting"),
            },
            {
                "node_id": "feature_scaling",
                "question": "What does feature scaling change?",
                "kind": VisibleObservationKind.ANSWER,
                "expected_fragments": ("tend to think", "ranking importance"),
            },
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_grounded_ambiguity_fixture(workspace_root)
            service = SimulatorService(workspace_root=workspace_root)

            for case in cases:
                with self.subTest(node_id=case["node_id"]):
                    response = service.answer_turn(
                        SimulatorTurnRequest.model_validate(
                            {
                                "benchmark_domain": BENCHMARK_DOMAIN,
                                "map_id": MAP_ID,
                                "question": {
                                    "question_id": f"q_{case['node_id']}",
                                    "text": case["question"],
                                },
                            }
                        )
                    )

                    self.assertEqual(case["kind"], response.observation.kind)
                    answer_text = response.answer.text.lower()
                    for fragment in case["expected_fragments"]:
                        self.assertIn(fragment, answer_text)
                    _assert_visible_response_has_no_hidden_artifacts(
                        self,
                        response.model_dump(mode="json"),
                    )

    def test_repeated_grounded_answer_is_deterministic_without_state_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_grounded_ambiguity_fixture(workspace_root)
            service = SimulatorService(workspace_root=workspace_root)
            request = SimulatorTurnRequest.model_validate(
                {
                    "benchmark_domain": BENCHMARK_DOMAIN,
                    "map_id": MAP_ID,
                    "question": {
                        "text": "How does regularization affect a fitted model?"
                    },
                }
            )

            first_response = service.answer_turn(request)
            second_response = service.answer_turn(request)

            self.assertEqual(first_response.answer.text, second_response.answer.text)
            self.assertIn("partial", first_response.answer.text.lower())
            self.assertIn("corrects themself", first_response.answer.text.lower())

    def test_visible_dialogue_supports_follow_up_grounding_without_mutating_static_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_grounded_ambiguity_fixture(workspace_root)
            service = SimulatorService(workspace_root=workspace_root)

            direct_response = service.answer_turn(
                SimulatorTurnRequest.model_validate(
                    {
                        "benchmark_domain": BENCHMARK_DOMAIN,
                        "map_id": MAP_ID,
                        "question": {
                            "text": "How does regularization affect a fitted model?"
                        },
                    }
                )
            )
            follow_up_response = service.answer_turn(
                SimulatorTurnRequest.model_validate(
                    {
                        "benchmark_domain": BENCHMARK_DOMAIN,
                        "map_id": MAP_ID,
                        "question": {
                            "question_id": "q_followup_regularization",
                            "text": "Can you say that again?",
                        },
                        "visible_dialogue_context": {
                            "turns": [
                                {
                                    "turn_id": "visible_turn_001",
                                    "question": {
                                        "text": "How does regularization affect a fitted model?"
                                    },
                                    "answer": {
                                        "text": "I fully understand regularization now."
                                    },
                                    "observation": {"kind": "answer"},
                                }
                            ]
                        },
                    }
                )
            )

            self.assertEqual(direct_response.answer.text, follow_up_response.answer.text)
            self.assertIn("partial", follow_up_response.answer.text.lower())
            self.assertNotIn("fully understand", follow_up_response.answer.text.lower())
            trace_payload = _read_json(
                workspace_root
                / "benchmark"
                / "domains"
                / BENCHMARK_DOMAIN
                / "simulator"
                / MAP_ID
                / "q_followup_regularization"
                / "debug_trace.json"
            )
            grounded_node = trace_payload["workflow"]["simulator_context"][
                "grounded_nodes"
            ][0]
            self.assertEqual("regularization", grounded_node["node_id"])
            self.assertEqual("L2", grounded_node["mastery_level"])
            self.assertEqual(
                ["ev_grounded_ambiguity_regularization_self_correction"],
                grounded_node["evidence_refs"],
            )

    def test_turn_test_response_exposes_only_grounded_node_ids_beyond_visible_answer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_grounded_ambiguity_fixture(workspace_root)
            client = _simulator_client(workspace_root)

            response = client.post(
                "/api/simulator/turn-test",
                json={
                    "benchmark_domain": BENCHMARK_DOMAIN,
                    "map_id": MAP_ID,
                    "question": {
                        "text": "How do you reason about the bias-variance tradeoff?"
                    },
                },
            )

            self.assertEqual(200, response.status_code)
            payload = response.json()
            self.assertEqual("answer", payload["observation"]["kind"])
            self.assertEqual(["bias_variance_tradeoff"], payload["grounded_node_ids"])
            self.assertIn("partial", payload["answer"]["text"].lower())
            _assert_visible_response_has_no_hidden_artifacts(self, payload)

    def test_preview_no_grounding_and_multi_question_are_visible_non_content_answers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_grounded_ambiguity_fixture(workspace_root, include_map_artifact=False)
            client = _simulator_client(workspace_root)

            no_grounding_response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": BENCHMARK_DOMAIN,
                    "map_id": MAP_ID,
                    "question": {"text": "What should I study next?"},
                },
            )
            multi_question_response = client.post(
                "/api/simulator/preview",
                json={
                    "benchmark_domain": BENCHMARK_DOMAIN,
                    "map_id": MAP_ID,
                    "question": {
                        "text": (
                            "How would you use a train/test split? "
                            "How do cross-validation folds work?"
                        )
                    },
                },
            )

            self.assertEqual(200, no_grounding_response.status_code)
            no_grounding_payload = no_grounding_response.json()
            self.assertEqual("non_answer", no_grounding_payload["observation"]["kind"])
            self.assertIn("which concept", no_grounding_payload["answer"]["text"].lower())
            _assert_visible_response_has_no_hidden_artifacts(self, no_grounding_payload)

            self.assertEqual(200, multi_question_response.status_code)
            multi_question_payload = multi_question_response.json()
            self.assertEqual("clarification", multi_question_payload["observation"]["kind"])
            self.assertIn(
                "one specific question",
                multi_question_payload["answer"]["text"].lower(),
            )
            _assert_visible_response_has_no_hidden_artifacts(self, multi_question_payload)


def _simulator_client(workspace_root: Path) -> TestClient:
    return TestClient(
        create_app(
            workspace_root=workspace_root,
            simulator_service_factory=lambda _provider, root: SimulatorService(
                workspace_root=root
            ),
        )
    )


def _write_grounded_ambiguity_fixture(
    workspace_root: Path,
    *,
    include_map_artifact: bool = True,
) -> None:
    graph_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / BENCHMARK_DOMAIN
        / "graphs"
        / GRAPH_VERSION
    )
    graph_dir.mkdir(parents=True)
    _write_json(
        graph_dir / "graph_manifest.json",
        {
            "graph_id": f"kg_{BENCHMARK_DOMAIN}_{GRAPH_VERSION}",
            "domain": BENCHMARK_DOMAIN,
            "version": GRAPH_VERSION,
            "promoted_from_candidate_run": "grounded_ambiguity_graph_run",
            "nodes_file": "authored_nodes.json",
            "edges_file": "authored_edges.json",
        },
    )
    _write_json(
        graph_dir / "authored_nodes.json",
        [
            _knowledge_node("train_test_split", "Train/Test Split"),
            _knowledge_node("bias_variance_tradeoff", "Bias-Variance Tradeoff"),
            _knowledge_node("regularization", "Regularization"),
            _knowledge_node("cross_validation", "Cross-Validation"),
            _knowledge_node("decision_tree_overfitting", "Decision Tree Overfitting"),
            _knowledge_node("feature_scaling", "Feature Scaling"),
        ],
    )
    _write_json(
        graph_dir / "authored_edges.json",
        [
            {
                "id": "edge_train_test_split_supports_cross_validation",
                "source": "train_test_split",
                "target": "cross_validation",
                "type": "supports",
                "rationale": "A single held-out split motivates repeated validation splits.",
                "weight": 0.5,
                "curation_confidence": 0.8,
            }
        ],
    )

    map_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / BENCHMARK_DOMAIN
        / "maps"
        / MAP_ID
    )
    map_dir.mkdir(parents=True)
    _write_json(
        map_dir / "map_manifest.json",
        {
            "map_id": MAP_ID,
            "user_id": USER_ID,
            "benchmark_domain": BENCHMARK_DOMAIN,
            "graph_version": GRAPH_VERSION,
            "promoted_from_candidate_run": "grounded_ambiguity_map_run",
        },
    )
    if include_map_artifact:
        _write_json(
            map_dir / "map.json",
            {
                "user_id": USER_ID,
                "kind": "ground_truth",
                "states": [
                    _state(
                        "train_test_split",
                        "L4",
                        ("ev_grounded_ambiguity_train_test_split_prior_answer",),
                    ),
                    _state(
                        "bias_variance_tradeoff",
                        "L3",
                        (
                            "ev_grounded_ambiguity_bias_variance_worked_example",
                            "ev_grounded_ambiguity_bias_variance_self_report",
                        ),
                        unknowns=(
                            "Where regularization changes the tradeoff.",
                        ),
                    ),
                    _state(
                        "regularization",
                        "L2",
                        ("ev_grounded_ambiguity_regularization_self_correction",),
                        unknowns=("How to tune penalty strength without overclaiming.",),
                    ),
                    _state(
                        "cross_validation",
                        "L1",
                        ("ev_grounded_ambiguity_cross_validation_self_report",),
                        unknowns=("How folds rotate validation data.",),
                    ),
                    _state(
                        "decision_tree_overfitting",
                        "L0",
                        ("ev_grounded_ambiguity_tree_background",),
                    ),
                    _state(
                        "feature_scaling",
                        "L1",
                        ("ev_grounded_ambiguity_feature_scaling_misconception",),
                        misconceptions=(
                            "Scaling a feature changes its ranking importance for every model.",
                        ),
                    ),
                ],
                "evidence": [
                    _evidence(
                        "ev_grounded_ambiguity_train_test_split_prior_answer",
                        "train_test_split",
                        "prior_answer",
                        "Can explain train/test split as a final held-out evaluation.",
                    ),
                    _evidence(
                        "ev_grounded_ambiguity_bias_variance_worked_example",
                        "bias_variance_tradeoff",
                        "worked_example",
                        "Can read a learning curve and explain high variance as overfitting.",
                    ),
                    _evidence(
                        "ev_grounded_ambiguity_bias_variance_self_report",
                        "bias_variance_tradeoff",
                        "self_report",
                        "Says the bias side is less intuitive than the variance side.",
                    ),
                    _evidence(
                        "ev_grounded_ambiguity_regularization_self_correction",
                        "regularization",
                        "prior_answer",
                        (
                            "Starts by saying penalties only lower variance, then "
                            "corrects themself that stronger penalties can add bias."
                        ),
                    ),
                    _evidence(
                        "ev_grounded_ambiguity_cross_validation_self_report",
                        "cross_validation",
                        "self_report",
                        "Recognizes that folds reuse data but cannot explain rotation.",
                    ),
                    _evidence(
                        "ev_grounded_ambiguity_tree_background",
                        "decision_tree_overfitting",
                        "background_fact",
                        "Has not worked with tree depth or leaf constraints.",
                    ),
                    _evidence(
                        "ev_grounded_ambiguity_feature_scaling_misconception",
                        "feature_scaling",
                        "misconception_trace",
                        "Claims scaling changes every model's notion of feature importance.",
                    ),
                ],
            },
        )

    profile_path = (
        workspace_root
        / "benchmark"
        / "domains"
        / BENCHMARK_DOMAIN
        / "users"
        / USER_ID
        / "profile_context.json"
    )
    profile_path.parent.mkdir(parents=True)
    _write_json(
        profile_path,
        {
            "user_id": USER_ID,
            "benchmark_domain": BENCHMARK_DOMAIN,
            "summary": "Development-only simulator regression persona.",
            "background": ["Has completed a short introductory ML notebook."],
            "prior_experience": ["Can run simple sklearn examples."],
            "goals": ["Diagnose model evaluation and regularization understanding."],
            "preferences": ["Prefers concrete wording."],
        },
    )


def _knowledge_node(node_id: str, name: str) -> dict[str, object]:
    return {
        "id": node_id,
        "name": name,
        "type": "concept",
        "definition": f"Development regression node for {name}.",
        "source_locators": [{"source_id": "simulator_regression", "locator": "test"}],
        "diagnostic_goal": f"Diagnose understanding of {name}.",
        "levels": {
            f"L{index}": f"Level {index} rubric for {name}."
            for index in range(6)
        },
        "diagnostic_signals": [f"Can discuss {name}."],
        "simulator_behavior": f"Answer consistently about {name}.",
    }


def _state(
    node_id: str,
    mastery_level: str,
    evidence_refs: tuple[str, ...],
    *,
    misconceptions: tuple[str, ...] = (),
    unknowns: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "node_id": node_id,
        "mastery_level": mastery_level,
        "evidence_refs": list(evidence_refs),
        "misconceptions": list(misconceptions),
        "unknowns": list(unknowns),
    }


def _evidence(
    evidence_id: str,
    node_id: str,
    evidence_kind: str,
    signal: str,
) -> dict[str, object]:
    return {
        "id": evidence_id,
        "node_id": node_id,
        "evidence_type": "ground_truth_profile",
        "evidence_kind": evidence_kind,
        "visibility": "simulator_only",
        "signal": signal,
        "turn_id": None,
    }


def _assert_visible_response_has_no_hidden_artifacts(
    test_case: unittest.TestCase,
    payload: object,
) -> None:
    serialized = json.dumps(payload, sort_keys=True).lower()
    hidden_fragments = (
        "mastery_level",
        "evidence_refs",
        "states",
        "map_manifest",
        "raw_debug_trace",
        "debug_trace_payload",
        "model_raw_output",
        "ground_truth",
        "simulator_only",
        "synthetic_grounded_ambiguity_user",
        "ev_grounded_ambiguity",
        "l0",
        "l1",
        "l2",
        "l3",
        "l4",
        "l5",
    )
    for fragment in hidden_fragments:
        with test_case.subTest(hidden_fragment=fragment):
            test_case.assertNotIn(fragment, serialized)


def _write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    unittest.main()
