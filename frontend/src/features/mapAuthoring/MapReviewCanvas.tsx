import { useEffect, useRef } from "react";
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
  isGraphRuntimeAvailable
} from "../candidateGraph/CandidateGraphCanvasModel";

type MapReviewCanvasProps = {
  graph: ReviewedGraphPayload;
  knowledgeMap: KnowledgeMap;
  warnings: MapEdgeConsistencyWarning[];
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string | null) => void;
};

const SELECTED_STATE = "selected";
const NODE_SIZE: [number, number] = [190, 76];
const COLUMN_GAP = 72;
const ROW_GAP = 52;

export function MapReviewCanvas({
  graph,
  knowledgeMap,
  warnings,
  selectedNodeId,
  onSelectNode
}: MapReviewCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<G6Graph | null>(null);
  const selectedNodeIdRef = useRef(selectedNodeId);

  const graphDataKey = [
    graph.graph_manifest.version,
    graph.authored_nodes.map((node) => `${node.id}:${node.name}`).join("\u0000"),
    graph.authored_edges.map((edge) => `${edge.id}:${edge.source}:${edge.target}:${edge.type}`).join("\u0000"),
    knowledgeMap.states.map((state) => `${state.node_id}:${state.mastery_level}`).join("\u0000"),
    warnings.map((warning) => `${warning.edge_id}:${warning.source_node_id}:${warning.target_node_id}`).join("\u0000")
  ].join("\u0001");

  useEffect(() => {
    selectedNodeIdRef.current = selectedNodeId;
  }, [selectedNodeId]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const graphInstance = new G6Graph({
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
            labelMaxWidth: 150,
            labelWordWrap: false,
            icon: false,
            badge: false,
            port: false
          };
        },
        state: {
          [SELECTED_STATE]: {
            stroke: "#111827",
            lineWidth: 5,
            halo: true,
            haloStroke: "#111827",
            haloStrokeOpacity: 0.14,
            haloLineWidth: 18
          }
        }
      },
      edge: {
        type: "polyline",
        style: (datum) => {
          const edgeType = getEdgeType(datum);
          return {
            stroke: "#7c8d88",
            strokeOpacity: 0.42,
            lineWidth: edgeType === "prerequisite_for" ? 1.8 : 1.2,
            lineDash: edgeType === "contrasts_with" ? [4, 5] : 0,
            endArrow: edgeType !== "contrasts_with",
            endArrowType: "vee",
            endArrowSize: 7,
            labelText: edgeType,
            labelFill: "#5f6d69",
            labelFontSize: 10,
            labelBackground: true,
            labelBackgroundFill: "#eef3f1",
            labelBackgroundOpacity: 0.82,
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
    const resizeObserver = new ResizeObserver(() => graphInstance.resize());
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

    try {
      graphInstance.setData(toG6Data(graph, knowledgeMap, warnings));
    } catch (error) {
      if (!isGraphRuntimeAvailable(graphInstance) || isGraphLifecycleError(error)) return;
      throw error;
    }

    let cancelled = false;
    let draw: Promise<unknown>;
    try {
      draw = graphInstance.render();
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
  }, [graph, graphDataKey, knowledgeMap, warnings]);

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
      aria-label="Candidate knowledge map review graph"
    />
  );
}

function toG6Data(
  graph: ReviewedGraphPayload,
  knowledgeMap: KnowledgeMap,
  warnings: MapEdgeConsistencyWarning[]
) {
  const stateByNodeId = new Map(knowledgeMap.states.map((state) => [state.node_id, state]));
  const warningNodeIds = new Set(
    warnings.flatMap((warning) => [warning.source_node_id, warning.target_node_id])
  );
  const nodeIds = new Set(graph.authored_nodes.map((node) => node.id));
  const positions = buildNodePositions(graph.authored_nodes);

  return {
    nodes: graph.authored_nodes.map((node): G6NodeData => {
      const state = stateByNodeId.get(node.id);
      return {
        id: node.id,
        style: {
          ...positions[node.id],
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

function buildNodePositions(nodes: ReviewedGraphPayload["authored_nodes"]) {
  const columnCount = Math.max(3, Math.ceil(Math.sqrt(nodes.length * 1.45)));
  const columnWidth = NODE_SIZE[0] + COLUMN_GAP;
  const rowHeight = NODE_SIZE[1] + ROW_GAP;
  const rowCount = Math.ceil(nodes.length / columnCount);
  const totalWidth = (columnCount - 1) * columnWidth;
  const totalHeight = Math.max(0, (rowCount - 1) * rowHeight);
  const positions: Record<string, { x: number; y: number }> = {};

  nodes.forEach((node, index) => {
    const column = index % columnCount;
    const row = Math.floor(index / columnCount);
    positions[node.id] = {
      x: column * columnWidth - totalWidth / 2,
      y: row * rowHeight - totalHeight / 2
    };
  });

  return positions;
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
  return wrapLabel(name, 21, 3);
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

function wrapLabel(value: string, maxLineLength: number, maxLines: number) {
  const words = value.split(/[\s_-]+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxLineLength || !current) {
      current = candidate;
      continue;
    }
    lines.push(current);
    current = word;
    if (lines.length === maxLines - 1) break;
  }

  if (current && lines.length < maxLines) {
    lines.push(current);
  }

  if (lines.length === maxLines && words.join(" ").length > lines.join(" ").length) {
    lines[maxLines - 1] = `${lines[maxLines - 1].slice(0, Math.max(0, maxLineLength - 1))}...`;
  }

  return lines.join("\n");
}
