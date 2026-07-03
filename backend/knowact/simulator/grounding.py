import json
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import DiagnosticQuestion, VisibleDialogueContext
from backend.knowact.llm.client import ModelClient, ModelClientError
from backend.knowact.logging_config import get_knowact_logger
from backend.knowact.simulator.debug_trace import (
    record_model_raw_output,
    record_parser_failure,
    record_parser_success,
)
from backend.knowact.simulator.templates.question_grounding import (
    build_question_grounding_messages,
)


_LOGGER = get_knowact_logger("simulator.grounding")
GroundingSource = Literal["rule_based", "model_client", "rule_based_fallback"]


class QuestionGroundingResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    grounded_node_ids: tuple[str, ...] = Field(default_factory=tuple)
    is_integrated_question: bool = False
    is_multiple_question: bool = False
    is_label_seeking: bool = False
    grounding_source: GroundingSource = Field(default="rule_based", exclude=True)
    fallback_reason: str | None = Field(default=None, exclude=True)

    @property
    def has_grounding(self) -> bool:
        return bool(self.grounded_node_ids)


class RuleBasedQuestionGrounder:
    def ground(
        self,
        *,
        question: DiagnosticQuestion,
        graph: KnowledgeGraph,
        visible_dialogue_context: VisibleDialogueContext | None = None,
    ) -> QuestionGroundingResult:
        haystack = _normalize_for_matching(question.text)
        if visible_dialogue_context is not None:
            haystack = " ".join(
                (
                    haystack,
                    *(
                        _normalize_for_matching(turn.question.text)
                        for turn in visible_dialogue_context.turns[-1:]
                    ),
                )
            )

        grounded_node_ids: list[str] = []
        for node in graph.nodes:
            terms = [
                node.id,
                node.name,
                node.definition or "",
                node.diagnostic_goal or "",
                *node.diagnostic_signals,
            ]
            if any(_normalize_for_matching(term) in haystack for term in terms if term):
                grounded_node_ids.append(node.id)

        is_multiple_question = _looks_like_multiple_questions(question.text)
        return QuestionGroundingResult(
            grounded_node_ids=tuple(grounded_node_ids),
            is_integrated_question=len(grounded_node_ids) > 1 and not is_multiple_question,
            is_multiple_question=is_multiple_question,
            is_label_seeking=_looks_like_label_seeking(question.text),
        )


class QuestionGrounder(Protocol):
    def ground(
        self,
        *,
        question: DiagnosticQuestion,
        graph: KnowledgeGraph,
        visible_dialogue_context: VisibleDialogueContext | None = None,
    ) -> QuestionGroundingResult:
        """Ground one diagnostic question against the visible authored graph."""


class ModelClientQuestionGroundingOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    grounded_node_ids: tuple[str, ...] = Field(default_factory=tuple)
    is_multiple_question: bool = False
    is_label_seeking: bool = False


class ModelClientQuestionGrounder:
    def __init__(
        self,
        *,
        model_client: ModelClient,
        fallback_grounder: QuestionGrounder | None = None,
        temperature: float | None = None,
    ) -> None:
        self._model_client = model_client
        self._fallback_grounder = fallback_grounder or RuleBasedQuestionGrounder()
        self._temperature = temperature

    def ground(
        self,
        *,
        question: DiagnosticQuestion,
        graph: KnowledgeGraph,
        visible_dialogue_context: VisibleDialogueContext | None = None,
    ) -> QuestionGroundingResult:
        metadata = getattr(self._model_client, "metadata", None)
        try:
            _LOGGER.info(
                "Question grounding model call started provider=%s model_name=%s nodes=%d temperature=%s",
                metadata.provider if metadata is not None else None,
                metadata.model_name if metadata is not None else None,
                len(graph.nodes),
                self._temperature,
            )
            raw_output = self._model_client.complete(
                messages=build_question_grounding_messages(
                    question=question,
                    graph=graph,
                    visible_dialogue_context=visible_dialogue_context,
                    message_profile=self._model_client.message_profile,
                ),
                temperature=self._temperature,
            )
            record_model_raw_output(raw_output)
            _LOGGER.info(
                "Question grounding model call succeeded provider=%s model_name=%s raw_output_chars=%d",
                metadata.provider if metadata is not None else None,
                metadata.model_name if metadata is not None else None,
                len(raw_output),
            )
            parsed_output = _parse_model_grounding_output(raw_output)
            result = _grounding_result_from_model_output(
                parsed_output,
                graph=graph,
            )
        except (ModelClientError, TimeoutError, ValueError) as exc:
            record_parser_failure(exc)
            _LOGGER.warning(
                "Question grounding model path failed grounder=%s error_type=%s fallback=rule_based",
                type(self).__name__,
                type(exc).__name__,
            )
            fallback_result = self._fallback_grounder.ground(
                question=question,
                graph=graph,
                visible_dialogue_context=visible_dialogue_context,
            )
            return fallback_result.model_copy(
                update={
                    "grounding_source": "rule_based_fallback",
                    "fallback_reason": type(exc).__name__,
                }
            )
        record_parser_success({"grounding": result.model_dump(mode="json")})
        _LOGGER.info(
            "Question grounding model parser succeeded grounded_nodes=%d multiple_question=%s label_seeking=%s",
            len(result.grounded_node_ids),
            result.is_multiple_question,
            result.is_label_seeking,
        )
        return result


def _looks_like_multiple_questions(question_text: str) -> bool:
    return question_text.count("?") > 1


def _looks_like_label_seeking(question_text: str) -> bool:
    normalized = _normalize_for_matching(question_text)
    label_terms = (
        "mastery level",
        "evidence id",
        "state table",
        "knowledge map",
        "ground truth",
    )
    return any(term in normalized for term in label_terms)


def _normalize_for_matching(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else " " for character in value)


def _parse_model_grounding_output(raw_output: str) -> ModelClientQuestionGroundingOutput:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ModelClientError("Question grounding returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ModelClientError("Question grounding returned a non-object payload")
    try:
        return ModelClientQuestionGroundingOutput.model_validate(payload)
    except ValueError as exc:
        raise ModelClientError("Question grounding returned an invalid decision") from exc


def _grounding_result_from_model_output(
    output: ModelClientQuestionGroundingOutput,
    *,
    graph: KnowledgeGraph,
) -> QuestionGroundingResult:
    known_node_ids = {node.id for node in graph.nodes}
    grounded_node_ids: list[str] = []
    for node_id in output.grounded_node_ids:
        if node_id not in known_node_ids:
            raise ModelClientError("Question grounding returned an unknown node id")
        if node_id not in grounded_node_ids:
            grounded_node_ids.append(node_id)
    is_multiple_question = output.is_multiple_question
    return QuestionGroundingResult(
        grounded_node_ids=tuple(grounded_node_ids),
        is_integrated_question=len(grounded_node_ids) > 1 and not is_multiple_question,
        is_multiple_question=is_multiple_question,
        is_label_seeking=output.is_label_seeking,
        grounding_source="model_client",
    )
