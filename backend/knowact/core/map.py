from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.core.evidence import EvidenceRecord


class KnowledgeMapKind(StrEnum):
    CANDIDATE = "candidate"
    GROUND_TRUTH = "ground_truth"
    RECONSTRUCTED = "reconstructed"


class MasteryLevel(StrEnum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"


class UserKnowledgeState(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    mastery_level: MasteryLevel
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    misconceptions: tuple[str, ...]
    unknowns: tuple[str, ...]

    @field_validator("node_id")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("misconceptions", "unknowns")
    @classmethod
    def _items_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank items")
        if len(value) != len(set(value)):
            raise ValueError("must not contain duplicate items")
        return value


class KnowledgeMap(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: str
    kind: KnowledgeMapKind
    states: tuple[UserKnowledgeState, ...]
    evidence: tuple[EvidenceRecord, ...] = Field(default_factory=tuple)

    @field_validator("user_id")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @property
    def state_by_node_id(self) -> dict[str, UserKnowledgeState]:
        return {state.node_id: state for state in self.states}


class GroundTruthMapManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    map_id: str
    user_id: str
    benchmark_domain: str
    graph_version: str
    promoted_from_candidate_run: str

    @field_validator(
        "map_id",
        "user_id",
        "benchmark_domain",
        "graph_version",
        "promoted_from_candidate_run",
    )
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value
