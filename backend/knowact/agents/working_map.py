from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.knowact.agents.belief import MasteryBelief
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.map import MasteryLevel


class AssessedMasteryLevel(StrEnum):
    UNKNOWN = "unknown"
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"

    def to_mastery_level(self) -> MasteryLevel:
        if self == AssessedMasteryLevel.UNKNOWN:
            raise ValueError("unknown cannot be converted to a final mastery level")
        return MasteryLevel(self.value)


class DiagnosticConfidence(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WorkingMapNodeAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    assessed_mastery_level: AssessedMasteryLevel = AssessedMasteryLevel.UNKNOWN
    diagnostic_confidence: DiagnosticConfidence = DiagnosticConfidence.UNKNOWN
    assessment_note: str | None = None
    supporting_turn_ids: tuple[str, ...] = Field(default_factory=tuple)
    mastery_belief: MasteryBelief | None = None

    @field_validator("node_id")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("assessment_note")
    @classmethod
    def _optional_note_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("supporting_turn_ids")
    @classmethod
    def _supporting_turn_ids_must_be_nonblank_unique(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not turn_id.strip() for turn_id in value):
            raise ValueError("must not contain blank items")
        if len(value) != len(set(value)):
            raise ValueError("must not contain duplicate items")
        return value

    @model_validator(mode="after")
    def _belief_mode_matches_committed_mastery(self) -> Self:
        if (
            self.mastery_belief is not None
            and self.assessed_mastery_level != AssessedMasteryLevel.UNKNOWN
            and self.mastery_belief.mode_level != self.assessed_mastery_level.value
        ):
            raise ValueError("mastery belief mode must match assessed mastery level")
        return self


class AgentWorkingKnowledgeMap(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    states: tuple[WorkingMapNodeAssessment, ...]

    @field_validator("episode_id", "benchmark_domain", "graph_version")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @property
    def assessment_by_node_id(self) -> dict[str, WorkingMapNodeAssessment]:
        return {state.node_id: state for state in self.states}


def initialize_working_map(
    *,
    episode_id: str,
    benchmark_domain: str,
    graph_version: str,
    graph: KnowledgeGraph,
) -> AgentWorkingKnowledgeMap:
    return AgentWorkingKnowledgeMap(
        episode_id=episode_id,
        benchmark_domain=benchmark_domain,
        graph_version=graph_version,
        states=tuple(
            WorkingMapNodeAssessment(node_id=node.id) for node in graph.nodes
        ),
    )
