import unittest

from backend.knowact.core.episode import ArtifactRef, EvaluationEpisodeManifest
from backend.knowact.validation.episode import validate_episode_manifest
from backend.knowact.validation.exceptions import KnowActValidationError


class V1EpisodeManifestTest(unittest.TestCase):
    def test_manifest_rejects_per_episode_scoring_overrides(self):
        manifest = EvaluationEpisodeManifest(
            episode_id="dev_episode_001",
            benchmark_domain="classical_supervised_ml_algorithms",
            graph=ArtifactRef(
                id="dev_graph_v1",
                uri="benchmark/fixtures/dev_graph/authored_graph.json",
                review_status="reviewed",
            ),
            hidden_map=ArtifactRef(
                id="dev_map_001",
                uri="benchmark/fixtures/dev_graph/map.json",
                review_status="reviewed",
            ),
            max_turns=3,
            interaction_rule="single_diagnostic_question_per_turn",
            scoring_profile="squared_mastery_distance_v1",
            scoring_overrides={"missing_prediction_penalty": 9},
        )

        with self.assertRaisesRegex(KnowActValidationError, "scoring overrides"):
            validate_episode_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
