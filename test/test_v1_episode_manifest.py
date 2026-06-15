import unittest

from pydantic import ValidationError

from backend.knowact.core.episode import EvaluationEpisodeManifest
from backend.knowact.validation.episode import validate_episode_manifest
from backend.knowact.validation.exceptions import KnowActValidationError


class V1EpisodeManifestTest(unittest.TestCase):
    def test_manifest_uses_identity_first_reviewed_episode_binding(self):
        manifest = EvaluationEpisodeManifest(
            episode_id="dev_episode_001",
            benchmark_domain="classical_supervised_ml_algorithms",
            graph_version="v1",
            hidden_map_id="dev_map_001",
            max_turns=3,
            interaction_rule="single_diagnostic_question_per_turn",
            scoring_profile="squared_mastery_distance_v1",
        )

        validate_episode_manifest(manifest)
        self.assertEqual("v1", manifest.graph_version)
        self.assertEqual("dev_map_001", manifest.hidden_map_id)

    def test_manifest_rejects_per_episode_scoring_overrides(self):
        manifest = EvaluationEpisodeManifest(
            episode_id="dev_episode_001",
            benchmark_domain="classical_supervised_ml_algorithms",
            graph_version="v1",
            hidden_map_id="dev_map_001",
            max_turns=3,
            interaction_rule="single_diagnostic_question_per_turn",
            scoring_profile="squared_mastery_distance_v1",
            scoring_overrides={"missing_prediction_penalty": 9},
        )

        with self.assertRaisesRegex(KnowActValidationError, "scoring overrides"):
            validate_episode_manifest(manifest)

    def test_manifest_rejects_blank_required_identities(self):
        required_identity_fields = [
            "episode_id",
            "benchmark_domain",
            "graph_version",
            "hidden_map_id",
        ]

        for field_name in required_identity_fields:
            with self.subTest(field_name=field_name):
                payload = {
                    "episode_id": "dev_episode_001",
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "hidden_map_id": "dev_map_001",
                    "max_turns": 3,
                    "interaction_rule": "single_diagnostic_question_per_turn",
                    "scoring_profile": "squared_mastery_distance_v1",
                }
                payload[field_name] = " "

                with self.assertRaises(ValidationError):
                    EvaluationEpisodeManifest.model_validate(payload)

    def test_manifest_rejects_missing_required_identities(self):
        required_identity_fields = [
            "episode_id",
            "benchmark_domain",
            "graph_version",
            "hidden_map_id",
        ]

        for field_name in required_identity_fields:
            with self.subTest(field_name=field_name):
                payload = {
                    "episode_id": "dev_episode_001",
                    "benchmark_domain": "classical_supervised_ml_algorithms",
                    "graph_version": "v1",
                    "hidden_map_id": "dev_map_001",
                    "max_turns": 3,
                    "interaction_rule": "single_diagnostic_question_per_turn",
                    "scoring_profile": "squared_mastery_distance_v1",
                }
                del payload[field_name]

                with self.assertRaises(ValidationError):
                    EvaluationEpisodeManifest.model_validate(payload)

    def test_manifest_rejects_invalid_rule_and_scoring_profile(self):
        base_payload = {
            "episode_id": "dev_episode_001",
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "graph_version": "v1",
            "hidden_map_id": "dev_map_001",
            "max_turns": 3,
            "interaction_rule": "single_diagnostic_question_per_turn",
            "scoring_profile": "squared_mastery_distance_v1",
        }

        for field_name, invalid_value in [
            ("interaction_rule", "open_conversation"),
            ("scoring_profile", "custom_weighted_profile"),
        ]:
            with self.subTest(field_name=field_name):
                payload = dict(base_payload)
                payload[field_name] = invalid_value

                with self.assertRaises(ValidationError):
                    EvaluationEpisodeManifest.model_validate(payload)

    def test_manifest_does_not_duplicate_profile_context_identity(self):
        base_payload = {
            "episode_id": "dev_episode_001",
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "graph_version": "v1",
            "hidden_map_id": "dev_map_001",
            "max_turns": 3,
            "interaction_rule": "single_diagnostic_question_per_turn",
            "scoring_profile": "squared_mastery_distance_v1",
        }

        for field_name, invalid_value in [
            ("user_id", "dev_user_001"),
            ("profile_context_id", "profile_context_dev_user_001"),
            ("profile_context", {"user_id": "dev_user_001"}),
        ]:
            with self.subTest(field_name=field_name):
                payload = dict(base_payload)
                payload[field_name] = invalid_value

                with self.assertRaises(ValidationError):
                    EvaluationEpisodeManifest.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
