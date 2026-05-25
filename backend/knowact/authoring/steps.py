from collections.abc import Sequence
from typing import Protocol

from backend.knowact.authoring.parsers.graph_authoring import (
    parse_edge_proposal_output,
    parse_node_extraction_output,
    parse_node_rubric_authoring_output,
)
from backend.knowact.authoring.schemas import SourceGroundedNodeSkeleton, SourceMaterial
from backend.knowact.authoring.templates.edge_proposal import build_edge_proposal_messages
from backend.knowact.authoring.templates.node_extraction import build_node_extraction_messages
from backend.knowact.authoring.templates.node_rubric_authoring import (
    build_node_rubric_authoring_messages,
)
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeNode
from backend.knowact.llm.client import ModelClient


class NodeExtractionStep(Protocol):
    def run(self, source_materials: Sequence[SourceMaterial]) -> tuple[SourceGroundedNodeSkeleton, ...]:
        """Extract source-grounded node skeletons from authoritative source material."""


class NodeRubricAuthoringStep(Protocol):
    def run(
        self,
        skeletons: Sequence[SourceGroundedNodeSkeleton],
        source_materials: Sequence[SourceMaterial],
    ) -> tuple[KnowledgeNode, ...]:
        """Turn node skeletons into complete candidate Knowledge Nodes."""


class EdgeProposalStep(Protocol):
    def run(
        self,
        candidate_nodes: Sequence[KnowledgeNode],
        source_materials: Sequence[SourceMaterial],
    ) -> tuple[KnowledgeEdge, ...]:
        """Propose precision-first candidate Knowledge Edges."""


class LLMNodeExtractionStep:
    def __init__(self, model_client: ModelClient) -> None:
        self._model_client = model_client

    def run(self, source_materials: Sequence[SourceMaterial]) -> tuple[SourceGroundedNodeSkeleton, ...]:
        raw_output = self._model_client.complete(messages=build_node_extraction_messages(source_materials))
        return parse_node_extraction_output(raw_output)


class LLMNodeRubricAuthoringStep:
    def __init__(self, model_client: ModelClient) -> None:
        self._model_client = model_client

    def run(
        self,
        skeletons: Sequence[SourceGroundedNodeSkeleton],
        source_materials: Sequence[SourceMaterial],
    ) -> tuple[KnowledgeNode, ...]:
        raw_output = self._model_client.complete(
            messages=build_node_rubric_authoring_messages(skeletons, source_materials)
        )
        return parse_node_rubric_authoring_output(raw_output)


class LLMEdgeProposalStep:
    def __init__(self, model_client: ModelClient) -> None:
        self._model_client = model_client

    def run(
        self,
        candidate_nodes: Sequence[KnowledgeNode],
        source_materials: Sequence[SourceMaterial],
    ) -> tuple[KnowledgeEdge, ...]:
        raw_output = self._model_client.complete(
            messages=build_edge_proposal_messages(candidate_nodes, source_materials)
        )
        return parse_edge_proposal_output(raw_output)
