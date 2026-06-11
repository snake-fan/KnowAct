export const MAP_NODE_SELECTED_STATE = "selected";
export const MAP_NODE_DIMMED_STATE = "dimmed";

type MapInteractionGraph = {
  authored_nodes: readonly { id: string }[];
};

export function buildMapNodeInteractionStates(
  graph: MapInteractionGraph,
  selectedNodeId: string | null,
  groundedNodeIds: readonly string[] | null | undefined
) {
  const groundedNodeIdSet = new Set(groundedNodeIds ?? []);
  const hasGroundedNodeFilter = groundedNodeIdSet.size > 0;
  const states: Record<string, string[]> = {};

  for (const node of graph.authored_nodes) {
    if (selectedNodeId === node.id) {
      states[node.id] = [MAP_NODE_SELECTED_STATE];
      continue;
    }
    states[node.id] =
      hasGroundedNodeFilter && !groundedNodeIdSet.has(node.id)
        ? [MAP_NODE_DIMMED_STATE]
        : [];
  }

  return states;
}
