from backend.knowact.core.interaction import VisibleSimulatorAnswer


def simulator_safe_fallback() -> VisibleSimulatorAnswer:
    return VisibleSimulatorAnswer(
        text="I am not confident I can answer that cleanly right now."
    )
