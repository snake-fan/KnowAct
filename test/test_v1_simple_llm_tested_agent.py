import unittest

from backend.knowact.agents.protocol import DecisionPhase, DecisionPhaseContext
from backend.knowact.agents.agents.simple_llm import (
    SimpleLLMTestedAgent,
    parse_assessment_update_output,
    parse_next_decision_output,
    parse_next_question_output,
)
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
from backend.knowact.llm.client import ModelClientError, ModelClientMetadata
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage


class V1SimpleLLMTestedAgentTest(unittest.TestCase):
    def test_assess_after_visible_answer_parses_model_updates(self):
        model_client = _FakeModelClient(
            responses=(
                """
                {
                  "updates": [
                    {
                      "node_id": "train_test_split",
                      "assessed_mastery_level": "L3",
                      "diagnostic_confidence": "high",
                      "assessment_note": "The user explained held-out testing.",
                      "supporting_turn_ids": ["turn_01"]
                    }
                  ]
                }
                """,
            )
        )
        agent = SimpleLLMTestedAgent(model_client=model_client, temperature=0.2)

        updates = agent.assess_after_visible_answer(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue(),
            decision_context=DecisionPhaseContext(
                phase=DecisionPhase.AFTER_ANSWER,
                remaining_diagnostic_turns=1,
            ),
        )

        self.assertEqual(1, len(updates))
        self.assertEqual("train_test_split", updates[0].node_id)
        self.assertEqual("L3", updates[0].assessed_mastery_level)
        self.assertEqual(("turn_01",), updates[0].supporting_turn_ids)
        self.assertEqual((0.2,), tuple(model_client.temperatures))
        self.assertIn("Visible runtime payload", model_client.messages[0][1].content)

    def test_select_diagnostic_question_parses_model_question(self):
        model_client = _FakeModelClient(
            responses=(
                """
                {
                  "action": "ask_diagnostic_question",
                  "question": {
                    "text": "How would you detect overfitting with a validation set?",
                    "question_id": "q_overfitting_validation"
                  },
                  "diagnostic_plan": {
                    "primary_target_node_id": "overfitting",
                    "secondary_target_node_ids": ["train_test_split"],
                    "target_mastery_boundary": "L2_vs_L3",
                    "selection_reason": "One scenario tests linked diagnosis and held-out evaluation."
                  }
                }
                """,
            )
        )
        agent = SimpleLLMTestedAgent(model_client=model_client)

        question = agent.select_diagnostic_question(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue(),
            decision_context=DecisionPhaseContext(
                phase=DecisionPhase.AFTER_ANSWER,
                remaining_diagnostic_turns=1,
            ),
        )

        self.assertIsNotNone(question)
        self.assertEqual(
            "How would you detect overfitting with a validation set?",
            question.text,
        )
        self.assertEqual("q_overfitting_validation", question.question_id)

    def test_next_decision_preserves_multi_node_diagnostic_plan(self):
        decision = parse_next_decision_output(
            """
            {
              "action": "ask_diagnostic_question",
              "question": {"text": "Diagnose this model evaluation failure."},
              "diagnostic_plan": {
                "primary_target_node_id": "overfitting",
                "secondary_target_node_ids": ["train_test_split"],
                "target_mastery_boundary": "L2_vs_L3",
                "selection_reason": "The integrated scenario tests both nodes."
              }
            }
            """
        )

        self.assertEqual(
            "overfitting",
            decision.diagnostic_plan.primary_target_node_id,
        )
        self.assertEqual(
            ("train_test_split",),
            decision.diagnostic_plan.secondary_target_node_ids,
        )

    def test_select_diagnostic_question_returns_none_for_finalize_action(self):
        model_client = _FakeModelClient(
            responses=(
                """
                {
                  "action": "finalize_reconstruction",
                  "reason": "The current working map is sufficiently supported."
                }
                """,
            )
        )
        agent = SimpleLLMTestedAgent(model_client=model_client)

        question = agent.select_diagnostic_question(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue(),
            decision_context=DecisionPhaseContext(
                phase=DecisionPhase.AFTER_ANSWER,
                remaining_diagnostic_turns=1,
            ),
        )

        self.assertIsNone(question)

    def test_parsers_reject_invalid_model_payloads(self):
        with self.assertRaisesRegex(ModelClientError, "invalid JSON"):
            parse_assessment_update_output("not json")

        with self.assertRaisesRegex(ModelClientError, "omitted question"):
            parse_next_question_output('{"action": "ask_diagnostic_question"}')

        with self.assertRaisesRegex(ModelClientError, "omitted diagnostic plan"):
            parse_next_question_output(
                '{"action":"ask_diagnostic_question","question":{"text":"Explain."}}'
            )


class _FakeModelClient:
    message_profile = OPENAI_MESSAGE_PROFILE
    metadata = ModelClientMetadata(
        provider="fake",
        model_name="fake-simple-llm-agent",
        message_profile=OPENAI_MESSAGE_PROFILE.name,
    )

    def __init__(self, *, responses: tuple[str, ...]) -> None:
        self._responses = list(responses)
        self.messages: list[tuple[ModelMessage, ...]] = []
        self.temperatures: list[float | None] = []

    def complete(
        self,
        *,
        messages,
        temperature: float | None = None,
    ) -> str:
        self.messages.append(tuple(messages))
        self.temperatures.append(temperature)
        if not self._responses:
            raise AssertionError("No fake model response configured")
        return self._responses.pop(0)


def _graph() -> KnowledgeGraph:
    return KnowledgeGraph(
        nodes=(
            KnowledgeNode(
                id="train_test_split",
                name="Train/Test Split",
                type="concept",
                definition="A split between training and held-out test data.",
                diagnostic_goal="Check whether the user understands held-out evaluation.",
                levels={
                    "L0": "Does not recognize train/test split.",
                    "L3": "Explains held-out evaluation and leakage risks.",
                },
            ),
            KnowledgeNode(
                id="overfitting",
                name="Overfitting",
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
