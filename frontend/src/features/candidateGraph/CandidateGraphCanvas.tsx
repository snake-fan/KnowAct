import { useEffect, useRef } from "react";
import {
  CanvasEvent,
  EdgeEvent,
  Graph as G6Graph,
  NodeEvent,
  type EdgeData as G6EdgeData,
  type IElementEvent,
  type NodeData as G6NodeData
} from "@antv/g6";
import {
  CandidateGraphPayload,
  KnowledgeEdge
} from "../../api/authoring";

type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | null;

type CandidateGraphCanvasProps = {
  graph: CandidateGraphPayload;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  layoutVersion: number;
};

const SELECTED_STATE = "selected";
const VIEW_PADDING: [number, number, number, number] = [84, 96, 84, 96];
const NODE_SIZE: [number, number] = [188, 76];

export function CandidateGraphCanvas({
  graph,
  selection,
  onSelect,
  layoutVersion
}: CandidateGraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<G6Graph | null>(null);
  const appliedStructureKeyRef = useRef<string | null>(null);
  const graphPayloadRef = useRef(graph);
  const selectionRef = useRef(selection);

  const structureKey = [
    graph.run_id,
    layoutVersion,
    graph.candidate_nodes.map((node) => node.id).join("\u0000"),
    graph.candidate_edges
      .map((edge) => `${edge.id}:${edge.source}:${edge.target}:${edge.type}`)
      .join("\u0000")
  ].join("\u0001");

  const contentKey = [
    graph.candidate_nodes
      .map((node) => `${node.id}:${node.name}:${node.type}`)
      .join("\u0000"),
    graph.candidate_edges
      .map((edge) => `${edge.id}:${edge.type}:${edge.weight}:${edge.curation_confidence}`)
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

    const graphInstance = new G6Graph({
      container,
      autoResize: true,
      background: "#eef3f1",
      padding: VIEW_PADDING,
      zoomRange: [0.24, 2.8],
      autoFit: { type: "view", options: { when: "always" }, animation: false },
      data: { nodes: [], edges: [] },
      layout: {
        type: "antv-dagre",
        rankdir: "LR",
        ranksep: 128,
        nodesep: 52,
        animation: false
      },
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
          labelFill: "#1b1f24",
          labelFontSize: 12,
          labelFontWeight: 700,
          labelLineHeight: 16,
          labelMaxWidth: 152,
          labelWordWrap: true,
          labelWordWrapWidth: 152
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
      behaviors: ["drag-canvas", "zoom-canvas", "drag-element"],
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

    const selectNode = (event: IElementEvent) => {
      event.stopPropagation();
      onSelect({ kind: "node", id: String(event.target.id) });
    };
    const selectEdge = (event: IElementEvent) => {
      event.stopPropagation();
      onSelect({ kind: "edge", id: String(event.target.id) });
    };
    const clearSelection = () => onSelect(null);

    graphInstance.on(NodeEvent.CLICK, selectNode);
    graphInstance.on(EdgeEvent.CLICK, selectEdge);
    graphInstance.on(CanvasEvent.CLICK, clearSelection);

    const resizeObserver = new ResizeObserver(() => {
      graphInstance.resize();
      void graphInstance.fitView({ when: "overflow" }, false);
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      graphInstance.destroy();
      graphRef.current = null;
    };
  }, [onSelect]);

  useEffect(() => {
    const graphInstance = graphRef.current;
    if (!graphInstance) return;

    const currentGraph = graphPayloadRef.current;
    const shouldRelayout = appliedStructureKeyRef.current !== structureKey;
    appliedStructureKeyRef.current = structureKey;
    graphInstance.setData(toG6Data(currentGraph));

    let cancelled = false;
    const draw = shouldRelayout ? graphInstance.render() : graphInstance.draw();
    void draw.then(async () => {
      if (cancelled) return;
      await applySelectionState(graphInstance, currentGraph, selectionRef.current);
    });

    return () => {
      cancelled = true;
    };
  }, [contentKey, structureKey]);

  useEffect(() => {
    const graphInstance = graphRef.current;
    if (!graphInstance) return;
    void applySelectionState(graphInstance, graph, selection);
  }, [graph, selection]);

  return (
    <div className="graph-canvas-shell">
      <div
        className="graph-canvas"
        ref={containerRef}
        role="img"
        aria-label="Candidate knowledge graph"
      />
    </div>
  );
}

function toG6Data(graph: CandidateGraphPayload) {
  const nodeIds = new Set(graph.candidate_nodes.map((node) => node.id));
  return {
    nodes: graph.candidate_nodes.map((node): G6NodeData => ({
      id: node.id,
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

async function applySelectionState(
  graphInstance: G6Graph,
  graph: CandidateGraphPayload,
  selection: Selection
) {
  const states: Record<string, string[]> = {};
  const visibleEdgeIds = new Set(toG6Data(graph).edges.map((edge) => String(edge.id)));

  for (const node of graph.candidate_nodes) {
    states[node.id] = selection?.kind === "node" && selection.id === node.id ? [SELECTED_STATE] : [];
  }
  for (const edge of graph.candidate_edges) {
    if (!visibleEdgeIds.has(edge.id)) continue;
    states[edge.id] = selection?.kind === "edge" && selection.id === edge.id ? [SELECTED_STATE] : [];
  }

  await graphInstance.setElementState(states, false);
}

function getNodeLabel(datum: G6NodeData) {
  const name = stringDataValue(datum, "name") || String(datum.id);
  return `${truncate(name, 24)}\n${truncate(String(datum.id), 22)}`;
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

function truncate(value: string, maxLength: number) {
  return value.length <= maxLength ? value : `${value.slice(0, maxLength - 1)}...`;
}
