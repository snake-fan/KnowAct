from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class GraphAuthoringScope(BaseModel):
    """Explicit research scope for a small, diagnostically useful graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    aspect_name: str
    aspect_description: str
    representative_tasks: tuple[str, ...] = Field(min_length=1)
    excluded_topics: tuple[str, ...] = ()
    target_node_count: int = Field(default=20, ge=5, le=40)
    max_node_count: int = Field(default=24, ge=5, le=50)

    @field_validator("aspect_name", "aspect_description")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("representative_tasks", "excluded_topics")
    @classmethod
    def _items_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank items")
        return value

    @model_validator(mode="after")
    def _maximum_must_cover_target(self) -> "GraphAuthoringScope":
        if self.max_node_count < self.target_node_count:
            raise ValueError("max_node_count must be greater than or equal to target_node_count")
        return self


DEFAULT_GRAPH_AUTHORING_SCOPE = GraphAuthoringScope(
    aspect_name="Provided source scope",
    aspect_description="Select stable concepts needed to answer questions about the provided source.",
    representative_tasks=("Explain and apply the central concepts in the provided source.",),
)


class ParsedSourceSegment(BaseModel):
    model_config = ConfigDict(frozen=True)

    segment_id: str
    source_id: str
    source_title: str
    location: str
    heading_path: tuple[str, ...] = Field(min_length=1, max_length=3)
    source_locator: SourceLocator
    text: str
    char_count: int = Field(ge=1)

    @field_validator("segment_id", "source_id", "source_title", "location", "text")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("heading_path")
    @classmethod
    def _heading_path_items_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank headings")
        return value


class SegmentNodeExtractionSourceLocatorPatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    locator: str
    note: str | None = None

    @field_validator("locator")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("note")
    @classmethod
    def _optional_values_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class SegmentNodeExtractionDraftPatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    definition: str
    source_locator: SegmentNodeExtractionSourceLocatorPatch
    grounding_note: str
    evidence_excerpt: str

    @field_validator("name", "definition", "grounding_note", "evidence_excerpt")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class SegmentNodeExtractionDraftPatchList(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    drafts: tuple[SegmentNodeExtractionDraftPatch, ...]


class SegmentNodeExtractionDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    draft_id: str
    segment_id: str
    name: str
    definition: str
    source_locator: SourceLocator
    grounding_note: str
    evidence_excerpt: str

    @field_validator(
        "draft_id",
        "segment_id",
        "name",
        "definition",
        "grounding_note",
        "evidence_excerpt",
    )
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ReconciledNodeSkeletonDraft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    definition: str
    source_locators: tuple[SourceLocator, ...] = Field(min_length=1)
    grounding_notes: tuple[str, ...] = Field(min_length=1)
    evidence_excerpts: tuple[str, ...] = Field(min_length=1)
    supporting_draft_ids: tuple[str, ...] = Field(min_length=1)
    supporting_segment_ids: tuple[str, ...] = Field(min_length=1)
    merge_split_note: str

    @field_validator("name", "definition", "merge_split_note")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator(
        "grounding_notes",
        "evidence_excerpts",
        "supporting_draft_ids",
        "supporting_segment_ids",
    )
    @classmethod
    def _items_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank items")
        return value


class ReconciledNodeSkeletonDraftList(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    skeletons: tuple[ReconciledNodeSkeletonDraft, ...]


class SourceGroundedNodeSkeleton(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    type: str = "concept"
    definition: str
    source_locators: tuple[SourceLocator, ...] = Field(min_length=1)
    source_grounding_notes: tuple[str, ...] = Field(min_length=1)
    source_evidence_excerpts: tuple[str, ...] = ()

    @field_validator("id", "name", "type", "definition")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("source_grounding_notes", "source_evidence_excerpts")
    @classmethod
    def _source_grounding_notes_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not note.strip() for note in value):
            raise ValueError("must not contain blank notes")
        return value


class SourceGroundedNodeSkeletonList(BaseModel):
    model_config = ConfigDict(frozen=True)

    skeletons: tuple[SourceGroundedNodeSkeleton, ...]


class NodeSkeletonReconciliationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    definition: str
    source_locators: tuple[SourceLocator, ...] = Field(min_length=1)
    grounding_notes: tuple[str, ...] = Field(min_length=1)
    evidence_excerpts: tuple[str, ...] = Field(min_length=1)
    supporting_draft_ids: tuple[str, ...] = Field(min_length=1)
    supporting_segment_ids: tuple[str, ...] = Field(min_length=1)
    merge_split_note: str

    @field_validator("id", "name", "definition", "merge_split_note")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator(
        "grounding_notes",
        "evidence_excerpts",
        "supporting_draft_ids",
        "supporting_segment_ids",
    )
    @classmethod
    def _items_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank items")
        return value


class NodeSkeletonReconciliationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    records: tuple[NodeSkeletonReconciliationRecord, ...]
    source_grounded_node_skeletons: tuple[SourceGroundedNodeSkeleton, ...]


class NodeSkeletonVerificationDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    decision: Literal["keep", "remove"]
    grounding_status: Literal["supported", "uncertain", "unsupported"]
    scope_status: Literal["in_scope", "boundary_case", "out_of_scope"]
    diagnostic_value: Literal["high", "medium", "low"]
    rationale: str

    @field_validator("id", "rationale")
    @classmethod
    def _values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class NodeSkeletonVerificationDecisionList(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    decisions: tuple[NodeSkeletonVerificationDecision, ...]


class NodeSkeletonVerificationInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    scope: GraphAuthoringScope
    skeletons: tuple[SourceGroundedNodeSkeleton, ...]


class NodeSkeletonVerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    decisions: tuple[NodeSkeletonVerificationDecision, ...]
    verified_skeletons: tuple[SourceGroundedNodeSkeleton, ...]


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

    scope: GraphAuthoringScope = DEFAULT_GRAPH_AUTHORING_SCOPE
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
