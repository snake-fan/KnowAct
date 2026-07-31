import unittest

from backend.knowact.agents.protocol import DiagnosticQuestionPlan
from backend.knowact.agents.question_selection import (
    DiagnosticCandidate,
    DiagnosticCandidateError,
    score_diagnostic_candidate,
    select_diagnostic_candidate,
)
from backend.knowact.core.graph import KnowledgeGraph, KnowledgeNode
from backend.knowact.core.interaction import DiagnosticQuestion


class V1QuestionSelectionTest(unittest.TestCase):
    def test_utility_shrinks_information_gain_and_penalizes_redundancy(self):
        candidate = _candidate(
            question_id="q1",
            information_gain=0.8,
            confidence=0.5,
            coverage=0.4,
            redundancy=0.2,
        )

        score = score_diagnostic_candidate(candidate)

        self.assertAlmostEqual(0.47, score)

    def test_selector_uses_stable_tie_order_and_skips_asked_ids(self):
        first = _candidate(question_id="q1", information_gain=0.7)
        second = _candidate(question_id="q2", information_gain=0.7)

        tied = select_diagnostic_candidate((first, second), graph=_graph())
        after_first = select_diagnostic_candidate(
            (first, second),
            graph=_graph(),
            asked_question_ids={"q1"},
        )

        self.assertEqual("q1", tied.candidate.question.question_id)
        self.assertEqual("q2", after_first.candidate.question.question_id)

    def test_selector_rejects_unknown_target(self):
        candidate = _candidate(question_id="q1").model_copy(
            update={
                "diagnostic_plan": DiagnosticQuestionPlan(
                    primary_target_node_id="missing",
                    target_mastery_boundary="L2_vs_L3",
                    selection_reason="Boundary probe.",
                )
            }
        )

        with self.assertRaisesRegex(DiagnosticCandidateError, "unknown graph"):
            select_diagnostic_candidate((candidate,), graph=_graph())


def _candidate(
    *,
    question_id: str,
    information_gain: float = 0.5,
    confidence: float = 1.0,
    coverage: float = 0.0,
    redundancy: float = 0.0,
) -> DiagnosticCandidate:
    return DiagnosticCandidate(
        question=DiagnosticQuestion(text="Explain the distinction.", question_id=question_id),
        diagnostic_plan=DiagnosticQuestionPlan(
            primary_target_node_id="node_a",
            target_mastery_boundary="L2_vs_L3",
            selection_reason="Boundary probe.",
        ),
        estimated_information_gain=information_gain,
        coverage_gain=coverage,
        graph_leverage=0.0,
        redundancy=redundancy,
        complexity=0.0,
        outcome_model_confidence=confidence,
    )


def _graph() -> KnowledgeGraph:
    return KnowledgeGraph(nodes=(KnowledgeNode(id="node_a", name="A", type="concept"),))


if __name__ == "__main__":
    unittest.main()
