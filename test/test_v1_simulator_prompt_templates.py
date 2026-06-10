import unittest

from backend.knowact.core.interaction import VisibleSimulatorAnswer
from backend.knowact.simulator.grounding import QuestionGroundingResult
from backend.knowact.simulator.policy import (
    GroundedNodeAnswerDecision,
    RuleBasedAnswerPolicy,
    SimulatorAnswerIntent,
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
        self.assertIn("answer_strategy", developer_prompt)
        self.assertNotIn('"visibility_guards"', developer_prompt)

    def test_answer_generation_template_is_structured_and_deidentified(self):
        intent = _answer_intent()

        messages = build_answer_generation_messages(
            intent=intent,
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
        self.assertIn("answer_intent", user_payload)
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
        intent = _answer_intent()

        messages = build_answer_validation_messages(
            candidate_answer=VisibleSimulatorAnswer(
                text="I understand held-out evaluation but mix up validation details."
            ),
            intent=intent,
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
        self.assertIn("answer_intent", user_payload)
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


def _answer_intent() -> SimulatorAnswerIntent:
    return SimulatorAnswerIntent(
        question_text="How would you use a train/test split?",
        response_mode=SimulatorResponseMode.ANSWER,
        primary_stance=SimulatorAnswerStance.PARTIAL_UNDERSTANDING,
        answer_strategy="Answer as the synthetic user with partial understanding.",
        node_decisions=(
            GroundedNodeAnswerDecision(
                node_name="Train/Test Split",
                stance=SimulatorAnswerStance.PARTIAL_UNDERSTANDING,
                answer_focus=(
                    "Can explain why held-out evaluation is useful but "
                    "mixes up validation details."
                ),
                boundary_focus="When validation differs from final testing.",
                supporting_signals=(),
            ),
        ),
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
