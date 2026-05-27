import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  CandidateGraphPayload,
  KnowledgeEdge,
  KnowledgeNode,
  SourceMaterialRecord,
  generateCandidateGraph,
  listSourceMaterials,
  readCandidateGraph,
  saveCandidateGraph,
  uploadSourceMaterial
} from "../../api/authoring";

type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | null;

const DEFAULT_DOMAIN = "classical_supervised_ml_algorithms";
const LEVEL_KEYS = ["L0", "L1", "L2", "L3", "L4", "L5"];

export function CandidateGraphWorkbench() {
  const [materials, setMaterials] = useState<SourceMaterialRecord[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [benchmarkDomain, setBenchmarkDomain] = useState(DEFAULT_DOMAIN);
  const [runId, setRunId] = useState("");
  const [clientProvider, setClientProvider] = useState<"openai" | "deepseek">("openai");
  const [graph, setGraph] = useState<CandidateGraphPayload | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
              <input value={runId} onChange={(event) => setRunId(event.target.value)} placeholder="Optional" />
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
              <button type="button" onClick={addNode} disabled={!graph}>Add Node</button>
              <button type="button" onClick={addEdge} disabled={!graph || graph.candidate_nodes.length < 2}>Add Edge</button>
              <button type="button" onClick={deleteSelection} disabled={!selection}>Delete</button>
              <button type="button" onClick={handleSave} disabled={!graph || busy !== null}>Save</button>
            </div>
          </div>
          {graph ? (
            <GraphCanvas graph={graph} selection={selection} onSelect={setSelection} />
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
  onSelect
}: {
  graph: CandidateGraphPayload;
  selection: Selection;
  onSelect: (selection: Selection) => void;
}) {
  const layout = useMemo(() => circularLayout(graph.candidate_nodes), [graph.candidate_nodes]);
  return (
    <svg className="graph-canvas" viewBox="0 0 900 620" role="img" aria-label="Candidate knowledge graph">
      <rect x="0" y="0" width="900" height="620" rx="0" className="canvas-bg" />
      {graph.candidate_edges.map((edge) => {
        const source = layout.get(edge.source);
        const target = layout.get(edge.target);
        if (!source || !target) return null;
        const active = selection?.kind === "edge" && selection.id === edge.id;
        return (
          <g key={edge.id} onClick={() => onSelect({ kind: "edge", id: edge.id })} className="edge-hit">
            <line
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              className={active ? "edge active" : "edge"}
            />
            <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 6} className="edge-label">
              {edge.type}
            </text>
          </g>
        );
      })}
      {graph.candidate_nodes.map((node) => {
        const point = layout.get(node.id);
        if (!point) return null;
        const active = selection?.kind === "node" && selection.id === node.id;
        return (
          <g key={node.id} transform={`translate(${point.x}, ${point.y})`} onClick={() => onSelect({ kind: "node", id: node.id })} className="node-hit">
            <circle r="36" className={active ? "node active" : "node"} />
            <text textAnchor="middle" y="-4" className="node-name">
              {truncate(node.name, 18)}
            </text>
            <text textAnchor="middle" y="14" className="node-id">
              {truncate(node.id, 20)}
            </text>
          </g>
        );
      })}
    </svg>
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

function circularLayout(nodes: KnowledgeNode[]) {
  const map = new Map<string, { x: number; y: number }>();
  const centerX = 450;
  const centerY = 310;
  const radius = Math.min(240, Math.max(120, nodes.length * 16));
  nodes.forEach((node, index) => {
    const angle = nodes.length === 1 ? -Math.PI / 2 : (index / nodes.length) * Math.PI * 2 - Math.PI / 2;
    map.set(node.id, {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius
    });
  });
  return map;
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
