from backend.knowact.core.interaction import (
    DiagnosticQuestion,
    VisibleDialogueContext,
    VisibleDialogueTurn,
    VisibleSimulatorAnswer,
    CoarseObservationMetadata,
)


def next_turn_id(visible_dialogue_context: VisibleDialogueContext) -> str:
    return f"turn_{len(visible_dialogue_context.turns) + 1:03d}"


def append_visible_turn(
    *,
    visible_dialogue_context: VisibleDialogueContext,
    question: DiagnosticQuestion,
    answer: VisibleSimulatorAnswer,
    observation: CoarseObservationMetadata,
    turn_id: str | None = None,
) -> VisibleDialogueContext:
    assigned_turn_id = turn_id or next_turn_id(visible_dialogue_context)
    return visible_dialogue_context.model_copy(
        update={
            "turns": (
                *visible_dialogue_context.turns,
                VisibleDialogueTurn(
                    turn_id=assigned_turn_id,
                    question=question,
                    answer=answer,
                    observation=observation,
                ),
            )
        }
    )
