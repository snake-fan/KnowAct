from pydantic import BaseModel, ConfigDict, Field

from backend.knowact.core.interaction import VisibleDialogueContext
from backend.knowact.simulator.policy import (
    SimulatorAnswerIntent,
    SimulatorAnswerStance,
    SimulatorResponseMode,
)


class NodeExpressionContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_name: str
    stance: SimulatorAnswerStance
    capability_summary: str
    limitation_summary: str | None = None
    evidence_signals: tuple[str, ...] = Field(default_factory=tuple)
    misconception_cues: tuple[str, ...] = Field(default_factory=tuple)
    unknown_cues: tuple[str, ...] = Field(default_factory=tuple)
    generation_directives: tuple[str, ...] = Field(default_factory=tuple)


class VisibleDialogueExpressionTurn(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_text: str
    answer_text: str
    observation_kind: str


class SimulatorExpressionContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_text: str
    response_mode: SimulatorResponseMode
    primary_stance: SimulatorAnswerStance
    overall_directive: str
    nodes: tuple[NodeExpressionContext, ...]
    generation_directives: tuple[str, ...] = Field(default_factory=tuple)
    visibility_guards: tuple[str, ...] = Field(default_factory=tuple)
    visible_dialogue_turns: tuple[VisibleDialogueExpressionTurn, ...] = Field(
        default_factory=tuple
    )
    style_hint: str | None = None
    regeneration_guidance: tuple[str, ...] = Field(default_factory=tuple)


class SimulatorExpressionContextBuilder:
    def build(
        self,
        *,
        intent: SimulatorAnswerIntent,
        visible_dialogue_context: VisibleDialogueContext | None = None,
        simulator_context: object | None = None,
        profile_context: object | None = None,
        regeneration_guidance: tuple[str, ...] = (),
    ) -> SimulatorExpressionContext:
        if visible_dialogue_context is None and simulator_context is not None:
            visible_dialogue_context = getattr(simulator_context, "visible_dialogue_context", None)
        return SimulatorExpressionContext(
            question_text=intent.question_text,
            response_mode=intent.response_mode,
            primary_stance=intent.primary_stance,
            overall_directive=intent.overall_directive,
            nodes=tuple(
                NodeExpressionContext(
                    node_name=node_decision.node_name,
                    stance=node_decision.stance,
                    capability_summary=node_decision.capability_summary,
                    limitation_summary=node_decision.limitation_summary,
                    evidence_signals=node_decision.evidence_signals,
                    misconception_cues=node_decision.misconception_cues,
                    unknown_cues=node_decision.unknown_cues,
                    generation_directives=node_decision.generation_directives,
                )
                for node_decision in intent.node_decisions
            ),
            generation_directives=intent.generation_directives,
            visibility_guards=intent.visibility_guards,
            visible_dialogue_turns=_visible_dialogue_turns(visible_dialogue_context),
            style_hint=_style_hint(profile_context),
            regeneration_guidance=regeneration_guidance,
        )


def _style_hint(profile_context: object | None) -> str | None:
    if profile_context is None:
        return None
    preferences = getattr(profile_context, "preferences", ())
    if any("concrete" in preference.lower() for preference in preferences):
        return "Use plain wording with a concrete phrasing preference."
    return "Use neutral first-person wording."


def _visible_dialogue_turns(
    visible_dialogue_context: VisibleDialogueContext | None,
) -> tuple[VisibleDialogueExpressionTurn, ...]:
    if visible_dialogue_context is None:
        return ()
    return tuple(
        VisibleDialogueExpressionTurn(
            question_text=turn.question.text,
            answer_text=turn.answer.text,
            observation_kind=turn.observation.kind.value,
        )
        for turn in visible_dialogue_context.turns
    )
