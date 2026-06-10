import json
import re
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.core.map import MasteryLevel
from backend.knowact.llm.client import ModelClient, ModelClientError
from backend.knowact.logging_config import get_knowact_logger
from backend.knowact.simulator.context_builder import (
    GroundedSimulatorNodeContext,
    SimulatorTurnContext,
)
from backend.knowact.simulator.debug_trace import (
    record_model_raw_output,
    record_parser_failure,
    record_parser_success,
)
from backend.knowact.simulator.grounding import QuestionGroundingResult
from backend.knowact.simulator.templates.answer_policy import (
    build_answer_policy_messages,
)


_LOGGER = get_knowact_logger("simulator.policy")
_MASTERY_LABEL_PATTERN = re.compile(r"\bL[0-5]\b")


class SimulatorAnswerStance(StrEnum):
    CORRECT_UNDERSTANDING = "correct_understanding"
    PARTIAL_UNDERSTANDING = "partial_understanding"
    UNCERTAIN_UNDERSTANDING = "uncertain_understanding"
    NOT_KNOWING = "not_knowing"
    MISCONCEPTION = "misconception"


class SimulatorResponseMode(StrEnum):
    ANSWER = "answer"
    CLARIFICATION = "clarification"
    LABEL_REFUSAL = "label_refusal"
    NON_ANSWER = "non_answer"
    SAFE_NON_ANSWER = "safe_non_answer"


class GroundedNodeAnswerDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_name: str
    stance: SimulatorAnswerStance
    capability_summary: str
    limitation_summary: str | None = None
    misconception_cues: tuple[str, ...] = Field(default_factory=tuple)
    unknown_cues: tuple[str, ...] = Field(default_factory=tuple)
    evidence_signals: tuple[str, ...] = Field(default_factory=tuple)
    generation_directives: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("node_name", "capability_summary")
    @classmethod
    def _required_values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("limitation_summary")
    @classmethod
    def _optional_value_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator(
        "misconception_cues",
        "unknown_cues",
        "evidence_signals",
        "generation_directives",
    )
    @classmethod
    def _items_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank items")
        return value


class SimulatorAnswerIntent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_text: str
    response_mode: SimulatorResponseMode
    primary_stance: SimulatorAnswerStance
    overall_directive: str
    node_decisions: tuple[GroundedNodeAnswerDecision, ...] = Field(default_factory=tuple)
    generation_directives: tuple[str, ...] = Field(default_factory=tuple)
    visibility_guards: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("question_text", "overall_directive")
    @classmethod
    def _required_values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("generation_directives", "visibility_guards")
    @classmethod
    def _items_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank items")
        return value


class GroundedNodePolicyTrace(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    node_name: str
    mastery_level: MasteryLevel
    selected_rubric: str | None = None
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    evidence_kinds: tuple[str, ...] = Field(default_factory=tuple)


class SimulatorPolicyDecisionTrace(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    response_mode: SimulatorResponseMode
    policy_source: str
    grounded_node_traces: tuple[GroundedNodePolicyTrace, ...] = Field(default_factory=tuple)
    grounding_flags: tuple[str, ...] = Field(default_factory=tuple)
    fallback_reason: str | None = None


class SimulatorPolicyResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    intent: SimulatorAnswerIntent
    trace: SimulatorPolicyDecisionTrace


class SimulatorAnswerPolicy(Protocol):
    def derive(
        self,
        *,
        question_text: str,
        simulator_context: SimulatorTurnContext,
        grounding: QuestionGroundingResult,
    ) -> SimulatorPolicyResult:
        """Derive a structured answer intent from one grounded simulator turn."""


class RuleBasedAnswerPolicy:
    def derive(
        self,
        *,
        question_text: str,
        simulator_context: SimulatorTurnContext,
        grounding: QuestionGroundingResult,
    ) -> SimulatorPolicyResult:
        response_mode = _response_mode_for_grounding(grounding)
        suppress_node_content = response_mode in (
            SimulatorResponseMode.CLARIFICATION,
            SimulatorResponseMode.NON_ANSWER,
        )
        node_decisions = (
            ()
            if suppress_node_content
            else tuple(
                _decision_for_grounded_node(context)
                for context in simulator_context.grounded_nodes
            )
        )
        primary_stance = (
            node_decisions[0].stance
            if node_decisions
            else SimulatorAnswerStance.NOT_KNOWING
        )
        intent = SimulatorAnswerIntent(
            question_text=question_text,
            response_mode=response_mode,
            primary_stance=primary_stance,
            overall_directive=_overall_directive(response_mode),
            node_decisions=node_decisions,
            generation_directives=_generation_directives(response_mode),
            visibility_guards=_visibility_guards(),
        )
        return SimulatorPolicyResult(
            intent=intent,
            trace=SimulatorPolicyDecisionTrace(
                response_mode=response_mode,
                policy_source="rule_based",
                grounded_node_traces=tuple(
                    _trace_for_grounded_node(context)
                    for context in simulator_context.grounded_nodes
                ),
                grounding_flags=_grounding_flags(grounding),
            ),
        )

    def derive_intent(
        self,
        *,
        question_text: str,
        simulator_context: SimulatorTurnContext,
    ) -> SimulatorAnswerIntent:
        """Compatibility helper for older callers that do not pass grounding."""

        grounding = QuestionGroundingResult(
            grounded_node_ids=tuple(
                context.state.node_id for context in simulator_context.grounded_nodes
            )
        )
        return self.derive(
            question_text=question_text,
            simulator_context=simulator_context,
            grounding=grounding,
        ).intent


class ModelClientAnswerPolicy:
    def __init__(
        self,
        *,
        model_client: ModelClient,
        fallback_policy: SimulatorAnswerPolicy | None = None,
        temperature: float | None = None,
    ) -> None:
        self._model_client = model_client
        self._fallback_policy = fallback_policy or RuleBasedAnswerPolicy()
        self._temperature = temperature

    def derive(
        self,
        *,
        question_text: str,
        simulator_context: SimulatorTurnContext,
        grounding: QuestionGroundingResult,
    ) -> SimulatorPolicyResult:
        fallback_result = self._fallback_policy.derive(
            question_text=question_text,
            simulator_context=simulator_context,
            grounding=grounding,
        )
        metadata = getattr(self._model_client, "metadata", None)
        _LOGGER.info(
            "Simulator answer policy model call started provider=%s model_name=%s grounded_nodes=%d temperature=%s",
            metadata.provider if metadata is not None else None,
            metadata.model_name if metadata is not None else None,
            len(simulator_context.grounded_nodes),
            self._temperature,
        )
        raw_output = self._model_client.complete(
            messages=build_answer_policy_messages(
                question_text=question_text,
                simulator_context=simulator_context,
                grounding=grounding,
                fallback_intent=fallback_result.intent,
                message_profile=self._model_client.message_profile,
            ),
            temperature=self._temperature,
        )
        record_model_raw_output(raw_output)
        _LOGGER.info(
            "Simulator answer policy model call succeeded provider=%s model_name=%s raw_output_chars=%d",
            metadata.provider if metadata is not None else None,
            metadata.model_name if metadata is not None else None,
            len(raw_output),
        )
        try:
            intent = _parse_policy_intent(raw_output)
            _reject_unsafe_intent(
                intent,
                simulator_context=simulator_context,
                grounding=grounding,
            )
        except ModelClientError as exc:
            record_parser_failure(exc)
            raise
        record_parser_success({"intent": intent.model_dump(mode="json")})
        _LOGGER.info(
            "Simulator answer policy parser succeeded response_mode=%s node_decisions=%d",
            intent.response_mode.value,
            len(intent.node_decisions),
        )
        return SimulatorPolicyResult(
            intent=intent,
            trace=SimulatorPolicyDecisionTrace(
                response_mode=intent.response_mode,
                policy_source="model_client",
                grounded_node_traces=fallback_result.trace.grounded_node_traces,
                grounding_flags=fallback_result.trace.grounding_flags,
            ),
        )


def _response_mode_for_grounding(
    grounding: QuestionGroundingResult,
) -> SimulatorResponseMode:
    if grounding.is_multiple_question:
        return SimulatorResponseMode.CLARIFICATION
    if not grounding.has_grounding:
        return SimulatorResponseMode.NON_ANSWER
    if grounding.is_label_seeking:
        return SimulatorResponseMode.LABEL_REFUSAL
    return SimulatorResponseMode.ANSWER


def _decision_for_grounded_node(
    context: GroundedSimulatorNodeContext,
) -> GroundedNodeAnswerDecision:
    state = context.state
    stance = _stance_for_state(state.mastery_level, state.misconceptions, state.unknowns)
    evidence_signals = tuple(evidence.signal for evidence in context.simulator_only_evidence)
    selected_rubric = context.node.levels.get(state.mastery_level.value)
    return GroundedNodeAnswerDecision(
        node_name=context.node.name,
        stance=stance,
        capability_summary=_capability_summary(
            mastery_level=state.mastery_level,
            selected_rubric=selected_rubric,
            evidence_signals=evidence_signals,
        ),
        limitation_summary=_limitation_summary(
            stance=stance,
            misconceptions=state.misconceptions,
            unknowns=state.unknowns,
            selected_rubric=selected_rubric,
        ),
        misconception_cues=state.misconceptions,
        unknown_cues=state.unknowns,
        evidence_signals=evidence_signals,
        generation_directives=_node_generation_directives(stance),
    )


def _trace_for_grounded_node(
    context: GroundedSimulatorNodeContext,
) -> GroundedNodePolicyTrace:
    state = context.state
    return GroundedNodePolicyTrace(
        node_id=state.node_id,
        node_name=context.node.name,
        mastery_level=state.mastery_level,
        selected_rubric=context.node.levels.get(state.mastery_level.value),
        evidence_refs=state.evidence_refs,
        evidence_kinds=tuple(evidence.evidence_kind.value for evidence in context.simulator_only_evidence),
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


def _capability_summary(
    *,
    mastery_level: MasteryLevel,
    selected_rubric: str | None,
    evidence_signals: tuple[str, ...],
) -> str:
    if evidence_signals:
        return evidence_signals[0]
    if selected_rubric:
        return _remove_mastery_labels(selected_rubric)
    if mastery_level in (MasteryLevel.L4, MasteryLevel.L5):
        return "Can explain and apply the concept in ordinary diagnostic situations."
    if mastery_level in (MasteryLevel.L2, MasteryLevel.L3):
        return "Has a partial working understanding but still has boundaries."
    if mastery_level == MasteryLevel.L1:
        return "Recognizes the concept but relies on shallow recall."
    return "Does not have a reliable answer for this concept."


def _limitation_summary(
    *,
    stance: SimulatorAnswerStance,
    misconceptions: tuple[str, ...],
    unknowns: tuple[str, ...],
    selected_rubric: str | None,
) -> str | None:
    if misconceptions:
        return misconceptions[0]
    if unknowns:
        return unknowns[0]
    if stance == SimulatorAnswerStance.PARTIAL_UNDERSTANDING:
        return "Should express that details or boundaries still need checking."
    if stance == SimulatorAnswerStance.NOT_KNOWING:
        return "Should not claim confident understanding."
    if selected_rubric and stance == SimulatorAnswerStance.UNCERTAIN_UNDERSTANDING:
        return _remove_mastery_labels(selected_rubric)
    return None


def _overall_directive(response_mode: SimulatorResponseMode) -> str:
    if response_mode == SimulatorResponseMode.CLARIFICATION:
        return "Ask the tested agent for one specific diagnostic question."
    if response_mode == SimulatorResponseMode.NON_ANSWER:
        return "State that the target concept is unclear and ask which concept to answer about."
    if response_mode == SimulatorResponseMode.LABEL_REFUSAL:
        return "Do not reveal benchmark labels or evidence identifiers; answer as a natural self-report."
    if response_mode == SimulatorResponseMode.SAFE_NON_ANSWER:
        return "Return a natural, non-leaking safe non-answer."
    return "Answer the diagnostic question as the synthetic user."


def _generation_directives(
    response_mode: SimulatorResponseMode,
) -> tuple[str, ...]:
    directives = [
        "Use first-person wording.",
        "Do not expose benchmark labels, hidden ids, maps, or state tables.",
        "Use only the supplied capability, limitation, misconception, unknown, and evidence cues.",
    ]
    if response_mode == SimulatorResponseMode.LABEL_REFUSAL:
        directives.append("Avoid the words mastery level, evidence id, state table, and scoring.")
    if response_mode == SimulatorResponseMode.CLARIFICATION:
        directives.append("Ask for one specific question instead of answering knowledge content.")
    if response_mode == SimulatorResponseMode.NON_ANSWER:
        directives.append("Ask which concept the tested agent wants to discuss.")
    return tuple(directives)


def _node_generation_directives(
    stance: SimulatorAnswerStance,
) -> tuple[str, ...]:
    if stance == SimulatorAnswerStance.CORRECT_UNDERSTANDING:
        return ("Express confident understanding without overexplaining beyond supplied cues.",)
    if stance == SimulatorAnswerStance.PARTIAL_UNDERSTANDING:
        return ("Express partial or fragile understanding.",)
    if stance == SimulatorAnswerStance.UNCERTAIN_UNDERSTANDING:
        return ("Express uncertainty or hesitation.",)
    if stance == SimulatorAnswerStance.MISCONCEPTION:
        return ("Express the misconception as the user's own tentative belief.",)
    return ("Express not knowing without inventing content.",)


def _visibility_guards() -> tuple[str, ...]:
    return (
        "No benchmark mastery labels.",
        "No hidden evidence identifiers or evidence reference fields.",
        "No map ids, user ids, graph versions, manifests, state tables, or scoring fields.",
        "No unsupported facts, examples, prior experiences, or abilities.",
    )


def _grounding_flags(
    grounding: QuestionGroundingResult,
) -> tuple[str, ...]:
    flags: list[str] = []
    if grounding.is_integrated_question:
        flags.append("integrated_question")
    if grounding.is_multiple_question:
        flags.append("multiple_question")
    if grounding.is_label_seeking:
        flags.append("label_seeking")
    if not grounding.has_grounding:
        flags.append("no_grounding")
    return tuple(flags)


def _parse_policy_intent(raw_output: str) -> SimulatorAnswerIntent:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ModelClientError("Simulator answer policy returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ModelClientError("Simulator answer policy returned a non-object payload")
    try:
        return SimulatorAnswerIntent.model_validate(payload)
    except ValueError as exc:
        raise ModelClientError("Simulator answer policy returned an invalid intent") from exc


def _reject_unsafe_intent(
    intent: SimulatorAnswerIntent,
    *,
    simulator_context: SimulatorTurnContext,
    grounding: QuestionGroundingResult,
) -> None:
    if intent.response_mode != _response_mode_for_grounding(grounding):
        raise ModelClientError("Simulator answer policy returned an invalid response mode")
    payload = intent.model_dump_json()
    lower_payload = payload.lower()
    forbidden_fragments = (
        "mastery_level",
        "evidence_refs",
        "map_id",
        "user_id",
        "ground_truth",
        simulator_context.map_id,
        simulator_context.user_id,
    )
    if any(fragment and fragment.lower() in lower_payload for fragment in forbidden_fragments):
        raise ModelClientError("Simulator answer policy returned unsafe hidden fields")
    if "ev_" in lower_payload or _MASTERY_LABEL_PATTERN.search(payload):
        raise ModelClientError("Simulator answer policy returned hidden labels or evidence ids")


def _remove_mastery_labels(value: str) -> str:
    return _MASTERY_LABEL_PATTERN.sub("this level", value).strip()
