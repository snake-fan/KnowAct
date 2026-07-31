import unittest

from backend.knowact.agents.agents.question_bank import (
    DiagnosticQuestionBank,
    FixedQuestionBankTestedAgent,
    QuestionBankItem,
    RandomQuestionBankTestedAgent,
)
from backend.knowact.agents.protocol import (
    DecisionPhase,
    DecisionPhaseContext,
    DiagnosticQuestionPlan,
)
from backend.knowact.agents.working_map import initialize_working_map
from backend.knowact.core.graph import KnowledgeGraph, KnowledgeNode
from backend.knowact.core.interaction import (
    CoarseObservationMetadata,
    DiagnosticQuestion,
    VisibleDialogueContext,
    VisibleDialogueTurn,
    VisibleObservationKind,
    VisibleSimulatorAnswer,
)
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE


class V1QuestionBankAgentsTest(unittest.TestCase):
    def test_fixed_agent_follows_bank_order_without_repeating(self):
        agent = FixedQuestionBankTestedAgent(
            model_client=_UnusedModelClient(),
            question_bank=_bank(),
        )

        first = agent.decide_next_action(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=VisibleDialogueContext(),
            decision_context=_decision_context(),
        )
        second = agent.decide_next_action(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue_with(first.question),
            decision_context=_decision_context(),
        )

        self.assertEqual("q1", first.question.question_id)
        self.assertEqual("q2", second.question.question_id)

    def test_random_agent_is_resume_stable_for_same_visible_history(self):
        first_agent = RandomQuestionBankTestedAgent(
            model_client=_UnusedModelClient(),
            question_bank=_bank(),
            seed="episode-17",
        )
        resumed_agent = RandomQuestionBankTestedAgent(
            model_client=_UnusedModelClient(),
            question_bank=_bank(),
            seed="episode-17",
        )

        first = first_agent.decide_next_action(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=VisibleDialogueContext(),
            decision_context=_decision_context(),
        )
        resumed = resumed_agent.decide_next_action(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=VisibleDialogueContext(),
            decision_context=_decision_context(),
        )

        self.assertEqual(first.question.question_id, resumed.question.question_id)


class _UnusedModelClient:
    message_profile = OPENAI_MESSAGE_PROFILE
    metadata = ModelClientMetadata(
        provider="fake",
        model_name="unused",
        message_profile=OPENAI_MESSAGE_PROFILE.name,
    )

    def complete(self, *, messages, temperature=None):
        raise AssertionError("question selection must not call the assessment model")


def _bank() -> DiagnosticQuestionBank:
    return DiagnosticQuestionBank(
        bank_id="bank_a",
        version="v1",
        items=tuple(_item(index) for index in range(1, 4)),
    )


def _item(index: int) -> QuestionBankItem:
    return QuestionBankItem(
        question=DiagnosticQuestion(text=f"Question {index}?", question_id=f"q{index}"),
        diagnostic_plan=DiagnosticQuestionPlan(
            primary_target_node_id="node_a",
            target_mastery_boundary="broad_probe",
            selection_reason="Registered bank item.",
        ),
    )


def _graph() -> KnowledgeGraph:
    return KnowledgeGraph(nodes=(KnowledgeNode(id="node_a", name="A", type="concept"),))


def _working_map():
    return initialize_working_map(
        episode_id="episode_a",
        benchmark_domain="domain_a",
        graph_version="v1",
        graph=_graph(),
    )


def _decision_context() -> DecisionPhaseContext:
    return DecisionPhaseContext(
        phase=DecisionPhase.INITIAL_QUESTION,
        remaining_diagnostic_turns=2,
    )


def _dialogue_with(question: DiagnosticQuestion) -> VisibleDialogueContext:
    return VisibleDialogueContext(
        turns=(
            VisibleDialogueTurn(
                turn_id="turn_01",
                question=question,
                answer=VisibleSimulatorAnswer(text="Answer."),
                observation=CoarseObservationMetadata(kind=VisibleObservationKind.ANSWER),
            ),
        )
    )


if __name__ == "__main__":
    unittest.main()
