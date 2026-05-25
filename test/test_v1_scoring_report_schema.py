import unittest

from backend.knowact.core.scoring import EpisodeScoreReport, NodeComparison


class V1ScoringReportSchemaTest(unittest.TestCase):
    def test_scoring_report_represents_missing_prediction_and_unsupported_inference_rates(self):
        report = EpisodeScoreReport(
            episode_id="dev_episode_001",
            scoring_profile="squared_mastery_distance_v1",
            per_node=[
                NodeComparison(
                    node_id="linear_regression",
                    ground_truth_mastery="L3",
                    predicted_mastery="L2",
                    mastery_distance=1.0,
                    missing_prediction=False,
                    unsupported_inference=True,
                ),
                NodeComparison(
                    node_id="train_test_split",
                    ground_truth_mastery="L2",
                    predicted_mastery=None,
                    mastery_distance=36.0,
                    missing_prediction=True,
                    unsupported_inference=False,
                ),
            ],
            episode_mastery_distance=18.5,
            missing_prediction_rate=0.5,
            unsupported_inference_rate=0.5,
        )

        self.assertEqual(report.scoring_profile, "squared_mastery_distance_v1")
        self.assertEqual(report.per_node[1].mastery_distance, 36.0)
        self.assertTrue(report.per_node[1].missing_prediction)


if __name__ == "__main__":
    unittest.main()
