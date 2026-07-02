import unittest

from backend.knowact.core.evidence import EvidenceRecord
from backend.knowact.core.graph import KnowledgeGraph, KnowledgeNode
from backend.knowact.core.map import KnowledgeMap, UserKnowledgeState
from backend.knowact.core.scoring import (
    FinalReconstructionPrediction,
    FinalReconstructionSubmission,
)
from backend.knowact.scoring import (
    MISSING_PREDICTION_DISTANCE,
    score_final_reconstruction,
    signed_mastery_error,
    squared_mastery_distance,
)
from backend.knowact.validation.exceptions import KnowActValidationError


class V1ScoringTest(unittest.TestCase):
    def test_score_final_reconstruction_reports_mastery_gap_and_supporting_metrics(self):
        report = score_final_reconstruction(
            graph=_graph(),
            ground_truth_map=_ground_truth_map(),
            submission=FinalReconstructionSubmission(
                episode_id="episode_a",
                benchmark_domain="classical_supervised_ml_algorithms",
                graph_version="v1",
                reconstructed_user_id="reconstructed_episode_a",
                predictions=(
                    FinalReconstructionPrediction(
                        node_id="train_test_split",
                        predicted_mastery="L2",
                        evidence_refs=("ev_train_test_split_turn_01",),
                    ),
                    FinalReconstructionPrediction(
                        node_id="linear_regression",
                        predicted_mastery="L2",
                    ),
                    FinalReconstructionPrediction(
                        node_id="logistic_regression",
                        predicted_mastery="unknown",
                    ),
                ),
                evidence=(
                    EvidenceRecord(
                        id="ev_train_test_split_turn_01",
                        node_id="train_test_split",
                        evidence_type="interaction_observation",
                        evidence_kind="prior_answer",
                        visibility="tested_agent",
                        signal="The user explained the held-out test set.",
                        turn_id="turn_01",
                    ),
                ),
            ),
        )

        self.assertEqual("episode_a", report.episode_id)
        self.assertEqual("squared_mastery_distance_v1", report.scoring_profile)
        self.assertEqual(
            ("train_test_split", "linear_regression", "logistic_regression"),
            tuple(node.node_id for node in report.per_node),
        )

        train_test_split = report.per_node[0]
        self.assertEqual("L2", train_test_split.ground_truth_mastery)
        self.assertEqual("L2", train_test_split.predicted_mastery)
        self.assertEqual(0.0, train_test_split.mastery_distance)
        self.assertEqual(0, train_test_split.signed_mastery_error)
        self.assertFalse(train_test_split.missing_prediction)
        self.assertFalse(train_test_split.unsupported_inference)
        self.assertTrue(train_test_split.exact_match)

        linear_regression = report.per_node[1]
        self.assertEqual("L4", linear_regression.ground_truth_mastery)
        self.assertEqual("L2", linear_regression.predicted_mastery)
        self.assertEqual(4.0, linear_regression.mastery_distance)
        self.assertEqual(-2, linear_regression.signed_mastery_error)
        self.assertFalse(linear_regression.missing_prediction)
        self.assertTrue(linear_regression.unsupported_inference)
        self.assertFalse(linear_regression.exact_match)

        logistic_regression = report.per_node[2]
        self.assertEqual("L1", logistic_regression.ground_truth_mastery)
        self.assertIsNone(logistic_regression.predicted_mastery)
        self.assertEqual(
            MISSING_PREDICTION_DISTANCE,
            logistic_regression.mastery_distance,
        )
        self.assertIsNone(logistic_regression.signed_mastery_error)
        self.assertTrue(logistic_regression.missing_prediction)
        self.assertFalse(logistic_regression.unsupported_inference)
        self.assertFalse(logistic_regression.exact_match)

        self.assertAlmostEqual((0.0 + 4.0 + 36.0) / 3, report.episode_mastery_distance)
        self.assertAlmostEqual(1 / 3, report.missing_prediction_rate)
        self.assertAlmostEqual(1 / 3, report.unsupported_inference_rate)
        self.assertAlmostEqual(1 / 3, report.exact_match_rate)

    def test_score_final_reconstruction_rejects_submission_node_set_mismatch(self):
        with self.assertRaisesRegex(
            KnowActValidationError,
            "missing graph nodes",
        ):
            score_final_reconstruction(
                graph=_graph(),
                ground_truth_map=_ground_truth_map(),
                submission=FinalReconstructionSubmission(
                    episode_id="episode_a",
                    benchmark_domain="classical_supervised_ml_algorithms",
                    graph_version="v1",
                    reconstructed_user_id="reconstructed_episode_a",
                    predictions=(
                        FinalReconstructionPrediction(
                            node_id="train_test_split",
                            predicted_mastery="L2",
                        ),
                    ),
                ),
            )

    def test_score_final_reconstruction_rejects_unknown_evidence_reference(self):
        with self.assertRaisesRegex(
            KnowActValidationError,
            "unknown evidence",
        ):
            score_final_reconstruction(
                graph=_graph(),
                ground_truth_map=_ground_truth_map(),
                submission=FinalReconstructionSubmission(
                    episode_id="episode_a",
                    benchmark_domain="classical_supervised_ml_algorithms",
                    graph_version="v1",
                    reconstructed_user_id="reconstructed_episode_a",
                    predictions=(
                        FinalReconstructionPrediction(
                            node_id="train_test_split",
                            predicted_mastery="L2",
                            evidence_refs=("ev_missing",),
                        ),
                        FinalReconstructionPrediction(
                            node_id="linear_regression",
                            predicted_mastery="unknown",
                        ),
                        FinalReconstructionPrediction(
                            node_id="logistic_regression",
                            predicted_mastery="unknown",
                        ),
                    ),
                ),
            )

    def test_mastery_distance_uses_squared_error(self):
        self.assertEqual(
            -3,
            signed_mastery_error(
                predicted_mastery="L1",
                ground_truth_mastery="L4",
            ),
        )
        self.assertEqual(
            9.0,
            squared_mastery_distance(
                predicted_mastery="L1",
                ground_truth_mastery="L4",
            ),
        )


def _graph() -> KnowledgeGraph:
    return KnowledgeGraph(
        nodes=(
            KnowledgeNode(
                id="train_test_split",
                name="Train/Test Split",
                type="concept",
            ),
            KnowledgeNode(
                id="linear_regression",
                name="Linear Regression",
                type="concept",
            ),
            KnowledgeNode(
                id="logistic_regression",
                name="Logistic Regression",
                type="concept",
            ),
        )
    )


def _ground_truth_map() -> KnowledgeMap:
    return KnowledgeMap(
        user_id="synthetic_user_001",
        kind="ground_truth",
        states=(
            UserKnowledgeState(
                node_id="train_test_split",
                mastery_level="L2",
                evidence_refs=("ev_train_test_split_gt",),
                misconceptions=(),
                unknowns=(),
            ),
            UserKnowledgeState(
                node_id="linear_regression",
                mastery_level="L4",
                evidence_refs=("ev_linear_regression_gt",),
                misconceptions=(),
                unknowns=(),
            ),
            UserKnowledgeState(
                node_id="logistic_regression",
                mastery_level="L1",
                evidence_refs=("ev_logistic_regression_gt",),
                misconceptions=(),
                unknowns=(),
            ),
        ),
        evidence=(
            EvidenceRecord(
                id="ev_train_test_split_gt",
                node_id="train_test_split",
                evidence_type="ground_truth_profile",
                evidence_kind="prior_answer",
                visibility="simulator_only",
                signal="Can explain held-out test data.",
            ),
            EvidenceRecord(
                id="ev_linear_regression_gt",
                node_id="linear_regression",
                evidence_type="ground_truth_profile",
                evidence_kind="worked_example",
                visibility="simulator_only",
                signal="Can work through a linear regression example.",
            ),
            EvidenceRecord(
                id="ev_logistic_regression_gt",
                node_id="logistic_regression",
                evidence_type="ground_truth_profile",
                evidence_kind="misconception_trace",
                visibility="simulator_only",
                signal="Confuses logits with probabilities.",
            ),
        ),
    )


if __name__ == "__main__":
    unittest.main()
