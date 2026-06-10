import json
import re
from enum import StrEnum
from typing import Literal, Protocol

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


class SimulatorAnswerVoice(StrEnum):
    FIRST_PERSON = "first_person"


class SimulatorAnswerIntegrationMode(StrEnum):
    SINGLE_NODE = "single_node"
    INTEGRATED_MULTI_NODE = "integrated_multi_node"
    CLARIFICATION = "clarification"
    NON_ANSWER = "non_answer"


class SimulatorAnswerShape(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    voice: SimulatorAnswerVoice = SimulatorAnswerVoice.FIRST_PERSON
    integration_mode: SimulatorAnswerIntegrationMode
    max_sentences: int = Field(default=2, ge=1, le=4)


class NodeAnswerBlueprint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_name: str
    stance: SimulatorAnswerStance
    core_claim: str | None = None
    boundary: str | None = None
    mistaken_belief: str | None = None
    uncertainty: str | None = None
    supporting_cues: tuple[str, ...] = Field(default_factory=tuple)
    avoid_overclaiming: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("node_name")
    @classmethod
    def _required_values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("core_claim", "boundary", "mistaken_belief", "uncertainty")
    @classmethod
    def _optional_value_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("supporting_cues", "avoid_overclaiming")
    @classmethod
    def _items_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank items")
        return value


GroundedNodeAnswerDecision = NodeAnswerBlueprint


class SimulatorAnswerPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    primary_stance: SimulatorAnswerStance
    answer_shape: SimulatorAnswerShape
    answer_strategy: str
    content_units: tuple[NodeAnswerBlueprint, ...] = Field(default_factory=tuple)

    @field_validator("answer_strategy")
    @classmethod
    def _required_values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class SimulatorAnswerBlueprint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["simulator_answer_blueprint.v1"] = (
        "simulator_answer_blueprint.v1"
    )
    question_text: str
    response_mode: SimulatorResponseMode
    primary_stance: SimulatorAnswerStance
    answer_shape: SimulatorAnswerShape
    answer_strategy: str
    content_units: tuple[NodeAnswerBlueprint, ...] = Field(default_factory=tuple)

    @property
    def node_decisions(self) -> tuple[NodeAnswerBlueprint, ...]:
        """Compatibility accessor for callers migrating to content_units."""

        return self.content_units

    @field_validator("question_text", "answer_strategy")
    @classmethod
    def _required_values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


SimulatorAnswerIntent = SimulatorAnswerBlueprint


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

    intent: SimulatorAnswerBlueprint
    trace: SimulatorPolicyDecisionTrace


class SimulatorAnswerPolicy(Protocol):
    def derive(
        self,
        *,
        question_text: str,
        simulator_context: SimulatorTurnContext,
        grounding: QuestionGroundingResult,
    ) -> SimulatorPolicyResult:
        """Derive a structured answer blueprint from one grounded simulator turn."""


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
        content_units = (
            ()
            if suppress_node_content
            else tuple(
                _decision_for_grounded_node(context)
                for context in simulator_context.grounded_nodes
            )
        )
        primary_stance = (
            content_units[0].stance
            if content_units
            else SimulatorAnswerStance.NOT_KNOWING
        )
        intent = SimulatorAnswerBlueprint(
            question_text=question_text,
            response_mode=response_mode,
            primary_stance=primary_stance,
            answer_shape=_answer_shape(
                response_mode=response_mode,
                content_units=content_units,
            ),
            answer_strategy=_answer_strategy(
                response_mode=response_mode,
                primary_stance=primary_stance,
                content_units=content_units,
            ),
            content_units=content_units,
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
    ) -> SimulatorAnswerBlueprint:
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
            plan = _parse_policy_plan(raw_output)
            intent = _intent_from_plan(
                question_text=question_text,
                response_mode=fallback_result.intent.response_mode,
                plan=plan,
            )
            _reject_unsafe_intent(
                intent,
                simulator_context=simulator_context,
                grounding=grounding,
            )
        except ModelClientError as exc:
            record_parser_failure(exc)
            raise
        record_parser_success({"plan": plan.model_dump(mode="json")})
        _LOGGER.info(
            "Simulator answer policy parser succeeded response_mode=%s content_units=%d",
            intent.response_mode.value,
            len(intent.content_units),
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
) -> NodeAnswerBlueprint:
    state = context.state
    stance = _stance_for_state(state.mastery_level, state.misconceptions, state.unknowns)
    evidence_signals = tuple(evidence.signal for evidence in context.simulator_only_evidence)
    selected_rubric = context.node.levels.get(state.mastery_level.value)
    answer_focus = _answer_focus(
        mastery_level=state.mastery_level,
        selected_rubric=selected_rubric,
        evidence_signals=evidence_signals,
    )
    boundary_focus = _boundary_focus(
        stance=stance,
        misconceptions=state.misconceptions,
        unknowns=state.unknowns,
        selected_rubric=selected_rubric,
    )
    core_claim = answer_focus
    mistaken_belief = state.misconceptions[0] if state.misconceptions else None
    uncertainty = state.unknowns[0] if state.unknowns else None
    boundary = None
    if stance in (
        SimulatorAnswerStance.PARTIAL_UNDERSTANDING,
        SimulatorAnswerStance.NOT_KNOWING,
    ):
        boundary = boundary_focus
    elif stance == SimulatorAnswerStance.UNCERTAIN_UNDERSTANDING:
        uncertainty = uncertainty or boundary_focus
    elif stance == SimulatorAnswerStance.MISCONCEPTION:
        mistaken_belief = mistaken_belief or boundary_focus
    return NodeAnswerBlueprint(
        node_name=context.node.name,
        stance=stance,
        core_claim=core_claim,
        boundary=boundary,
        mistaken_belief=mistaken_belief,
        uncertainty=uncertainty,
        supporting_cues=_supporting_cues(
            evidence_signals=evidence_signals,
            content_fields=(
                core_claim,
                boundary,
                mistaken_belief,
                uncertainty,
            ),
        ),
        avoid_overclaiming=_avoid_overclaiming(
            stance=stance,
            unknowns=state.unknowns,
        ),
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
        evidence_kinds=tuple(
            evidence.evidence_kind.value
            for evidence in context.simulator_only_evidence
        ),
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


def _answer_focus(
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


def _boundary_focus(
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


def _supporting_cues(
    *,
    evidence_signals: tuple[str, ...],
    content_fields: tuple[str | None, ...],
) -> tuple[str, ...]:
    repeated_values = {field.strip() for field in content_fields if field is not None}
    return tuple(
        signal for signal in evidence_signals
        if signal.strip() not in repeated_values
    )


def _avoid_overclaiming(
    *,
    stance: SimulatorAnswerStance,
    unknowns: tuple[str, ...],
) -> tuple[str, ...]:
    if stance == SimulatorAnswerStance.CORRECT_UNDERSTANDING:
        return ()
    items = list(unknowns)
    if stance == SimulatorAnswerStance.MISCONCEPTION:
        items.append("Do not present the mistaken belief as settled expertise.")
    elif stance == SimulatorAnswerStance.PARTIAL_UNDERSTANDING:
        items.append("Do not claim full independent application of the concept.")
    elif stance == SimulatorAnswerStance.UNCERTAIN_UNDERSTANDING:
        items.append("Do not sound confident about details that are still uncertain.")
    elif stance == SimulatorAnswerStance.NOT_KNOWING:
        items.append("Do not claim reliable understanding of the concept.")
    return tuple(items)


def _answer_shape(
    *,
    response_mode: SimulatorResponseMode,
    content_units: tuple[NodeAnswerBlueprint, ...],
) -> SimulatorAnswerShape:
    if response_mode == SimulatorResponseMode.CLARIFICATION:
        return SimulatorAnswerShape(
            integration_mode=SimulatorAnswerIntegrationMode.CLARIFICATION,
            max_sentences=1,
        )
    if response_mode in (
        SimulatorResponseMode.NON_ANSWER,
        SimulatorResponseMode.SAFE_NON_ANSWER,
    ):
        return SimulatorAnswerShape(
            integration_mode=SimulatorAnswerIntegrationMode.NON_ANSWER,
            max_sentences=1,
        )
    if len(content_units) > 1:
        return SimulatorAnswerShape(
            integration_mode=SimulatorAnswerIntegrationMode.INTEGRATED_MULTI_NODE,
            max_sentences=3,
        )
    return SimulatorAnswerShape(
        integration_mode=SimulatorAnswerIntegrationMode.SINGLE_NODE,
        max_sentences=2,
    )


def _answer_strategy(
    *,
    response_mode: SimulatorResponseMode,
    primary_stance: SimulatorAnswerStance,
    content_units: tuple[NodeAnswerBlueprint, ...],
) -> str:
    if response_mode == SimulatorResponseMode.CLARIFICATION:
        return "Ask the tested agent for one specific diagnostic question."
    if response_mode == SimulatorResponseMode.NON_ANSWER:
        return "State that the target concept is unclear and ask which concept to answer about."
    if response_mode == SimulatorResponseMode.LABEL_REFUSAL:
        return (
            "Answer as a natural self-report instead of revealing benchmark "
            "labels or evidence identifiers."
        )
    if response_mode == SimulatorResponseMode.SAFE_NON_ANSWER:
        return "Return a natural, non-leaking safe non-answer."
    if len(content_units) > 1:
        return (
            "Give one integrated first-person answer that preserves the "
            f"{primary_stance.value.replace('_', ' ')} stance across the grounded concepts."
        )
    return (
        "Give a first-person answer that preserves the "
        f"{primary_stance.value.replace('_', ' ')} stance."
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


def _parse_policy_plan(raw_output: str) -> SimulatorAnswerPlan:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ModelClientError("Simulator answer policy returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ModelClientError("Simulator answer policy returned a non-object payload")
    try:
        return SimulatorAnswerPlan.model_validate(payload)
    except ValueError as exc:
        raise ModelClientError("Simulator answer policy returned an invalid plan") from exc


def _intent_from_plan(
    *,
    question_text: str,
    response_mode: SimulatorResponseMode,
    plan: SimulatorAnswerPlan,
) -> SimulatorAnswerBlueprint:
    return SimulatorAnswerBlueprint(
        question_text=question_text,
        response_mode=response_mode,
        primary_stance=plan.primary_stance,
        answer_shape=plan.answer_shape,
        answer_strategy=plan.answer_strategy,
        content_units=plan.content_units,
    )


def _reject_unsafe_intent(
    intent: SimulatorAnswerBlueprint,
    *,
    simulator_context: SimulatorTurnContext,
    grounding: QuestionGroundingResult,
) -> None:
    if intent.response_mode != _response_mode_for_grounding(grounding):
        raise ModelClientError("Simulator answer policy returned an invalid response mode")
    expected_shape = _answer_shape(
        response_mode=intent.response_mode,
        content_units=intent.content_units,
    )
    if intent.answer_shape.voice != SimulatorAnswerVoice.FIRST_PERSON:
        raise ModelClientError("Simulator answer policy returned an invalid answer voice")
    if intent.answer_shape.integration_mode != expected_shape.integration_mode:
        raise ModelClientError(
            "Simulator answer policy returned an invalid answer integration mode"
        )
    expected_node_names = tuple(context.node.name for context in simulator_context.grounded_nodes)
    actual_node_names = tuple(unit.node_name for unit in intent.content_units)
    if intent.response_mode in (
        SimulatorResponseMode.CLARIFICATION,
        SimulatorResponseMode.NON_ANSWER,
    ) and actual_node_names:
        raise ModelClientError(
            "Simulator answer policy returned node content for a non-content mode"
        )
    if expected_node_names and actual_node_names != expected_node_names:
        raise ModelClientError("Simulator answer policy returned decisions for unexpected nodes")
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
