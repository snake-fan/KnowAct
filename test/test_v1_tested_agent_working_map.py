import unittest

from backend.knowact.agents.tools import (
    FinalizationWarningCode,
    WorkingMapNodeAssessmentUpdate,
    finalize_reconstructed_map,
    update_node_assessments,
)
from backend.knowact.agents.working_map import (
    AgentWorkingKnowledgeMap,
    WorkingMapNodeAssessment,
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
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.map import validate_knowledge_map


class V1TestedAgentWorkingMapTest(unittest.TestCase):
    def test_initialize_working_map_creates_full_graph_unknown_shell(self):
        graph = _graph()

        working_map = initialize_working_map(
            episode_id="episode_a",
            benchmark_domain="classical_supervised_ml_algorithms",
            graph_version="v1",
            graph=graph,
        )

        self.assertEqual("episode_a", working_map.episode_id)
        self.assertEqual(("train_test_split", "linear_regression"), _state_ids(working_map))
        for state in working_map.states:
            self.assertEqual("unknown", state.assessed_mastery_level)
            self.assertEqual("unknown", state.diagnostic_confidence)
            self.assertIsNone(state.assessment_note)
            self.assertEqual((), state.supporting_turn_ids)

    def test_update_node_assessments_applies_batch_atomically(self):
        graph = _graph()
        working_map = _working_map(graph)
        dialogue = _dialogue()

        updated = update_node_assessments(
            working_map=working_map,
            graph=graph,
            visible_dialogue_context=dialogue,
            updates=(
                WorkingMapNodeAssessmentUpdate(
                    node_id="train_test_split",
                    assessed_mastery_level="L3",
                    diagnostic_confidence="high",
                    assessment_note="The user explained train/test split clearly.",
                    supporting_turn_ids=("turn_01",),
                ),
                WorkingMapNodeAssessmentUpdate(
                    node_id="linear_regression",
                    assessed_mastery_level="L1",
                    diagnostic_confidence="low",
                    assessment_note=(
                        "The train/test answer suggests weak downstream model "
                        "assessment understanding."
                    ),
                    supporting_turn_ids=("turn_01",),
                ),
            ),
        )

        self.assertEqual("unknown", working_map.states[0].assessed_mastery_level)
        self.assertEqual("L3", updated.assessment_by_node_id["train_test_split"].assessed_mastery_level)
        self.assertEqual("high", updated.assessment_by_node_id["train_test_split"].diagnostic_confidence)
        self.assertEqual(("turn_01",), updated.assessment_by_node_id["linear_regression"].supporting_turn_ids)

    def test_update_node_assessments_rejects_invalid_batch_without_mutating(self):
        graph = _graph()
        working_map = _working_map(graph)
        dialogue = _dialogue()

        with self.assertRaisesRegex(KnowActValidationError, "unknown visible turns"):
            update_node_assessments(
                working_map=working_map,
                graph=graph,
                visible_dialogue_context=dialogue,
                updates=(
                    WorkingMapNodeAssessmentUpdate(
                        node_id="train_test_split",
                        assessed_mastery_level="L3",
                        diagnostic_confidence="high",
                        assessment_note="Supported by turn one.",
                        supporting_turn_ids=("turn_01",),
                    ),
                    WorkingMapNodeAssessmentUpdate(
                        node_id="linear_regression",
                        assessed_mastery_level="L2",
                        diagnostic_confidence="medium",
                        assessment_note="This cites a non-visible turn.",
                        supporting_turn_ids=("turn_missing",),
                    ),
                ),
            )

        self.assertTrue(
            all(state.assessed_mastery_level == "unknown" for state in working_map.states)
        )

    def test_update_node_assessments_requires_support_for_non_unknown_state(self):
        graph = _graph()
        working_map = _working_map(graph)

        with self.assertRaisesRegex(KnowActValidationError, "must cite a visible turn"):
            update_node_assessments(
                working_map=working_map,
                graph=graph,
                visible_dialogue_context=_dialogue(),
                updates=(
                    WorkingMapNodeAssessmentUpdate(
                        node_id="train_test_split",
                        assessed_mastery_level="L3",
                        diagnostic_confidence="high",
                        assessment_note="The user seemed confident.",
                        supporting_turn_ids=(),
                    ),
                ),
            )

    def test_finalize_reconstructed_map_wraps_supporting_turns_as_visible_evidence(self):
        graph = _graph()
        working_map = update_node_assessments(
            working_map=_working_map(graph),
            graph=graph,
            visible_dialogue_context=_dialogue(),
            updates=(
                WorkingMapNodeAssessmentUpdate(
                    node_id="train_test_split",
                    assessed_mastery_level="L3",
                    diagnostic_confidence="high",
                    assessment_note="The user explained why a test set is held out.",
                    supporting_turn_ids=("turn_01",),
                ),
            ),
        )

        result = finalize_reconstructed_map(
            working_map=working_map,
            graph=graph,
            visible_dialogue_context=_dialogue(),
        )

        reconstructed_map = result.knowledge_map
        submission = result.submission
        self.assertEqual((), result.warnings)
        self.assertEqual("episode_a", submission.episode_id)
        self.assertEqual(
            ("train_test_split", "linear_regression"),
            tuple(prediction.node_id for prediction in submission.predictions),
        )
        self.assertEqual(
            "L3",
            submission.prediction_by_node_id[
                "train_test_split"
            ].predicted_mastery,
        )
        self.assertEqual(
            "unknown",
            submission.prediction_by_node_id[
                "linear_regression"
            ].predicted_mastery,
        )
        self.assertEqual("reconstructed_episode_a", reconstructed_map.user_id)
        self.assertEqual("reconstructed", reconstructed_map.kind)
        self.assertEqual(1, len(reconstructed_map.states))
        state = reconstructed_map.states[0]
        self.assertEqual("train_test_split", state.node_id)
        self.assertEqual("L3", state.mastery_level)
        self.assertEqual(("ev_train_test_split_turn_01",), state.evidence_refs)
        self.assertEqual((), state.misconceptions)
        self.assertEqual((), state.unknowns)

        evidence = reconstructed_map.evidence[0]
        self.assertEqual("interaction_observation", evidence.evidence_type)
        self.assertEqual("prior_answer", evidence.evidence_kind)
        self.assertEqual("tested_agent", evidence.visibility)
        self.assertEqual("turn_01", evidence.turn_id)
        self.assertIn("Question:", evidence.signal)
        self.assertIn("Answer:", evidence.signal)
        validate_knowledge_map(reconstructed_map, graph)

    def test_finalize_reconstructed_map_reports_unsupported_judgment(self):
        graph = _graph()
        working_map = AgentWorkingKnowledgeMap(
            episode_id="episode_a",
            benchmark_domain="classical_supervised_ml_algorithms",
            graph_version="v1",
            states=(
                WorkingMapNodeAssessment(
                    node_id="train_test_split",
                    assessed_mastery_level="L3",
                    diagnostic_confidence="high",
                    assessment_note="The agent wrote a note but cited no turn.",
                    supporting_turn_ids=(),
                ),
                WorkingMapNodeAssessment(node_id="linear_regression"),
            ),
        )

        result = finalize_reconstructed_map(
            working_map=working_map,
            graph=graph,
            visible_dialogue_context=_dialogue(),
        )

        train_test_prediction = result.submission.prediction_by_node_id[
            "train_test_split"
        ]
        self.assertEqual("L3", train_test_prediction.predicted_mastery)
        self.assertEqual((), train_test_prediction.evidence_refs)
        self.assertEqual("unknown", result.submission.prediction_by_node_id["linear_regression"].predicted_mastery)
        self.assertEqual((), result.knowledge_map.states)
        self.assertEqual((), result.knowledge_map.evidence)
        self.assertEqual(1, len(result.warnings))
        self.assertEqual(
            FinalizationWarningCode.MISSING_SUPPORT_UNSUPPORTED,
            result.warnings[0].code,
        )
        validate_knowledge_map(result.knowledge_map, graph)


def _graph() -> KnowledgeGraph:
    return KnowledgeGraph(
        nodes=(
            KnowledgeNode(
                id="train_test_split",
                name="Train/Test Split",
                type="concept",
            ),
            KnowledgeNode(
                id="linear_regression",
                name="Linear Regression",
                type="concept",
            ),
        )
    )


def _working_map(graph: KnowledgeGraph) -> AgentWorkingKnowledgeMap:
    return initialize_working_map(
        episode_id="episode_a",
        benchmark_domain="classical_supervised_ml_algorithms",
        graph_version="v1",
        graph=graph,
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
                    text=(
                        "I use a test set to check performance on held-out "
                        "data, separate from training."
                    )
                ),
                observation=CoarseObservationMetadata(
                    kind=VisibleObservationKind.ANSWER
                ),
            ),
        )
    )


def _state_ids(working_map: AgentWorkingKnowledgeMap) -> tuple[str, ...]:
    return tuple(state.node_id for state in working_map.states)
