import { useEffect, useRef } from "react";
import {
  Graph as G6Graph,
  type EdgeData as G6EdgeData,
  type IPointerEvent,
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

type CandidateGraphCanvasProps = {
  graph: CandidateGraphPayload;
  selection: Selection;
  onSelect: (selection: Selection) => void;
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
const EDGE_TYPE_LAYOUT_WEIGHTS: Record<KnowledgeEdge["type"], number> = {
  prerequisite_for: 3,
  part_of: 2,
  supports: 1,
  contrasts_with: 0
};

type CandidateNode = CandidateGraphPayload["candidate_nodes"][number];
type LayoutEdge = KnowledgeEdge & {
  layoutStrength: number;
};
type LayoutContext = {
  incoming: Map<string, LayoutEdge[]>;
  outgoing: Map<string, LayoutEdge[]>;
  adjacent: Map<string, LayoutEdge[]>;
  directedRanks: Map<string, number>;
  degreeMap: Map<string, number>;
  foundationScore: Map<string, number>;
};

export function CandidateGraphCanvas({
  graph,
  selection,
  onSelect,
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
          type: "zoom-canvas",
          key: "candidate-zoom-canvas",
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
        aria-label="Candidate knowledge graph"
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
  const positions = buildLayeredNodePositions(graph.candidate_nodes, graph.candidate_edges);
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
  return wrapLabel(name, 22, 3);
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

function buildLayeredNodePositions(nodes: CandidateNode[], edges: KnowledgeEdge[]) {
  const context = buildLayoutContext(nodes, edges);
  const layeredNodes = buildReviewLayoutLayers(nodes, context);
  const totalWidth = Math.max(0, (layeredNodes.length - 1) * (NODE_SIZE[0] + LAYER_GAP));
  const positions: Record<string, NodePosition> = {};

  layeredNodes.forEach((layerNodes, layer) => {
    const x = layer * (NODE_SIZE[0] + LAYER_GAP) - totalWidth / 2;
    const totalHeight = Math.max(0, (layerNodes.length - 1) * (NODE_SIZE[1] + ROW_GAP));
    layerNodes.forEach((node, index) => {
      positions[node.id] = {
        x,
        y: index * (NODE_SIZE[1] + ROW_GAP) - totalHeight / 2
      };
    });
  });

  return positions;
}

function buildLayoutContext(nodes: CandidateNode[], edges: KnowledgeEdge[]): LayoutContext {
  const nodeIds = nodes.map((node) => node.id);
  const knownNodeIds = new Set(nodeIds);
  const directedEdges: LayoutEdge[] = [];
  const incoming = initializeEdgeMap(nodeIds);
  const outgoing = initializeEdgeMap(nodeIds);
  const adjacent = initializeEdgeMap(nodeIds);
  const degreeMap = new Map(nodeIds.map((id) => [id, 0]));

  for (const edge of edges) {
    if (!knownNodeIds.has(edge.source) || !knownNodeIds.has(edge.target)) continue;
    degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1);
    degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1);

    if (!isDirectedLayoutEdge(edge)) continue;

    const typeWeight = EDGE_TYPE_LAYOUT_WEIGHTS[edge.type];
    const layoutEdge: LayoutEdge = {
      ...edge,
      layoutStrength: typeWeight * clamp01(edge.weight) * clamp01(edge.curation_confidence)
    };
    directedEdges.push(layoutEdge);
    outgoing.get(edge.source)?.push(layoutEdge);
    incoming.get(edge.target)?.push(layoutEdge);
    adjacent.get(edge.source)?.push(layoutEdge);
    adjacent.get(edge.target)?.push(layoutEdge);
  }

  const directedRanks = computeDirectedRanks(nodeIds, directedEdges);
  const foundationScore = new Map(
    nodeIds.map((id) => {
      const outgoingEdges = outgoing.get(id) ?? [];
      const incomingEdges = incoming.get(id) ?? [];
      return [
        id,
        sumEdgeStrength(outgoingEdges) * 4 +
          outgoingEdges.length * 2 -
          sumEdgeStrength(incomingEdges) * 1.5 -
          incomingEdges.length * 3
      ];
    })
  );

  return {
    incoming,
    outgoing,
    adjacent,
    directedRanks,
    degreeMap,
    foundationScore
  };
}

function buildReviewLayoutLayers(nodes: CandidateNode[], context: LayoutContext) {
  const nodesById = new Map(nodes.map((node) => [node.id, node]));
  const unplaced = new Set(nodes.map((node) => node.id));
  const placed = new Set<string>();
  const layers: CandidateNode[][] = [];
  let previousLayerIds = new Set<string>();

  while (unplaced.size > 0) {
    const layer =
      layers.length === 0
        ? pickFirstLayer(nodesById, unplaced, context)
        : pickNextLayer(nodesById, unplaced, placed, previousLayerIds, context);

    if (layer.length === 0) {
      const fallback = getUnplacedNodes(nodesById, unplaced).sort((left, right) =>
        compareFoundationNodes(left.id, right.id, context)
      )[0];
      if (!fallback) break;
      layer.push(fallback);
    }

    layers.push(layer);
    previousLayerIds = new Set(layer.map((node) => node.id));
    for (const node of layer) {
      unplaced.delete(node.id);
      placed.add(node.id);
    }
  }

  return layers;
}

function pickFirstLayer(nodesById: Map<string, CandidateNode>, unplaced: Set<string>, context: LayoutContext) {
  const unplacedNodes = getUnplacedNodes(nodesById, unplaced);
  const zeroIncomingNodes = unplacedNodes.filter((node) => (context.incoming.get(node.id)?.length ?? 0) === 0);
  const primaryNodes = zeroIncomingNodes.length > 0 ? zeroIncomingNodes : unplacedNodes;
  const forceCycleSplit = zeroIncomingNodes.length === 0 && hasDirectedLayoutEdges(context);
  const layerSize = chooseLayerSize(primaryNodes.length, unplacedNodes.length, forceCycleSplit);
  return pickLayerNodes(
    primaryNodes.sort((left, right) => compareFoundationNodes(left.id, right.id, context)),
    unplacedNodes.sort((left, right) => compareFoundationNodes(left.id, right.id, context)),
    layerSize
  );
}

function pickNextLayer(
  nodesById: Map<string, CandidateNode>,
  unplaced: Set<string>,
  placed: Set<string>,
  previousLayerIds: Set<string>,
  context: LayoutContext
) {
  const unplacedNodes = getUnplacedNodes(nodesById, unplaced);
  const primaryNodes = unplacedNodes
    .filter((node) => previousLayerConnectionMetrics(node.id, previousLayerIds, context).count > 0)
    .sort((left, right) => compareProgressionNodes(left.id, right.id, previousLayerIds, context));
  const layerSize = chooseLayerSize(primaryNodes.length, unplacedNodes.length);
  const layer = primaryNodes.slice(0, layerSize);
  const selected = new Set(layer.map((node) => node.id));

  if (layer.length < layerSize) {
    const frontierNodes = unplacedNodes
      .filter((node) => !selected.has(node.id) && frontierConnectionMetrics(node.id, placed, context).count > 0)
      .sort((left, right) => compareFrontierNodes(left.id, right.id, placed, context));
    for (const node of frontierNodes) {
      if (layer.length >= layerSize) break;
      layer.push(node);
      selected.add(node.id);
    }
  }

  if (layer.length < layerSize) {
    const fallbackNodes = unplacedNodes
      .filter((node) => !selected.has(node.id))
      .sort((left, right) => compareFoundationNodes(left.id, right.id, context));
    for (const node of fallbackNodes) {
      if (layer.length >= layerSize) break;
      layer.push(node);
    }
  }

  return layer;
}

function pickLayerNodes(primaryNodes: CandidateNode[], fallbackNodes: CandidateNode[], layerSize: number) {
  const layer = primaryNodes.slice(0, layerSize);
  const selected = new Set(layer.map((node) => node.id));
  for (const node of fallbackNodes) {
    if (layer.length >= layerSize) break;
    if (selected.has(node.id)) continue;
    layer.push(node);
    selected.add(node.id);
  }
  return layer;
}

function chooseLayerSize(primaryCandidateCount: number, remainingCount: number, forceSplit = false) {
  if (remainingCount <= MAX_NODES_PER_LAYER) {
    if (
      remainingCount >= MIN_NODES_PER_LAYER * 2 &&
      (forceSplit || (primaryCandidateCount > 0 && primaryCandidateCount < remainingCount))
    ) {
      return Math.min(Math.max(primaryCandidateCount, MIN_NODES_PER_LAYER), remainingCount - MIN_NODES_PER_LAYER);
    }
    return remainingCount;
  }

  let layerSize = primaryCandidateCount > TARGET_NODES_PER_LAYER ? MAX_NODES_PER_LAYER : TARGET_NODES_PER_LAYER;
  layerSize = Math.min(layerSize, remainingCount);
  layerSize = Math.max(layerSize, MIN_NODES_PER_LAYER);

  const remainder = remainingCount - layerSize;
  if (remainder > 0 && remainder < MIN_NODES_PER_LAYER) {
    const shrinkBy = MIN_NODES_PER_LAYER - remainder;
    if (layerSize - shrinkBy >= MIN_NODES_PER_LAYER) {
      layerSize -= shrinkBy;
    } else if (layerSize + remainder <= MAX_NODES_PER_LAYER) {
      layerSize += remainder;
    }
  }

  return layerSize;
}

function getUnplacedNodes(nodesById: Map<string, CandidateNode>, unplaced: Set<string>) {
  return Array.from(unplaced)
    .map((id) => nodesById.get(id))
    .filter((node): node is CandidateNode => node !== undefined);
}

function initializeEdgeMap(nodeIds: string[]) {
  return new Map(nodeIds.map((id) => [id, [] as LayoutEdge[]]));
}

function hasDirectedLayoutEdges(context: LayoutContext) {
  return Array.from(context.outgoing.values()).some((edges) => edges.length > 0);
}

function computeDirectedRanks(nodeIds: string[], directedEdges: LayoutEdge[]) {
  const ranks = new Map(nodeIds.map((id) => [id, 0]));
  const indegree = new Map(nodeIds.map((id) => [id, 0]));
  const outgoing = new Map(nodeIds.map((id) => [id, [] as string[]]));

  for (const edge of directedEdges) {
    outgoing.get(edge.source)?.push(edge.target);
    indegree.set(edge.target, (indegree.get(edge.target) ?? 0) + 1);
  }

  const queue = nodeIds.filter((id) => (indegree.get(id) ?? 0) === 0).sort(compareNodeIds);
  const visited = new Set<string>();

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (visited.has(current)) continue;
    visited.add(current);
    for (const target of outgoing.get(current) ?? []) {
      ranks.set(target, Math.max(ranks.get(target) ?? 0, (ranks.get(current) ?? 0) + 1));
      indegree.set(target, (indegree.get(target) ?? 0) - 1);
      if ((indegree.get(target) ?? 0) === 0) {
        queue.push(target);
        queue.sort(compareNodeIds);
      }
    }
  }

  for (const id of nodeIds) {
    if (visited.has(id)) continue;
    const incomingRanks = directedEdges
      .filter((edge) => edge.target === id && visited.has(edge.source))
      .map((edge) => (ranks.get(edge.source) ?? 0) + 1);
    if (incomingRanks.length > 0) {
      ranks.set(id, Math.max(...incomingRanks));
    }
  }

  return ranks;
}

function compareFoundationNodes(leftId: string, rightId: string, context: LayoutContext) {
  return (
    compareAscending(context.incoming.get(leftId)?.length ?? 0, context.incoming.get(rightId)?.length ?? 0) ||
    compareDescending(context.foundationScore.get(leftId) ?? 0, context.foundationScore.get(rightId) ?? 0) ||
    compareDescending(context.outgoing.get(leftId)?.length ?? 0, context.outgoing.get(rightId)?.length ?? 0) ||
    compareDescending(context.degreeMap.get(leftId) ?? 0, context.degreeMap.get(rightId) ?? 0) ||
    compareNodeIds(leftId, rightId)
  );
}

function compareProgressionNodes(
  leftId: string,
  rightId: string,
  previousLayerIds: Set<string>,
  context: LayoutContext
) {
  const left = previousLayerConnectionMetrics(leftId, previousLayerIds, context);
  const right = previousLayerConnectionMetrics(rightId, previousLayerIds, context);
  return (
    compareDescending(left.count, right.count) ||
    compareDescending(left.strength, right.strength) ||
    compareDescending(context.degreeMap.get(leftId) ?? 0, context.degreeMap.get(rightId) ?? 0) ||
    compareFoundationNodes(leftId, rightId, context)
  );
}

function compareFrontierNodes(leftId: string, rightId: string, placed: Set<string>, context: LayoutContext) {
  const left = frontierConnectionMetrics(leftId, placed, context);
  const right = frontierConnectionMetrics(rightId, placed, context);
  return (
    compareDescending(left.incomingCount, right.incomingCount) ||
    compareDescending(left.incomingStrength, right.incomingStrength) ||
    compareDescending(left.count, right.count) ||
    compareDescending(left.strength, right.strength) ||
    compareAscending(context.directedRanks.get(leftId) ?? 0, context.directedRanks.get(rightId) ?? 0) ||
    compareDescending(context.degreeMap.get(leftId) ?? 0, context.degreeMap.get(rightId) ?? 0) ||
    compareFoundationNodes(leftId, rightId, context)
  );
}

function previousLayerConnectionMetrics(nodeId: string, previousLayerIds: Set<string>, context: LayoutContext) {
  const incomingEdges = (context.incoming.get(nodeId) ?? []).filter((edge) => previousLayerIds.has(edge.source));
  return {
    count: incomingEdges.length,
    strength: sumEdgeStrength(incomingEdges)
  };
}

function frontierConnectionMetrics(nodeId: string, placed: Set<string>, context: LayoutContext) {
  const incomingEdges = (context.incoming.get(nodeId) ?? []).filter((edge) => placed.has(edge.source));
  const adjacentEdges = (context.adjacent.get(nodeId) ?? []).filter(
    (edge) => placed.has(edge.source) || placed.has(edge.target)
  );
  return {
    incomingCount: incomingEdges.length,
    incomingStrength: sumEdgeStrength(incomingEdges),
    count: adjacentEdges.length,
    strength: sumEdgeStrength(adjacentEdges)
  };
}

function sumEdgeStrength(edges: LayoutEdge[]) {
  return edges.reduce((total, edge) => total + edge.layoutStrength, 0);
}

function clamp01(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

function compareAscending(left: number, right: number) {
  return left === right ? 0 : left - right;
}

function compareDescending(left: number, right: number) {
  return left === right ? 0 : right - left;
}

function isDirectedLayoutEdge(edge: KnowledgeEdge) {
  return edge.type !== "contrasts_with" && edge.source !== edge.target;
}

function compareNodeIds(left: string, right: string) {
  return left.localeCompare(right);
}

function wrapLabel(value: string, maxLineLength: number, maxLines: number) {
  const words = value.trim().split(/\s+/).filter(Boolean);
  const lines: string[] = [];

  for (const word of words.length > 0 ? words : [value]) {
    const parts = splitLongWord(word, maxLineLength);
    for (const part of parts) {
      const current = lines[lines.length - 1] ?? "";
      const next = current ? `${current} ${part}` : part;
      if (next.length <= maxLineLength && current) {
        lines[lines.length - 1] = next;
      } else {
        lines.push(part);
      }
    }
  }

  const truncated = lines.length > maxLines;
  if (truncated) {
    return formatLabelLines(lines.slice(0, maxLines), maxLineLength, true).join("\n");
  }
  return formatLabelLines(lines, maxLineLength, truncated).join("\n");
}

function splitLongWord(word: string, maxLineLength: number) {
  if (word.length <= maxLineLength) return [word];
  const parts: string[] = [];
  for (let index = 0; index < word.length; index += maxLineLength) {
    parts.push(word.slice(index, index + maxLineLength));
  }
  return parts;
}

function formatLabelLines(lines: string[], maxLineLength: number, truncated: boolean) {
  const next = [...lines];
  const lastIndex = next.length - 1;
  if (lastIndex < 0) {
    return next;
  }
  if (truncated) {
    next[lastIndex] = `${next[lastIndex].slice(0, Math.max(0, maxLineLength - 3))}...`;
    return next;
  }
  if (next[lastIndex].length > maxLineLength) {
    next[lastIndex] = `${next[lastIndex].slice(0, maxLineLength - 1)}...`;
  }
  return next;
}
