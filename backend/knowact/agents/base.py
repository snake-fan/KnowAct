from backend.knowact.agents.protocol import (
    AskDiagnosticQuestionDecision,
    DecisionPhase,
    DecisionPhaseContext,
    FinalizeReconstructionDecision,
    TestedAgent,
    TestedAgentDecision,
)
from backend.knowact.agents.tools import WorkingMapNodeAssessmentUpdate
from backend.knowact.agents.working_map import AgentWorkingKnowledgeMap
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import DiagnosticQuestion, VisibleDialogueContext


class BaseTestedAgent(TestedAgent):
    """Phase-aware base class for tested-agent implementations."""

    def update_after_visible_answer(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> tuple[WorkingMapNodeAssessmentUpdate, ...]:
        if decision_context.phase == DecisionPhase.INITIAL_QUESTION:
            return ()
        return self.assess_after_visible_answer(
            graph=graph,
            working_map=working_map,
            visible_dialogue_context=visible_dialogue_context,
            decision_context=decision_context,
        )

    def decide_next_action(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> TestedAgentDecision:
        if _must_finalize(decision_context):
            return FinalizeReconstructionDecision(
                reason=_finalization_reason(decision_context)
            )

        question = self.select_diagnostic_question(
            graph=graph,
            working_map=working_map,
            visible_dialogue_context=visible_dialogue_context,
            decision_context=decision_context,
        )
        if question is None:
            return FinalizeReconstructionDecision(
                reason="No diagnostic question selected."
            )
        return AskDiagnosticQuestionDecision(question=question)

    def assess_after_visible_answer(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> tuple[WorkingMapNodeAssessmentUpdate, ...]:
        return ()

    def select_diagnostic_question(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> DiagnosticQuestion | None:
        return None


def _must_finalize(decision_context: DecisionPhaseContext) -> bool:
    return (
        decision_context.phase == DecisionPhase.FORCED_FINALIZATION
        or decision_context.remaining_diagnostic_turns == 0
    )


def _finalization_reason(decision_context: DecisionPhaseContext) -> str:
    if decision_context.phase == DecisionPhase.FORCED_FINALIZATION:
        return "Forced finalization phase requires final reconstruction."
    return "No diagnostic turns remain."
