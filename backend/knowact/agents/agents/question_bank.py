from __future__ import annotations

import hashlib
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.knowact.agents.agents.simple_llm import SimpleLLMTestedAgent
from backend.knowact.agents.protocol import (
    AskDiagnosticQuestionDecision,
    DecisionPhase,
    DecisionPhaseContext,
    DiagnosticQuestionPlan,
    FinalizeReconstructionDecision,
    TestedAgentDecision,
)
from backend.knowact.agents.working_map import AgentWorkingKnowledgeMap
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import DiagnosticQuestion, VisibleDialogueContext
from backend.knowact.llm.client import ModelClient


class QuestionBankItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question: DiagnosticQuestion
    diagnostic_plan: DiagnosticQuestionPlan

    @model_validator(mode="after")
    def _question_id_is_required(self) -> Self:
        if self.question.question_id is None:
            raise ValueError("question-bank items require a stable question_id")
        return self


class DiagnosticQuestionBank(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    bank_id: str
    version: str
    items: tuple[QuestionBankItem, ...] = Field(min_length=1)

    @field_validator("bank_id", "version")
    @classmethod
    def _identity_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def _question_ids_are_unique(self) -> Self:
        question_ids = [item.question.question_id for item in self.items]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("question-bank question ids must be unique")
        return self


class QuestionBankTestedAgent(SimpleLLMTestedAgent):
    """Shared estimator with an injected, immutable question-selection policy."""

    def __init__(
        self,
        *,
        model_client: ModelClient,
        question_bank: DiagnosticQuestionBank,
        temperature: float | None = None,
    ) -> None:
        super().__init__(model_client=model_client, temperature=temperature)
        self._question_bank = question_bank

    def decide_next_action(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> TestedAgentDecision:
        if (
            decision_context.phase == DecisionPhase.FORCED_FINALIZATION
            or decision_context.remaining_diagnostic_turns == 0
        ):
            return FinalizeReconstructionDecision(
                reason="Question-bank agent reached forced finalization."
            )
        remaining_items = self._remaining_valid_items(
            graph=graph,
            visible_dialogue_context=visible_dialogue_context,
        )
        if not remaining_items:
            return FinalizeReconstructionDecision(
                reason="The diagnostic question bank is exhausted."
            )
        item = self._select_item(
            remaining_items=remaining_items,
            visible_dialogue_context=visible_dialogue_context,
        )
        return AskDiagnosticQuestionDecision(
            question=item.question,
            diagnostic_plan=item.diagnostic_plan,
        )

    def _select_item(
        self,
        *,
        remaining_items: tuple[QuestionBankItem, ...],
        visible_dialogue_context: VisibleDialogueContext,
    ) -> QuestionBankItem:
        return remaining_items[0]

    def _remaining_valid_items(
        self,
        *,
        graph: KnowledgeGraph,
        visible_dialogue_context: VisibleDialogueContext,
    ) -> tuple[QuestionBankItem, ...]:
        asked_ids = {
            turn.question.question_id
            for turn in visible_dialogue_context.turns
            if turn.question.question_id is not None
        }
        valid_items: list[QuestionBankItem] = []
        for item in self._question_bank.items:
            targets = (
                item.diagnostic_plan.primary_target_node_id,
                *item.diagnostic_plan.secondary_target_node_ids,
            )
            if set(targets) - graph.node_ids:
                raise ValueError(
                    "question-bank item references nodes outside the episode graph"
                )
            if item.question.question_id not in asked_ids:
                valid_items.append(item)
        return tuple(valid_items)


class FixedQuestionBankTestedAgent(QuestionBankTestedAgent):
    """Select the first unanswered item in immutable bank order."""


class RandomQuestionBankTestedAgent(QuestionBankTestedAgent):
    """Select without replacement using a resume-stable deterministic seed."""

    def __init__(
        self,
        *,
        model_client: ModelClient,
        question_bank: DiagnosticQuestionBank,
        seed: str,
        temperature: float | None = None,
    ) -> None:
        super().__init__(
            model_client=model_client,
            question_bank=question_bank,
            temperature=temperature,
        )
        if not seed.strip():
            raise ValueError("random question-bank seed must not be blank")
        self._seed = seed

    def _select_item(
        self,
        *,
        remaining_items: tuple[QuestionBankItem, ...],
        visible_dialogue_context: VisibleDialogueContext,
    ) -> QuestionBankItem:
        asked_ids = tuple(
            turn.question.question_id or ""
            for turn in visible_dialogue_context.turns
        )
        identity = "|".join(
            (
                self._seed,
                self._question_bank.bank_id,
                self._question_bank.version,
                *asked_ids,
            )
        )
        digest = hashlib.sha256(identity.encode("utf-8")).digest()
        index = int.from_bytes(digest[:8], byteorder="big") % len(remaining_items)
        return remaining_items[index]
