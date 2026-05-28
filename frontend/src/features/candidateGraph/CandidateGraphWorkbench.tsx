import { FormEvent, PointerEvent as ReactPointerEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  CandidateGraphPayload,
  CandidateGraphRunSummary,
  KnowledgeEdge,
  KnowledgeNode,
  SourceMaterialRecord,
  generateCandidateGraph,
  listCandidateGraphRuns,
  listSourceMaterials,
  readCandidateGraph,
  saveCandidateGraph,
  uploadSourceMaterial
} from "../../api/authoring";

type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | null;

type Point = {
  x: number;
  y: number;
};

type CanvasSize = {
  width: number;
  height: number;
};

type ViewportState = {
  centerX: number;
  centerY: number;
  zoom: number;
};

type DragState =
  | {
      kind: "pan";
      pointerId: number;
      startClientX: number;
      startClientY: number;
      originCenterX: number;
      originCenterY: number;
    }
  | {
      kind: "node";
      pointerId: number;
      nodeId: string;
      startClientX: number;
      startClientY: number;
      originX: number;
      originY: number;
    };

const DEFAULT_DOMAIN = "classical_supervised_ml_algorithms";
const LEVEL_KEYS = ["L0", "L1", "L2", "L3", "L4", "L5"];
const NODE_RADIUS = 42;
const MIN_CANVAS_SIZE: CanvasSize = { width: 900, height: 620 };
const MIN_ZOOM = 0.24;
const MAX_ZOOM = 2.8;

export function CandidateGraphWorkbench() {
  const [materials, setMaterials] = useState<SourceMaterialRecord[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [benchmarkDomain, setBenchmarkDomain] = useState(DEFAULT_DOMAIN);
  const [runId, setRunId] = useState("");
  const [runs, setRuns] = useState<CandidateGraphRunSummary[]>([]);
  const [clientProvider, setClientProvider] = useState<"openai" | "deepseek">("openai");
  const [graph, setGraph] = useState<CandidateGraphPayload | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [layoutVersion, setLayoutVersion] = useState(0);

  useEffect(() => {
    refreshMaterials();
  }, []);

  const selectedNode = useMemo(() => {
    if (!graph || selection?.kind !== "node") return null;
    return graph.candidate_nodes.find((node) => node.id === selection.id) ?? null;
  }, [graph, selection]);

  const selectedEdge = useMemo(() => {
    if (!graph || selection?.kind !== "edge") return null;
    return graph.candidate_edges.find((edge) => edge.id === selection.id) ?? null;
  }, [graph, selection]);

  async function refreshMaterials() {
    await runTask("materials", async () => {
      const nextMaterials = await listSourceMaterials();
      setMaterials(nextMaterials);
      if (!selectedSourceId && nextMaterials.length > 0) {
        setSelectedSourceId(nextMaterials[0].source_id);
      }
    });
  }

  async function refreshRuns() {
    if (!benchmarkDomain.trim()) return;
    await runTask("runs", async () => {
      const response = await listCandidateGraphRuns(benchmarkDomain);
      setRuns(response.runs);
    });
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    const sourceId = String(form.get("source_id") ?? "").trim();
    const title = String(form.get("title") ?? "").trim();
    const citation = String(form.get("citation") ?? "").trim();
    if (!(file instanceof File) || file.size === 0) {
      setError("Choose a PDF file before uploading.");
      return;
    }
    await runTask("upload", async () => {
      const material = await uploadSourceMaterial({ file, sourceId, title, citation });
      setSelectedSourceId(material.source_id);
      setNotice(`Uploaded ${material.source_id}`);
      await refreshMaterials();
    });
  }

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedSourceId) {
      setError("Select a source material first.");
      return;
    }
    await runTask("generate", async () => {
      const response = await generateCandidateGraph({
        sourceId: selectedSourceId,
        benchmarkDomain,
        runId: runId.trim() || undefined,
        clientProvider
      });
      if (!response.artifact_paths) {
        throw new Error("Generation completed without artifact paths.");
      }
      const nextGraph: CandidateGraphPayload = {
        benchmark_domain: benchmarkDomain,
        run_id: response.run_log_summary.run_id,
        candidate_nodes: response.candidate_nodes,
        candidate_edges: response.candidate_edges,
        artifact_paths: response.artifact_paths
      };
      setGraph(nextGraph);
      setRunId(nextGraph.run_id);
      setSelection(nextGraph.candidate_nodes[0] ? { kind: "node", id: nextGraph.candidate_nodes[0].id } : null);
      setLayoutVersion((version) => version + 1);
      setNotice(`Generated ${nextGraph.candidate_nodes.length} nodes and ${nextGraph.candidate_edges.length} edges.`);
    });
  }

  async function handleLoadRun() {
    if (!benchmarkDomain.trim() || !runId.trim()) {
      setError("Benchmark domain and run id are required.");
      return;
    }
    await runTask("load", async () => {
      const nextGraph = await readCandidateGraph(benchmarkDomain, runId);
      setGraph(nextGraph);
      setSelection(nextGraph.candidate_nodes[0] ? { kind: "node", id: nextGraph.candidate_nodes[0].id } : null);
      setLayoutVersion((version) => version + 1);
      setNotice(`Loaded ${nextGraph.run_id}`);
    });
  }

  async function handleSave() {
    if (!graph) return;
    await runTask("save", async () => {
      const saved = await saveCandidateGraph(graph);
      setGraph(saved);
      setNotice("Candidate graph saved.");
    });
  }

  async function runTask(label: string, task: () => Promise<void>) {
    setBusy(label);
    setError(null);
    setNotice(null);
    try {
      await task();
    } catch (taskError) {
      setError(taskError instanceof Error ? taskError.message : String(taskError));
    } finally {
      setBusy(null);
    }
  }

  function updateNode(id: string, patch: Partial<KnowledgeNode>) {
    if (!graph) return;
    setGraph({
      ...graph,
      candidate_nodes: graph.candidate_nodes.map((node) =>
        node.id === id ? { ...node, ...patch } : node
      )
    });
    if (patch.id) {
      setSelection({ kind: "node", id: patch.id });
    }
  }

  function updateEdge(id: string, patch: Partial<KnowledgeEdge>) {
    if (!graph) return;
    setGraph({
      ...graph,
      candidate_edges: graph.candidate_edges.map((edge) =>
        edge.id === id ? { ...edge, ...patch } : edge
      )
    });
    if (patch.id) {
      setSelection({ kind: "edge", id: patch.id });
    }
  }

  function addNode() {
    if (!graph) return;
    const id = nextId("new_node", graph.candidate_nodes.map((node) => node.id));
    const node: KnowledgeNode = {
      id,
      name: "New Knowledge Node",
      type: "concept",
      definition: "",
      source_locators: [],
      diagnostic_goal: "",
      levels: Object.fromEntries(LEVEL_KEYS.map((level) => [level, ""])),
      diagnostic_signals: [],
      simulator_behavior: ""
    };
    setGraph({ ...graph, candidate_nodes: [...graph.candidate_nodes, node] });
    setSelection({ kind: "node", id });
  }

  function addEdge() {
    if (!graph || graph.candidate_nodes.length < 2) return;
    const source = graph.candidate_nodes[0].id;
    const target = graph.candidate_nodes[1].id;
    const id = nextId("edge_new", graph.candidate_edges.map((edge) => edge.id));
    const edge: KnowledgeEdge = {
      id,
      source,
      target,
      type: "supports",
      rationale: "",
      weight: 0.5,
      curation_confidence: 0.5
    };
    setGraph({ ...graph, candidate_edges: [...graph.candidate_edges, edge] });
    setSelection({ kind: "edge", id });
  }

  function deleteSelection() {
    if (!graph || !selection) return;
    if (selection.kind === "node") {
      setGraph({
        ...graph,
        candidate_nodes: graph.candidate_nodes.filter((node) => node.id !== selection.id),
        candidate_edges: graph.candidate_edges.filter(
          (edge) => edge.source !== selection.id && edge.target !== selection.id
        )
      });
    } else {
      setGraph({
        ...graph,
        candidate_edges: graph.candidate_edges.filter((edge) => edge.id !== selection.id)
      });
    }
    setSelection(null);
  }

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <h1>Candidate Graph Review Workbench</h1>
          <p>Upload source material, generate a candidate graph, inspect nodes and edges, then save reviewed candidate artifacts.</p>
        </div>
        <div className="status-strip" aria-live="polite">
          {busy && <span className="status busy">Working: {busy}</span>}
          {notice && <span className="status ok">{notice}</span>}
          {error && <span className="status error">{error}</span>}
        </div>
      </section>

      <section className="workspace">
        <aside className="left-panel">
          <form className="panel-block" onSubmit={handleUpload}>
            <h2>Source Material</h2>
            <label>
              PDF
              <input name="file" type="file" accept="application/pdf,.pdf" />
            </label>
            <label>
              Source ID
              <input name="source_id" placeholder="isl_python" required />
            </label>
            <label>
              Title
              <input name="title" placeholder="An Introduction to Statistical Learning" required />
            </label>
            <label>
              Citation
              <input name="citation" placeholder="Optional" />
            </label>
            <button type="submit" disabled={busy !== null}>Upload</button>
          </form>

          <form className="panel-block" onSubmit={handleGenerate}>
            <h2>Generate</h2>
            <label>
              Source
              <select value={selectedSourceId} onChange={(event) => setSelectedSourceId(event.target.value)}>
                <option value="">Select source</option>
                {materials.map((material) => (
                  <option key={material.source_id} value={material.source_id}>
                    {material.source_id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Benchmark Domain
              <input value={benchmarkDomain} onChange={(event) => setBenchmarkDomain(event.target.value)} />
            </label>
            <label>
              Run ID
              <div className="select-with-action">
                <select value={runId} onChange={(event) => setRunId(event.target.value)}>
                  <option value="">-- New run --</option>
                  {runs.map((run) => (
                    <option key={run.run_id} value={run.run_id}>{run.run_id}</option>
                  ))}
                </select>
                <button type="button" onClick={refreshRuns} disabled={busy !== null} title="Refresh runs">&#x21bb;</button>
              </div>
            </label>
            <label>
              Provider
              <select value={clientProvider} onChange={(event) => setClientProvider(event.target.value as "openai" | "deepseek")}>
                <option value="openai">openai</option>
                <option value="deepseek">deepseek</option>
              </select>
            </label>
            <div className="button-row">
              <button type="submit" disabled={busy !== null || !selectedSourceId}>Generate</button>
              <button type="button" onClick={handleLoadRun} disabled={busy !== null || !runId}>Load</button>
            </div>
          </form>

          <div className="panel-block material-list">
            <h2>Catalog</h2>
            {materials.length === 0 ? (
              <p className="empty">No source materials uploaded.</p>
            ) : (
              materials.map((material) => (
                <button
                  key={material.source_id}
                  type="button"
                  className={material.source_id === selectedSourceId ? "list-row active" : "list-row"}
                  onClick={() => setSelectedSourceId(material.source_id)}
                >
                  <strong>{material.source_id}</strong>
                  <span>{material.title}</span>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="graph-panel">
          <div className="graph-toolbar">
            <div>
              <h2>{graph ? graph.run_id : "No candidate graph loaded"}</h2>
              {graph && <p>{graph.candidate_nodes.length} nodes / {graph.candidate_edges.length} edges</p>}
            </div>
            <div className="button-row">
              <button type="button" onClick={() => setLayoutVersion((version) => version + 1)} disabled={!graph}>
                Reflow
              </button>
              <button type="button" onClick={addNode} disabled={!graph}>Add Node</button>
              <button type="button" onClick={addEdge} disabled={!graph || graph.candidate_nodes.length < 2}>Add Edge</button>
              <button type="button" onClick={deleteSelection} disabled={!selection}>Delete</button>
              <button type="button" onClick={handleSave} disabled={!graph || busy !== null}>Save</button>
            </div>
          </div>
          {graph ? (
            <GraphCanvas
              graph={graph}
              selection={selection}
              onSelect={setSelection}
              layoutVersion={layoutVersion}
            />
          ) : (
            <div className="empty-graph">Upload or select a source material, then generate a candidate graph.</div>
          )}
        </section>

        <aside className="right-panel">
          <h2>Inspector</h2>
          {selectedNode && (
            <NodeInspector node={selectedNode} onChange={(patch) => updateNode(selectedNode.id, patch)} />
          )}
          {selectedEdge && graph && (
            <EdgeInspector
              edge={selectedEdge}
              nodeIds={graph.candidate_nodes.map((node) => node.id)}
              onChange={(patch) => updateEdge(selectedEdge.id, patch)}
            />
          )}
          {!selectedNode && !selectedEdge && <p className="empty">Select a node or edge.</p>}
        </aside>
      </section>
    </main>
  );
}

function GraphCanvas({
  graph,
  selection,
  onSelect,
  layoutVersion
}: {
  graph: CandidateGraphPayload;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  layoutVersion: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const appliedLayoutKeyRef = useRef<string | null>(null);
  const nodePositionsRef = useRef<Record<string, Point>>({});
  const viewportRef = useRef<ViewportState>({ centerX: 0, centerY: 0, zoom: 1 });
  const canvasSizeRef = useRef<CanvasSize>(MIN_CANVAS_SIZE);

  const [canvasSize, setCanvasSize] = useState<CanvasSize>(MIN_CANVAS_SIZE);
  const [nodePositions, setNodePositions] = useState<Record<string, Point>>({});
  const [viewport, setViewport] = useState<ViewportState>({ centerX: 0, centerY: 0, zoom: 1 });
  const [isPanning, setIsPanning] = useState(false);

  const nodeIdsKey = graph.candidate_nodes.map((node) => node.id).join("\u0000");
  const edgeKey = graph.candidate_edges
    .map((edge) => `${edge.id}:${edge.source}:${edge.target}:${edge.type}`)
    .join("\u0000");
  const layoutKey = `${graph.run_id}:${layoutVersion}`;

  useEffect(() => {
    nodePositionsRef.current = nodePositions;
  }, [nodePositions]);

  useEffect(() => {
    viewportRef.current = viewport;
  }, [viewport]);

  useEffect(() => {
    canvasSizeRef.current = canvasSize;
  }, [canvasSize]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const nextSize = {
        width: Math.max(Math.round(entry.contentRect.width), MIN_CANVAS_SIZE.width),
        height: Math.max(Math.round(entry.contentRect.height), MIN_CANVAS_SIZE.height)
      };
      setCanvasSize((current) => (
        current.width === nextSize.width && current.height === nextSize.height ? current : nextSize
      ));
    });

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    function preventPageScroll(event: WheelEvent) {
      event.preventDefault();
    }

    element.addEventListener("wheel", preventPageScroll, { passive: false });
    return () => element.removeEventListener("wheel", preventPageScroll);
  }, []);

  useEffect(() => {
    if (canvasSize.width === 0 || canvasSize.height === 0) return;
    if (appliedLayoutKeyRef.current === layoutKey) return;

    const nextPositions = buildStructuredLayout(graph.candidate_nodes, graph.candidate_edges);
    const nextViewport = fitViewport(nextPositions, canvasSize);

    appliedLayoutKeyRef.current = layoutKey;
    nodePositionsRef.current = nextPositions;
    viewportRef.current = nextViewport;
    setNodePositions(nextPositions);
    setViewport(nextViewport);
  }, [canvasSize.height, canvasSize.width, edgeKey, layoutKey, nodeIdsKey]);

  useEffect(() => {
    const suggestedPositions = buildStructuredLayout(graph.candidate_nodes, graph.candidate_edges);
    setNodePositions((current) => {
      const next = syncNodePositions(current, graph.candidate_nodes, suggestedPositions);
      nodePositionsRef.current = next;
      return arePositionMapsEqual(current, next) ? current : next;
    });
  }, [edgeKey, nodeIdsKey]);

  const viewWidth = canvasSize.width / viewport.zoom;
  const viewHeight = canvasSize.height / viewport.zoom;
  const viewBoxX = viewport.centerX - viewWidth / 2;
  const viewBoxY = viewport.centerY - viewHeight / 2;

  function handleCanvasPointerDown(event: ReactPointerEvent<SVGSVGElement>) {
    if (event.button !== 1) return;
    event.preventDefault();
    svgRef.current?.setPointerCapture(event.pointerId);
    dragRef.current = {
      kind: "pan",
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      originCenterX: viewportRef.current.centerX,
      originCenterY: viewportRef.current.centerY
    };
    setIsPanning(true);
  }

  function handleCanvasPointerMove(event: ReactPointerEvent<SVGSVGElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    event.preventDefault();
    const worldDelta = screenDeltaToWorldDelta(event.clientX - drag.startClientX, event.clientY - drag.startClientY);

    if (drag.kind === "pan") {
      const nextViewport = {
        ...viewportRef.current,
        centerX: drag.originCenterX - worldDelta.x,
        centerY: drag.originCenterY - worldDelta.y
      };
      viewportRef.current = nextViewport;
      setViewport(nextViewport);
      return;
    }

    const nextPoint = {
      x: drag.originX + worldDelta.x,
      y: drag.originY + worldDelta.y
    };

    setNodePositions((current) => {
      const existing = current[drag.nodeId];
      if (existing && existing.x === nextPoint.x && existing.y === nextPoint.y) {
        return current;
      }
      const next = {
        ...current,
        [drag.nodeId]: nextPoint
      };
      nodePositionsRef.current = next;
      return next;
    });
  }

  function handleCanvasPointerUp(event: ReactPointerEvent<SVGSVGElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    if (svgRef.current?.hasPointerCapture(event.pointerId)) {
      svgRef.current.releasePointerCapture(event.pointerId);
    }
    dragRef.current = null;
    setIsPanning(false);
  }

  function handleNodePointerDown(nodeId: string, event: ReactPointerEvent<SVGGElement>) {
    if (event.button !== 0) return;
    event.stopPropagation();

    if (selection?.kind !== "node" || selection.id !== nodeId) {
      onSelect({ kind: "node", id: nodeId });
      return;
    }

    const point = nodePositionsRef.current[nodeId];
    if (!point) return;

    svgRef.current?.setPointerCapture(event.pointerId);
    dragRef.current = {
      kind: "node",
      pointerId: event.pointerId,
      nodeId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      originX: point.x,
      originY: point.y
    };
  }

  function handleBackgroundClick() {
    onSelect(null);
  }

  function handleCanvasWheel(event: React.WheelEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return;

    event.preventDefault();

    const rect = svg.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const currentViewport = viewportRef.current;
    const wheelDelta = normalizeWheelDelta(event.deltaY, event.deltaMode, rect.height);
    const zoomFactor = Math.exp(-wheelDelta * 0.0015);
    const nextZoom = clamp(currentViewport.zoom * zoomFactor, MIN_ZOOM, MAX_ZOOM);

    if (nextZoom === currentViewport.zoom) return;

    const pointerRatioX = clamp((event.clientX - rect.left) / rect.width, 0, 1);
    const pointerRatioY = clamp((event.clientY - rect.top) / rect.height, 0, 1);
    const currentViewWidth = canvasSizeRef.current.width / currentViewport.zoom;
    const currentViewHeight = canvasSizeRef.current.height / currentViewport.zoom;
    const currentViewLeft = currentViewport.centerX - currentViewWidth / 2;
    const currentViewTop = currentViewport.centerY - currentViewHeight / 2;
    const anchorX = currentViewLeft + pointerRatioX * currentViewWidth;
    const anchorY = currentViewTop + pointerRatioY * currentViewHeight;

    const nextViewWidth = canvasSizeRef.current.width / nextZoom;
    const nextViewHeight = canvasSizeRef.current.height / nextZoom;
    const nextViewport = {
      centerX: anchorX + (0.5 - pointerRatioX) * nextViewWidth,
      centerY: anchorY + (0.5 - pointerRatioY) * nextViewHeight,
      zoom: nextZoom
    };

    viewportRef.current = nextViewport;
    setViewport(nextViewport);
  }

  function screenDeltaToWorldDelta(deltaX: number, deltaY: number) {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return { x: 0, y: 0 };
    const currentViewWidth = canvasSizeRef.current.width / viewportRef.current.zoom;
    const currentViewHeight = canvasSizeRef.current.height / viewportRef.current.zoom;
    return {
      x: (deltaX / rect.width) * currentViewWidth,
      y: (deltaY / rect.height) * currentViewHeight
    };
  }

  return (
    <div className="graph-canvas-shell" ref={containerRef}>
      <svg
        ref={svgRef}
        className={isPanning ? "graph-canvas is-panning" : "graph-canvas"}
        viewBox={`${viewBoxX} ${viewBoxY} ${viewWidth} ${viewHeight}`}
        role="img"
        aria-label="Candidate knowledge graph"
        onPointerDown={handleCanvasPointerDown}
        onPointerMove={handleCanvasPointerMove}
        onPointerUp={handleCanvasPointerUp}
        onPointerCancel={handleCanvasPointerUp}
        onWheel={handleCanvasWheel}
        onAuxClick={(event) => {
          if (event.button === 1) {
            event.preventDefault();
          }
        }}
      >
        <defs>
          <pattern id="canvas-grid" width="48" height="48" patternUnits="userSpaceOnUse">
            <path d="M 48 0 L 0 0 0 48" className="canvas-grid-minor" />
          </pattern>
          <pattern id="canvas-grid-major" width="240" height="240" patternUnits="userSpaceOnUse">
            <rect width="240" height="240" fill="url(#canvas-grid)" />
            <path d="M 240 0 L 0 0 0 240" className="canvas-grid-major" />
          </pattern>
        </defs>

        <rect
          x={viewBoxX - viewWidth}
          y={viewBoxY - viewHeight}
          width={viewWidth * 3}
          height={viewHeight * 3}
          className="canvas-bg"
          fill="url(#canvas-grid-major)"
          onClick={handleBackgroundClick}
        />

        {graph.candidate_edges.map((edge) => {
          const source = nodePositions[edge.source];
          const target = nodePositions[edge.target];
          if (!source || !target) return null;
          const active = selection?.kind === "edge" && selection.id === edge.id;
          const labelPoint = getEdgeLabelPoint(source, target);
          return (
            <g
              key={edge.id}
              onClick={(event) => {
                event.stopPropagation();
                onSelect({ kind: "edge", id: edge.id });
              }}
              className="edge-hit"
            >
              <line
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                className="edge-hitline"
              />
              <line
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                className={active ? "edge active" : "edge"}
              />
              <text x={labelPoint.x} y={labelPoint.y} className="edge-label">
                {edge.type}
              </text>
            </g>
          );
        })}

        {graph.candidate_nodes.map((node) => {
          const point = nodePositions[node.id];
          if (!point) return null;
          const active = selection?.kind === "node" && selection.id === node.id;
          const draggable = active;
          const hitClassName = draggable ? "node-hit drag-enabled" : "node-hit";
          return (
            <g
              key={node.id}
              transform={`translate(${point.x}, ${point.y})`}
              onPointerDown={(event) => handleNodePointerDown(node.id, event)}
              className={hitClassName}
            >
              <circle r={NODE_RADIUS} className={active ? "node active" : "node"} />
              <text textAnchor="middle" y="-6" className="node-name">
                {truncate(node.name, 20)}
              </text>
              <text textAnchor="middle" y="14" className="node-id">
                {truncate(node.id, 22)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function NodeInspector({
  node,
  onChange
}: {
  node: KnowledgeNode;
  onChange: (patch: Partial<KnowledgeNode>) => void;
}) {
  return (
    <div className="inspector-form">
      <label>ID<input value={node.id} onChange={(event) => onChange({ id: event.target.value })} /></label>
      <label>Name<input value={node.name} onChange={(event) => onChange({ name: event.target.value })} /></label>
      <label>Type<input value={node.type} onChange={(event) => onChange({ type: event.target.value })} /></label>
      <label>Definition<textarea value={node.definition ?? ""} onChange={(event) => onChange({ definition: event.target.value })} /></label>
      <label>Diagnostic Goal<textarea value={node.diagnostic_goal ?? ""} onChange={(event) => onChange({ diagnostic_goal: event.target.value })} /></label>
      {LEVEL_KEYS.map((level) => (
        <label key={level}>{level}<textarea value={node.levels[level] ?? ""} onChange={(event) => onChange({ levels: { ...node.levels, [level]: event.target.value } })} /></label>
      ))}
      <label>
        Diagnostic Signals
        <textarea
          value={node.diagnostic_signals.join("\n")}
          onChange={(event) => onChange({ diagnostic_signals: lines(event.target.value) })}
        />
      </label>
      <label>
        Simulator Behavior
        <textarea value={node.simulator_behavior ?? ""} onChange={(event) => onChange({ simulator_behavior: event.target.value })} />
      </label>
    </div>
  );
}

function EdgeInspector({
  edge,
  nodeIds,
  onChange
}: {
  edge: KnowledgeEdge;
  nodeIds: string[];
  onChange: (patch: Partial<KnowledgeEdge>) => void;
}) {
  return (
    <div className="inspector-form">
      <label>ID<input value={edge.id} onChange={(event) => onChange({ id: event.target.value })} /></label>
      <label>
        Source
        <select value={edge.source} onChange={(event) => onChange({ source: event.target.value })}>
          {nodeIds.map((id) => <option key={id} value={id}>{id}</option>)}
        </select>
      </label>
      <label>
        Target
        <select value={edge.target} onChange={(event) => onChange({ target: event.target.value })}>
          {nodeIds.map((id) => <option key={id} value={id}>{id}</option>)}
        </select>
      </label>
      <label>
        Type
        <select value={edge.type} onChange={(event) => onChange({ type: event.target.value as KnowledgeEdge["type"] })}>
          <option value="part_of">part_of</option>
          <option value="prerequisite_for">prerequisite_for</option>
          <option value="supports">supports</option>
          <option value="contrasts_with">contrasts_with</option>
        </select>
      </label>
      <label>Rationale<textarea value={edge.rationale} onChange={(event) => onChange({ rationale: event.target.value })} /></label>
      <label>Weight<input type="number" min="0" max="1" step="0.05" value={edge.weight} onChange={(event) => onChange({ weight: Number(event.target.value) })} /></label>
      <label>Curation Confidence<input type="number" min="0" max="1" step="0.05" value={edge.curation_confidence} onChange={(event) => onChange({ curation_confidence: Number(event.target.value) })} /></label>
    </div>
  );
}

function buildStructuredLayout(nodes: KnowledgeNode[], edges: KnowledgeEdge[]) {
  const layers = assignNodeLayers(nodes, edges);
  const orderedLayerEntries = orderNodesWithinLayers(nodes, edges, layers);
  const basePositions: Record<string, Point> = {};
  const layerGap = 250;
  const rowGap = 128;
  const totalWidth = Math.max(0, (orderedLayerEntries.length - 1) * layerGap);

  orderedLayerEntries.forEach(([layer, ids]) => {
    const x = layer * layerGap - totalWidth / 2;
    const totalHeight = Math.max(0, (ids.length - 1) * rowGap);
    ids.forEach((id, index) => {
      basePositions[id] = {
        x,
        y: index * rowGap - totalHeight / 2
      };
    });
  });

  return relaxLayout(basePositions, nodes, edges, layers);
}

function assignNodeLayers(nodes: KnowledgeNode[], edges: KnowledgeEdge[]) {
  const nodeIds = nodes.map((node) => node.id);
  const layers = Object.fromEntries(nodeIds.map((id) => [id, 0])) as Record<string, number>;
  const indegree = Object.fromEntries(nodeIds.map((id) => [id, 0])) as Record<string, number>;
  const outgoing = new Map<string, string[]>();

  for (const edge of edges) {
    if (edge.type !== "prerequisite_for" && edge.type !== "part_of") {
      continue;
    }
    if (!outgoing.has(edge.source)) {
      outgoing.set(edge.source, []);
    }
    outgoing.get(edge.source)?.push(edge.target);
    if (edge.target in indegree) {
      indegree[edge.target] += 1;
    }
  }

  const queue = nodeIds.filter((id) => indegree[id] === 0).sort();
  const visited = new Set<string>();

  while (queue.length > 0) {
    const current = queue.shift()!;
    visited.add(current);
    for (const target of outgoing.get(current) ?? []) {
      layers[target] = Math.max(layers[target], layers[current] + 1);
      indegree[target] -= 1;
      if (indegree[target] === 0) {
        queue.push(target);
        queue.sort();
      }
    }
  }

  for (const id of nodeIds) {
    if (!visited.has(id)) {
      const fallbackSources = edges
        .filter((edge) => (edge.type === "prerequisite_for" || edge.type === "part_of") && edge.target === id)
        .map((edge) => layers[edge.source] ?? 0);
      layers[id] = fallbackSources.length > 0 ? Math.max(...fallbackSources) + 1 : 0;
    }
  }

  return layers;
}

function orderNodesWithinLayers(
  nodes: KnowledgeNode[],
  edges: KnowledgeEdge[],
  layers: Record<string, number>
) {
  const layerMap = new Map<number, string[]>();
  const degreeMap = new Map<string, number>();
  const neighborMap = new Map<string, string[]>();

  for (const node of nodes) {
    const layer = layers[node.id] ?? 0;
    if (!layerMap.has(layer)) {
      layerMap.set(layer, []);
    }
    layerMap.get(layer)?.push(node.id);
    degreeMap.set(node.id, 0);
    neighborMap.set(node.id, []);
  }

  for (const edge of edges) {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1);
    degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1);
    if (edge.type !== "contrasts_with") {
      neighborMap.get(edge.source)?.push(edge.target);
      neighborMap.get(edge.target)?.push(edge.source);
    }
  }

  for (const ids of layerMap.values()) {
    ids.sort((left, right) => {
      const degreeGap = (degreeMap.get(right) ?? 0) - (degreeMap.get(left) ?? 0);
      return degreeGap !== 0 ? degreeGap : left.localeCompare(right);
    });
  }

  const sortedLayers = Array.from(layerMap.keys()).sort((left, right) => left - right);

  for (let iteration = 0; iteration < 4; iteration += 1) {
    reorderLayers(sortedLayers, layerMap, neighborMap);
    reorderLayers([...sortedLayers].reverse(), layerMap, neighborMap);
  }

  return sortedLayers.map((layer) => [layer, layerMap.get(layer) ?? []] as const);
}

function reorderLayers(
  sortedLayers: number[],
  layerMap: Map<number, string[]>,
  neighborMap: Map<string, string[]>
) {
  const orderMap = new Map<string, number>();

  for (const layer of sortedLayers) {
    const ids = layerMap.get(layer) ?? [];
    ids.forEach((id, index) => orderMap.set(id, index));
  }

  for (const layer of sortedLayers) {
    const ids = [...(layerMap.get(layer) ?? [])];
    ids.sort((left, right) => {
      const leftAnchor = averageNeighborOrder(left, neighborMap, orderMap);
      const rightAnchor = averageNeighborOrder(right, neighborMap, orderMap);

      if (leftAnchor === rightAnchor) {
        return left.localeCompare(right);
      }
      if (leftAnchor === null) return 1;
      if (rightAnchor === null) return -1;
      return leftAnchor - rightAnchor;
    });
    layerMap.set(layer, ids);
  }
}

function averageNeighborOrder(
  nodeId: string,
  neighborMap: Map<string, string[]>,
  orderMap: Map<string, number>
) {
  const neighborOrders = (neighborMap.get(nodeId) ?? [])
    .map((id) => orderMap.get(id))
    .filter((value): value is number => typeof value === "number");
  if (neighborOrders.length === 0) {
    return null;
  }
  return neighborOrders.reduce((sum, value) => sum + value, 0) / neighborOrders.length;
}

function relaxLayout(
  basePositions: Record<string, Point>,
  nodes: KnowledgeNode[],
  edges: KnowledgeEdge[],
  layers: Record<string, number>
) {
  const positions = Object.fromEntries(
    Object.entries(basePositions).map(([id, point]) => [id, { ...point }])
  ) as Record<string, Point>;
  const velocities = Object.fromEntries(
    nodes.map((node) => [node.id, { x: 0, y: 0 }])
  ) as Record<string, Point>;
  const layerGroups = new Map<number, string[]>();

  for (const node of nodes) {
    const layer = layers[node.id] ?? 0;
    if (!layerGroups.has(layer)) {
      layerGroups.set(layer, []);
    }
    layerGroups.get(layer)?.push(node.id);
  }

  const repulsionStrength = 28000 + nodes.length * 900;

  for (let iteration = 0; iteration < 180; iteration += 1) {
    const forces = Object.fromEntries(
      nodes.map((node) => [node.id, { x: 0, y: 0 }])
    ) as Record<string, Point>;

    for (let index = 0; index < nodes.length; index += 1) {
      for (let nextIndex = index + 1; nextIndex < nodes.length; nextIndex += 1) {
        const leftId = nodes[index].id;
        const rightId = nodes[nextIndex].id;
        const dx = positions[leftId].x - positions[rightId].x;
        const dy = positions[leftId].y - positions[rightId].y;
        const distanceSquared = Math.max(dx * dx + dy * dy, 6000);
        const distance = Math.sqrt(distanceSquared);
        const force = repulsionStrength / distanceSquared;
        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;
        forces[leftId].x += fx;
        forces[leftId].y += fy;
        forces[rightId].x -= fx;
        forces[rightId].y -= fy;
      }
    }

    for (const edge of edges) {
      const source = positions[edge.source];
      const target = positions[edge.target];
      if (!source || !target) continue;
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
      const desiredDistance = edge.type === "part_of"
        ? 180
        : edge.type === "prerequisite_for"
          ? 220
          : edge.type === "supports"
            ? 210
            : 170;
      const springStrength = edge.type === "supports" ? 0.016 : 0.026;
      const stretch = (distance - desiredDistance) * springStrength;
      const fx = (dx / distance) * stretch;
      const fy = (dy / distance) * stretch;
      forces[edge.source].x += fx;
      forces[edge.source].y += fy;
      forces[edge.target].x -= fx;
      forces[edge.target].y -= fy;
    }

    for (const [layer, ids] of layerGroups.entries()) {
      const sortedIds = [...ids].sort((left, right) => positions[left].y - positions[right].y);
      for (let index = 0; index < sortedIds.length - 1; index += 1) {
        const currentId = sortedIds[index];
        const nextId = sortedIds[index + 1];
        const gap = positions[nextId].y - positions[currentId].y;
        const minimumGap = 112;
        if (gap >= minimumGap) continue;
        const push = (minimumGap - gap) * 0.05;
        forces[currentId].y -= push;
        forces[nextId].y += push;
      }

      for (const nodeId of ids) {
        forces[nodeId].x += (basePositions[nodeId].x - positions[nodeId].x) * 0.085;
        forces[nodeId].y += (basePositions[nodeId].y - positions[nodeId].y) * (layer === 0 ? 0.032 : 0.042);
      }
    }

    for (const node of nodes) {
      const velocity = velocities[node.id];
      velocity.x = velocity.x * 0.74 + forces[node.id].x;
      velocity.y = velocity.y * 0.74 + forces[node.id].y;
      positions[node.id] = {
        x: positions[node.id].x + velocity.x,
        y: positions[node.id].y + velocity.y
      };
    }
  }

  return positions;
}

function fitViewport(positions: Record<string, Point>, canvasSize: CanvasSize): ViewportState {
  const points = Object.values(positions);
  if (points.length === 0) {
    return { centerX: 0, centerY: 0, zoom: 1 };
  }

  const bounds = calculateBounds(positions);
  const padding = 180;
  const boundedWidth = Math.max(bounds.maxX - bounds.minX + padding * 2, 320);
  const boundedHeight = Math.max(bounds.maxY - bounds.minY + padding * 2, 320);
  const zoom = clamp(
    Math.min(canvasSize.width / boundedWidth, canvasSize.height / boundedHeight),
    0.42,
    1.15
  );

  return {
    centerX: (bounds.minX + bounds.maxX) / 2,
    centerY: (bounds.minY + bounds.maxY) / 2,
    zoom
  };
}

function calculateBounds(positions: Record<string, Point>) {
  const points = Object.values(positions);
  if (points.length === 0) {
    return { minX: 0, maxX: 0, minY: 0, maxY: 0 };
  }

  return points.reduce(
    (bounds, point) => ({
      minX: Math.min(bounds.minX, point.x - NODE_RADIUS),
      maxX: Math.max(bounds.maxX, point.x + NODE_RADIUS),
      minY: Math.min(bounds.minY, point.y - NODE_RADIUS),
      maxY: Math.max(bounds.maxY, point.y + NODE_RADIUS)
    }),
    {
      minX: Number.POSITIVE_INFINITY,
      maxX: Number.NEGATIVE_INFINITY,
      minY: Number.POSITIVE_INFINITY,
      maxY: Number.NEGATIVE_INFINITY
    }
  );
}

function syncNodePositions(
  current: Record<string, Point>,
  nodes: KnowledgeNode[],
  suggested: Record<string, Point>
) {
  const next: Record<string, Point> = {};

  for (const node of nodes) {
    next[node.id] = current[node.id] ?? suggested[node.id] ?? { x: 0, y: 0 };
  }

  return next;
}

function arePositionMapsEqual(left: Record<string, Point>, right: Record<string, Point>) {
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  if (leftKeys.length !== rightKeys.length) return false;

  for (const key of leftKeys) {
    if (!(key in right)) return false;
    if (left[key].x !== right[key].x || left[key].y !== right[key].y) {
      return false;
    }
  }

  return true;
}

function getEdgeLabelPoint(source: Point, target: Point) {
  const midpointX = (source.x + target.x) / 2;
  const midpointY = (source.y + target.y) / 2;
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const length = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
  const normalX = -dy / length;
  const normalY = dx / length;
  return {
    x: midpointX + normalX * 12,
    y: midpointY + normalY * 12
  };
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
}

function normalizeWheelDelta(deltaY: number, deltaMode: number, pageHeight: number) {
  if (deltaMode === 1) {
    return deltaY * 16;
  }
  if (deltaMode === 2) {
    return deltaY * pageHeight;
  }
  return deltaY;
}

function nextId(prefix: string, existingIds: string[]) {
  const existing = new Set(existingIds);
  let index = 1;
  while (existing.has(`${prefix}_${index}`)) {
    index += 1;
  }
  return `${prefix}_${index}`;
}

function lines(value: string) {
  return value.split("\n").map((line) => line.trim()).filter(Boolean);
}

function truncate(value: string, maxLength: number) {
  return value.length <= maxLength ? value : `${value.slice(0, maxLength - 1)}...`;
}
