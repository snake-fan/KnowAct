import { memo, useEffect, useRef } from "react";
import {
  Graph as G6Graph,
  type EdgeData as G6EdgeData,
  type IPointerEvent,
  type NodeData as G6NodeData
} from "@antv/g6";
import {
  KnowledgeEdge,
  KnowledgeMap,
  MapEdgeConsistencyWarning,
  MasteryLevel,
  ReviewedGraphPayload
} from "../../api/authoring";
import {
  isGraphLifecycleError,
  isGraphRuntimeAvailable,
  safeGetCurrentNodePositions
} from "../candidateGraph/CandidateGraphCanvasModel";
import type { NodePositionMap } from "../candidateGraph/CandidateGraphWorkbenchModel";
import {
  buildLayeredGraphNodePositions,
  wrapGraphNodeLabel
} from "../candidateGraph/KnowledgeGraphLayout";

type MapPreviewCanvasProps = {
  graph: ReviewedGraphPayload;
  knowledgeMap: KnowledgeMap;
  warnings?: MapEdgeConsistencyWarning[];
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string | null) => void;
  ariaLabel?: string;
};

const SELECTED_STATE = "selected";
const NODE_SIZE: [number, number] = [208, 88];
const LAYER_GAP = 156;
const ROW_GAP = 56;
const MIN_NODES_PER_LAYER = 3;
const TARGET_NODES_PER_LAYER = 5;
const MAX_NODES_PER_LAYER = 6;

export const MapPreviewCanvas = memo(function MapPreviewCanvas({
  graph,
  knowledgeMap,
  warnings = [],
  selectedNodeId,
  onSelectNode,
  ariaLabel = "Knowledge map preview graph"
}: MapPreviewCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<G6Graph | null>(null);
  const graphPayloadRef = useRef(graph);
  const selectedNodeIdRef = useRef(selectedNodeId);
  const nodePositionsRef = useRef<NodePositionMap>({});
  const appliedLayoutKeyRef = useRef<string | null>(null);

  const layoutKey = [
    graph.graph_manifest.version,
    graph.authored_nodes.map((node) => node.id).join("\u0000"),
    graph.authored_edges.map((edge) => `${edge.id}:${edge.source}:${edge.target}:${edge.type}`).join("\u0000")
  ].join("\u0001");

  const graphDataKey = [
    layoutKey,
    graph.authored_nodes.map((node) => `${node.id}:${node.name}:${node.type}`).join("\u0000"),
    knowledgeMap.states.map((state) => `${state.node_id}:${state.mastery_level}`).join("\u0000"),
    warnings.map((warning) => `${warning.edge_id}:${warning.source_node_id}:${warning.target_node_id}`).join("\u0000")
  ].join("\u0001");

  useEffect(() => {
    graphPayloadRef.current = graph;
  }, [graph]);

  useEffect(() => {
    selectedNodeIdRef.current = selectedNodeId;
  }, [selectedNodeId]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let graphInstance: G6Graph | null = null;
    const captureNodePositions = () => {
      if (!isGraphRuntimeAvailable(graphInstance)) return;
      nodePositionsRef.current = {
        ...nodePositionsRef.current,
        ...safeGetCurrentNodePositions(graphInstance)
      };
    };

    graphInstance = new G6Graph({
      container,
      autoResize: true,
      background: "#eef3f1",
      padding: [60, 54, 60, 54],
      zoomRange: [0.22, 2.6],
      autoFit: { type: "view", options: { when: "always" }, animation: false },
      data: { nodes: [], edges: [] },
      node: {
        type: "rect",
        style: (datum) => {
          const masteryLevel = getMasteryLevel(datum);
          const hasWarning = Boolean(datum.data?.hasWarning);
          return {
            size: NODE_SIZE,
            radius: 8,
            fill: masteryColor(masteryLevel),
            stroke: hasWarning ? "#7f3f1d" : "#2d5f59",
            lineWidth: hasWarning ? 4 : 2,
            shadowColor: "rgba(31, 58, 52, 0.13)",
            shadowBlur: 14,
            shadowOffsetY: 7,
            labelText: getNodeLabel(datum),
            labelPlacement: "center",
            labelFill: labelColor(masteryLevel),
            labelFontSize: 12,
            labelFontWeight: 800,
            labelLineHeight: 16,
            labelTextAlign: "center",
            labelTextBaseline: "middle",
            labelMaxWidth: 164,
            labelWordWrap: false,
            icon: false,
            badge: false,
            port: false
          };
        },
        state: {
          [SELECTED_STATE]: {
            stroke: "#2563eb",
            lineWidth: 5,
            halo: true,
            haloStroke: "#2563eb",
            haloStrokeOpacity: 0.18,
            haloLineWidth: 18
          }
        }
      },
      edge: {
        type: "polyline",
        style: (datum) => {
          const edgeType = getEdgeType(datum);
          const visual = getEdgeVisual(edgeType);
          return {
            stroke: visual.stroke,
            lineWidth: 2,
            lineDash: visual.lineDash,
            endArrow: edgeType !== "contrasts_with",
            endArrowType: "vee",
            endArrowSize: 8,
            labelText: edgeType,
            labelFill: "#58645f",
            labelFontSize: 11,
            labelBackground: true,
            labelBackgroundFill: "#eef3f1",
            labelBackgroundOpacity: 0.92,
            labelBackgroundRadius: 4,
            labelPadding: [2, 5],
            labelOffsetY: -6
          };
        }
      },
      behaviors: [
        { type: "drag-canvas", key: "map-drag-canvas" },
        { type: "zoom-canvas", key: "map-zoom-canvas" },
        {
          type: "click-select",
          key: "map-click-select",
          animation: false,
          degree: 0,
          state: undefined,
          neighborState: undefined,
          unselectedState: undefined,
          onClick: (event: IPointerEvent) => {
            const id = getEventTargetId(event);
            if (event.targetType === "node" && id) {
              onSelectNode(id);
              return;
            }
            if (event.targetType === "canvas") {
              onSelectNode(null);
            }
          }
        },
        {
          type: "drag-element",
          key: "map-drag-element",
          animation: false,
          hideEdge: "none",
          onFinish: (ids: unknown[]) => {
            captureNodePositions();
            const id = ids.length > 0 ? String(ids[0]) : "";
            if (id && graphPayloadRef.current.authored_nodes.some((node) => node.id === id)) {
              onSelectNode(id);
            }
          },
          cursor: {
            grab: "grab",
            grabbing: "grabbing"
          }
        }
      ],
      plugins: [
        {
          type: "grid-line",
          key: "map-review-grid",
          size: 48,
          stroke: "#d6dfdb",
          lineWidth: 1,
          border: false,
          follow: { translate: true, zoom: true }
        }
      ]
    });

    graphRef.current = graphInstance;
    const resizeObserver = new ResizeObserver(() => graphInstance?.resize());
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      if (graphRef.current === graphInstance) {
        graphRef.current = null;
      }
      if (isGraphRuntimeAvailable(graphInstance)) {
        graphInstance.destroy();
      }
    };
  }, [onSelectNode]);

  useEffect(() => {
    const graphInstance = graphRef.current;
    if (!isGraphRuntimeAvailable(graphInstance)) return;

    const shouldRelayout = appliedLayoutKeyRef.current !== layoutKey;
    appliedLayoutKeyRef.current = layoutKey;
    if (shouldRelayout) {
      nodePositionsRef.current = {};
    } else {
      nodePositionsRef.current = {
        ...nodePositionsRef.current,
        ...safeGetCurrentNodePositions(graphInstance)
      };
    }

    try {
      graphInstance.setData(
        toG6Data(
          graph,
          knowledgeMap,
          warnings,
          shouldRelayout ? undefined : nodePositionsRef.current
        )
      );
    } catch (error) {
      if (!isGraphRuntimeAvailable(graphInstance) || isGraphLifecycleError(error)) return;
      throw error;
    }

    let cancelled = false;
    let draw: Promise<unknown>;
    try {
      draw = shouldRelayout ? graphInstance.render() : graphInstance.draw();
    } catch (error) {
      if (!isGraphRuntimeAvailable(graphInstance) || isGraphLifecycleError(error)) return;
      throw error;
    }
    void draw
      .then(() => {
        if (cancelled || graphRef.current !== graphInstance || !isGraphRuntimeAvailable(graphInstance)) return;
        applySelectedState(graphInstance, graph, selectedNodeIdRef.current);
      })
      .catch((error: unknown) => {
        if (!isGraphRuntimeAvailable(graphInstance) || isGraphLifecycleError(error)) return;
        throw error;
      });

    return () => {
      cancelled = true;
    };
  }, [graph, graphDataKey, knowledgeMap, layoutKey, warnings]);

  useEffect(() => {
    const graphInstance = graphRef.current;
    if (!isGraphRuntimeAvailable(graphInstance)) return;
    applySelectedState(graphInstance, graph, selectedNodeId);
  }, [graph, selectedNodeId]);

  return (
    <div
      className="map-review-canvas"
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
    />
  );
});

function toG6Data(
  graph: ReviewedGraphPayload,
  knowledgeMap: KnowledgeMap,
  warnings: MapEdgeConsistencyWarning[],
  positionOverrides?: NodePositionMap
) {
  const stateByNodeId = new Map(knowledgeMap.states.map((state) => [state.node_id, state]));
  const warningNodeIds = new Set(
    warnings.flatMap((warning) => [warning.source_node_id, warning.target_node_id])
  );
  const nodeIds = new Set(graph.authored_nodes.map((node) => node.id));
  const positions = buildLayeredGraphNodePositions(graph.authored_nodes, graph.authored_edges, {
    nodeSize: NODE_SIZE,
    layerGap: LAYER_GAP,
    rowGap: ROW_GAP,
    minNodesPerLayer: MIN_NODES_PER_LAYER,
    targetNodesPerLayer: TARGET_NODES_PER_LAYER,
    maxNodesPerLayer: MAX_NODES_PER_LAYER
  });

  return {
    nodes: graph.authored_nodes.map((node): G6NodeData => {
      const state = stateByNodeId.get(node.id);
      return {
        id: node.id,
        style: {
          ...(positionOverrides?.[node.id] ?? positions[node.id]),
          size: NODE_SIZE
        },
        data: {
          name: node.name,
          masteryLevel: state?.mastery_level ?? "L0",
          hasWarning: warningNodeIds.has(node.id)
        }
      };
    }),
    edges: graph.authored_edges
      .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
      .map((edge): G6EdgeData => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        data: {
          edgeType: edge.type
        }
      }))
  };
}

function applySelectedState(
  graphInstance: G6Graph,
  graph: ReviewedGraphPayload,
  selectedNodeId: string | null
) {
  const states: Record<string, string[]> = {};
  for (const node of graph.authored_nodes) {
    states[node.id] = selectedNodeId === node.id ? [SELECTED_STATE] : [];
  }
  void graphInstance.setElementState(states, false);
}

function getEventTargetId(event: IPointerEvent) {
  const target = event.target as { id?: unknown };
  return target.id == null ? "" : String(target.id);
}

function getNodeLabel(datum: G6NodeData) {
  const name = stringDataValue(datum, "name") || String(datum.id);
  return wrapGraphNodeLabel(name, 22, 3);
}

function getMasteryLevel(datum: G6NodeData): MasteryLevel {
  const value = stringDataValue(datum, "masteryLevel");
  if (value === "L0" || value === "L1" || value === "L2" || value === "L3" || value === "L4" || value === "L5") {
    return value;
  }
  return "L0";
}

function getEdgeType(datum: G6EdgeData): KnowledgeEdge["type"] {
  const edgeType = stringDataValue(datum, "edgeType");
  if (
    edgeType === "part_of" ||
    edgeType === "prerequisite_for" ||
    edgeType === "supports" ||
    edgeType === "contrasts_with"
  ) {
    return edgeType;
  }
  return "supports";
}

function getEdgeVisual(edgeType: KnowledgeEdge["type"]) {
  switch (edgeType) {
    case "part_of":
      return { stroke: "#64748b", lineDash: [7, 4] };
    case "prerequisite_for":
      return { stroke: "#2f6f9f", lineDash: 0 };
    case "contrasts_with":
      return { stroke: "#9f4f68", lineDash: [3, 5] };
    case "supports":
    default:
      return { stroke: "#1f6f66", lineDash: 0 };
  }
}

function masteryColor(level: MasteryLevel) {
  switch (level) {
    case "L0":
      return "#c94e45";
    case "L1":
      return "#d97a52";
    case "L2":
      return "#dba85c";
    case "L3":
      return "#b9bd64";
    case "L4":
      return "#7fb46f";
    case "L5":
      return "#2f8e68";
  }
}

function labelColor(level: MasteryLevel) {
  return level === "L0" || level === "L1" || level === "L5" ? "#ffffff" : "#1b1f24";
}

function stringDataValue(datum: G6NodeData | G6EdgeData, key: string) {
  const value = datum.data?.[key];
  return typeof value === "string" ? value : "";
}
