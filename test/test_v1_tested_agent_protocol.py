import inspect
import unittest

from pydantic import TypeAdapter, ValidationError

from backend.knowact.agents.protocol import (
    AskDiagnosticQuestionDecision,
    DecisionPhase,
    DecisionPhaseContext,
    FinalizeReconstructionDecision,
    TestedAgent,
    TestedAgentDecision,
)
from backend.knowact.core.interaction import DiagnosticQuestion


class V1TestedAgentProtocolTest(unittest.TestCase):
    def test_decision_phase_context_rejects_negative_remaining_turns(self):
        with self.assertRaises(ValidationError):
            DecisionPhaseContext(
                phase=DecisionPhase.AFTER_ANSWER,
                remaining_diagnostic_turns=-1,
            )

    def test_ask_diagnostic_question_decision_requires_valid_question(self):
        decision = AskDiagnosticQuestionDecision(
            question=DiagnosticQuestion(text="How do you use a validation set?")
        )

        self.assertEqual("ask_diagnostic_question", decision.kind)
        self.assertEqual(
            "How do you use a validation set?",
            decision.question.text,
        )

        with self.assertRaises(ValidationError):
            AskDiagnosticQuestionDecision.model_validate(
                {
                    "kind": "ask_diagnostic_question",
                    "question": {"text": " "},
                }
            )

    def test_finalize_reconstruction_decision_reason_is_optional_but_nonblank(self):
        decision = FinalizeReconstructionDecision()

        self.assertEqual("finalize_reconstruction", decision.kind)
        self.assertIsNone(decision.reason)

        with self.assertRaises(ValidationError):
            FinalizeReconstructionDecision(reason=" ")

    def test_tested_agent_decision_union_uses_kind_discriminator(self):
        adapter = TypeAdapter(TestedAgentDecision)

        ask_decision = adapter.validate_python(
            {
                "kind": "ask_diagnostic_question",
                "question": {"text": "Explain a precision/recall tradeoff."},
            }
        )
        finalize_decision = adapter.validate_python(
            {
                "kind": "finalize_reconstruction",
                "reason": "No diagnostic turns remain.",
            }
        )

        self.assertIsInstance(ask_decision, AskDiagnosticQuestionDecision)
        self.assertIsInstance(finalize_decision, FinalizeReconstructionDecision)

    def test_protocol_methods_receive_decision_phase_context(self):
        update_signature = inspect.signature(TestedAgent.update_after_visible_answer)
        decide_signature = inspect.signature(TestedAgent.decide_next_action)

        self.assertIn("decision_context", update_signature.parameters)
        self.assertIn("decision_context", decide_signature.parameters)
        self.assertFalse(hasattr(TestedAgent, "choose_next_question"))


if __name__ == "__main__":
    unittest.main()
