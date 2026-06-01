from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeEdgeType(StrEnum):
    PART_OF = "part_of"
    PREREQUISITE_FOR = "prerequisite_for"
    SUPPORTS = "supports"
    CONTRASTS_WITH = "contrasts_with"


class SourceLocator(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    locator: str
    note: str | None = None

    @field_validator("source_id", "locator")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class KnowledgeNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    type: str
    definition: str | None = None
    source_locators: tuple[SourceLocator, ...] = Field(default_factory=tuple)
    diagnostic_goal: str | None = None
    levels: dict[str, str] = Field(default_factory=dict)
    diagnostic_signals: tuple[str, ...] = Field(default_factory=tuple)
    simulator_behavior: str | None = None

    @field_validator("id", "name", "type")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class KnowledgeEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    source: str
    target: str
    type: KnowledgeEdgeType
    rationale: str
    weight: float = Field(ge=0.0, le=1.0)
    curation_confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("id", "source", "target", "rationale")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class KnowledgeGraph(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    nodes: tuple[KnowledgeNode, ...]
    edges: tuple[KnowledgeEdge, ...] = Field(default_factory=tuple)

    @property
    def node_ids(self) -> set[str]:
        return {node.id for node in self.nodes}


class GraphManifestSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    title: str
    citation: str | None = None

    @field_validator("source_id", "title")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("citation")
    @classmethod
    def _optional_values_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class GraphManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    graph_id: str
    domain: str
    version: str
    promoted_from_candidate_run: str
    nodes_file: str = "authored_nodes.json"
    edges_file: str = "authored_edges.json"
    source: tuple[GraphManifestSource, ...] = Field(default_factory=tuple)

    @field_validator(
        "graph_id",
        "domain",
        "version",
        "promoted_from_candidate_run",
        "nodes_file",
        "edges_file",
    )
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value
