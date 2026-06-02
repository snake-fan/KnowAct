from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.core.evidence import EvidenceKind
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeNode, SourceLocator
from backend.knowact.core.map import MasteryLevel


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


class GeneratedProfileContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: str
    background: tuple[str, ...] = Field(min_length=1)
    prior_experience: tuple[str, ...]
    goals: tuple[str, ...] = Field(min_length=1)
    preferences: tuple[str, ...]

    @field_validator("summary")
    @classmethod
    def _summary_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("background", "prior_experience", "goals", "preferences")
    @classmethod
    def _items_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank items")
        return value


class CandidateProfileContext(GeneratedProfileContext):
    benchmark_domain: str

    @field_validator("benchmark_domain")
    @classmethod
    def _benchmark_domain_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ConfirmedProfileContext(CandidateProfileContext):
    user_id: str

    @field_validator("user_id")
    @classmethod
    def _user_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ProfileContextAuthoringInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    benchmark_domain: str
    rough_description: str
    domain_summary: str | None = None

    @field_validator("benchmark_domain", "rough_description", "domain_summary")
    @classmethod
    def _values_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class KnowledgeStateOutline(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    mastery_level: MasteryLevel
    misconceptions: tuple[str, ...]
    unknowns: tuple[str, ...]

    @field_validator("node_id")
    @classmethod
    def _node_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("misconceptions", "unknowns")
    @classmethod
    def _items_must_not_be_blank_or_duplicated(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank items")
        if len(value) != len(set(value)):
            raise ValueError("must not contain duplicate items")
        return value


class KnowledgeStateOutlineList(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    states: tuple[KnowledgeStateOutline, ...]


class GroundTruthEvidenceDraft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    evidence_kind: EvidenceKind
    signal: str

    @field_validator("node_id", "signal")
    @classmethod
    def _values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class GroundTruthEvidenceDraftList(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence: tuple[GroundTruthEvidenceDraft, ...]


class MapEdgeConsistencyWarning(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: str
    source_node_id: str
    source_mastery_level: MasteryLevel
    target_node_id: str
    target_mastery_level: MasteryLevel
    rule: Literal[
        "prerequisite_target_mastery_exceeds_source_by_at_least_two_levels"
    ] = "prerequisite_target_mastery_exceeds_source_by_at_least_two_levels"

    @field_validator("edge_id", "source_node_id", "target_node_id", "rule")
    @classmethod
    def _values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class MapEdgeConsistencyWarningList(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    warnings: tuple[MapEdgeConsistencyWarning, ...]
