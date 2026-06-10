import json
from typing import Protocol

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
from backend.knowact.simulator.policy import (
    NodeAnswerBlueprint,
    SimulatorAnswerBlueprint,
    SimulatorAnswerStance,
    SimulatorResponseMode,
)
from backend.knowact.simulator.templates.answer_generation import (
    build_answer_generation_messages,
)


_LOGGER = get_knowact_logger("simulator.generators")


class SimulatorAnswerGenerator(Protocol):
    def render(
        self,
        *,
        intent: SimulatorAnswerBlueprint,
        visible_dialogue_context: VisibleDialogueContext | None = None,
        style_hint: str | None = None,
        regeneration_guidance: tuple[str, ...] = (),
    ) -> VisibleSimulatorAnswer:
        """Render a candidate visible simulator answer from an answer blueprint."""


class ModelClientAnswerGenerator:
    def __init__(
        self,
        *,
        model_client: ModelClient,
        temperature: float | None = None,
    ) -> None:
        self._model_client = model_client
        self._temperature = temperature

    def render(
        self,
        *,
        intent: SimulatorAnswerBlueprint,
        visible_dialogue_context: VisibleDialogueContext | None = None,
        style_hint: str | None = None,
        regeneration_guidance: tuple[str, ...] = (),
    ) -> VisibleSimulatorAnswer:
        metadata = getattr(self._model_client, "metadata", None)
        _LOGGER.info(
            "Simulator answer generation model call started provider=%s model_name=%s content_units=%d temperature=%s",
            metadata.provider if metadata is not None else None,
            metadata.model_name if metadata is not None else None,
            len(intent.content_units),
            self._temperature,
        )
        raw_output = self._model_client.complete(
            messages=build_answer_generation_messages(
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
            "Simulator answer generation model call succeeded provider=%s model_name=%s raw_output_chars=%d",
            metadata.provider if metadata is not None else None,
            metadata.model_name if metadata is not None else None,
            len(raw_output),
        )
        try:
            answer_text = _parse_answer_text(raw_output)
        except ModelClientError as exc:
            record_parser_failure(exc)
            raise
        record_parser_success({"answer": {"text": answer_text}})
        _LOGGER.info(
            "Simulator answer generation parser succeeded answer_chars=%d",
            len(answer_text),
        )
        return VisibleSimulatorAnswer(text=answer_text)


class RuleBasedAnswerGenerator:
    def render(
        self,
        *,
        intent: SimulatorAnswerBlueprint,
        visible_dialogue_context: VisibleDialogueContext | None = None,
        style_hint: str | None = None,
        regeneration_guidance: tuple[str, ...] = (),
    ) -> VisibleSimulatorAnswer:
        _LOGGER.info(
            "Rule-based simulator answer generation started content_units=%d",
            len(intent.content_units),
        )
        if intent.response_mode == SimulatorResponseMode.CLARIFICATION:
            answer = VisibleSimulatorAnswer(
                text="Please ask one specific question at a time so I can answer it directly."
            )
        elif intent.response_mode == SimulatorResponseMode.NON_ANSWER:
            answer = VisibleSimulatorAnswer(
                text="I am not sure which concept you want me to answer about."
            )
        elif intent.response_mode == SimulatorResponseMode.SAFE_NON_ANSWER:
            answer = VisibleSimulatorAnswer(
                text="I am not confident I can answer that cleanly right now."
            )
        elif not intent.content_units:
            answer = VisibleSimulatorAnswer(
                text="I am not confident I can answer that cleanly right now."
            )
        elif len(intent.content_units) == 1:
            answer = VisibleSimulatorAnswer(
                text=_render_node_answer(
                    intent.content_units[0],
                    response_mode=intent.response_mode,
                )
            )
        else:
            rendered_parts = [
                _render_node_answer(node, response_mode=intent.response_mode)
                for node in intent.content_units
            ]
            answer = VisibleSimulatorAnswer(text=" ".join(rendered_parts))
        _LOGGER.info(
            "Rule-based simulator answer generation succeeded answer_chars=%d",
            len(answer.text),
        )
        return answer


def _render_node_answer(
    node: NodeAnswerBlueprint,
    *,
    response_mode: SimulatorResponseMode,
) -> str:
    node_name = node.node_name.lower()
    support_text = " ".join(node.supporting_cues)
    if response_mode == SimulatorResponseMode.LABEL_REFUSAL:
        return _render_label_refusal_node_answer(node)
    if node.stance == SimulatorAnswerStance.CORRECT_UNDERSTANDING:
        if support_text:
            return f"I can explain {node_name}: {node.core_claim} {support_text}"
        if node.core_claim:
            return f"I can explain {node_name}: {node.core_claim}"
        return f"I can explain {node_name} and apply it in concrete situations."
    if node.stance == SimulatorAnswerStance.PARTIAL_UNDERSTANDING:
        if node.boundary:
            return (
                f"I have a partial handle on {node.node_name}: "
                f"{node.core_claim} But {node.boundary}"
            )
        if support_text:
            return (
                f"I have a partial handle on {node.node_name}: "
                f"{node.core_claim} {support_text}"
            )
        if node.core_claim:
            return f"I have a partial handle on {node.node_name}: {node.core_claim}"
        return f"I have a partial handle on {node.node_name}, but I would check details."
    if node.stance == SimulatorAnswerStance.MISCONCEPTION:
        cue = node.mistaken_belief or support_text or node.core_claim
        if cue:
            return f"I am shaky on {node.node_name}; I tend to think {cue}"
        return f"I am shaky on {node.node_name} and may be mixing it up."
    if node.stance == SimulatorAnswerStance.UNCERTAIN_UNDERSTANDING:
        cue = node.uncertainty or node.boundary or support_text or node.core_claim
        if cue:
            return f"I am not fully sure about {node.node_name}, especially {cue}"
        return f"I am not fully sure about {node.node_name}."
    return f"I do not really know how to answer about {node.node_name} yet."


def _render_label_refusal_node_answer(node: NodeAnswerBlueprint) -> str:
    if node.stance == SimulatorAnswerStance.CORRECT_UNDERSTANDING:
        return (
            f"I can talk about {node.node_name}, but only in my own words: "
            f"{node.core_claim}"
        )
    cue = node.mistaken_belief or node.uncertainty or node.boundary or node.core_claim
    if cue:
        return (
            f"I can describe how {node.node_name} feels to me, "
            f"but not as a benchmark label: {cue}"
        )
    return f"I can describe {node.node_name} in my own words, but not as a benchmark label."


def _parse_answer_text(raw_output: str) -> str:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ModelClientError("Simulator answer generator returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ModelClientError("Simulator answer generator returned a non-object payload")
    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ModelClientError("Simulator answer generator returned an empty answer")
    return answer.strip()
