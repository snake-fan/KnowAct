from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from backend.knowact.core.map import MasteryLevel
from backend.knowact.simulator.context_builder import SimulatorTurnContext


class SimulatorAnswerStance(StrEnum):
    CORRECT_UNDERSTANDING = "correct_understanding"
    PARTIAL_UNDERSTANDING = "partial_understanding"
    UNCERTAIN_UNDERSTANDING = "uncertain_understanding"
    NOT_KNOWING = "not_knowing"
    MISCONCEPTION = "misconception"


class GroundedNodeAnswerIntent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_name: str
    stance: SimulatorAnswerStance
    evidence_signals: tuple[str, ...] = Field(default_factory=tuple)
    misconception_cues: tuple[str, ...] = Field(default_factory=tuple)
    unknown_cues: tuple[str, ...] = Field(default_factory=tuple)
    hidden_evidence_refs: tuple[str, ...] = Field(default_factory=tuple)


class SimulatorAnswerIntent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_text: str
    primary_stance: SimulatorAnswerStance
    node_intents: tuple[GroundedNodeAnswerIntent, ...]
    hidden_evidence_refs: tuple[str, ...] = Field(default_factory=tuple)


class RuleBasedAnswerPolicy:
    def derive_intent(
        self,
        *,
        question_text: str,
        simulator_context: SimulatorTurnContext,
    ) -> SimulatorAnswerIntent:
        node_intents = tuple(
            _intent_for_grounded_node(context)
            for context in simulator_context.grounded_nodes
        )
        hidden_evidence_refs = tuple(
            evidence_ref
            for node_intent in node_intents
            for evidence_ref in node_intent.hidden_evidence_refs
        )
        primary_stance = (
            node_intents[0].stance
            if node_intents
            else SimulatorAnswerStance.NOT_KNOWING
        )
        return SimulatorAnswerIntent(
            question_text=question_text,
            primary_stance=primary_stance,
            node_intents=node_intents,
            hidden_evidence_refs=hidden_evidence_refs,
        )


def _intent_for_grounded_node(context) -> GroundedNodeAnswerIntent:
    state = context.state
    evidence_signals = tuple(evidence.signal for evidence in context.simulator_only_evidence)
    stance = _stance_for_state(state.mastery_level, state.misconceptions, state.unknowns)
    return GroundedNodeAnswerIntent(
        node_name=context.node.name,
        stance=stance,
        evidence_signals=evidence_signals,
        misconception_cues=state.misconceptions,
        unknown_cues=state.unknowns,
        hidden_evidence_refs=state.evidence_refs,
    )


def _stance_for_state(
    mastery_level: MasteryLevel,
    misconceptions: tuple[str, ...],
    unknowns: tuple[str, ...],
) -> SimulatorAnswerStance:
    if misconceptions and mastery_level in (MasteryLevel.L0, MasteryLevel.L1, MasteryLevel.L2):
        return SimulatorAnswerStance.MISCONCEPTION
    if mastery_level in (MasteryLevel.L4, MasteryLevel.L5):
        return SimulatorAnswerStance.CORRECT_UNDERSTANDING
    if mastery_level in (MasteryLevel.L2, MasteryLevel.L3):
        return SimulatorAnswerStance.PARTIAL_UNDERSTANDING
    if mastery_level == MasteryLevel.L1 or unknowns:
        return SimulatorAnswerStance.UNCERTAIN_UNDERSTANDING
    return SimulatorAnswerStance.NOT_KNOWING
