import json
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.core.interaction import (
    VisibleDialogueContext,
    VisibleSimulatorAnswer,
)
from backend.knowact.llm.client import ModelClient, ModelClientError
from backend.knowact.logging_config import get_knowact_logger
from backend.knowact.simulator.debug_trace import (
    record_model_raw_output,
    record_parser_failure,
    record_parser_success,
)
from backend.knowact.simulator.policy import SimulatorAnswerIntent
from backend.knowact.simulator.templates.answer_validation import (
    build_answer_validation_messages,
)


_LOGGER = get_knowact_logger("simulator.checks")


class SimulatorAnswerValidationDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    blocking_safety_reasons: tuple[str, ...] = Field(default_factory=tuple)
    intent_coverage_notes: tuple[str, ...] = Field(default_factory=tuple)
    fallback_guidance: str | None = None

    @field_validator(
        "blocking_safety_reasons",
        "intent_coverage_notes",
    )
    @classmethod
    def _items_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank items")
        return value

    @field_validator("fallback_guidance")
    @classmethod
    def _optional_value_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class SimulatorAnswerValidator(Protocol):
    def validate(
        self,
        *,
        candidate_answer: VisibleSimulatorAnswer,
        intent: SimulatorAnswerIntent,
        visible_dialogue_context: VisibleDialogueContext | None = None,
        style_hint: str | None = None,
        regeneration_guidance: tuple[str, ...] = (),
    ) -> SimulatorAnswerValidationDecision:
        """Check whether a generated simulator answer is safe and intent-covering."""


class HeuristicSimulatorAnswerValidator:
    def validate(
        self,
        *,
        candidate_answer: VisibleSimulatorAnswer,
        intent: SimulatorAnswerIntent,
        visible_dialogue_context: VisibleDialogueContext | None = None,
        style_hint: str | None = None,
        regeneration_guidance: tuple[str, ...] = (),
    ) -> SimulatorAnswerValidationDecision:
        _LOGGER.info(
            "Heuristic simulator answer validation started answer_chars=%d node_decisions=%d",
            len(candidate_answer.text),
            len(intent.node_decisions),
        )
        blocking_reasons = _blocking_safety_reasons(candidate_answer.text)
        decision = SimulatorAnswerValidationDecision(
            passed=not blocking_reasons,
            blocking_safety_reasons=blocking_reasons,
            intent_coverage_notes=(
                f"Expected stance: {intent.primary_stance.value}.",
            ),
            fallback_guidance=(
                "Return a safe simulator fallback."
                if blocking_reasons else None
            ),
        )
        _LOGGER.info(
            "Heuristic simulator answer validation completed passed=%s blocking_reasons=%d intent_coverage_notes=%d",
            decision.passed,
            len(decision.blocking_safety_reasons),
            len(decision.intent_coverage_notes),
        )
        return decision


class ModelClientAnswerValidator:
    def __init__(
        self,
        *,
        model_client: ModelClient,
        temperature: float | None = None,
    ) -> None:
        self._model_client = model_client
        self._temperature = temperature

    def validate(
        self,
        *,
        candidate_answer: VisibleSimulatorAnswer,
        intent: SimulatorAnswerIntent,
        visible_dialogue_context: VisibleDialogueContext | None = None,
        style_hint: str | None = None,
        regeneration_guidance: tuple[str, ...] = (),
    ) -> SimulatorAnswerValidationDecision:
        metadata = getattr(self._model_client, "metadata", None)
        _LOGGER.info(
            "Simulator answer validation model call started provider=%s model_name=%s answer_chars=%d node_decisions=%d temperature=%s",
            metadata.provider if metadata is not None else None,
            metadata.model_name if metadata is not None else None,
            len(candidate_answer.text),
            len(intent.node_decisions),
            self._temperature,
        )
        raw_output = self._model_client.complete(
            messages=build_answer_validation_messages(
                candidate_answer=candidate_answer,
                intent=intent,
                visible_dialogue_context=visible_dialogue_context,
                style_hint=style_hint,
                regeneration_guidance=regeneration_guidance,
                message_profile=self._model_client.message_profile,
            ),
            temperature=self._temperature,
        )
        record_model_raw_output(raw_output)
        _LOGGER.info(
            "Simulator answer validation model call succeeded provider=%s model_name=%s raw_output_chars=%d",
            metadata.provider if metadata is not None else None,
            metadata.model_name if metadata is not None else None,
            len(raw_output),
        )
        try:
            decision = _parse_validation_decision(raw_output)
        except ModelClientError as exc:
            record_parser_failure(exc)
            raise
        hard_block_reasons = _blocking_safety_reasons(candidate_answer.text)
        if not hard_block_reasons:
            record_parser_success(decision.model_dump(mode="json"))
            _LOGGER.info(
                "Simulator answer validation parser succeeded passed=%s blocking_reasons=%d intent_coverage_notes=%d hard_blocking_reasons=0",
                decision.passed,
                len(decision.blocking_safety_reasons),
                len(decision.intent_coverage_notes),
            )
            return decision

        merged_reasons = tuple(
            dict.fromkeys((*decision.blocking_safety_reasons, *hard_block_reasons))
        )
        merged_decision = SimulatorAnswerValidationDecision(
            passed=False,
            blocking_safety_reasons=merged_reasons,
            intent_coverage_notes=decision.intent_coverage_notes,
            fallback_guidance=decision.fallback_guidance
            or "Return a safe simulator fallback.",
        )
        record_parser_success(merged_decision.model_dump(mode="json"))
        _LOGGER.info(
            "Simulator answer validation parser succeeded passed=%s blocking_reasons=%d intent_coverage_notes=%d hard_blocking_reasons=%d",
            merged_decision.passed,
            len(merged_decision.blocking_safety_reasons),
            len(merged_decision.intent_coverage_notes),
            len(hard_block_reasons),
        )
        return merged_decision


def _blocking_safety_reasons(answer_text: str) -> tuple[str, ...]:
    normalized = answer_text.lower()
    reasons: list[str] = []
    checks: Sequence[tuple[str, bool]] = (
        ("mastery label leakage", any(f"l{index}" in normalized for index in range(6))),
        ("hidden evidence id leakage", "ev_" in normalized),
        ("state-table language", "state table" in normalized),
        ("benchmark scoring fields", "scoring" in normalized),
        (
            "full-map or state dump language",
            "knowledge map" in normalized or "ground truth" in normalized,
        ),
    )
    for reason, failed in checks:
        if failed:
            reasons.append(reason)
    return tuple(reasons)


def _parse_validation_decision(raw_output: str) -> SimulatorAnswerValidationDecision:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ModelClientError("Simulator answer validator returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ModelClientError("Simulator answer validator returned a non-object payload")
    try:
        return SimulatorAnswerValidationDecision.model_validate(payload)
    except ValueError as exc:
        raise ModelClientError("Simulator answer validator returned an invalid decision") from exc
