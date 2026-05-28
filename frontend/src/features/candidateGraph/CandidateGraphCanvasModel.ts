import type { CandidateGraphPayload } from "../../api/authoring.js";
import type {
  NodePosition,
  NodePositionMap,
  Selection
} from "./CandidateGraphWorkbenchModel.js";

export type CandidateGraphRuntime = {
  destroyed?: boolean;
  getNodeData?: () => Array<{
    id?: unknown;
    style?: {
      x?: unknown;
      y?: unknown;
    };
  }>;
  getViewportCenter?: () => unknown;
  setElementState?: (
    states: Record<string, string[]>,
    animation: boolean
  ) => Promise<unknown> | unknown;
};

const DEFAULT_VIEWPORT_CENTER: NodePosition = { x: 0, y: 0 };
const SELECTED_STATE = "selected";

export function isGraphRuntimeAvailable(
  graphInstance: CandidateGraphRuntime | null | undefined
): graphInstance is CandidateGraphRuntime {
  return Boolean(graphInstance && graphInstance.destroyed !== true);
}

export function safeGetCurrentNodePositions(
  graphInstance: CandidateGraphRuntime | null | undefined
): NodePositionMap {
  if (!isGraphRuntimeAvailable(graphInstance) || typeof graphInstance.getNodeData !== "function") {
    return {};
  }

  try {
    const positions: NodePositionMap = {};
    for (const node of graphInstance.getNodeData()) {
      const x = Number(node.style?.x);
      const y = Number(node.style?.y);
      if (node.id != null && Number.isFinite(x) && Number.isFinite(y)) {
        positions[String(node.id)] = { x, y };
      }
    }
    return positions;
  } catch {
    return {};
  }
}

export function safeGetViewportCenterPosition(
  graphInstance: CandidateGraphRuntime | null | undefined,
  fallback: NodePosition = DEFAULT_VIEWPORT_CENTER
): NodePosition {
  if (!isGraphRuntimeAvailable(graphInstance) || typeof graphInstance.getViewportCenter !== "function") {
    return fallback;
  }

  try {
    const center = graphInstance.getViewportCenter();
    if (Array.isArray(center)) {
      return finitePosition(center[0], center[1], fallback);
    }
    if (center && typeof center === "object") {
      const point = center as { x?: unknown; y?: unknown };
      return finitePosition(point.x, point.y, fallback);
    }
  } catch {
    return fallback;
  }

  return fallback;
}

export async function safeApplySelectionState(
  graphInstance: CandidateGraphRuntime | null | undefined,
  graph: CandidateGraphPayload,
  selection: Selection
) {
  if (!isGraphRuntimeAvailable(graphInstance) || typeof graphInstance.setElementState !== "function") {
    return;
  }

  try {
    await graphInstance.setElementState(buildSelectionStates(graph, selection), false);
  } catch (error) {
    if (!isGraphRuntimeAvailable(graphInstance) || isGraphLifecycleError(error)) {
      return;
    }
    throw error;
  }
}

export function isGraphLifecycleError(error: unknown) {
  if (!(error instanceof Error)) return false;
  return (
    error.message.includes("graph instance has been destroyed") ||
    error.message.includes("Cannot read properties of undefined")
  );
}

function buildSelectionStates(graph: CandidateGraphPayload, selection: Selection) {
  const states: Record<string, string[]> = {};
  const nodeIds = new Set(graph.candidate_nodes.map((node) => node.id));

  for (const node of graph.candidate_nodes) {
    states[node.id] = selection?.kind === "node" && selection.id === node.id ? [SELECTED_STATE] : [];
  }
  for (const edge of graph.candidate_edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) continue;
    states[edge.id] = selection?.kind === "edge" && selection.id === edge.id ? [SELECTED_STATE] : [];
  }

  return states;
}

function finitePosition(xValue: unknown, yValue: unknown, fallback: NodePosition): NodePosition {
  const x = Number(xValue);
  const y = Number(yValue);
  return {
    x: Number.isFinite(x) ? x : fallback.x,
    y: Number.isFinite(y) ? y : fallback.y
  };
}
