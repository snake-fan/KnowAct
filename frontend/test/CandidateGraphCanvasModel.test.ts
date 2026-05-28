import {
  safeApplySelectionState,
  safeGetCurrentNodePositions,
  safeGetViewportCenterPosition
} from "../src/features/candidateGraph/CandidateGraphCanvasModel.js";
import type { CandidateGraphPayload } from "../src/api/authoring.js";

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
  const fallback = { x: 9, y: -3 };
  const center = safeGetViewportCenterPosition(
    {
      destroyed: true,
      getViewportCenter() {
        throw new Error("destroyed graph should not be read");
      }
    },
    fallback
  );

  assertEqual(center.x, fallback.x, "destroyed graph returns fallback center x");
  assertEqual(center.y, fallback.y, "destroyed graph returns fallback center y");
}

{
  const fallback = { x: 4, y: 7 };
  const center = safeGetViewportCenterPosition(
    {
      getViewportCenter() {
        throw new TypeError("Cannot read properties of undefined (reading 'getViewportCenter')");
      }
    },
    fallback
  );

  assertEqual(center.x, fallback.x, "viewport read failure returns fallback center x");
  assertEqual(center.y, fallback.y, "viewport read failure returns fallback center y");
}

{
  const positions = safeGetCurrentNodePositions({
    destroyed: true,
    getNodeData() {
      throw new Error("destroyed graph should not provide nodes");
    }
  });

  assertEqual(Object.keys(positions).length, 0, "destroyed graph returns no current positions");
}

{
  let called = false;
  await safeApplySelectionState(
    {
      destroyed: true,
      setElementState() {
        called = true;
      }
    },
    graphFixture(),
    { kind: "node", id: "node_a" }
  );

  assert(!called, "destroyed graph does not receive selection updates");
}

{
  const capturedStates: Record<string, string[]>[] = [];
  await safeApplySelectionState(
    {
      destroyed: false,
      setElementState(states: Record<string, string[]>) {
        capturedStates.push(states);
      }
    },
    graphFixture(),
    { kind: "edge", id: "edge_a_b" }
  );

  assertEqual(capturedStates.length, 1, "live graph receives selection states");
  const states = capturedStates[0];
  assert(states, "selection states were captured");
  assertEqual(states.node_a?.length, 0, "unselected node has no selected state");
  assertEqual(states.edge_a_b?.[0], "selected", "selected edge receives selected state");
}

function graphFixture(): CandidateGraphPayload {
  return {
    benchmark_domain: "classical_supervised_ml_algorithms",
    run_id: "test_run",
    candidate_nodes: [
      {
        id: "node_a",
        name: "Node A",
        type: "concept",
        definition: "",
        source_locators: [],
        diagnostic_goal: "",
        levels: {},
        diagnostic_signals: [],
        simulator_behavior: ""
      },
      {
        id: "node_b",
        name: "Node B",
        type: "concept",
        definition: "",
        source_locators: [],
        diagnostic_goal: "",
        levels: {},
        diagnostic_signals: [],
        simulator_behavior: ""
      }
    ],
    candidate_edges: [
      {
        id: "edge_a_b",
        source: "node_a",
        target: "node_b",
        type: "supports",
        rationale: "",
        weight: 0.5,
        curation_confidence: 0.5
      }
    ],
    artifact_paths: {
      output_dir_uri: ".",
      candidate_nodes_uri: "candidate_nodes.json",
      candidate_edges_uri: "candidate_edges.json",
      workflow_log_uri: "workflow_log.json"
    }
  };
}
