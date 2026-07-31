import unittest

from backend.knowact.agents.agents.evidence_calibrated import (
    EvidenceCalibratedLLMTestedAgent,
    parse_diagnostic_candidate_output,
    parse_evidence_likelihood_output,
)
from backend.knowact.agents.belief import MasteryBelief, MasteryLikelihood
from backend.knowact.agents.protocol import DecisionPhase, DecisionPhaseContext
from backend.knowact.agents.tools import update_node_assessments
from backend.knowact.agents.working_map import AgentWorkingKnowledgeMap, initialize_working_map
from backend.knowact.core.graph import KnowledgeGraph, KnowledgeNode
from backend.knowact.core.interaction import (
    CoarseObservationMetadata,
    DiagnosticQuestion,
    VisibleDialogueContext,
    VisibleDialogueTurn,
    VisibleObservationKind,
    VisibleSimulatorAnswer,
)
from backend.knowact.core.episode import EpisodeExecutionConfiguration
from backend.knowact.llm.client import ModelClientError, ModelClientMetadata
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE
from backend.knowact.runtime.episode_options import build_episode_model_catalog
from backend.knowact.runtime.runner import EpisodeRunAgentKind, EpisodeRunRequest


class V1EvidenceCalibratedAgentTest(unittest.TestCase):
    def test_belief_update_is_normalized_and_projects_deterministically(self):
        prior = MasteryBelief.uniform()
        likelihood = MasteryLikelihood(
            l0=0.01,
            l1=0.03,
            l2=0.06,
            l3=0.80,
            l4=0.08,
            l5=0.02,
        )

        posterior = prior.bayes_update(likelihood)

        self.assertAlmostEqual(1.0, sum(posterior.values))
        self.assertEqual("L3", posterior.mode_level)
        self.assertEqual("L3", posterior.project()[0])

    def test_agent_persists_posterior_and_visible_evidence(self):
        model_client = _FakeModelClient(
            responses=(
                """
                {
                  "updates": [
                    {
                      "node_id": "node_a",
                      "answer_likelihood": {
                        "l0": 0.01, "l1": 0.03, "l2": 0.06,
                        "l3": 0.80, "l4": 0.08, "l5": 0.02
                      },
                      "observed_behavior": "Applied the distinction correctly.",
                      "supporting_turn_ids": ["turn_01"],
                      "contradiction": false
                    }
                  ]
                }
                """,
            )
        )
        agent = EvidenceCalibratedLLMTestedAgent(model_client=model_client)
        working_map = _working_map()

        updates = agent.assess_after_visible_answer(
            graph=_graph(),
            working_map=working_map,
            visible_dialogue_context=_dialogue(),
            decision_context=_after_answer_context(),
        )
        updated = update_node_assessments(
            working_map=working_map,
            graph=_graph(),
            visible_dialogue_context=_dialogue(),
            updates=updates,
        )
        restored = AgentWorkingKnowledgeMap.model_validate(
            updated.model_dump(mode="json")
        )

        state = restored.assessment_by_node_id["node_a"]
        self.assertEqual("L3", state.assessed_mastery_level)
        self.assertEqual(("turn_01",), state.supporting_turn_ids)
        self.assertIsNotNone(state.mastery_belief)
        self.assertEqual("L3", state.mastery_belief.mode_level)
        self.assertIn("answer_likelihood", _client_error_context(model_client))

    def test_agent_selects_highest_deterministic_candidate_utility(self):
        model_client = _FakeModelClient(responses=(_candidate_payload(),))
        agent = EvidenceCalibratedLLMTestedAgent(model_client=model_client)

        decision = agent.decide_next_action(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue(),
            decision_context=_after_answer_context(),
        )

        self.assertEqual("q_high", decision.question.question_id)
        self.assertEqual("node_a", decision.diagnostic_plan.primary_target_node_id)
        self.assertIsNotNone(decision.diagnostic_plan.utility_trace)
        self.assertGreater(
            decision.diagnostic_plan.utility_trace.selected_utility,
            0.9,
        )

    def test_forced_finalization_does_not_call_model(self):
        model_client = _FakeModelClient(responses=())
        agent = EvidenceCalibratedLLMTestedAgent(model_client=model_client)

        decision = agent.decide_next_action(
            graph=_graph(),
            working_map=_working_map(),
            visible_dialogue_context=_dialogue(),
            decision_context=DecisionPhaseContext(
                phase=DecisionPhase.FORCED_FINALIZATION,
                remaining_diagnostic_turns=0,
            ),
        )

        self.assertEqual("finalize_reconstruction", decision.kind)
        self.assertEqual(0, len(model_client.messages))

    def test_parsers_reject_invalid_contracts(self):
        with self.assertRaisesRegex(ModelClientError, "invalid JSON"):
            parse_evidence_likelihood_output("not json")
        with self.assertRaisesRegex(ModelClientError, "invalid diagnostic candidates"):
            parse_diagnostic_candidate_output(
                '{"action":"ask_diagnostic_question","candidates":[]}'
            )

    def test_runtime_contract_registers_evidence_calibrated_kind(self):
        configuration = EpisodeExecutionConfiguration(
            agent_kind="evidence_calibrated_agent",
            tested_agent_client_provider="openai",
            tested_agent_model="model-a",
            simulator_client_provider="deepseek",
            simulator_model="model-b",
            tested_agent_temperature=0.0,
            max_tool_retries=3,
        )
        request = EpisodeRunRequest(
            episode_id="episode_a",
            agent_kind=EpisodeRunAgentKind.EVIDENCE_CALIBRATED_AGENT,
        )

        self.assertEqual("evidence_calibrated_agent", configuration.agent_kind)
        self.assertEqual(
            EpisodeRunAgentKind.EVIDENCE_CALIBRATED_AGENT,
            request.agent_kind,
        )
        self.assertIn(
            "evidence_calibrated_agent",
            build_episode_model_catalog({}).agent_kinds,
        )


class _FakeModelClient:
    message_profile = OPENAI_MESSAGE_PROFILE
    metadata = ModelClientMetadata(
        provider="fake",
        model_name="fake-ecda",
        message_profile=OPENAI_MESSAGE_PROFILE.name,
    )

    def __init__(self, *, responses: tuple[str, ...]) -> None:
        self._responses = list(responses)
        self.messages = []

    def complete(self, *, messages, temperature=None):
        self.messages.append(tuple(messages))
        if not self._responses:
            raise AssertionError("No fake model response configured")
        return self._responses.pop(0)


def _client_error_context(model_client: _FakeModelClient) -> str:
    return " ".join(message.content for message in model_client.messages[0])


def _candidate_payload() -> str:
    return """
    {
      "action": "ask_diagnostic_question",
      "candidates": [
        {
          "question": {"text": "Low utility?", "question_id": "q_low"},
          "diagnostic_plan": {
            "primary_target_node_id": "node_a",
            "secondary_target_node_ids": [],
            "target_mastery_boundary": "L1_vs_L2",
            "selection_reason": "Low-value probe."
          },
          "estimated_information_gain": 0.2,
          "coverage_gain": 0.1,
          "graph_leverage": 0.0,
          "redundancy": 0.4,
          "complexity": 0.1,
          "outcome_model_confidence": 0.5
        },
        {
          "question": {"text": "High utility?", "question_id": "q_high"},
          "diagnostic_plan": {
            "primary_target_node_id": "node_a",
            "secondary_target_node_ids": [],
            "target_mastery_boundary": "L2_vs_L3",
            "selection_reason": "High-value probe."
          },
          "estimated_information_gain": 0.9,
          "coverage_gain": 0.7,
          "graph_leverage": 0.2,
          "redundancy": 0.0,
          "complexity": 0.1,
          "outcome_model_confidence": 0.9
        },
        {
          "question": {"text": "Medium utility?", "question_id": "q_medium"},
          "diagnostic_plan": {
            "primary_target_node_id": "node_a",
            "secondary_target_node_ids": [],
            "target_mastery_boundary": "L3_vs_L4",
            "selection_reason": "Medium-value probe."
          },
          "estimated_information_gain": 0.5,
          "coverage_gain": 0.3,
          "graph_leverage": 0.0,
          "redundancy": 0.1,
          "complexity": 0.1,
          "outcome_model_confidence": 0.8
        }
      ]
    }
    """


def _graph() -> KnowledgeGraph:
    return KnowledgeGraph(
        nodes=(
            KnowledgeNode(
                id="node_a",
                name="Concept A",
                type="concept",
                levels={
                    "L0": "No recognition.",
                    "L3": "Can apply the distinction.",
                },
            ),
        )
    )


def _working_map() -> AgentWorkingKnowledgeMap:
    return initialize_working_map(
        episode_id="episode_a",
        benchmark_domain="domain_a",
        graph_version="v1",
        graph=_graph(),
    )


def _dialogue() -> VisibleDialogueContext:
    return VisibleDialogueContext(
        turns=(
            VisibleDialogueTurn(
                turn_id="turn_01",
                question=DiagnosticQuestion(text="Explain the distinction."),
                answer=VisibleSimulatorAnswer(text="A correct applied distinction."),
                observation=CoarseObservationMetadata(kind=VisibleObservationKind.ANSWER),
            ),
        )
    )


def _after_answer_context() -> DecisionPhaseContext:
    return DecisionPhaseContext(
        phase=DecisionPhase.AFTER_ANSWER,
        remaining_diagnostic_turns=1,
    )


if __name__ == "__main__":
    unittest.main()
