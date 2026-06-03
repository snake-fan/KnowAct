import type { KnowledgeEdge } from "../../api/authoring";

export type GraphLayoutNode = {
  id: string;
};

export type GraphNodePosition = {
  x: number;
  y: number;
};

export type GraphLayoutOptions = {
  nodeSize: [number, number];
  layerGap: number;
  rowGap: number;
  minNodesPerLayer: number;
  targetNodesPerLayer: number;
  maxNodesPerLayer: number;
};

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

const EDGE_TYPE_LAYOUT_WEIGHTS: Record<KnowledgeEdge["type"], number> = {
  prerequisite_for: 3,
  part_of: 2,
  supports: 1,
  contrasts_with: 0
};

export function buildLayeredGraphNodePositions<Node extends GraphLayoutNode>(
  nodes: Node[],
  edges: KnowledgeEdge[],
  options: GraphLayoutOptions
) {
  const context = buildLayoutContext(nodes, edges);
  const layeredNodes = buildReviewLayoutLayers(nodes, context, options);
  const totalWidth = Math.max(0, (layeredNodes.length - 1) * (options.nodeSize[0] + options.layerGap));
  const positions: Record<string, GraphNodePosition> = {};

  layeredNodes.forEach((layerNodes, layer) => {
    const x = layer * (options.nodeSize[0] + options.layerGap) - totalWidth / 2;
    const totalHeight = Math.max(0, (layerNodes.length - 1) * (options.nodeSize[1] + options.rowGap));
    layerNodes.forEach((node, index) => {
      positions[node.id] = {
        x,
        y: index * (options.nodeSize[1] + options.rowGap) - totalHeight / 2
      };
    });
  });

  return positions;
}

export function wrapGraphNodeLabel(value: string, maxLineLength: number, maxLines: number) {
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

function buildLayoutContext<Node extends GraphLayoutNode>(nodes: Node[], edges: KnowledgeEdge[]): LayoutContext {
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

function buildReviewLayoutLayers<Node extends GraphLayoutNode>(
  nodes: Node[],
  context: LayoutContext,
  options: GraphLayoutOptions
) {
  const nodesById = new Map(nodes.map((node) => [node.id, node]));
  const unplaced = new Set(nodes.map((node) => node.id));
  const placed = new Set<string>();
  const layers: Node[][] = [];
  let previousLayerIds = new Set<string>();

  while (unplaced.size > 0) {
    const layer =
      layers.length === 0
        ? pickFirstLayer(nodesById, unplaced, context, options)
        : pickNextLayer(nodesById, unplaced, placed, previousLayerIds, context, options);

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

function pickFirstLayer<Node extends GraphLayoutNode>(
  nodesById: Map<string, Node>,
  unplaced: Set<string>,
  context: LayoutContext,
  options: GraphLayoutOptions
) {
  const unplacedNodes = getUnplacedNodes(nodesById, unplaced);
  const zeroIncomingNodes = unplacedNodes.filter((node) => (context.incoming.get(node.id)?.length ?? 0) === 0);
  const primaryNodes = zeroIncomingNodes.length > 0 ? zeroIncomingNodes : unplacedNodes;
  const forceCycleSplit = zeroIncomingNodes.length === 0 && hasDirectedLayoutEdges(context);
  const layerSize = chooseLayerSize(primaryNodes.length, unplacedNodes.length, options, forceCycleSplit);
  return pickLayerNodes(
    primaryNodes.sort((left, right) => compareFoundationNodes(left.id, right.id, context)),
    unplacedNodes.sort((left, right) => compareFoundationNodes(left.id, right.id, context)),
    layerSize
  );
}

function pickNextLayer<Node extends GraphLayoutNode>(
  nodesById: Map<string, Node>,
  unplaced: Set<string>,
  placed: Set<string>,
  previousLayerIds: Set<string>,
  context: LayoutContext,
  options: GraphLayoutOptions
) {
  const unplacedNodes = getUnplacedNodes(nodesById, unplaced);
  const primaryNodes = unplacedNodes
    .filter((node) => previousLayerConnectionMetrics(node.id, previousLayerIds, context).count > 0)
    .sort((left, right) => compareProgressionNodes(left.id, right.id, previousLayerIds, context));
  const layerSize = chooseLayerSize(primaryNodes.length, unplacedNodes.length, options);
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

function pickLayerNodes<Node extends GraphLayoutNode>(primaryNodes: Node[], fallbackNodes: Node[], layerSize: number) {
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

function chooseLayerSize(
  primaryCandidateCount: number,
  remainingCount: number,
  options: GraphLayoutOptions,
  forceSplit = false
) {
  if (remainingCount <= options.maxNodesPerLayer) {
    if (
      remainingCount >= options.minNodesPerLayer * 2 &&
      (forceSplit || (primaryCandidateCount > 0 && primaryCandidateCount < remainingCount))
    ) {
      return Math.min(
        Math.max(primaryCandidateCount, options.minNodesPerLayer),
        remainingCount - options.minNodesPerLayer
      );
    }
    return remainingCount;
  }

  let layerSize = primaryCandidateCount > options.targetNodesPerLayer
    ? options.maxNodesPerLayer
    : options.targetNodesPerLayer;
  layerSize = Math.min(layerSize, remainingCount);
  layerSize = Math.max(layerSize, options.minNodesPerLayer);

  const remainder = remainingCount - layerSize;
  if (remainder > 0 && remainder < options.minNodesPerLayer) {
    const shrinkBy = options.minNodesPerLayer - remainder;
    if (layerSize - shrinkBy >= options.minNodesPerLayer) {
      layerSize -= shrinkBy;
    } else if (layerSize + remainder <= options.maxNodesPerLayer) {
      layerSize += remainder;
    }
  }

  return layerSize;
}

function getUnplacedNodes<Node extends GraphLayoutNode>(nodesById: Map<string, Node>, unplaced: Set<string>) {
  return Array.from(unplaced)
    .map((id) => nodesById.get(id))
    .filter((node): node is Node => node !== undefined);
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
