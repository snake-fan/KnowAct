from collections.abc import Hashable
from typing import TypeVar

from backend.knowact.core.evidence import EvidenceType, EvidenceVisibility
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.map import KnowledgeMap, KnowledgeMapKind
from backend.knowact.validation.exceptions import KnowActValidationError


def validate_knowledge_map(knowledge_map: KnowledgeMap, graph: KnowledgeGraph) -> None:
    known_node_ids = graph.node_ids
    state_node_ids = [state.node_id for state in knowledge_map.states]
    duplicate_state_nodes = _duplicates(state_node_ids)
    if duplicate_state_nodes:
        raise KnowActValidationError(
            f"Knowledge map contains multiple current states for nodes: {sorted(duplicate_state_nodes)}"
        )

    unknown_state_nodes = set(state_node_ids) - known_node_ids
    if unknown_state_nodes:
        raise KnowActValidationError(f"Knowledge map references unknown nodes: {sorted(unknown_state_nodes)}")

    if knowledge_map.kind == KnowledgeMapKind.GROUND_TRUTH:
        missing_nodes = known_node_ids - set(state_node_ids)
        if missing_nodes:
            raise KnowActValidationError(f"Ground-truth knowledge map is missing nodes: {sorted(missing_nodes)}")

    evidence_ids = [evidence.id for evidence in knowledge_map.evidence]
    duplicate_evidence_ids = _duplicates(evidence_ids)
    if duplicate_evidence_ids:
        raise KnowActValidationError(f"Knowledge map contains duplicate evidence ids: {sorted(duplicate_evidence_ids)}")

    duplicate_evidence_signatures = _duplicates(
        [
            (evidence.node_id, evidence.evidence_kind.value, evidence.signal)
            for evidence in knowledge_map.evidence
        ]
    )
    if duplicate_evidence_signatures:
        duplicate_evidence_nodes = {node_id for node_id, _, _ in duplicate_evidence_signatures}
        raise KnowActValidationError(
            "Knowledge map contains duplicate evidence entries for nodes: "
            f"{sorted(duplicate_evidence_nodes)}"
        )

    evidence_by_id = {evidence.id: evidence for evidence in knowledge_map.evidence}
    unknown_evidence_nodes = {evidence.node_id for evidence in knowledge_map.evidence} - known_node_ids
    if unknown_evidence_nodes:
        raise KnowActValidationError(f"Evidence references unknown nodes: {sorted(unknown_evidence_nodes)}")

    _validate_evidence_boundary(knowledge_map)

    for state in knowledge_map.states:
        for evidence_ref in state.evidence_refs:
            if evidence_ref not in evidence_by_id:
                raise KnowActValidationError(
                    f"State for node {state.node_id} references unknown evidence {evidence_ref}"
                )
            if evidence_by_id[evidence_ref].node_id != state.node_id:
                raise KnowActValidationError(
                    f"State for node {state.node_id} references evidence {evidence_ref} "
                    f"for node {evidence_by_id[evidence_ref].node_id}"
                )

        if knowledge_map.kind == KnowledgeMapKind.GROUND_TRUTH:
            if not state.evidence_refs:
                raise KnowActValidationError(
                    f"Ground-truth state for node {state.node_id} must cite "
                    "simulator-only ground-truth-profile evidence"
                )

        if knowledge_map.kind == KnowledgeMapKind.RECONSTRUCTED:
            if not state.evidence_refs:
                raise KnowActValidationError(
                    f"Reconstructed state for node {state.node_id} must cite "
                    "tested-agent-visible evidence"
                )


def _validate_evidence_boundary(knowledge_map: KnowledgeMap) -> None:
    if knowledge_map.kind == KnowledgeMapKind.GROUND_TRUTH:
        for evidence in knowledge_map.evidence:
            if evidence.evidence_type != EvidenceType.GROUND_TRUTH_PROFILE:
                raise KnowActValidationError(
                    f"Ground-truth evidence {evidence.id} must have evidence type ground_truth_profile"
                )
            if evidence.visibility != EvidenceVisibility.SIMULATOR_ONLY:
                raise KnowActValidationError(
                    f"Ground-truth evidence {evidence.id} must use simulator_only visibility"
                )

    if knowledge_map.kind == KnowledgeMapKind.RECONSTRUCTED:
        for evidence in knowledge_map.evidence:
            if evidence.evidence_type != EvidenceType.INTERACTION_OBSERVATION:
                raise KnowActValidationError(
                    f"Reconstructed-map evidence {evidence.id} must have evidence type interaction_observation"
                )
            if evidence.visibility != EvidenceVisibility.TESTED_AGENT:
                raise KnowActValidationError(
                    f"Reconstructed-map evidence {evidence.id} must use tested_agent visibility"
                )


_DuplicateValue = TypeVar("_DuplicateValue", bound=Hashable)


def _duplicates(values: list[_DuplicateValue]) -> set[_DuplicateValue]:
    seen: set[_DuplicateValue] = set()
    duplicates: set[_DuplicateValue] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
