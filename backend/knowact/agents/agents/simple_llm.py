import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from backend.knowact.agents.base import BaseTestedAgent
from backend.knowact.agents.protocol import DecisionPhaseContext
from backend.knowact.agents.templates.simple_llm import (
    build_assessment_update_messages,
    build_next_action_messages,
)
from backend.knowact.agents.tools import WorkingMapNodeAssessmentUpdate
from backend.knowact.agents.working_map import AgentWorkingKnowledgeMap
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import DiagnosticQuestion, VisibleDialogueContext
from backend.knowact.llm.client import ModelClient, ModelClientError
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessageProfile


class SimpleLLMTestedAgent(BaseTestedAgent):
    """Minimal LLM-backed tested agent using the shared working-map contract."""

    def __init__(
        self,
        *,
        model_client: ModelClient,
        temperature: float | None = None,
    ) -> None:
        self._model_client = model_client
        self._temperature = temperature

    def assess_after_visible_answer(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> tuple[WorkingMapNodeAssessmentUpdate, ...]:
        raw_output = self._model_client.complete(
            messages=build_assessment_update_messages(
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=visible_dialogue_context,
                decision_context=decision_context,
                message_profile=_message_profile_for(self._model_client),
            ),
            temperature=self._temperature,
        )
        return parse_assessment_update_output(raw_output)

    def select_diagnostic_question(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> DiagnosticQuestion | None:
        raw_output = self._model_client.complete(
            messages=build_next_action_messages(
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=visible_dialogue_context,
                decision_context=decision_context,
                message_profile=_message_profile_for(self._model_client),
            ),
            temperature=self._temperature,
        )
        return parse_next_question_output(raw_output)


class _AssessmentUpdateOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    updates: tuple[WorkingMapNodeAssessmentUpdate, ...] = ()


class _NextActionOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action: Literal["ask_diagnostic_question", "finalize_reconstruction"]
    question: DiagnosticQuestion | None = None
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def _optional_reason_must_not_be_blank(
        cls, value: str | None
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


def parse_assessment_update_output(
    raw_output: str,
) -> tuple[WorkingMapNodeAssessmentUpdate, ...]:
    return _parse_model_output(
        raw_output,
        model=_AssessmentUpdateOutput,
        output_name="assessment updates",
    ).updates


def parse_next_question_output(raw_output: str) -> DiagnosticQuestion | None:
    decision = _parse_model_output(
        raw_output,
        model=_NextActionOutput,
        output_name="next action",
    )
    if decision.action == "finalize_reconstruction":
        return None
    if decision.question is None:
        raise ModelClientError("Simple LLM tested agent ask action omitted question")
    return decision.question


def _parse_model_output(raw_output: str, *, model, output_name: str):
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ModelClientError(
            f"Simple LLM tested agent returned invalid JSON for {output_name}"
        ) from exc
    if not isinstance(payload, dict):
        raise ModelClientError(
            f"Simple LLM tested agent returned a non-object payload for {output_name}"
        )
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ModelClientError(
            f"Simple LLM tested agent returned invalid {output_name}"
        ) from exc


def _message_profile_for(model_client: ModelClient) -> ModelMessageProfile:
    return getattr(model_client, "message_profile", OPENAI_MESSAGE_PROFILE)
