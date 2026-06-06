from pydantic import BaseModel, ConfigDict, Field

from backend.knowact.simulator.context_builder import SimulatorTurnContext
from backend.knowact.simulator.policy import SimulatorAnswerIntent, SimulatorAnswerStance


class NodeExpressionContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_name: str
    stance: SimulatorAnswerStance
    evidence_signals: tuple[str, ...] = Field(default_factory=tuple)
    misconception_cues: tuple[str, ...] = Field(default_factory=tuple)
    unknown_cues: tuple[str, ...] = Field(default_factory=tuple)


class SimulatorExpressionContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_text: str
    primary_stance: SimulatorAnswerStance
    nodes: tuple[NodeExpressionContext, ...]
    style_hint: str | None = None


class SimulatorExpressionContextBuilder:
    def build(
        self,
        *,
        intent: SimulatorAnswerIntent,
        simulator_context: SimulatorTurnContext,
        profile_context: object | None = None,
    ) -> SimulatorExpressionContext:
        return SimulatorExpressionContext(
            question_text=intent.question_text,
            primary_stance=intent.primary_stance,
            nodes=tuple(
                NodeExpressionContext(
                    node_name=node_intent.node_name,
                    stance=node_intent.stance,
                    evidence_signals=node_intent.evidence_signals,
                    misconception_cues=node_intent.misconception_cues,
                    unknown_cues=node_intent.unknown_cues,
                )
                for node_intent in intent.node_intents
            ),
            style_hint=_style_hint(profile_context),
        )


def _style_hint(profile_context: object | None) -> str | None:
    if profile_context is None:
        return None
    preferences = getattr(profile_context, "preferences", ())
    if any("concrete" in preference.lower() for preference in preferences):
        return "Use plain wording with a concrete phrasing preference."
    return "Use neutral first-person wording."
