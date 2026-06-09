import json
from typing import Protocol

from backend.knowact.core.interaction import VisibleSimulatorAnswer
from backend.knowact.llm.client import ModelClient, ModelClientError
from backend.knowact.simulator.expression import (
    NodeExpressionContext,
    SimulatorExpressionContext,
)
from backend.knowact.simulator.policy import SimulatorAnswerStance
from backend.knowact.simulator.templates.answer_generation import (
    build_answer_generation_messages,
)


class SimulatorAnswerGenerator(Protocol):
    def render(self, expression_context: SimulatorExpressionContext) -> VisibleSimulatorAnswer:
        """Render a candidate visible simulator answer from de-identified context."""


class ModelClientAnswerGenerator:
    def __init__(
        self,
        *,
        model_client: ModelClient,
        temperature: float | None = None,
    ) -> None:
        self._model_client = model_client
        self._temperature = temperature

    def render(self, expression_context: SimulatorExpressionContext) -> VisibleSimulatorAnswer:
        raw_output = self._model_client.complete(
            messages=build_answer_generation_messages(
                expression_context=expression_context,
                message_profile=self._model_client.message_profile,
            ),
            temperature=self._temperature,
        )
        return VisibleSimulatorAnswer(text=_parse_answer_text(raw_output))


class RuleBasedAnswerGenerator:
    def render(self, expression_context: SimulatorExpressionContext) -> VisibleSimulatorAnswer:
        if not expression_context.nodes:
            return VisibleSimulatorAnswer(
                text="I am not sure which concept you want me to answer about."
            )
        if len(expression_context.nodes) == 1:
            return VisibleSimulatorAnswer(
                text=_render_node_answer(expression_context.nodes[0])
            )
        rendered_parts = [_render_node_answer(node) for node in expression_context.nodes]
        return VisibleSimulatorAnswer(text=" ".join(rendered_parts))


def _render_node_answer(node: NodeExpressionContext) -> str:
    node_name = node.node_name.lower()
    evidence_text = " ".join(node.evidence_signals)
    if node.stance == SimulatorAnswerStance.CORRECT_UNDERSTANDING:
        if evidence_text:
            return f"I can explain {node_name}: {evidence_text}"
        return f"I can explain {node_name} and apply it in concrete situations."
    if node.stance == SimulatorAnswerStance.PARTIAL_UNDERSTANDING:
        if evidence_text:
            return f"I have a partial handle on {node.node_name}: {evidence_text}"
        return f"I have a partial handle on {node.node_name}, but I would check details."
    if node.stance == SimulatorAnswerStance.MISCONCEPTION:
        cue = _first_nonblank(node.misconception_cues) or evidence_text
        if cue:
            return f"I am shaky on {node.node_name}; I tend to think {cue}"
        return f"I am shaky on {node.node_name} and may be mixing it up."
    if node.stance == SimulatorAnswerStance.UNCERTAIN_UNDERSTANDING:
        cue = _first_nonblank(node.unknown_cues) or evidence_text
        if cue:
            return f"I am not fully sure about {node.node_name}, especially {cue}"
        return f"I am not fully sure about {node.node_name}."
    return f"I do not really know how to answer about {node.node_name} yet."


def _first_nonblank(values: tuple[str, ...]) -> str | None:
    for value in values:
        if value.strip():
            return value
    return None


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
