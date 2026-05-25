from backend.knowact.core.evidence import EvidenceVisibility
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

    evidence_by_id = {evidence.id: evidence for evidence in knowledge_map.evidence}
    unknown_evidence_nodes = {evidence.node_id for evidence in knowledge_map.evidence} - known_node_ids
    if unknown_evidence_nodes:
        raise KnowActValidationError(f"Evidence references unknown nodes: {sorted(unknown_evidence_nodes)}")

    for state in knowledge_map.states:
        for evidence_ref in state.evidence_refs:
            if evidence_ref not in evidence_by_id:
                raise KnowActValidationError(
                    f"State for node {state.node_id} references unknown evidence {evidence_ref}"
                )

        if knowledge_map.kind == KnowledgeMapKind.GROUND_TRUTH:
            hidden_refs = [
                evidence_ref
                for evidence_ref in state.evidence_refs
                if evidence_by_id[evidence_ref].visibility == EvidenceVisibility.HIDDEN
            ]
            if not hidden_refs:
                raise KnowActValidationError(
                    f"Ground-truth state for node {state.node_id} must cite hidden evidence"
                )

        if knowledge_map.kind == KnowledgeMapKind.RECONSTRUCTED:
            visible_refs = [
                evidence_ref
                for evidence_ref in state.evidence_refs
                if evidence_by_id[evidence_ref].visibility == EvidenceVisibility.VISIBLE
            ]
            if not visible_refs:
                raise KnowActValidationError(
                    f"Reconstructed state for node {state.node_id} must cite visible evidence"
                )


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
