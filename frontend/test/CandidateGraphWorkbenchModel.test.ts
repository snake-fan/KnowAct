import {
  addCandidateEdgeFromSelection,
  addCandidateNodeAtPosition,
  candidateGraphLoadState,
  deleteCandidateGraphSelection,
  reviewedGraphLoadState
} from "../src/features/candidateGraph/CandidateGraphWorkbenchModel.js";
import type {
  CandidateGraphPayload,
  KnowledgeNode,
  ReviewedGraphPayload
} from "../src/api/authoring.js";

const baseGraph: CandidateGraphPayload = {
  benchmark_domain: "classical_supervised_ml_algorithms",
  run_id: "test_run",
  candidate_nodes: [],
  candidate_edges: [],
  artifact_paths: {
    output_dir_uri: ".",
    candidate_nodes_uri: "candidate_nodes.json",
    candidate_edges_uri: "candidate_edges.json",
    workflow_log_uri: "workflow_log.json"
  }
};

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function assertEqual<T>(actual: T, expected: T, message: string) {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

{
  const graph: CandidateGraphPayload = {
    ...baseGraph,
    candidate_nodes: [node("candidate_first"), node("candidate_second")]
  };
  const loaded = candidateGraphLoadState(graph);

  assertEqual(loaded.graphMode, "candidate", "saved candidate loads in editable candidate mode");
  assertEqual(loaded.graph, graph, "saved candidate payload remains the displayed graph");
  assertEqual(loaded.selection?.kind, "node", "saved candidate selects a node");
  assertEqual(loaded.selection?.id, "candidate_first", "saved candidate selects its first node");
}

{
  const reviewed: ReviewedGraphPayload = {
    benchmark_domain: "ISLP",
    graph_manifest: {
      graph_id: "kg_ISLP_v1",
      domain: "ISLP",
      version: "v1",
      promoted_from_candidate_run: "candidate_run",
      nodes_file: "authored_nodes.json",
      edges_file: "authored_edges.json",
      source: []
    },
    authored_nodes: [node("reviewed_first")],
    authored_edges: [],
    artifact_paths: {
      output_dir_uri: "benchmark/domains/ISLP/graphs/v1",
      graph_manifest_uri: "benchmark/domains/ISLP/graphs/v1/graph_manifest.json",
      authored_nodes_uri: "benchmark/domains/ISLP/graphs/v1/authored_nodes.json",
      authored_edges_uri: "benchmark/domains/ISLP/graphs/v1/authored_edges.json"
    }
  };
  const loaded = reviewedGraphLoadState(reviewed);

  assertEqual(loaded.graphMode, "reviewed", "published graph loads in reviewed mode");
  assertEqual(loaded.graph.run_id, "reviewed:v1", "reviewed display identity uses its version");
  assertEqual(loaded.selection?.id, "reviewed_first", "reviewed graph selects its first node");
}

{
  const center = { x: 120, y: -40 };
  const edit = addCandidateNodeAtPosition(baseGraph, center);
  const addedNode = edit.graph.candidate_nodes[0];

  assert(addedNode, "adds a node");
  assertEqual(edit.selection?.kind, "node", "selects the added node");
  assertEqual(edit.selection?.id, addedNode.id, "selection points at the added node");
  assertEqual(edit.nodePositions[addedNode.id]?.x, center.x, "places added node at viewport center x");
  assertEqual(edit.nodePositions[addedNode.id]?.y, center.y, "places added node at viewport center y");
}

{
  const graph: CandidateGraphPayload = {
    ...baseGraph,
    candidate_nodes: [node("first"), node("selected"), node("third")]
  };
  const edit = addCandidateEdgeFromSelection(graph, { kind: "node", id: "selected" });
  const edge = edit.graph.candidate_edges[0];

  assert(edge, "adds an edge");
  assertEqual(edge.source, "selected", "uses the selected node as edge source");
  assertEqual(edge.target, "first", "uses another node as edge target");
  assertEqual(edit.selection?.kind, "edge", "selects the added edge");
  assertEqual(edit.selection?.id, edge.id, "selection points at the added edge");
}

{
  const graph: CandidateGraphPayload = {
    ...baseGraph,
    candidate_nodes: [node("keep"), node("remove")],
    candidate_edges: [
      {
        id: "edge_remove",
        source: "remove",
        target: "keep",
        type: "supports",
        rationale: "",
        weight: 0.5,
        curation_confidence: 0.5
      }
    ]
  };
  const edit = deleteCandidateGraphSelection(
    graph,
    { kind: "node", id: "remove" },
    {
      keep: { x: 1, y: 2 },
      remove: { x: 3, y: 4 }
    }
  );

  assertEqual(edit.graph.candidate_nodes.length, 1, "removes selected node");
  assertEqual(edit.graph.candidate_edges.length, 0, "removes connected edges");
  assertEqual(edit.nodePositions.keep?.x, 1, "preserves remaining node position x");
  assertEqual(edit.nodePositions.remove, undefined, "drops removed node position");
  assertEqual(edit.selection, null, "clears selection after delete");
}

function node(id: string): KnowledgeNode {
  return {
    id,
    name: id,
    type: "concept",
    definition: "",
    source_locators: [],
    diagnostic_goal: "",
    levels: {},
    diagnostic_signals: [],
    simulator_behavior: ""
  };
}
