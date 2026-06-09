from backend.knowact.core.interaction import VisibleSimulatorAnswer


def no_grounding_answer() -> VisibleSimulatorAnswer:
    return VisibleSimulatorAnswer(
        text="I am not sure which concept you want me to answer about."
    )


def multiple_question_clarification() -> VisibleSimulatorAnswer:
    return VisibleSimulatorAnswer(
        text="Please ask one specific question at a time so I can answer it directly."
    )


def simulator_safe_fallback() -> VisibleSimulatorAnswer:
    return VisibleSimulatorAnswer(
        text="I am not confident I can answer that cleanly right now."
    )
