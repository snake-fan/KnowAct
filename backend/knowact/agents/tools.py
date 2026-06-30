from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.agents.working_map import (
    AgentWorkingKnowledgeMap,
    AssessedMasteryLevel,
    DiagnosticConfidence,
    WorkingMapNodeAssessment,
)
from backend.knowact.core.evidence import (
    EvidenceKind,
    EvidenceRecord,
    EvidenceType,
    EvidenceVisibility,
)
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import VisibleDialogueContext, VisibleDialogueTurn
from backend.knowact.core.map import (
    KnowledgeMap,
    KnowledgeMapKind,
    UserKnowledgeState,
)
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.map import validate_knowledge_map


class WorkingMapNodeAssessmentUpdate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    assessed_mastery_level: AssessedMasteryLevel
    diagnostic_confidence: DiagnosticConfidence
    assessment_note: str | None = None
    supporting_turn_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("node_id")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("assessment_note")
    @classmethod
    def _optional_note_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("supporting_turn_ids")
    @classmethod
    def _supporting_turn_ids_must_be_nonblank_unique(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not turn_id.strip() for turn_id in value):
            raise ValueError("must not contain blank items")
        if len(value) != len(set(value)):
            raise ValueError("must not contain duplicate items")
        return value


class FinalizationWarningCode(StrEnum):
    MISSING_NOTE_DOWNGRADED = "missing_note_downgraded"
    MISSING_SUPPORT_DOWNGRADED = "missing_support_downgraded"
    INVALID_SUPPORT_DROPPED = "invalid_support_dropped"


class FinalizationWarning(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: FinalizationWarningCode
    node_id: str
    message: str

    @field_validator("node_id", "message")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class FinalizedReconstructedMap(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    knowledge_map: KnowledgeMap
    warnings: tuple[FinalizationWarning, ...] = Field(default_factory=tuple)


def validate_working_map(
    working_map: AgentWorkingKnowledgeMap,
    graph: KnowledgeGraph,
) -> None:
    graph_node_ids = graph.node_ids
    state_node_ids = [state.node_id for state in working_map.states]
    duplicate_state_node_ids = _duplicates(state_node_ids)
    if duplicate_state_node_ids:
        raise KnowActValidationError(
            "Agent working map contains duplicate node assessments: "
            f"{sorted(duplicate_state_node_ids)}"
        )

    unknown_state_node_ids = set(state_node_ids) - graph_node_ids
    if unknown_state_node_ids:
        raise KnowActValidationError(
            "Agent working map references unknown nodes: "
            f"{sorted(unknown_state_node_ids)}"
        )

    missing_state_node_ids = graph_node_ids - set(state_node_ids)
    if missing_state_node_ids:
        raise KnowActValidationError(
            "Agent working map is missing graph nodes: "
            f"{sorted(missing_state_node_ids)}"
        )


def update_node_assessments(
    *,
    working_map: AgentWorkingKnowledgeMap,
    graph: KnowledgeGraph,
    visible_dialogue_context: VisibleDialogueContext,
    updates: tuple[WorkingMapNodeAssessmentUpdate, ...],
) -> AgentWorkingKnowledgeMap:
    validate_working_map(working_map, graph)
    visible_turns_by_id = _visible_turns_by_id(visible_dialogue_context)
    _validate_update_batch(
        updates=updates,
        known_node_ids=graph.node_ids,
        visible_turn_ids=set(visible_turns_by_id),
    )

    updates_by_node_id = {update.node_id: update for update in updates}
    updated_states = tuple(
        _apply_update_to_state(state, updates_by_node_id[state.node_id])
        if state.node_id in updates_by_node_id
        else state
        for state in working_map.states
    )
    return working_map.model_copy(update={"states": updated_states})


def finalize_reconstructed_map(
    *,
    working_map: AgentWorkingKnowledgeMap,
    graph: KnowledgeGraph,
    visible_dialogue_context: VisibleDialogueContext,
    reconstructed_user_id: str | None = None,
) -> FinalizedReconstructedMap:
    validate_working_map(working_map, graph)
    visible_turns_by_id = _visible_turns_by_id(visible_dialogue_context)
    user_id = reconstructed_user_id or f"reconstructed_{working_map.episode_id}"

    states: list[UserKnowledgeState] = []
    evidence: list[EvidenceRecord] = []
    warnings: list[FinalizationWarning] = []
    evidence_ids: set[str] = set()

    for assessment in working_map.states:
        if assessment.assessed_mastery_level == AssessedMasteryLevel.UNKNOWN:
            continue

        if not assessment.assessment_note:
            warnings.append(
                FinalizationWarning(
                    code=FinalizationWarningCode.MISSING_NOTE_DOWNGRADED,
                    node_id=assessment.node_id,
                    message=(
                        "Working-map judgment was omitted because it has no "
                        "assessment note."
                    ),
                )
            )
            continue

        valid_turn_ids, invalid_turn_ids = _split_valid_supporting_turn_ids(
            assessment.supporting_turn_ids,
            visible_turns_by_id,
        )
        if invalid_turn_ids:
            warnings.append(
                FinalizationWarning(
                    code=FinalizationWarningCode.INVALID_SUPPORT_DROPPED,
                    node_id=assessment.node_id,
                    message=(
                        "Working-map judgment cited turns that are not visible: "
                        + ", ".join(invalid_turn_ids)
                    ),
                )
            )
        if not valid_turn_ids:
            warnings.append(
                FinalizationWarning(
                    code=FinalizationWarningCode.MISSING_SUPPORT_DOWNGRADED,
                    node_id=assessment.node_id,
                    message=(
                        "Working-map judgment was omitted because it has no "
                        "visible supporting turns."
                    ),
                )
            )
            continue

        state_evidence_ids: list[str] = []
        for turn_id in valid_turn_ids:
            evidence_id = _evidence_id(
                node_id=assessment.node_id,
                turn_id=turn_id,
            )
            if evidence_id in evidence_ids:
                continue
            evidence_ids.add(evidence_id)
            state_evidence_ids.append(evidence_id)
            evidence.append(
                EvidenceRecord(
                    id=evidence_id,
                    node_id=assessment.node_id,
                    evidence_type=EvidenceType.INTERACTION_OBSERVATION,
                    evidence_kind=EvidenceKind.PRIOR_ANSWER,
                    visibility=EvidenceVisibility.TESTED_AGENT,
                    signal=_turn_signal(visible_turns_by_id[turn_id]),
                    turn_id=turn_id,
                )
            )

        states.append(
            UserKnowledgeState(
                node_id=assessment.node_id,
                mastery_level=assessment.assessed_mastery_level.to_mastery_level(),
                evidence_refs=tuple(state_evidence_ids),
                misconceptions=(),
                unknowns=(),
            )
        )

    knowledge_map = KnowledgeMap(
        user_id=user_id,
        kind=KnowledgeMapKind.RECONSTRUCTED,
        states=tuple(states),
        evidence=tuple(evidence),
    )
    validate_knowledge_map(knowledge_map, graph)
    return FinalizedReconstructedMap(
        knowledge_map=knowledge_map,
        warnings=tuple(warnings),
    )


def _validate_update_batch(
    *,
    updates: tuple[WorkingMapNodeAssessmentUpdate, ...],
    known_node_ids: set[str],
    visible_turn_ids: set[str],
) -> None:
    update_node_ids = [update.node_id for update in updates]
    duplicate_update_node_ids = _duplicates(update_node_ids)
    if duplicate_update_node_ids:
        raise KnowActValidationError(
            "Working-map update batch contains duplicate nodes: "
            f"{sorted(duplicate_update_node_ids)}"
        )

    unknown_update_node_ids = set(update_node_ids) - known_node_ids
    if unknown_update_node_ids:
        raise KnowActValidationError(
            "Working-map update references unknown nodes: "
            f"{sorted(unknown_update_node_ids)}"
        )

    for update in updates:
        if update.assessed_mastery_level == AssessedMasteryLevel.UNKNOWN:
            continue

        if update.diagnostic_confidence == DiagnosticConfidence.UNKNOWN:
            raise KnowActValidationError(
                f"Assessment for node {update.node_id} must set diagnostic confidence"
            )
        if update.assessment_note is None:
            raise KnowActValidationError(
                f"Assessment for node {update.node_id} must include an assessment note"
            )
        if not update.supporting_turn_ids:
            raise KnowActValidationError(
                f"Assessment for node {update.node_id} must cite a visible turn"
            )
        unknown_turn_ids = set(update.supporting_turn_ids) - visible_turn_ids
        if unknown_turn_ids:
            raise KnowActValidationError(
                f"Assessment for node {update.node_id} cites unknown visible turns: "
                f"{sorted(unknown_turn_ids)}"
            )


def _apply_update_to_state(
    state: WorkingMapNodeAssessment,
    update: WorkingMapNodeAssessmentUpdate,
) -> WorkingMapNodeAssessment:
    return state.model_copy(
        update={
            "assessed_mastery_level": update.assessed_mastery_level,
            "diagnostic_confidence": update.diagnostic_confidence,
            "assessment_note": update.assessment_note,
            "supporting_turn_ids": update.supporting_turn_ids,
        }
    )


def _visible_turns_by_id(
    visible_dialogue_context: VisibleDialogueContext,
) -> dict[str, VisibleDialogueTurn]:
    turns_by_id: dict[str, VisibleDialogueTurn] = {}
    duplicate_turn_ids: set[str] = set()
    for turn in visible_dialogue_context.turns:
        if turn.turn_id is None:
            continue
        if turn.turn_id in turns_by_id:
            duplicate_turn_ids.add(turn.turn_id)
            continue
        turns_by_id[turn.turn_id] = turn
    if duplicate_turn_ids:
        raise KnowActValidationError(
            "Visible dialogue contains duplicate turn ids: "
            f"{sorted(duplicate_turn_ids)}"
        )
    return turns_by_id


def _split_valid_supporting_turn_ids(
    supporting_turn_ids: tuple[str, ...],
    visible_turns_by_id: dict[str, VisibleDialogueTurn],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    valid: list[str] = []
    invalid: list[str] = []
    for turn_id in supporting_turn_ids:
        if turn_id in visible_turns_by_id:
            valid.append(turn_id)
        else:
            invalid.append(turn_id)
    return tuple(valid), tuple(invalid)


def _turn_signal(turn: VisibleDialogueTurn) -> str:
    return f"Question: {turn.question.text}\nAnswer: {turn.answer.text}"


def _evidence_id(*, node_id: str, turn_id: str) -> str:
    return f"ev_{node_id}_{turn_id}"


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
