import unittest

from backend.knowact.core.interaction import VisibleSimulatorAnswer
from backend.knowact.simulator.expression import (
    NodeExpressionContext,
    SimulatorExpressionContext,
)
from backend.knowact.simulator.grounding import QuestionGroundingResult
from backend.knowact.simulator.policy import (
    RuleBasedAnswerPolicy,
    SimulatorAnswerStance,
    SimulatorResponseMode,
)
from backend.knowact.simulator.templates.answer_policy import (
    build_answer_policy_messages,
)
from backend.knowact.simulator.templates.answer_generation import (
    build_answer_generation_messages,
)
from backend.knowact.simulator.templates.answer_validation import (
    build_answer_validation_messages,
)


class V1SimulatorPromptTemplatesTest(unittest.TestCase):
    def test_answer_policy_template_is_structured_and_hidden_input_bounded(self):
        fallback_intent = RuleBasedAnswerPolicy().derive_intent(
            question_text="What should I study next?",
            simulator_context=_empty_simulator_context(),
        )

        messages = build_answer_policy_messages(
            question_text="What should I study next?",
            simulator_context=_empty_simulator_context(),
            grounding=QuestionGroundingResult(),
            fallback_intent=fallback_intent,
        )

        self.assertEqual(2, len(messages))
        developer_prompt = messages[0].content
        for section in (
            "Role:",
            "Objective:",
            "Inputs:",
            "Process:",
            "Visibility rules:",
            "Output contract:",
            "Final check before output:",
        ):
            with self.subTest(section=section):
                self.assertIn(section, developer_prompt)
        self.assertIn("strict JSON", developer_prompt)
        self.assertIn("response_mode", developer_prompt)

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
        response_mode=SimulatorResponseMode.ANSWER,
        primary_stance=SimulatorAnswerStance.PARTIAL_UNDERSTANDING,
        overall_directive="Answer the diagnostic question as the synthetic user.",
        nodes=(
            NodeExpressionContext(
                node_name="Train/Test Split",
                stance=SimulatorAnswerStance.PARTIAL_UNDERSTANDING,
                capability_summary=(
                    "Can explain why held-out evaluation is useful but "
                    "mixes up validation details."
                ),
                limitation_summary="When validation differs from final testing.",
                evidence_signals=(
                    "Can explain why held-out evaluation is useful but "
                    "mixes up validation details.",
                ),
                misconception_cues=(),
                unknown_cues=("When validation differs from final testing.",),
            ),
        ),
        generation_directives=("Use first-person wording.",),
        visibility_guards=("No hidden ids.",),
    )


def _empty_simulator_context():
    from backend.knowact.simulator.context_builder import SimulatorTurnContext

    return SimulatorTurnContext(
        benchmark_domain="classical_supervised_ml_algorithms",
        map_id="gt_map_001",
        graph_version="v1",
        user_id="synthetic_user_001",
        grounded_nodes=(),
    )


if __name__ == "__main__":
    unittest.main()
