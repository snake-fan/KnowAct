import json

from pydantic import ValidationError

from backend.knowact.authoring.schemas import (
    GroundTruthEvidenceDraftList,
    KnowledgeStateOutlineList,
)


class CandidateMapOutputParseError(RuntimeError):
    """Raised when candidate-map model output cannot be parsed."""


def parse_knowledge_state_outline_output(raw_output: str) -> KnowledgeStateOutlineList:
    return _parse_output(
        raw_output,
        model=KnowledgeStateOutlineList,
        output_name="Knowledge-State Outline",
    )


def parse_ground_truth_evidence_output(raw_output: str) -> GroundTruthEvidenceDraftList:
    return _parse_output(
        raw_output,
        model=GroundTruthEvidenceDraftList,
        output_name="Ground-Truth Evidence",
    )


def _parse_output(raw_output: str, *, model, output_name: str):
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise CandidateMapOutputParseError(f"{output_name} output was not valid JSON: {exc}") from exc
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise CandidateMapOutputParseError(
            f"{output_name} output did not match {model.__name__}: {exc}"
        ) from exc
