from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.knowact.agents.protocol import DiagnosticQuestionPlan
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import DiagnosticQuestion


class DiagnosticCandidate(BaseModel):
    """One model-proposed question with inspectable acquisition estimates."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    question: DiagnosticQuestion
    diagnostic_plan: DiagnosticQuestionPlan
    estimated_information_gain: float = Field(ge=0.0, le=1.0)
    coverage_gain: float = Field(ge=0.0, le=1.0)
    graph_leverage: float = Field(ge=0.0, le=1.0)
    redundancy: float = Field(ge=0.0, le=1.0)
    complexity: float = Field(ge=0.0, le=1.0)
    outcome_model_confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _requires_stable_question_id(self) -> Self:
        if self.question.question_id is None:
            raise ValueError("diagnostic candidates require a stable question_id")
        return self


class DiagnosticUtilityWeights(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    information_gain: float = Field(default=1.0, ge=0.0)
    coverage: float = Field(default=0.30, ge=0.0)
    graph_leverage: float = Field(default=0.15, ge=0.0)
    redundancy: float = Field(default=0.25, ge=0.0)
    complexity: float = Field(default=0.10, ge=0.0)


class SelectedDiagnosticCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: DiagnosticCandidate
    utility: float


class DiagnosticCandidateError(ValueError):
    """Raised when model-proposed diagnostic candidates are unusable."""


def score_diagnostic_candidate(
    candidate: DiagnosticCandidate,
    *,
    weights: DiagnosticUtilityWeights | None = None,
) -> float:
    selected_weights = weights or DiagnosticUtilityWeights()
    return (
        selected_weights.information_gain
        * candidate.outcome_model_confidence
        * candidate.estimated_information_gain
        + selected_weights.coverage * candidate.coverage_gain
        + selected_weights.graph_leverage * candidate.graph_leverage
        - selected_weights.redundancy * candidate.redundancy
        - selected_weights.complexity * candidate.complexity
    )


def select_diagnostic_candidate(
    candidates: tuple[DiagnosticCandidate, ...],
    *,
    graph: KnowledgeGraph,
    asked_question_ids: set[str] | None = None,
    weights: DiagnosticUtilityWeights | None = None,
) -> SelectedDiagnosticCandidate:
    if not candidates:
        raise DiagnosticCandidateError("no diagnostic candidates were proposed")
    already_asked = asked_question_ids or set()
    selectable: list[DiagnosticCandidate] = []
    for candidate in candidates:
        _validate_candidate_targets(candidate, graph)
        question_id = candidate.question.question_id
        if question_id is not None and question_id in already_asked:
            continue
        selectable.append(candidate)
    if not selectable:
        raise DiagnosticCandidateError(
            "all diagnostic candidates repeat previously asked questions"
        )
    selected = max(
        selectable,
        key=lambda candidate: score_diagnostic_candidate(
            candidate,
            weights=weights,
        ),
    )
    return SelectedDiagnosticCandidate(
        candidate=selected,
        utility=score_diagnostic_candidate(selected, weights=weights),
    )


def _validate_candidate_targets(
    candidate: DiagnosticCandidate,
    graph: KnowledgeGraph,
) -> None:
    plan = candidate.diagnostic_plan
    targets = (plan.primary_target_node_id, *plan.secondary_target_node_ids)
    unknown_targets = set(targets) - graph.node_ids
    if unknown_targets:
        raise DiagnosticCandidateError(
            "diagnostic candidate references unknown graph nodes: "
            f"{sorted(unknown_targets)}"
        )
    if plan.primary_target_node_id in plan.secondary_target_node_ids:
        raise DiagnosticCandidateError(
            "diagnostic candidate repeats its primary target"
        )
    if len(targets) > 1 and not _targets_form_connected_subgraph(
        set(targets),
        graph,
    ):
        raise DiagnosticCandidateError(
            "diagnostic candidate targets are not a connected graph cluster"
        )


def _targets_form_connected_subgraph(
    target_ids: set[str],
    graph: KnowledgeGraph,
) -> bool:
    adjacency = {node_id: set() for node_id in target_ids}
    for edge in graph.edges:
        if edge.source in target_ids and edge.target in target_ids:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)
    pending = [next(iter(target_ids))]
    visited: set[str] = set()
    while pending:
        node_id = pending.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        pending.extend(adjacency[node_id] - visited)
    return visited == target_ids
