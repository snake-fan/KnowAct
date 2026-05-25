from backend.knowact.core.graph import KnowledgeEdgeType, KnowledgeGraph
from backend.knowact.validation.exceptions import KnowActValidationError


def validate_knowledge_graph(graph: KnowledgeGraph) -> None:
    node_ids = [node.id for node in graph.nodes]
    duplicate_node_ids = _duplicates(node_ids)
    if duplicate_node_ids:
        raise KnowActValidationError(f"Duplicate knowledge node ids: {sorted(duplicate_node_ids)}")

    edge_ids = [edge.id for edge in graph.edges]
    duplicate_edge_ids = _duplicates(edge_ids)
    if duplicate_edge_ids:
        raise KnowActValidationError(f"Duplicate knowledge edge ids: {sorted(duplicate_edge_ids)}")

    known_nodes = set(node_ids)
    for edge in graph.edges:
        if edge.source not in known_nodes:
            raise KnowActValidationError(f"Edge {edge.id} references unknown source node {edge.source}")
        if edge.target not in known_nodes:
            raise KnowActValidationError(f"Edge {edge.id} references unknown target node {edge.target}")
        if edge.type == KnowledgeEdgeType.CONTRASTS_WITH and edge.source > edge.target:
            raise KnowActValidationError(
                f"contrasts_with edge {edge.id} must use canonical source/target ordering"
            )


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
