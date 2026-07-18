import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ApiRequestError,
  CandidateGraphPayload,
  CandidateGraphPromotionResponse,
  KnowledgeEdge,
  KnowledgeNode,
  ReviewedGraphVersionSummary,
  SourceMaterialRecord,
  generateCandidateGraph,
  listBenchmarkDomains,
  listReviewedGraphs,
  listSourceMaterials,
  promoteCandidateGraph,
  readReviewedGraph,
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

export function CandidateGraphWorkbench() {
  const [materials, setMaterials] = useState<SourceMaterialRecord[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [benchmarkDomain, setBenchmarkDomain] = useState("");
  const [runId, setRunId] = useState("");
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
  const [reviewedDomains, setReviewedDomains] = useState<string[]>([]);
  const [reviewedDomain, setReviewedDomain] = useState("");
  const [reviewedVersions, setReviewedVersions] = useState<ReviewedGraphVersionSummary[]>([]);
  const [reviewedVersion, setReviewedVersion] = useState("");
  const [graphMode, setGraphMode] = useState<"candidate" | "reviewed">("candidate");

  useEffect(() => {
    void initializeWorkbench();
  }, []);

  const isReviewedGraph = graphMode === "reviewed";

  const selectedNode = useMemo(() => {
    if (!graph || selection?.kind !== "node") return null;
    return graph.candidate_nodes.find((node) => node.id === selection.id) ?? null;
  }, [graph, selection]);

  const selectedEdge = useMemo(() => {
    if (!graph || selection?.kind !== "edge") return null;
    return graph.candidate_edges.find((edge) => edge.id === selection.id) ?? null;
  }, [graph, selection]);

  async function initializeWorkbench() {
    await runTask("workspace", async () => {
      const [nextMaterials, nextDomains] = await Promise.all([
        listSourceMaterials(),
        listBenchmarkDomains()
      ]);
      setMaterials(nextMaterials);
      if (nextMaterials.length > 0) {
        setSelectedSourceId(nextMaterials[0].source_id);
      }
      setReviewedDomains(nextDomains);
      const initialDomain = nextDomains[0] ?? "";
      setReviewedDomain(initialDomain);
      if (initialDomain) {
        const versions = await listReviewedGraphs(initialDomain);
        setReviewedVersions(versions);
        setReviewedVersion(versions[0]?.version ?? "");
      }
    });
  }

  async function refreshMaterials() {
    await runTask("materials", async () => {
      const nextMaterials = await listSourceMaterials();
      setMaterials(nextMaterials);
      if (!selectedSourceId && nextMaterials.length > 0) {
        setSelectedSourceId(nextMaterials[0].source_id);
      }
    });
  }

  async function handleReviewedDomainChange(domain: string) {
    setReviewedDomain(domain);
    setReviewedVersions([]);
    setReviewedVersion("");
    if (!domain) return;
    await runTask("reviewed graphs", async () => {
      const versions = await listReviewedGraphs(domain);
      setReviewedVersions(versions);
      setReviewedVersion(versions[0]?.version ?? "");
    });
  }

  async function handleLoadReviewedGraph() {
    if (!reviewedDomain || !reviewedVersion) return;
    await runTask("reviewed graph", async () => {
      const reviewedGraph = await readReviewedGraph(reviewedDomain, reviewedVersion);
      const nextGraph: CandidateGraphPayload = {
        benchmark_domain: reviewedGraph.benchmark_domain,
        run_id: `reviewed:${reviewedGraph.graph_manifest.version}`,
        candidate_nodes: reviewedGraph.authored_nodes,
        candidate_edges: reviewedGraph.authored_edges,
        artifact_paths: {
          output_dir_uri: reviewedGraph.artifact_paths.output_dir_uri,
          candidate_nodes_uri: reviewedGraph.artifact_paths.authored_nodes_uri,
          candidate_edges_uri: reviewedGraph.artifact_paths.authored_edges_uri,
          workflow_log_uri: reviewedGraph.artifact_paths.graph_manifest_uri
        }
      };
      setGraph(nextGraph);
      setGraphMode("reviewed");
      setConfirmDialogOpen(false);
      setNodePositions({});
      setSelection(nextGraph.candidate_nodes[0] ? { kind: "node", id: nextGraph.candidate_nodes[0].id } : null);
      setLayoutVersion((version) => version + 1);
      setNotice(`Loaded reviewed graph ${reviewedGraph.graph_manifest.version}.`);
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
    if (!benchmarkDomain.trim()) {
      setError("Enter a benchmark domain first.");
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
      setGraphMode("candidate");
      setNodePositions({});
      setRunId(nextGraph.run_id);
      setSelection(nextGraph.candidate_nodes[0] ? { kind: "node", id: nextGraph.candidate_nodes[0].id } : null);
      setLayoutVersion((version) => version + 1);
      setNotice(`Generated ${nextGraph.candidate_nodes.length} nodes and ${nextGraph.candidate_edges.length} edges.`);
    });
  }

  async function handleSave() {
    if (!graph || isReviewedGraph) return;
    await runTask("save", async () => {
      const saved = await saveCandidateGraph(graph);
      setGraph(saved);
      setNotice("Candidate graph saved.");
    });
  }

  function openConfirmDialog() {
    if (!graph || isReviewedGraph) return;
    setError(null);
    setGraphVersion("");
    setConfirmDialogOpen(true);
  }

  async function handleConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!graph || isReviewedGraph) return;
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
        throw new Error(
          `Version "${version}" already exists and cannot be overwritten. Enter a new graph version. Candidate graph saved.`
        );
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
    if (!graph || isReviewedGraph) return;
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
    if (!graph || isReviewedGraph) return;
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
    if (!graph || isReviewedGraph) return;
    const edit = addCandidateNodeAtPosition(graph, viewportCenter);
    setGraph(edit.graph);
    setSelection(edit.selection);
    setNodePositions((positions) => ({ ...positions, ...edit.nodePositions }));
  }

  function addEdge() {
    if (!graph || isReviewedGraph || graph.candidate_nodes.length < 2) return;
    const edit = addCandidateEdgeFromSelection(graph, selection);
    setGraph(edit.graph);
    setSelection(edit.selection);
  }

  function deleteSelection() {
    if (!graph || isReviewedGraph || !selection) return;
    const edit = deleteCandidateGraphSelection(graph, selection, nodePositions);
    setGraph(edit.graph);
    setSelection(edit.selection);
    setNodePositions(edit.nodePositions);
  }

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <h1>Knowledge Graph Workbench</h1>
          <p>Generate and review candidate graphs, or load a reviewed graph for read-only preview.</p>
        </div>
        <div className="status-strip" aria-live="polite">
          {busy && <span className="status busy">Working: {busy}</span>}
          {notice && <span className="status ok">{notice}</span>}
          {error && <span className="status error">{error}</span>}
        </div>
      </section>

      <section className="workspace">
        <aside className="left-panel">
          <div className="panel-block">
            <h2>Load Reviewed Graph</h2>
            <label>
              Domain
              <select
                value={reviewedDomain}
                onChange={(event) => void handleReviewedDomainChange(event.target.value)}
              >
                <option value="">Select domain</option>
                {reviewedDomains.map((domain) => (
                  <option key={domain} value={domain}>{domain}</option>
                ))}
              </select>
            </label>
            <label>
              Version
              <select value={reviewedVersion} onChange={(event) => setReviewedVersion(event.target.value)}>
                <option value="">Select version</option>
                {reviewedVersions.map((version) => (
                  <option key={version.version} value={version.version}>
                    {version.version}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={handleLoadReviewedGraph}
              disabled={busy !== null || !reviewedDomain || !reviewedVersion}
            >
              Load Reviewed Graph
            </button>
          </div>

          <form className="panel-block" onSubmit={handleUpload}>
            <h2>Source Material</h2>
            <label>
              PDF
              <input name="file" type="file" accept="application/pdf,.pdf" />
            </label>
            <label>
              Source ID
              <input name="source_id" placeholder="Enter a stable identifier for this source" required />
            </label>
            <label>
              Title
              <input name="title" placeholder="Enter the source material title" required />
            </label>
            <label>
              Citation
              <input name="citation" placeholder="Enter citation details (optional)" />
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
              <input
                value={benchmarkDomain}
                onChange={(event) => setBenchmarkDomain(event.target.value)}
                placeholder="Enter the domain identifier for this benchmark"
                required
              />
            </label>
            <label>
              Run ID
              <input
                value={runId}
                onChange={(event) => setRunId(event.target.value)}
                placeholder="Optional; generated automatically when empty"
                disabled={busy !== null}
              />
            </label>
            <label>
              Provider
              <select value={clientProvider} onChange={(event) => setClientProvider(event.target.value as "openai" | "deepseek")}>
                <option value="openai">openai</option>
                <option value="deepseek">deepseek</option>
              </select>
            </label>
            <button type="submit" disabled={busy !== null || !selectedSourceId || !benchmarkDomain.trim()}>Generate</button>
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
              <h2>
                {graph
                  ? isReviewedGraph
                    ? `${graph.benchmark_domain} · ${graph.run_id.replace("reviewed:", "")}`
                    : graph.run_id
                  : "No knowledge graph loaded"}
              </h2>
              {graph && <p>{graph.candidate_nodes.length} nodes / {graph.candidate_edges.length} edges</p>}
              {graph && isReviewedGraph && <p className="reviewed-graph-notice">Reviewed snapshot · read-only</p>}
            </div>
            <div className="button-row">
              <button type="button" onClick={() => setLayoutVersion((version) => version + 1)} disabled={!graph}>
                Reflow
              </button>
              <button type="button" onClick={addNode} disabled={!graph || isReviewedGraph}>Add Node</button>
              <button type="button" onClick={addEdge} disabled={!graph || isReviewedGraph || graph.candidate_nodes.length < 2}>Add Edge</button>
              <button type="button" onClick={deleteSelection} disabled={!selection || isReviewedGraph}>Delete</button>
              <button type="button" onClick={handleSave} disabled={!graph || isReviewedGraph || busy !== null}>Save</button>
              <button type="button" onClick={openConfirmDialog} disabled={!graph || isReviewedGraph || busy !== null}>Confirm</button>
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
              ariaLabel={isReviewedGraph ? "Reviewed knowledge graph preview" : undefined}
            />
          ) : (
            <div className="empty-graph">Generate a candidate graph or load a reviewed graph.</div>
          )}
        </section>

        <aside className="right-panel">
          <h2>Inspector</h2>
          {selectedNode && (
            <NodeInspector
              node={selectedNode}
              readOnly={isReviewedGraph}
              onChange={(patch) => updateNode(selectedNode.id, patch)}
            />
          )}
          {selectedEdge && graph && (
            <EdgeInspector
              edge={selectedEdge}
              nodeIds={graph.candidate_nodes.map((node) => node.id)}
              readOnly={isReviewedGraph}
              onChange={(patch) => updateEdge(selectedEdge.id, patch)}
            />
          )}
          {!selectedNode && !selectedEdge && <p className="empty">Select a node or edge.</p>}
        </aside>
      </section>
      {confirmDialogOpen && graph && !isReviewedGraph && (
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
                placeholder="Enter a unique graph version identifier"
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
  readOnly,
  onChange
}: {
  node: KnowledgeNode;
  readOnly: boolean;
  onChange: (patch: Partial<KnowledgeNode>) => void;
}) {
  return (
    <div className="inspector-form">
      <label>ID<input readOnly={readOnly} value={node.id} onChange={(event) => onChange({ id: event.target.value })} /></label>
      <label>Name<input readOnly={readOnly} value={node.name} onChange={(event) => onChange({ name: event.target.value })} /></label>
      <label>Type<input readOnly={readOnly} value={node.type} onChange={(event) => onChange({ type: event.target.value })} /></label>
      <label>Definition<textarea readOnly={readOnly} value={node.definition ?? ""} onChange={(event) => onChange({ definition: event.target.value })} /></label>
      <label>Diagnostic Goal<textarea readOnly={readOnly} value={node.diagnostic_goal ?? ""} onChange={(event) => onChange({ diagnostic_goal: event.target.value })} /></label>
      {LEVEL_KEYS.map((level) => (
        <label key={level}>{level}<textarea readOnly={readOnly} value={node.levels[level] ?? ""} onChange={(event) => onChange({ levels: { ...node.levels, [level]: event.target.value } })} /></label>
      ))}
      <label>
        Diagnostic Signals
        <textarea
          readOnly={readOnly}
          value={node.diagnostic_signals.join("\n")}
          onChange={(event) => onChange({ diagnostic_signals: lines(event.target.value) })}
        />
      </label>
      <label>
        Simulator Behavior
        <textarea readOnly={readOnly} value={node.simulator_behavior ?? ""} onChange={(event) => onChange({ simulator_behavior: event.target.value })} />
      </label>
    </div>
  );
}

function EdgeInspector({
  edge,
  nodeIds,
  readOnly,
  onChange
}: {
  edge: KnowledgeEdge;
  nodeIds: string[];
  readOnly: boolean;
  onChange: (patch: Partial<KnowledgeEdge>) => void;
}) {
  return (
    <div className="inspector-form">
      <label>ID<input readOnly={readOnly} value={edge.id} onChange={(event) => onChange({ id: event.target.value })} /></label>
      <label>
        Source
        <select disabled={readOnly} value={edge.source} onChange={(event) => onChange({ source: event.target.value })}>
          {nodeIds.map((id) => <option key={id} value={id}>{id}</option>)}
        </select>
      </label>
      <label>
        Target
        <select disabled={readOnly} value={edge.target} onChange={(event) => onChange({ target: event.target.value })}>
          {nodeIds.map((id) => <option key={id} value={id}>{id}</option>)}
        </select>
      </label>
      <label>
        Type
        <select disabled={readOnly} value={edge.type} onChange={(event) => onChange({ type: event.target.value as KnowledgeEdge["type"] })}>
          <option value="part_of">part_of</option>
          <option value="prerequisite_for">prerequisite_for</option>
          <option value="supports">supports</option>
          <option value="contrasts_with">contrasts_with</option>
        </select>
      </label>
      <label>Rationale<textarea readOnly={readOnly} value={edge.rationale} onChange={(event) => onChange({ rationale: event.target.value })} /></label>
      <label>Weight<input readOnly={readOnly} type="number" min="0" max="1" step="0.05" value={edge.weight} onChange={(event) => onChange({ weight: Number(event.target.value) })} /></label>
      <label>Curation Confidence<input readOnly={readOnly} type="number" min="0" max="1" step="0.05" value={edge.curation_confidence} onChange={(event) => onChange({ curation_confidence: Number(event.target.value) })} /></label>
    </div>
  );
}

function lines(value: string) {
  return value.split("\n").map((line) => line.trim()).filter(Boolean);
}
