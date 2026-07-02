from enum import StrEnum
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.agents.tools import WorkingMapNodeAssessmentUpdate
from backend.knowact.agents.working_map import AgentWorkingKnowledgeMap
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import DiagnosticQuestion, VisibleDialogueContext


class DecisionPhase(StrEnum):
    INITIAL_QUESTION = "initial_question"
    AFTER_ANSWER = "after_answer"
    FORCED_FINALIZATION = "forced_finalization"


class DecisionPhaseContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    phase: DecisionPhase
    remaining_diagnostic_turns: int = Field(ge=0)


class AskDiagnosticQuestionDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["ask_diagnostic_question"] = "ask_diagnostic_question"
    question: DiagnosticQuestion


class FinalizeReconstructionDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["finalize_reconstruction"] = "finalize_reconstruction"
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def _optional_reason_must_not_be_blank(
        cls, value: str | None
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


TestedAgentDecision = Annotated[
    AskDiagnosticQuestionDecision | FinalizeReconstructionDecision,
    Field(discriminator="kind"),
]


class TestedAgent(Protocol):
    """Protocol implemented by baseline and experimental tested agents."""

    def update_after_visible_answer(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> tuple[WorkingMapNodeAssessmentUpdate, ...]:
        """Return working-map updates after the latest visible simulator answer."""

    def decide_next_action(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> TestedAgentDecision:
        """Return whether to ask a diagnostic question or finalize reconstruction."""
