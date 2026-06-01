import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ApiRequestError,
  CandidateGraphPayload,
  CandidateGraphPromotionResponse,
  CandidateGraphRunSummary,
  KnowledgeEdge,
  KnowledgeNode,
  SourceMaterialRecord,
  generateCandidateGraph,
  listCandidateGraphRuns,
  listSourceMaterials,
  promoteCandidateGraph,
  readCandidateGraph,
  saveCandidateGraph,
  uploadSourceMaterial
} from "../../api/authoring";
import { CandidateGraphCanvas } from "./CandidateGraphCanvas";
import {
  LEVEL_KEYS,
  addCandidateEdgeFromSelection,
  addCandidateNodeAtPosition,
  deleteCandidateGraphSelection,
  type NodePosition,
  type NodePositionMap,
  type Selection
} from "./CandidateGraphWorkbenchModel";

const DEFAULT_DOMAIN = "classical_supervised_ml_algorithms";

export function CandidateGraphWorkbench() {
  const [materials, setMaterials] = useState<SourceMaterialRecord[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [benchmarkDomain, setBenchmarkDomain] = useState(DEFAULT_DOMAIN);
  const [runId, setRunId] = useState("");
  const [runs, setRuns] = useState<CandidateGraphRunSummary[]>([]);
  const [clientProvider, setClientProvider] = useState<"openai" | "deepseek">("openai");
  const [graph, setGraph] = useState<CandidateGraphPayload | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [nodePositions, setNodePositions] = useState<NodePositionMap>({});
  const [viewportCenter, setViewportCenter] = useState<NodePosition>({ x: 0, y: 0 });
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [layoutVersion, setLayoutVersion] = useState(0);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [graphVersion, setGraphVersion] = useState("");

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
      setNodePositions({});
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
      setNodePositions({});
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

  function openConfirmDialog() {
    if (!graph) return;
    setError(null);
    setGraphVersion("");
    setConfirmDialogOpen(true);
  }

  async function handleConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!graph) return;
    const version = graphVersion.trim();
    if (!version) {
      setError("Graph version is required.");
      return;
    }
    await runTask("confirm", async () => {
      const saved = await saveCandidateGraph(graph);
      setGraph(saved);
      let promotion: CandidateGraphPromotionResponse;
      try {
        promotion = await promoteCandidateGraph(saved, version);
      } catch (taskError) {
        if (!(taskError instanceof ApiRequestError) || taskError.status !== 409) {
          throw taskError;
        }
        const overwrite = window.confirm(`Version "${version}" already exists. Overwrite it?`);
        if (!overwrite) {
          setConfirmDialogOpen(false);
          setGraphVersion("");
          setNotice(`Promotion of ${version} cancelled. Candidate graph saved.`);
          return;
        }
        promotion = await promoteCandidateGraph(saved, version, true);
      }
      setConfirmDialogOpen(false);
      setGraphVersion("");
      setNotice(`Published to ${promotion.artifact_paths.output_dir_uri}`);
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
      const newId = patch.id;
      setNodePositions((positions) => {
        const existing = positions[id];
        if (!existing || newId === id) return positions;
        const { [id]: _removedPosition, ...remainingPositions } = positions;
        return { ...remainingPositions, [newId]: existing };
      });
      setSelection({ kind: "node", id: newId });
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
    const edit = addCandidateNodeAtPosition(graph, viewportCenter);
    setGraph(edit.graph);
    setSelection(edit.selection);
    setNodePositions((positions) => ({ ...positions, ...edit.nodePositions }));
  }

  function addEdge() {
    if (!graph || graph.candidate_nodes.length < 2) return;
    const edit = addCandidateEdgeFromSelection(graph, selection);
    setGraph(edit.graph);
    setSelection(edit.selection);
  }

  function deleteSelection() {
    if (!graph || !selection) return;
    const edit = deleteCandidateGraphSelection(graph, selection, nodePositions);
    setGraph(edit.graph);
    setSelection(edit.selection);
    setNodePositions(edit.nodePositions);
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
              <button type="button" onClick={openConfirmDialog} disabled={!graph || busy !== null}>Confirm</button>
            </div>
          </div>
          {graph ? (
            <CandidateGraphCanvas
              graph={graph}
              selection={selection}
              onSelect={setSelection}
              nodePositionOverrides={nodePositions}
              onViewportCenterChange={setViewportCenter}
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
      {confirmDialogOpen && graph && (
        <div className="dialog-backdrop">
          <form className="dialog" onSubmit={handleConfirm}>
            <h2>Confirm Reviewed Graph</h2>
            <p>Save the current candidate edits and publish them as a reviewed graph version.</p>
            <label>
              Graph Version
              <input
                autoFocus
                value={graphVersion}
                onChange={(event) => setGraphVersion(event.target.value)}
                placeholder="v1"
                pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,127}"
                required
              />
            </label>
            <div className="button-row dialog-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setConfirmDialogOpen(false)}
                disabled={busy !== null}
              >
                Cancel
              </button>
              <button type="submit" disabled={busy !== null}>Confirm</button>
            </div>
          </form>
        </div>
      )}
    </main>
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

function lines(value: string) {
  return value.split("\n").map((line) => line.trim()).filter(Boolean);
}
