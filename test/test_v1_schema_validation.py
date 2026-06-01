import unittest

from pydantic import ValidationError

from backend.knowact.core.evidence import EvidenceRecord
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode, SourceLocator
from backend.knowact.core.map import KnowledgeMap, UserKnowledgeState
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.graph import validate_knowledge_graph
from backend.knowact.validation.map import validate_knowledge_map


class V1SchemaValidationTest(unittest.TestCase):
    def test_user_knowledge_state_requires_explicit_misconceptions_and_unknowns(self):
        with self.assertRaises(ValidationError):
            UserKnowledgeState(
                node_id="linear_regression",
                mastery_level="L3",
            )

    def test_user_knowledge_state_rejects_duplicate_misconceptions(self):
        with self.assertRaisesRegex(ValidationError, "must not contain duplicate items"):
            UserKnowledgeState(
                node_id="linear_regression",
                mastery_level="L3",
                misconceptions=["Confuses residuals with errors.", "Confuses residuals with errors."],
                unknowns=[],
            )

    def test_reviewed_graph_and_ground_truth_map_validate_through_public_api(self):
        graph = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    id="linear_regression",
                    name="Linear Regression",
                    type="concept",
                    source_locators=[
                        SourceLocator(
                            source_id="isl_python",
                            locator="chapter_3",
                            note="Linear regression chapter",
                        )
                    ],
                ),
                KnowledgeNode(
                    id="train_test_split",
                    name="Train Test Split",
                    type="concept",
                    source_locators=[
                        SourceLocator(
                            source_id="isl_python",
                            locator="chapter_2",
                            note="Model assessment introduction",
                        )
                    ],
                ),
            ],
            edges=[
                KnowledgeEdge(
                    id="edge_train_test_split_supports_linear_regression",
                    source="train_test_split",
                    target="linear_regression",
                    type="supports",
                    rationale="Model assessment helps diagnose whether a linear model generalizes.",
                    weight=0.7,
                    curation_confidence=0.9,
                )
            ],
        )

        ground_truth_map = KnowledgeMap(
            user_id="dev_user_001",
            kind="ground_truth",
            states=[
                UserKnowledgeState(
                    node_id="linear_regression",
                    mastery_level="L3",
                    evidence_refs=["ev_linear_regression_prior_answer"],
                    misconceptions=["Treats residual noise as proof that the model is unusable."],
                    unknowns=["Whether the user can explain confidence intervals."],
                ),
                UserKnowledgeState(
                    node_id="train_test_split",
                    mastery_level="L2",
                    evidence_refs=["ev_train_test_split_prior_answer"],
                    misconceptions=[],
                    unknowns=[],
                ),
            ],
            evidence=[
                EvidenceRecord(
                    id="ev_linear_regression_prior_answer",
                    node_id="linear_regression",
                    evidence_type="ground_truth_profile",
                    evidence_kind="prior_answer",
                    visibility="simulator_only",
                    signal="The user can fit and interpret a line but struggles with assumptions.",
                ),
                EvidenceRecord(
                    id="ev_train_test_split_prior_answer",
                    node_id="train_test_split",
                    evidence_type="ground_truth_profile",
                    evidence_kind="self_report",
                    visibility="simulator_only",
                    signal="The user reports having used train/test split only by copying examples.",
                ),
            ],
        )

        validate_knowledge_graph(graph)
        validate_knowledge_map(ground_truth_map, graph)
        self.assertEqual(
            ("Treats residual noise as proof that the model is unusable.",),
            ground_truth_map.states[0].misconceptions,
        )
        self.assertEqual(
            ("Whether the user can explain confidence intervals.",),
            ground_truth_map.states[0].unknowns,
        )
        self.assertEqual((), ground_truth_map.states[1].misconceptions)
        self.assertEqual((), ground_truth_map.states[1].unknowns)

    def test_reconstructed_map_must_cite_tested_agent_visible_evidence(self):
        graph = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    id="linear_regression",
                    name="Linear Regression",
                    type="concept",
                )
            ]
        )
        reconstructed_map = KnowledgeMap(
            user_id="dev_user_001",
            kind="reconstructed",
            states=[
                UserKnowledgeState(
                    node_id="linear_regression",
                    mastery_level="L3",
                    evidence_refs=["ev_hidden_profile_note"],
                    misconceptions=[],
                    unknowns=[],
                )
            ],
            evidence=[
                EvidenceRecord(
                    id="ev_hidden_profile_note",
                    node_id="linear_regression",
                    evidence_type="interaction_observation",
                    evidence_kind="prior_answer",
                    visibility="simulator_only",
                    signal="Simulator-only evidence must not support reconstructed maps.",
                )
            ],
        )

        with self.assertRaisesRegex(KnowActValidationError, "tested_agent visibility"):
            validate_knowledge_map(reconstructed_map, graph)

    def test_reconstructed_map_accepts_tested_agent_visible_interaction_observation(self):
        graph = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    id="linear_regression",
                    name="Linear Regression",
                    type="concept",
                )
            ]
        )
        reconstructed_map = KnowledgeMap(
            user_id="dev_user_001",
            kind="reconstructed",
            states=[
                UserKnowledgeState(
                    node_id="linear_regression",
                    mastery_level="L3",
                    evidence_refs=["ev_turn_01_linear_regression"],
                    misconceptions=[],
                    unknowns=[],
                )
            ],
            evidence=[
                EvidenceRecord(
                    id="ev_turn_01_linear_regression",
                    node_id="linear_regression",
                    evidence_type="interaction_observation",
                    evidence_kind="prior_answer",
                    visibility="tested_agent",
                    signal="The user correctly interprets the slope in a simple example.",
                    turn_id="turn_01",
                )
            ],
        )

        validate_knowledge_map(reconstructed_map, graph)

    def test_ground_truth_map_rejects_tested_agent_visible_evidence(self):
        graph = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    id="linear_regression",
                    name="Linear Regression",
                    type="concept",
                )
            ]
        )
        ground_truth_map = KnowledgeMap(
            user_id="dev_user_001",
            kind="ground_truth",
            states=[
                UserKnowledgeState(
                    node_id="linear_regression",
                    mastery_level="L3",
                    evidence_refs=["ev_linear_regression_prior_answer"],
                    misconceptions=[],
                    unknowns=[],
                )
            ],
            evidence=[
                EvidenceRecord(
                    id="ev_linear_regression_prior_answer",
                    node_id="linear_regression",
                    evidence_type="ground_truth_profile",
                    evidence_kind="prior_answer",
                    visibility="tested_agent",
                    signal="Ground-truth profile evidence must remain hidden from the tested agent.",
                )
            ],
        )

        with self.assertRaisesRegex(KnowActValidationError, "simulator_only visibility"):
            validate_knowledge_map(ground_truth_map, graph)

    def test_state_must_not_reference_evidence_for_another_node(self):
        graph = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    id="linear_regression",
                    name="Linear Regression",
                    type="concept",
                ),
                KnowledgeNode(
                    id="train_test_split",
                    name="Train Test Split",
                    type="concept",
                ),
            ]
        )
        candidate_map = KnowledgeMap(
            user_id="dev_user_001",
            kind="candidate",
            states=[
                UserKnowledgeState(
                    node_id="linear_regression",
                    mastery_level="L3",
                    evidence_refs=["ev_train_test_split_prior_answer"],
                    misconceptions=[],
                    unknowns=[],
                )
            ],
            evidence=[
                EvidenceRecord(
                    id="ev_train_test_split_prior_answer",
                    node_id="train_test_split",
                    evidence_type="ground_truth_profile",
                    evidence_kind="prior_answer",
                    visibility="simulator_only",
                    signal="The user can explain the purpose of a test set.",
                )
            ],
        )

        with self.assertRaisesRegex(KnowActValidationError, "for node train_test_split"):
            validate_knowledge_map(candidate_map, graph)

    def test_map_rejects_duplicate_evidence_kind_and_signal_for_same_node(self):
        graph = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    id="linear_regression",
                    name="Linear Regression",
                    type="concept",
                )
            ]
        )
        candidate_map = KnowledgeMap(
            user_id="dev_user_001",
            kind="candidate",
            states=[
                UserKnowledgeState(
                    node_id="linear_regression",
                    mastery_level="L3",
                    evidence_refs=["ev_linear_regression_prior_answer_01", "ev_linear_regression_prior_answer_02"],
                    misconceptions=[],
                    unknowns=[],
                )
            ],
            evidence=[
                EvidenceRecord(
                    id="ev_linear_regression_prior_answer_01",
                    node_id="linear_regression",
                    evidence_type="ground_truth_profile",
                    evidence_kind="prior_answer",
                    visibility="simulator_only",
                    signal="The user can fit a line but cannot explain its assumptions.",
                ),
                EvidenceRecord(
                    id="ev_linear_regression_prior_answer_02",
                    node_id="linear_regression",
                    evidence_type="ground_truth_profile",
                    evidence_kind="prior_answer",
                    visibility="simulator_only",
                    signal="The user can fit a line but cannot explain its assumptions.",
                ),
            ],
        )

        with self.assertRaisesRegex(KnowActValidationError, "duplicate evidence entries"):
            validate_knowledge_map(candidate_map, graph)


if __name__ == "__main__":
    unittest.main()
