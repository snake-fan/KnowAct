import { useEffect, useRef } from "react";
import {
  Graph as G6Graph,
  type EdgeData as G6EdgeData,
  type IKeyboardEvent,
  type IPointerEvent,
  type IWheelEvent,
  type NodeData as G6NodeData
} from "@antv/g6";
import {
  CandidateGraphPayload,
  KnowledgeEdge
} from "../../api/authoring";
import {
  isGraphLifecycleError,
  isGraphRuntimeAvailable,
  safeApplySelectionState,
  safeGetCurrentNodePositions,
  safeGetViewportCenterPosition
} from "./CandidateGraphCanvasModel";
import type {
  NodePosition,
  NodePositionMap,
  Selection
} from "./CandidateGraphWorkbenchModel";
import {
  buildLayeredGraphNodePositions,
  wrapGraphNodeLabel
} from "./KnowledgeGraphLayout";

type CandidateGraphCanvasProps = {
  graph: CandidateGraphPayload;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  ariaLabel?: string;
  nodePositionOverrides?: NodePositionMap;
  onViewportCenterChange?: (position: NodePosition) => void;
  layoutVersion: number;
};

const SELECTED_STATE = "selected";
const VIEW_PADDING: [number, number, number, number] = [84, 96, 84, 96];
const NODE_SIZE: [number, number] = [208, 88];
const LAYER_GAP = 156;
const ROW_GAP = 56;
const MIN_NODES_PER_LAYER = 3;
const TARGET_NODES_PER_LAYER = 5;
const MAX_NODES_PER_LAYER = 6;

export function CandidateGraphCanvas({
  graph,
  selection,
  onSelect,
  ariaLabel = "Candidate knowledge graph",
  nodePositionOverrides,
  onViewportCenterChange,
  layoutVersion
}: CandidateGraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<G6Graph | null>(null);
  const appliedLayoutKeyRef = useRef<string | null>(null);
  const graphPayloadRef = useRef(graph);
  const selectionRef = useRef(selection);

  const layoutKey = [
    graph.run_id,
    layoutVersion
  ].join("\u0001");

  const graphDataKey = [
    graph.candidate_nodes.map((node) => node.id).join("\u0000"),
    graph.candidate_nodes
      .map((node) => `${node.id}:${node.name}:${node.type}`)
      .join("\u0000"),
    graph.candidate_edges
      .map((edge) => `${edge.id}:${edge.source}:${edge.target}:${edge.type}:${edge.weight}:${edge.curation_confidence}`)
      .join("\u0000")
  ].join("\u0001");

  useEffect(() => {
    graphPayloadRef.current = graph;
  }, [graph]);

  useEffect(() => {
    selectionRef.current = selection;
  }, [selection]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let graphInstance: G6Graph | null = null;
    const publishViewportCenter = () => {
      if (!isGraphRuntimeAvailable(graphInstance)) return;
      onViewportCenterChange?.(safeGetViewportCenterPosition(graphInstance));
    };

    graphInstance = new G6Graph({
      container,
      autoResize: true,
      background: "#eef3f1",
      padding: VIEW_PADDING,
      zoomRange: [0.24, 2.8],
      autoFit: { type: "view", options: { when: "always" }, animation: false },
      data: { nodes: [], edges: [] },
      node: {
        type: "rect",
        style: (datum) => ({
          size: NODE_SIZE,
          radius: 8,
          fill: "#ffffff",
          stroke: "#1f6f66",
          lineWidth: 2,
          shadowColor: "rgba(31, 111, 102, 0.1)",
          shadowBlur: 16,
          shadowOffsetY: 8,
          labelText: getNodeLabel(datum),
          labelPlacement: "center",
          labelFill: "#1b1f24",
          labelFontSize: 12,
          labelFontWeight: 700,
          labelLineHeight: 16,
          labelTextAlign: "center",
          labelTextBaseline: "middle",
          labelMaxWidth: 164,
          labelWordWrap: false,
          icon: false,
          badge: false,
          port: false
        }),
        state: {
          [SELECTED_STATE]: {
            fill: "#e1f2ee",
            stroke: "#d78232",
            lineWidth: 4,
            halo: true,
            haloStroke: "#d78232",
            haloStrokeOpacity: 0.16,
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
        },
        state: {
          [SELECTED_STATE]: {
            stroke: "#d78232",
            lineWidth: 4,
            halo: true,
            haloStroke: "#d78232",
            haloStrokeOpacity: 0.18,
            labelFill: "#8a4d13"
          }
        }
      },
      behaviors: [
        {
          type: "drag-canvas",
          key: "candidate-drag-canvas",
          onFinish: publishViewportCenter
        },
        {
          type: "scroll-canvas",
          key: "candidate-trackpad-pan",
          enable: (event: WheelEvent) => !event.ctrlKey,
          range: Infinity,
          onFinish: publishViewportCenter
        },
        {
          type: "zoom-canvas",
          key: "candidate-zoom-canvas",
          enable: (event: IWheelEvent | IKeyboardEvent | IPointerEvent) => event.ctrlKey,
          onFinish: publishViewportCenter
        },
        {
          type: "click-select",
          key: "candidate-click-select",
          animation: false,
          degree: 0,
          state: undefined,
          neighborState: undefined,
          unselectedState: undefined,
          onClick: (event: IPointerEvent) => {
            const id = getEventTargetId(event);
            if (event.targetType === "node" && id) {
              onSelect({ kind: "node", id });
              return;
            }
            if (event.targetType === "edge" && id) {
              onSelect({ kind: "edge", id });
              return;
            }
            if (event.targetType === "canvas") {
              onSelect(null);
            }
          }
        },
        {
          type: "drag-element",
          key: "candidate-drag-element",
          animation: false,
          hideEdge: "none",
          onFinish: (ids: unknown[]) => {
            const id = ids.length > 0 ? String(ids[0]) : "";
            if (id && graphPayloadRef.current.candidate_nodes.some((node) => node.id === id)) {
              onSelect({ kind: "node", id });
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
          key: "candidate-graph-grid",
          size: 48,
          stroke: "#d6dfdb",
          lineWidth: 1,
          border: false,
          follow: { translate: true, zoom: true }
        }
      ]
    });

    graphRef.current = graphInstance;

    const resizeObserver = new ResizeObserver(() => {
      graphInstance.resize();
      publishViewportCenter();
    });
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
  }, [onSelect, onViewportCenterChange]);

  useEffect(() => {
    const graphInstance = graphRef.current;
    if (!isGraphRuntimeAvailable(graphInstance)) return;

    const currentGraph = graphPayloadRef.current;
    const shouldRelayout = appliedLayoutKeyRef.current !== layoutKey;
    appliedLayoutKeyRef.current = layoutKey;
    const currentPositions = shouldRelayout ? undefined : safeGetCurrentNodePositions(graphInstance);
    const positionOverrides = shouldRelayout ? undefined : { ...nodePositionOverrides, ...currentPositions };
    const fallbackPosition = shouldRelayout ? undefined : safeGetViewportCenterPosition(graphInstance);
    try {
      graphInstance.setData(toG6Data(currentGraph, positionOverrides, fallbackPosition));
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
      .then(async () => {
        if (cancelled || graphRef.current !== graphInstance || !isGraphRuntimeAvailable(graphInstance)) return;
        await safeApplySelectionState(graphInstance, currentGraph, selectionRef.current);
        if (cancelled || graphRef.current !== graphInstance || !isGraphRuntimeAvailable(graphInstance)) return;
        onViewportCenterChange?.(safeGetViewportCenterPosition(graphInstance));
      })
      .catch((error: unknown) => {
        if (!isGraphRuntimeAvailable(graphInstance) || isGraphLifecycleError(error)) return;
        throw error;
      });

    return () => {
      cancelled = true;
    };
  }, [graphDataKey, layoutKey, nodePositionOverrides, onViewportCenterChange]);

  useEffect(() => {
    const graphInstance = graphRef.current;
    if (!isGraphRuntimeAvailable(graphInstance)) return;
    void safeApplySelectionState(graphInstance, graph, selection).catch((error: unknown) => {
      if (!isGraphRuntimeAvailable(graphInstance) || isGraphLifecycleError(error)) return;
      throw error;
    });
  }, [graph, selection]);

  return (
    <div className="graph-canvas-shell">
      <div
        className="graph-canvas"
        ref={containerRef}
        role="img"
        aria-label={ariaLabel}
      />
    </div>
  );
}

function getEventTargetId(event: IPointerEvent) {
  const target = event.target as { id?: unknown };
  return target.id == null ? "" : String(target.id);
}

function toG6Data(
  graph: CandidateGraphPayload,
  positionOverrides?: NodePositionMap,
  fallbackPosition?: NodePosition
) {
  const nodeIds = new Set(graph.candidate_nodes.map((node) => node.id));
  const positions = buildLayeredGraphNodePositions(graph.candidate_nodes, graph.candidate_edges, {
    nodeSize: NODE_SIZE,
    layerGap: LAYER_GAP,
    rowGap: ROW_GAP,
    minNodesPerLayer: MIN_NODES_PER_LAYER,
    targetNodesPerLayer: TARGET_NODES_PER_LAYER,
    maxNodesPerLayer: MAX_NODES_PER_LAYER
  });
  return {
    nodes: graph.candidate_nodes.map((node): G6NodeData => ({
      id: node.id,
      style: {
        ...(positionOverrides?.[node.id] ?? fallbackPosition ?? positions[node.id]),
        size: NODE_SIZE
      },
      data: {
        name: node.name,
        nodeType: node.type
      }
    })),
    edges: graph.candidate_edges
      .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
      .map((edge): G6EdgeData => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        data: {
          edgeType: edge.type,
          weight: edge.weight,
          curationConfidence: edge.curation_confidence
        }
      }))
  };
}

function getNodeLabel(datum: G6NodeData) {
  const name = stringDataValue(datum, "name") || String(datum.id);
  return wrapGraphNodeLabel(name, 22, 3);
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

function stringDataValue(datum: G6NodeData | G6EdgeData, key: string) {
  const value = datum.data?.[key];
  return typeof value === "string" ? value : "";
}
