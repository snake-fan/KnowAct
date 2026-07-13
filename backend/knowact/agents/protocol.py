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


class DiagnosticQuestionPlan(BaseModel):
    """Tested-agent-visible rationale for one information-seeking action."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    primary_target_node_id: str
    secondary_target_node_ids: tuple[str, ...] = Field(default_factory=tuple)
    target_mastery_boundary: str
    selection_reason: str

    @field_validator(
        "primary_target_node_id", "target_mastery_boundary", "selection_reason"
    )
    @classmethod
    def _plan_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("secondary_target_node_ids")
    @classmethod
    def _secondary_targets_must_be_nonblank_unique(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not node_id.strip() for node_id in value):
            raise ValueError("must not contain blank items")
        if len(value) != len(set(value)):
            raise ValueError("must not contain duplicate items")
        return value


class AskDiagnosticQuestionDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["ask_diagnostic_question"] = "ask_diagnostic_question"
    question: DiagnosticQuestion
    diagnostic_plan: DiagnosticQuestionPlan | None = None


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
