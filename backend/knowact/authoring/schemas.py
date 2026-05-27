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
    source_grounding_notes: tuple[str, ...] = Field(min_length=1)

    @field_validator("id", "name", "type", "definition")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("source_grounding_notes")
    @classmethod
    def _source_grounding_notes_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not note.strip() for note in value):
            raise ValueError("must not contain blank notes")
        return value


class SourceGroundedNodeSkeletonList(BaseModel):
    model_config = ConfigDict(frozen=True)

    skeletons: tuple[SourceGroundedNodeSkeleton, ...]


class NodeRubricPatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    diagnostic_goal: str
    levels: dict[str, str]
    diagnostic_signals: tuple[str, ...] = Field(min_length=1)
    simulator_behavior: str

    @field_validator("id", "diagnostic_goal", "simulator_behavior")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("levels")
    @classmethod
    def _levels_must_not_be_empty(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("must not be empty")
        if any(not key.strip() or not description.strip() for key, description in value.items()):
            raise ValueError("keys and descriptions must not be blank")
        return value

    @field_validator("diagnostic_signals")
    @classmethod
    def _signals_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not signal.strip() for signal in value):
            raise ValueError("must not contain blank signals")
        return value


class NodeRubricPatchList(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    nodes: tuple[NodeRubricPatch, ...]


class NodeRubricAuthoringInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    skeletons: tuple[SourceGroundedNodeSkeleton, ...]


class NodeRubricAuthoringResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    rubric_patches: tuple[NodeRubricPatch, ...]
    candidate_nodes: tuple[KnowledgeNode, ...]


class EdgeProposalInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_nodes: tuple[KnowledgeNode, ...]
    source_grounded_node_skeletons: tuple[SourceGroundedNodeSkeleton, ...]


class KnowledgeEdgeList(BaseModel):
    model_config = ConfigDict(frozen=True)

    edges: tuple[KnowledgeEdge, ...]


class GraphAuthoringWorkflowResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_grounded_node_skeletons: tuple[SourceGroundedNodeSkeleton, ...]
    candidate_nodes: tuple[KnowledgeNode, ...]
    candidate_edges: tuple[KnowledgeEdge, ...]
