import {
  buildMapNodeInteractionStates,
  MAP_NODE_DIMMED_STATE,
  MAP_NODE_SELECTED_STATE
} from "../src/features/mapAuthoring/MapPreviewCanvasModel.js";

function assertEqual<T>(actual: T, expected: T, message: string) {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

{
  const states = buildMapNodeInteractionStates(graphFixture(), null, ["node_a"]);

  assertEqual(states.node_a?.length, 0, "grounded node stays in the normal state");
  assertEqual(states.node_b?.[0], MAP_NODE_DIMMED_STATE, "non-grounded node is dimmed");
}

{
  const states = buildMapNodeInteractionStates(graphFixture(), "node_b", ["node_a"]);

  assertEqual(
    states.node_b?.[0],
    MAP_NODE_SELECTED_STATE,
    "selected non-grounded node gets selected state instead of dimmed state"
  );
  assertEqual(states.node_b?.length, 1, "selected node does not retain dimmed state");
}

{
  const states = buildMapNodeInteractionStates(graphFixture(), null, []);

  assertEqual(states.node_a?.length, 0, "empty grounded filter keeps node a normal");
  assertEqual(states.node_b?.length, 0, "empty grounded filter keeps node b normal");
}

function graphFixture() {
  return {
    authored_nodes: [
      { id: "node_a" },
      { id: "node_b" }
    ]
  };
}
