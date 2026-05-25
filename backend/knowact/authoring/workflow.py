from collections.abc import Sequence

from backend.knowact.authoring.schemas import GraphAuthoringWorkflowResult, SourceMaterial
from backend.knowact.authoring.steps import EdgeProposalStep, NodeExtractionStep, NodeRubricAuthoringStep
from backend.knowact.authoring.validation import (
    validate_candidate_edges,
    validate_complete_candidate_nodes,
    validate_source_grounded_node_skeletons,
)


class GraphAuthoringAgentWorkflow:
    def __init__(
        self,
        *,
        node_extraction_step: NodeExtractionStep,
        node_rubric_authoring_step: NodeRubricAuthoringStep,
        edge_proposal_step: EdgeProposalStep,
    ) -> None:
        self._node_extraction_step = node_extraction_step
        self._node_rubric_authoring_step = node_rubric_authoring_step
        self._edge_proposal_step = edge_proposal_step

    def run(self, source_materials: Sequence[SourceMaterial]) -> GraphAuthoringWorkflowResult:
        skeletons = self._node_extraction_step.run(source_materials)
        validate_source_grounded_node_skeletons(skeletons)

        candidate_nodes = self._node_rubric_authoring_step.run(skeletons, source_materials)
        validate_complete_candidate_nodes(candidate_nodes, skeletons)

        candidate_edges = self._edge_proposal_step.run(candidate_nodes, source_materials)
        validate_candidate_edges(candidate_nodes, candidate_edges)

        return GraphAuthoringWorkflowResult(
            source_grounded_node_skeletons=tuple(skeletons),
            candidate_nodes=tuple(candidate_nodes),
            candidate_edges=tuple(candidate_edges),
        )

