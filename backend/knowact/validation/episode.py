from backend.knowact.core.episode import ArtifactReviewStatus, EvaluationEpisodeManifest
from backend.knowact.validation.exceptions import KnowActValidationError


def validate_episode_manifest(manifest: EvaluationEpisodeManifest) -> None:
    if manifest.graph.review_status != ArtifactReviewStatus.REVIEWED:
        raise KnowActValidationError("Evaluation episode graph must reference reviewed authored graph data")

    if manifest.hidden_map.review_status != ArtifactReviewStatus.REVIEWED:
        raise KnowActValidationError("Evaluation episode hidden map must reference a reviewed ground-truth map")

    if manifest.scoring_overrides:
        raise KnowActValidationError("Evaluation episode manifests must not define per-episode scoring overrides")
