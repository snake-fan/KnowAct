from backend.knowact.core.episode import EvaluationEpisodeManifest
from backend.knowact.validation.exceptions import KnowActValidationError


def validate_episode_manifest(manifest: EvaluationEpisodeManifest) -> None:
    if manifest.scoring_overrides:
        raise KnowActValidationError("Evaluation episode manifests must not define per-episode scoring overrides")
