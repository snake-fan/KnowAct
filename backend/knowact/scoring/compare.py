from backend.knowact.core.episode import SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.map import KnowledgeMap, KnowledgeMapKind, MasteryLevel
from backend.knowact.core.scoring import (
    EpisodeScoreReport,
    FinalReconstructionSubmission,
    NodeComparison,
    SubmittedMasteryLevel,
)
from backend.knowact.scoring.distance import (
    MISSING_PREDICTION_DISTANCE,
    signed_mastery_error,
    squared_mastery_distance,
)
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.graph import validate_knowledge_graph
from backend.knowact.validation.map import validate_knowledge_map
from backend.knowact.validation.scoring import validate_final_reconstruction_submission


def score_final_reconstruction(
    *,
    graph: KnowledgeGraph,
    ground_truth_map: KnowledgeMap,
    submission: FinalReconstructionSubmission,
    scoring_profile: str = SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
) -> EpisodeScoreReport:
    if scoring_profile != SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1:
        raise KnowActValidationError(
            f"Unsupported scoring profile: {scoring_profile}"
        )
    if not graph.nodes:
        raise KnowActValidationError("Cannot score an empty episode graph")

    validate_knowledge_graph(graph)
    if ground_truth_map.kind != KnowledgeMapKind.GROUND_TRUTH:
        raise KnowActValidationError(
            "Scoring requires a ground-truth reviewed map"
        )
    validate_knowledge_map(ground_truth_map, graph)
    validate_final_reconstruction_submission(submission, graph)

    ground_truth_by_node_id = ground_truth_map.state_by_node_id
    predictions_by_node_id = submission.prediction_by_node_id
    per_node = tuple(
        _compare_node(
            node_id=node.id,
            ground_truth_mastery=ground_truth_by_node_id[node.id].mastery_level,
            submitted_mastery=predictions_by_node_id[node.id].predicted_mastery,
            has_support=bool(predictions_by_node_id[node.id].evidence_refs),
        )
        for node in graph.nodes
    )
    node_count = len(per_node)
    return EpisodeScoreReport(
        episode_id=submission.episode_id,
        scoring_profile=SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
        per_node=per_node,
        episode_mastery_distance=sum(
            node.mastery_distance for node in per_node
        )
        / node_count,
        missing_prediction_rate=sum(
            1 for node in per_node if node.missing_prediction
        )
        / node_count,
        unsupported_inference_rate=sum(
            1 for node in per_node if node.unsupported_inference
        )
        / node_count,
        exact_match_rate=sum(1 for node in per_node if node.exact_match)
        / node_count,
    )


def _compare_node(
    *,
    node_id: str,
    ground_truth_mastery: MasteryLevel,
    submitted_mastery: SubmittedMasteryLevel,
    has_support: bool,
) -> NodeComparison:
    if submitted_mastery == SubmittedMasteryLevel.UNKNOWN:
        return NodeComparison(
            node_id=node_id,
            ground_truth_mastery=ground_truth_mastery,
            predicted_mastery=None,
            mastery_distance=MISSING_PREDICTION_DISTANCE,
            signed_mastery_error=None,
            missing_prediction=True,
            unsupported_inference=False,
            exact_match=False,
        )

    predicted_mastery = submitted_mastery.to_mastery_level()
    signed_error = signed_mastery_error(
        predicted_mastery=predicted_mastery,
        ground_truth_mastery=ground_truth_mastery,
    )
    return NodeComparison(
        node_id=node_id,
        ground_truth_mastery=ground_truth_mastery,
        predicted_mastery=predicted_mastery,
        mastery_distance=squared_mastery_distance(
            predicted_mastery=predicted_mastery,
            ground_truth_mastery=ground_truth_mastery,
        ),
        signed_mastery_error=signed_error,
        missing_prediction=False,
        unsupported_inference=not has_support,
        exact_match=signed_error == 0,
    )
