from collections.abc import Hashable
from typing import TypeVar

from backend.knowact.core.evidence import EvidenceType, EvidenceVisibility
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.scoring import FinalReconstructionSubmission
from backend.knowact.validation.exceptions import KnowActValidationError


def validate_final_reconstruction_submission(
    submission: FinalReconstructionSubmission,
    graph: KnowledgeGraph,
) -> None:
    graph_node_ids = graph.node_ids
    prediction_node_ids = [
        prediction.node_id for prediction in submission.predictions
    ]
    duplicate_prediction_nodes = _duplicates(prediction_node_ids)
    if duplicate_prediction_nodes:
        raise KnowActValidationError(
            "Final reconstruction submission contains duplicate node predictions: "
            f"{sorted(duplicate_prediction_nodes)}"
        )

    unknown_prediction_nodes = set(prediction_node_ids) - graph_node_ids
    if unknown_prediction_nodes:
        raise KnowActValidationError(
            "Final reconstruction submission references unknown nodes: "
            f"{sorted(unknown_prediction_nodes)}"
        )

    missing_prediction_nodes = graph_node_ids - set(prediction_node_ids)
    if missing_prediction_nodes:
        raise KnowActValidationError(
            "Final reconstruction submission is missing graph nodes: "
            f"{sorted(missing_prediction_nodes)}"
        )

    evidence_ids = [evidence.id for evidence in submission.evidence]
    duplicate_evidence_ids = _duplicates(evidence_ids)
    if duplicate_evidence_ids:
        raise KnowActValidationError(
            "Final reconstruction submission contains duplicate evidence ids: "
            f"{sorted(duplicate_evidence_ids)}"
        )

    evidence_by_id = {evidence.id: evidence for evidence in submission.evidence}
    unknown_evidence_nodes = {
        evidence.node_id for evidence in submission.evidence
    } - graph_node_ids
    if unknown_evidence_nodes:
        raise KnowActValidationError(
            "Final reconstruction submission evidence references unknown nodes: "
            f"{sorted(unknown_evidence_nodes)}"
        )

    for evidence in submission.evidence:
        if evidence.evidence_type != EvidenceType.INTERACTION_OBSERVATION:
            raise KnowActValidationError(
                f"Final reconstruction evidence {evidence.id} must have "
                "evidence type interaction_observation"
            )
        if evidence.visibility != EvidenceVisibility.TESTED_AGENT:
            raise KnowActValidationError(
                f"Final reconstruction evidence {evidence.id} must use "
                "tested_agent visibility"
            )

    for prediction in submission.predictions:
        for evidence_ref in prediction.evidence_refs:
            if evidence_ref not in evidence_by_id:
                raise KnowActValidationError(
                    f"Prediction for node {prediction.node_id} references "
                    f"unknown evidence {evidence_ref}"
                )
            if evidence_by_id[evidence_ref].node_id != prediction.node_id:
                raise KnowActValidationError(
                    f"Prediction for node {prediction.node_id} references "
                    f"evidence {evidence_ref} for node "
                    f"{evidence_by_id[evidence_ref].node_id}"
                )


_DuplicateValue = TypeVar("_DuplicateValue", bound=Hashable)


def _duplicates(values: list[_DuplicateValue]) -> set[_DuplicateValue]:
    seen: set[_DuplicateValue] = set()
    duplicates: set[_DuplicateValue] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
