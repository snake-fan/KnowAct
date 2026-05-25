from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.core.graph import KnowledgeEdge, KnowledgeNode, SourceLocator


class SourceMaterial(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    title: str
    text: str
    citation: str | None = None

    @field_validator("source_id", "title", "text")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class SourceGroundedNodeSkeleton(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    type: str = "concept"
    definition: str
    source_locators: tuple[SourceLocator, ...] = Field(min_length=1)

    @field_validator("id", "name", "type", "definition")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class SourceGroundedNodeSkeletonList(BaseModel):
    model_config = ConfigDict(frozen=True)

    skeletons: tuple[SourceGroundedNodeSkeleton, ...]


class KnowledgeNodeList(BaseModel):
    model_config = ConfigDict(frozen=True)

    nodes: tuple[KnowledgeNode, ...]


class KnowledgeEdgeList(BaseModel):
    model_config = ConfigDict(frozen=True)

    edges: tuple[KnowledgeEdge, ...]


class GraphAuthoringWorkflowResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_grounded_node_skeletons: tuple[SourceGroundedNodeSkeleton, ...]
    candidate_nodes: tuple[KnowledgeNode, ...]
    candidate_edges: tuple[KnowledgeEdge, ...]

