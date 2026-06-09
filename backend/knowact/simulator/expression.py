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


class VisibleDialogueExpressionTurn(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_text: str
    answer_text: str
    observation_kind: str


class SimulatorExpressionContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_text: str
    primary_stance: SimulatorAnswerStance
    nodes: tuple[NodeExpressionContext, ...]
    visible_dialogue_turns: tuple[VisibleDialogueExpressionTurn, ...] = Field(
        default_factory=tuple
    )
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
            visible_dialogue_turns=_visible_dialogue_turns(simulator_context),
            style_hint=_style_hint(profile_context),
        )


def _style_hint(profile_context: object | None) -> str | None:
    if profile_context is None:
        return None
    preferences = getattr(profile_context, "preferences", ())
    if any("concrete" in preference.lower() for preference in preferences):
        return "Use plain wording with a concrete phrasing preference."
    return "Use neutral first-person wording."


def _visible_dialogue_turns(
    simulator_context: SimulatorTurnContext,
) -> tuple[VisibleDialogueExpressionTurn, ...]:
    if simulator_context.visible_dialogue_context is None:
        return ()
    return tuple(
        VisibleDialogueExpressionTurn(
            question_text=turn.question.text,
            answer_text=turn.answer.text,
            observation_kind=turn.observation.kind.value,
        )
        for turn in simulator_context.visible_dialogue_context.turns
    )
