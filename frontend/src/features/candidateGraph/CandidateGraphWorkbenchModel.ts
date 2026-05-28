import type {
  CandidateGraphPayload,
  KnowledgeEdge,
  KnowledgeNode
} from "../../api/authoring.js";

export type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | null;

export type NodePosition = { x: number; y: number };
export type NodePositionMap = Record<string, NodePosition>;

export const LEVEL_KEYS = ["L0", "L1", "L2", "L3", "L4", "L5"];

export function addCandidateNodeAtPosition(
  graph: CandidateGraphPayload,
  position: NodePosition
) {
  const id = nextId("new_node", graph.candidate_nodes.map((node) => node.id));
  const node: KnowledgeNode = {
    id,
    name: "New Knowledge Node",
    type: "concept",
    definition: "",
    source_locators: [],
    diagnostic_goal: "",
    levels: Object.fromEntries(LEVEL_KEYS.map((level) => [level, ""])),
    diagnostic_signals: [],
    simulator_behavior: ""
  };

  return {
    graph: {
      ...graph,
      candidate_nodes: [...graph.candidate_nodes, node]
    },
    selection: { kind: "node", id } satisfies Selection,
    nodePositions: {
      [id]: position
    }
  };
}

export function addCandidateEdgeFromSelection(graph: CandidateGraphPayload, selection: Selection) {
  const source = selectEdgeSource(graph, selection);
  const target = graph.candidate_nodes.find((node) => node.id !== source)?.id ?? source;
  const id = nextId("edge_new", graph.candidate_edges.map((edge) => edge.id));
  const edge: KnowledgeEdge = {
    id,
    source,
    target,
    type: "supports",
    rationale: "",
    weight: 0.5,
    curation_confidence: 0.5
  };

  return {
    graph: {
      ...graph,
      candidate_edges: [...graph.candidate_edges, edge]
    },
    selection: { kind: "edge", id } satisfies Selection
  };
}

export function deleteCandidateGraphSelection(
  graph: CandidateGraphPayload,
  selection: Selection,
  nodePositions: NodePositionMap
) {
  if (!selection) {
    return { graph, selection: null, nodePositions };
  }

  if (selection.kind === "node") {
    const { [selection.id]: _removedPosition, ...remainingPositions } = nodePositions;
    return {
      graph: {
        ...graph,
        candidate_nodes: graph.candidate_nodes.filter((node) => node.id !== selection.id),
        candidate_edges: graph.candidate_edges.filter(
          (edge) => edge.source !== selection.id && edge.target !== selection.id
        )
      },
      selection: null,
      nodePositions: remainingPositions
    };
  }

  return {
    graph: {
      ...graph,
      candidate_edges: graph.candidate_edges.filter((edge) => edge.id !== selection.id)
    },
    selection: null,
    nodePositions
  };
}

function selectEdgeSource(graph: CandidateGraphPayload, selection: Selection) {
  if (selection?.kind === "node" && graph.candidate_nodes.some((node) => node.id === selection.id)) {
    return selection.id;
  }
  return graph.candidate_nodes[0]?.id ?? "";
}

function nextId(prefix: string, existingIds: string[]) {
  const existing = new Set(existingIds);
  let index = existing.size + 1;
  let candidate = `${prefix}_${index}`;
  while (existing.has(candidate)) {
    index += 1;
    candidate = `${prefix}_${index}`;
  }
  return candidate;
}
