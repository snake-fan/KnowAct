from backend.knowact.core.map import MasteryLevel


MISSING_PREDICTION_DISTANCE = 36.0

_MASTERY_SCORES: dict[MasteryLevel, int] = {
    MasteryLevel.L0: 0,
    MasteryLevel.L1: 1,
    MasteryLevel.L2: 2,
    MasteryLevel.L3: 3,
    MasteryLevel.L4: 4,
    MasteryLevel.L5: 5,
}


def mastery_score(mastery_level: MasteryLevel | str) -> int:
    return _MASTERY_SCORES[MasteryLevel(mastery_level)]


def squared_mastery_distance(
    *,
    predicted_mastery: MasteryLevel | str,
    ground_truth_mastery: MasteryLevel | str,
) -> float:
    error = signed_mastery_error(
        predicted_mastery=predicted_mastery,
        ground_truth_mastery=ground_truth_mastery,
    )
    return float(error * error)


def signed_mastery_error(
    *,
    predicted_mastery: MasteryLevel | str,
    ground_truth_mastery: MasteryLevel | str,
) -> int:
    return mastery_score(predicted_mastery) - mastery_score(ground_truth_mastery)
