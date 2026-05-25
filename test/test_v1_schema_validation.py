import unittest

from backend.knowact.core.evidence import EvidenceRecord
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode, SourceLocator
from backend.knowact.core.map import KnowledgeMap, UserKnowledgeState
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.graph import validate_knowledge_graph
from backend.knowact.validation.map import validate_knowledge_map


class V1SchemaValidationTest(unittest.TestCase):
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
                    confidence=0.8,
                    evidence_refs=["ev_linear_regression_prior_answer"],
                ),
                UserKnowledgeState(
                    node_id="train_test_split",
                    mastery_level="L2",
                    confidence=0.7,
                    evidence_refs=["ev_train_test_split_prior_answer"],
                ),
            ],
            evidence=[
                EvidenceRecord(
                    id="ev_linear_regression_prior_answer",
                    node_id="linear_regression",
                    type="ground_truth",
                    kind="prior_answer",
                    visibility="hidden",
                    summary="The user can fit and interpret a line but struggles with assumptions.",
                ),
                EvidenceRecord(
                    id="ev_train_test_split_prior_answer",
                    node_id="train_test_split",
                    type="ground_truth",
                    kind="self_report",
                    visibility="hidden",
                    summary="The user reports having used train/test split only by copying examples.",
                ),
            ],
        )

        validate_knowledge_graph(graph)
        validate_knowledge_map(ground_truth_map, graph)

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
                    confidence=0.8,
                    evidence_refs=["ev_hidden_profile_note"],
                )
            ],
            evidence=[
                EvidenceRecord(
                    id="ev_hidden_profile_note",
                    node_id="linear_regression",
                    type="ground_truth",
                    kind="prior_answer",
                    visibility="hidden",
                    summary="Hidden profile evidence must not support reconstructed maps.",
                )
            ],
        )

        with self.assertRaisesRegex(KnowActValidationError, "visible evidence"):
            validate_knowledge_map(reconstructed_map, graph)


if __name__ == "__main__":
    unittest.main()
