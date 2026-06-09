import unittest

from backend.knowact.core.interaction import VisibleSimulatorAnswer
from backend.knowact.simulator.expression import (
    NodeExpressionContext,
    SimulatorExpressionContext,
)
from backend.knowact.simulator.policy import SimulatorAnswerStance
from backend.knowact.simulator.templates.answer_generation import (
    build_answer_generation_messages,
)
from backend.knowact.simulator.templates.answer_validation import (
    build_answer_validation_messages,
)


class V1SimulatorPromptTemplatesTest(unittest.TestCase):
    def test_answer_generation_template_is_structured_and_deidentified(self):
        expression_context = _expression_context()

        messages = build_answer_generation_messages(
            expression_context=expression_context,
        )

        self.assertEqual(2, len(messages))
        developer_prompt = messages[0].content
        for section in (
            "Role:",
            "Objective:",
            "Inputs:",
            "Process:",
            "Decision rules:",
            "Output contract:",
            "Example:",
            "Final check before output:",
        ):
            with self.subTest(section=section):
                self.assertIn(section, developer_prompt)

        user_payload = messages[1].content
        self.assertIn("simulator_expression_context", user_payload)
        self.assertIn("held-out evaluation", user_payload)
        for hidden_fragment in (
            "mastery_level",
            "evidence_refs",
            "ev_hidden",
            "synthetic_user",
            "map_manifest",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, user_payload)

    def test_answer_validation_template_is_structured_and_deidentified(self):
        expression_context = _expression_context()

        messages = build_answer_validation_messages(
            candidate_answer=VisibleSimulatorAnswer(
                text="I understand held-out evaluation but mix up validation details."
            ),
            expression_context=expression_context,
        )

        self.assertEqual(2, len(messages))
        developer_prompt = messages[0].content
        for section in (
            "Role:",
            "Objective:",
            "Inputs:",
            "Process:",
            "Blocking safety rules:",
            "Intent coverage rules:",
            "Output contract:",
            "Example:",
            "Final check before output:",
        ):
            with self.subTest(section=section):
                self.assertIn(section, developer_prompt)

        user_payload = messages[1].content
        self.assertIn("candidate_answer", user_payload)
        self.assertIn("simulator_expression_context", user_payload)
        self.assertIn("held-out evaluation", user_payload)
        for hidden_fragment in (
            "mastery_level",
            "evidence_refs",
            "ev_hidden",
            "synthetic_user",
            "map_manifest",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, user_payload)


def _expression_context() -> SimulatorExpressionContext:
    return SimulatorExpressionContext(
        question_text="How would you use a train/test split?",
        primary_stance=SimulatorAnswerStance.PARTIAL_UNDERSTANDING,
        nodes=(
            NodeExpressionContext(
                node_name="Train/Test Split",
                stance=SimulatorAnswerStance.PARTIAL_UNDERSTANDING,
                evidence_signals=(
                    "Can explain why held-out evaluation is useful but "
                    "mixes up validation details.",
                ),
                misconception_cues=(),
                unknown_cues=("When validation differs from final testing.",),
            ),
        ),
    )


if __name__ == "__main__":
    unittest.main()
