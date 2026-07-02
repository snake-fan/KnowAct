import unittest

from backend.knowact.agents.base import BaseTestedAgent
from backend.knowact.agents.protocol import (
    AskDiagnosticQuestionDecision,
    DecisionPhase,
    DecisionPhaseContext,
    FinalizeReconstructionDecision,
)
from backend.knowact.agents.tools import WorkingMapNodeAssessmentUpdate
from backend.knowact.agents.working_map import (
    AgentWorkingKnowledgeMap,
    initialize_working_map,
)
from backend.knowact.core.graph import KnowledgeGraph, KnowledgeNode
from backend.knowact.core.interaction import (
    CoarseObservationMetadata,
    DiagnosticQuestion,
    VisibleDialogueContext,
    VisibleDialogueTurn,
    VisibleObservationKind,
    VisibleSimulatorAnswer,
)


class V1TestedAgentBaseTest(unittest.TestCase):
    def test_initial_question_phase_does_not_update_working_map(self):
        agent = _RecordingTestedAgent(
            updates=(
                WorkingMapNodeAssessmentUpdate(
                    node_id="train_test_split",
                    assessed_mastery_level="L3",
                    diagnostic_confidence="high",
                    assessment_note="Would be invalid before an answer.",
                    supporting_turn_ids=("turn_01",),
                ),
            )
        )

        updates = agent.update_after_visible_answer(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=VisibleDialogueContext(),
            decision_context=DecisionPhaseContext(
                phase=DecisionPhase.INITIAL_QUESTION,
                remaining_diagnostic_turns=2,
            ),
        )

        self.assertEqual((), updates)
        self.assertEqual(0, agent.assessment_calls)

    def test_after_answer_phase_delegates_to_assessment_hook(self):
        expected_updates = (
            WorkingMapNodeAssessmentUpdate(
                node_id="train_test_split",
                assessed_mastery_level="L3",
                diagnostic_confidence="high",
                assessment_note="The user explained held-out testing.",
                supporting_turn_ids=("turn_01",),
            ),
        )
        agent = _RecordingTestedAgent(updates=expected_updates)

        updates = agent.update_after_visible_answer(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue(),
            decision_context=DecisionPhaseContext(
                phase=DecisionPhase.AFTER_ANSWER,
                remaining_diagnostic_turns=1,
            ),
        )

        self.assertEqual(expected_updates, updates)
        self.assertEqual(1, agent.assessment_calls)

    def test_decide_next_action_asks_selected_question_when_turns_remain(self):
        agent = _RecordingTestedAgent(
            question=DiagnosticQuestion(
                text="How would you detect overfitting with a validation set?"
            )
        )

        decision = agent.decide_next_action(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue(),
            decision_context=DecisionPhaseContext(
                phase=DecisionPhase.AFTER_ANSWER,
                remaining_diagnostic_turns=1,
            ),
        )

        self.assertIsInstance(decision, AskDiagnosticQuestionDecision)
        self.assertEqual(
            "How would you detect overfitting with a validation set?",
            decision.question.text,
        )
        self.assertEqual(1, agent.selection_calls)

    def test_decide_next_action_finalizes_when_no_turns_remain(self):
        agent = _RecordingTestedAgent(
            question=DiagnosticQuestion(text="This should not be asked.")
        )

        decision = agent.decide_next_action(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue(),
            decision_context=DecisionPhaseContext(
                phase=DecisionPhase.AFTER_ANSWER,
                remaining_diagnostic_turns=0,
            ),
        )

        self.assertIsInstance(decision, FinalizeReconstructionDecision)
        self.assertEqual("No diagnostic turns remain.", decision.reason)
        self.assertEqual(0, agent.selection_calls)

    def test_decide_next_action_finalizes_during_forced_finalization(self):
        agent = _RecordingTestedAgent(
            question=DiagnosticQuestion(text="This should not be asked.")
        )

        decision = agent.decide_next_action(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue(),
            decision_context=DecisionPhaseContext(
                phase=DecisionPhase.FORCED_FINALIZATION,
                remaining_diagnostic_turns=1,
            ),
        )

        self.assertIsInstance(decision, FinalizeReconstructionDecision)
        self.assertEqual(
            "Forced finalization phase requires final reconstruction.",
            decision.reason,
        )
        self.assertEqual(0, agent.selection_calls)

    def test_decide_next_action_finalizes_when_no_question_is_selected(self):
        agent = _RecordingTestedAgent()

        decision = agent.decide_next_action(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue(),
            decision_context=DecisionPhaseContext(
                phase=DecisionPhase.AFTER_ANSWER,
                remaining_diagnostic_turns=1,
            ),
        )

        self.assertIsInstance(decision, FinalizeReconstructionDecision)
        self.assertEqual("No diagnostic question selected.", decision.reason)
        self.assertEqual(1, agent.selection_calls)


class _RecordingTestedAgent(BaseTestedAgent):
    def __init__(
        self,
        *,
        question: DiagnosticQuestion | None = None,
        updates: tuple[WorkingMapNodeAssessmentUpdate, ...] = (),
    ) -> None:
        self.question = question
        self.updates = updates
        self.assessment_calls = 0
        self.selection_calls = 0

    def assess_after_visible_answer(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> tuple[WorkingMapNodeAssessmentUpdate, ...]:
        self.assessment_calls += 1
        return self.updates

    def select_diagnostic_question(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> DiagnosticQuestion | None:
        self.selection_calls += 1
        return self.question


def _graph() -> KnowledgeGraph:
    return KnowledgeGraph(
        nodes=(
            KnowledgeNode(
                id="train_test_split",
                name="Train/Test Split",
                type="concept",
            ),
        )
    )


def _working_map() -> AgentWorkingKnowledgeMap:
    return initialize_working_map(
        episode_id="episode_a",
        benchmark_domain="classical_supervised_ml_algorithms",
        graph_version="v1",
        graph=_graph(),
    )


def _dialogue() -> VisibleDialogueContext:
    return VisibleDialogueContext(
        turns=(
            VisibleDialogueTurn(
                turn_id="turn_01",
                question=DiagnosticQuestion(
                    text="Why do we keep a test set separate?"
                ),
                answer=VisibleSimulatorAnswer(
                    text="To check performance on held-out data."
                ),
                observation=CoarseObservationMetadata(
                    kind=VisibleObservationKind.ANSWER
                ),
            ),
        )
    )


if __name__ == "__main__":
    unittest.main()
