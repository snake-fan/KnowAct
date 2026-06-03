import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  ApiRequestError,
  CandidateMapResponse,
  CandidateMapRunSummary,
  ConfirmedProfileContext,
  ConfirmedProfileContextSummary,
  EvidenceRecord,
  KnowledgeMap,
  KnowledgeNode,
  MapEdgeConsistencyWarning,
  ReviewedGraphPayload,
  ReviewedGraphVersionSummary,
  generateCandidateMap,
  listBenchmarkDomains,
  listCandidateMapRuns,
  listConfirmedProfileContexts,
  listReviewedGraphs,
  promoteCandidateMap,
  readCandidateMap,
  readCandidateMapWarnings,
  readConfirmedProfileContext,
  readReviewedGraph
} from "../../api/authoring";
import { MapReviewCanvas } from "./MapReviewCanvas";

type ClientProvider = "openai" | "deepseek";

type ReviewContext = {
  benchmarkDomain: string;
  graphVersion: string;
  userId: string;
  candidate: CandidateMapResponse;
  graph: ReviewedGraphPayload;
  profile: ConfirmedProfileContext;
  warnings: MapEdgeConsistencyWarning[];
};

export function MapAuthoringWorkbench() {
  const [benchmarkDomains, setBenchmarkDomains] = useState<string[]>([]);
  const [benchmarkDomain, setBenchmarkDomain] = useState("");
  const [graphs, setGraphs] = useState<ReviewedGraphVersionSummary[]>([]);
  const [graphVersion, setGraphVersion] = useState("");
  const [users, setUsers] = useState<ConfirmedProfileContextSummary[]>([]);
  const [userId, setUserId] = useState("");
  const [profile, setProfile] = useState<ConfirmedProfileContext | null>(null);
  const [graph, setGraph] = useState<ReviewedGraphPayload | null>(null);
  const [candidateRuns, setCandidateRuns] = useState<CandidateMapRunSummary[]>([]);
  const [clientProvider, setClientProvider] = useState<ClientProvider>("openai");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [runId, setRunId] = useState("");
  const [evidenceBatchSize, setEvidenceBatchSize] = useState(5);
  const [samplingTemperature, setSamplingTemperature] = useState(0.7);
  const [reviewContext, setReviewContext] = useState<ReviewContext | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [promotionDialogOpen, setPromotionDialogOpen] = useState(false);
  const [mapId, setMapId] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const composerStageRef = useRef<HTMLElement | null>(null);
  const reviewStageRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    void refreshBenchmarkDomains();
  }, []);

  useEffect(() => {
    if (!benchmarkDomain) return;
    void refreshDomainAssets(benchmarkDomain);
  }, [benchmarkDomain]);

  useEffect(() => {
    if (!benchmarkDomain || !graphVersion) {
      setGraph(null);
      return;
    }
    void loadGraph(benchmarkDomain, graphVersion);
  }, [benchmarkDomain, graphVersion]);

  useEffect(() => {
    if (!benchmarkDomain || !userId) {
      setProfile(null);
      return;
    }
    void loadProfile(benchmarkDomain, userId);
  }, [benchmarkDomain, userId]);

  const selectedNode = useMemo(() => {
    if (!reviewContext || !selectedNodeId) return null;
    return reviewContext.graph.authored_nodes.find((node) => node.id === selectedNodeId) ?? null;
  }, [reviewContext, selectedNodeId]);

  const selectedState = useMemo(() => {
    if (!reviewContext || !selectedNodeId) return null;
    return reviewContext.candidate.candidate_map.states.find((state) => state.node_id === selectedNodeId) ?? null;
  }, [reviewContext, selectedNodeId]);

  const selectedEvidence = useMemo(() => {
    if (!selectedState || !reviewContext) return [];
    const evidenceById = new Map(reviewContext.candidate.candidate_map.evidence.map((record) => [record.id, record]));
    return selectedState.evidence_refs.map((evidenceRef) => ({
      evidenceRef,
      record: evidenceById.get(evidenceRef) ?? null
    }));
  }, [reviewContext, selectedState]);

  const selectedWarnings = useMemo(() => {
    if (!selectedNodeId || !reviewContext) return [];
    return reviewContext.warnings.filter(
      (warning) =>
        warning.source_node_id === selectedNodeId ||
        warning.target_node_id === selectedNodeId
    );
  }, [reviewContext, selectedNodeId]);

  async function refreshBenchmarkDomains() {
    await runTask("domains", async () => {
      const domains = await listBenchmarkDomains();
      setBenchmarkDomains(domains);
      setBenchmarkDomain((current) => current || domains[0] || "");
    });
  }

  async function refreshDomainAssets(domain: string) {
    await runTask("domain assets", async () => {
      const [nextGraphs, nextUsers, nextRuns] = await Promise.all([
        listReviewedGraphs(domain),
        listConfirmedProfileContexts(domain),
        listCandidateMapRuns(domain)
      ]);
      setGraphs(nextGraphs);
      setUsers(nextUsers);
      setCandidateRuns(nextRuns);
      setGraphVersion((current) =>
        nextGraphs.some((candidate) => candidate.version === current)
          ? current
          : nextGraphs[0]?.version ?? ""
      );
      setUserId((current) =>
        nextUsers.some((candidate) => candidate.user_id === current)
          ? current
          : nextUsers[0]?.user_id ?? ""
      );
    });
  }

  async function loadGraph(domain: string, version: string) {
    await runTask("graph", async () => {
      setGraph(await readReviewedGraph(domain, version));
    });
  }

  async function loadProfile(domain: string, selectedUserId: string) {
    await runTask("profile", async () => {
      const response = await readConfirmedProfileContext(domain, selectedUserId);
      setProfile(response.profile_context);
    });
  }

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!benchmarkDomain || !graphVersion || !userId) {
      setError("Select a benchmark domain, reviewed graph, and confirmed profile.");
      return;
    }

    await runTask("generate map", async () => {
      const [loadedGraph, loadedProfile] = await Promise.all([
        graph?.graph_manifest.version === graphVersion
          ? Promise.resolve(graph)
          : readReviewedGraph(benchmarkDomain, graphVersion),
        profile?.user_id === userId
          ? Promise.resolve(profile)
          : readConfirmedProfileContext(benchmarkDomain, userId).then((response) => response.profile_context)
      ]);
      const candidate = await generateCandidateMap({
        benchmarkDomain,
        graphVersion,
        userId,
        runId: runId.trim() || undefined,
        clientProvider,
        evidenceBatchSize,
        samplingTemperature
      });
      const warnings = await readCandidateMapWarnings(benchmarkDomain, candidate.run_id);
      const nextRuns = await listCandidateMapRuns(benchmarkDomain);
      setGraph(loadedGraph);
      setProfile(loadedProfile);
      setCandidateRuns(nextRuns);
      setReviewContext({
        benchmarkDomain,
        graphVersion,
        userId,
        candidate,
        graph: loadedGraph,
        profile: loadedProfile,
        warnings
      });
      setSelectedNodeId(null);
      setNotice(`Generated Candidate Knowledge Map ${candidate.run_id}.`);
      scrollToReview();
    });
  }

  async function handleLoadCandidateRun(summary: CandidateMapRunSummary) {
    if (!summary.has_candidate_map) {
      setNotice(`Candidate map run ${summary.run_id} is ${summary.status}: ${summary.error ?? "no promotable candidate map was written."}`);
      setError(null);
      return;
    }
    if (!summary.graph_version || !summary.user_id) {
      setError(`Candidate map run ${summary.run_id} is missing graph or user metadata.`);
      return;
    }
    const summaryGraphVersion = summary.graph_version;
    const summaryUserId = summary.user_id;

    await runTask("load candidate map", async () => {
      const [candidate, warnings, loadedGraph, loadedProfileResponse] = await Promise.all([
        readCandidateMap(benchmarkDomain, summary.run_id),
        readCandidateMapWarnings(benchmarkDomain, summary.run_id),
        readReviewedGraph(benchmarkDomain, summaryGraphVersion),
        readConfirmedProfileContext(benchmarkDomain, summaryUserId)
      ]);
      setGraphVersion(summaryGraphVersion);
      setUserId(summaryUserId);
      setGraph(loadedGraph);
      setProfile(loadedProfileResponse.profile_context);
      setReviewContext({
        benchmarkDomain,
        graphVersion: summaryGraphVersion,
        userId: summaryUserId,
        candidate,
        graph: loadedGraph,
        profile: loadedProfileResponse.profile_context,
        warnings
      });
      setSelectedNodeId(null);
      setNotice(`Loaded Candidate Knowledge Map ${summary.run_id}.`);
      scrollToReview();
    });
  }

  function openPromotionDialog() {
    if (!reviewContext) return;
    setError(null);
    setMapId("");
    setPromotionDialogOpen(true);
  }

  async function handlePromote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reviewContext) return;
    const trimmedMapId = mapId.trim();
    if (!trimmedMapId) {
      setError("Map ID is required.");
      return;
    }

    await runTask("promote map", async () => {
      let publishedMapId = trimmedMapId;
      try {
        const response = await promoteCandidateMap({
          benchmarkDomain: reviewContext.benchmarkDomain,
          runId: reviewContext.candidate.run_id,
          mapId: trimmedMapId
        });
        publishedMapId = response.map_manifest.map_id;
      } catch (taskError) {
        if (!(taskError instanceof ApiRequestError) || taskError.status !== 409) {
          throw taskError;
        }
        throw new Error(taskError.message);
      }
      const nextRuns = await listCandidateMapRuns(reviewContext.benchmarkDomain);
      setCandidateRuns(nextRuns);
      setReviewContext(null);
      setSelectedNodeId(null);
      setPromotionDialogOpen(false);
      setMapId("");
      setNotice(`Published immutable Map ${publishedMapId}.`);
      scrollToComposer();
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

  function scrollToReview() {
    requestAnimationFrame(() => {
      reviewStageRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function scrollToComposer() {
    requestAnimationFrame(() => {
      composerStageRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  return (
    <main className="map-workbench">
      <section className="topbar map-topbar">
        <div>
          <p className="eyebrow">Map Authoring</p>
          <h1>User Map</h1>
          <p>Generate, inspect, and promote Candidate Knowledge Maps from one confirmed Profile Context and one reviewed graph version.</p>
        </div>
        <div className="status-strip" aria-live="polite">
          {busy && <span className="status busy">Working: {busy}</span>}
          {notice && <span className="status ok">{notice}</span>}
          {error && <span className="status error">{error}</span>}
        </div>
      </section>

      <div className="map-scroll">
        <section className="map-composer-stage" ref={composerStageRef}>
          <form className="map-composer-shell" onSubmit={handleGenerate}>
            <div className="map-card-heading">
              <div>
                <p className="eyebrow">Candidate Map Inputs</p>
                <h2>Select a reviewed graph and confirmed profile</h2>
              </div>
              <button type="button" className="secondary" onClick={() => benchmarkDomain && void refreshDomainAssets(benchmarkDomain)} disabled={busy !== null || !benchmarkDomain}>
                Refresh
              </button>
            </div>

            <div className="map-filter-row">
              <label>
                Benchmark Domain
                <select value={benchmarkDomain} onChange={(event) => setBenchmarkDomain(event.target.value)} disabled={busy !== null}>
                  <option value="">Select domain</option>
                  {benchmarkDomains.map((domain) => (
                    <option key={domain} value={domain}>{domain}</option>
                  ))}
                </select>
              </label>
              <label>
                Reviewed Graph
                <select value={graphVersion} onChange={(event) => setGraphVersion(event.target.value)} disabled={busy !== null || graphs.length === 0}>
                  <option value="">Select graph</option>
                  {graphs.map((candidate) => (
                    <option key={candidate.version} value={candidate.version}>
                      {candidate.version}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Confirmed Profile
                <select value={userId} onChange={(event) => setUserId(event.target.value)} disabled={busy !== null || users.length === 0}>
                  <option value="">Select profile</option>
                  {users.map((candidate) => (
                    <option key={candidate.user_id} value={candidate.user_id}>
                      {candidate.user_id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Model Provider
                <select value={clientProvider} onChange={(event) => setClientProvider(event.target.value as ClientProvider)} disabled={busy !== null}>
                  <option value="openai">OpenAI</option>
                  <option value="deepseek">DeepSeek</option>
                </select>
              </label>
            </div>

            <div className="map-input-preview-grid">
              <ProfilePreview profile={profile} selectedUserId={userId} />
              <GraphPreview graph={graph} selectedVersion={graphVersion} />
            </div>

            <div className="map-advanced-block">
              <button type="button" className="secondary compact-button" onClick={() => setAdvancedOpen((open) => !open)}>
                {advancedOpen ? "Hide advanced" : "Show advanced"}
              </button>
              {advancedOpen && (
                <div className="map-advanced-grid">
                  <label>
                    Run ID
                    <input value={runId} onChange={(event) => setRunId(event.target.value)} placeholder="Optional" disabled={busy !== null} />
                  </label>
                  <label>
                    Evidence Batch Size
                    <input type="number" min={1} value={evidenceBatchSize} onChange={(event) => setEvidenceBatchSize(Math.max(1, Number(event.target.value) || 1))} disabled={busy !== null} />
                  </label>
                  <label>
                    Sampling Temperature
                    <input type="number" min={0} step={0.1} value={samplingTemperature} onChange={(event) => setSamplingTemperature(Math.max(0, Number(event.target.value) || 0))} disabled={busy !== null} />
                  </label>
                </div>
              )}
            </div>

            <div className="map-composer-actions">
              <div>
                <strong>{candidateRuns.length}</strong>
                <span>candidate map runs</span>
              </div>
              <button type="submit" disabled={busy !== null || !benchmarkDomain || !graphVersion || !userId}>
                Generate Candidate Map
              </button>
            </div>
          </form>

          <section className="map-runs-panel">
            <div className="map-runs-header">
              <div>
                <p className="eyebrow">Saved Runs</p>
                <h2>Candidate Maps</h2>
              </div>
            </div>
            {candidateRuns.length === 0 ? (
              <p className="empty">No candidate map runs for this domain.</p>
            ) : (
              <div className="map-run-list">
                {candidateRuns.map((run) => (
                  <button
                    type="button"
                    key={run.run_id}
                    className={run.has_candidate_map ? "list-row map-run-row" : "list-row map-run-row failed"}
                    onClick={() => void handleLoadCandidateRun(run)}
                  >
                    <strong>{run.run_id}</strong>
                    <span>{run.status} / {run.graph_version ?? "no graph"} / {run.user_id ?? "no user"}</span>
                    <small>{run.has_candidate_map ? `${run.warning_count ?? 0} warnings` : run.error ?? "No candidate map"}</small>
                  </button>
                ))}
              </div>
            )}
          </section>
        </section>

        {reviewContext && (
          <section className="map-review-stage" ref={reviewStageRef}>
            <div className="map-review-header">
              <div>
                <p className="eyebrow">Candidate Knowledge Map</p>
                <h2>{reviewContext.candidate.run_id}</h2>
                <p>{reviewContext.benchmarkDomain} / {reviewContext.graphVersion} / {reviewContext.userId}</p>
              </div>
              <div className="map-review-actions">
                <span className="lifecycle-badge">Candidate</span>
                <span className={reviewContext.warnings.length > 0 ? "warning-count active" : "warning-count"}>
                  {reviewContext.warnings.length} warnings
                </span>
                <button type="button" onClick={openPromotionDialog} disabled={busy !== null}>
                  Publish Map
                </button>
              </div>
            </div>

            <div className="map-legend" aria-label="Mastery color scale">
              {(["L0", "L1", "L2", "L3", "L4", "L5"] as const).map((level) => (
                <span key={level} className={`mastery-chip mastery-${level.toLowerCase()}`}>{level}</span>
              ))}
            </div>

            <div className="map-review-canvas-shell">
              <MapReviewCanvas
                graph={reviewContext.graph}
                knowledgeMap={reviewContext.candidate.candidate_map}
                warnings={reviewContext.warnings}
                selectedNodeId={selectedNodeId}
                onSelectNode={setSelectedNodeId}
              />
              {selectedNode && selectedState && (
                <NodeInspectionCard
                  node={selectedNode}
                  knowledgeMap={reviewContext.candidate.candidate_map}
                  evidence={selectedEvidence}
                  warnings={selectedWarnings}
                  onClose={() => setSelectedNodeId(null)}
                />
              )}
            </div>
          </section>
        )}
      </div>

      {promotionDialogOpen && reviewContext && (
        <div className="dialog-backdrop">
          <form className="dialog" onSubmit={handlePromote}>
            <h2>Publish Map</h2>
            <p>This publishes the candidate unchanged as an immutable reviewed map.</p>
            <div className="promotion-summary">
              <Meta label="Candidate run" value={reviewContext.candidate.run_id} />
              <Meta label="User ID" value={reviewContext.userId} />
              <Meta label="Graph version" value={reviewContext.graphVersion} />
              <Meta label="Warnings" value={String(reviewContext.warnings.length)} />
            </div>
            <label>
              Map ID
              <input
                autoFocus
                value={mapId}
                onChange={(event) => setMapId(event.target.value)}
                placeholder="gt_map_001"
                pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,127}"
                required
              />
            </label>
            <div className="button-row dialog-actions">
              <button type="button" className="secondary" onClick={() => setPromotionDialogOpen(false)} disabled={busy !== null}>
                Cancel
              </button>
              <button type="submit" disabled={busy !== null}>Publish Snapshot</button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}

function ProfilePreview({
  profile,
  selectedUserId
}: {
  profile: ConfirmedProfileContext | null;
  selectedUserId: string;
}) {
  return (
    <section className="map-preview-card">
      <div>
        <p className="eyebrow">Confirmed Profile</p>
        <h3>{profile?.user_id ?? (selectedUserId || "No profile selected")}</h3>
      </div>
      {profile ? (
        <div className="profile-preview-body">
          <p>{profile.summary}</p>
          <PreviewList title="Background" items={profile.background} />
          <PreviewList title="Prior Experience" items={profile.prior_experience} />
          <PreviewList title="Goals" items={profile.goals} />
          <PreviewList title="Preferences" items={profile.preferences} />
        </div>
      ) : (
        <p className="empty">Select a confirmed profile to preview it.</p>
      )}
    </section>
  );
}

function GraphPreview({
  graph,
  selectedVersion
}: {
  graph: ReviewedGraphPayload | null;
  selectedVersion: string;
}) {
  return (
    <section className="map-preview-card">
      <div>
        <p className="eyebrow">Reviewed Graph</p>
        <h3>{graph?.graph_manifest.version ?? (selectedVersion || "No graph selected")}</h3>
      </div>
      {graph ? (
        <div className="graph-preview-stats">
          <Meta label="Graph ID" value={graph.graph_manifest.graph_id} />
          <Meta label="Nodes" value={String(graph.authored_nodes.length)} />
          <Meta label="Edges" value={String(graph.authored_edges.length)} />
          <Meta label="Candidate Run" value={graph.graph_manifest.promoted_from_candidate_run} />
        </div>
      ) : (
        <p className="empty">Select a reviewed graph to preview its snapshot.</p>
      )}
    </section>
  );
}

function PreviewList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="preview-list">
      <strong>{title}</strong>
      <ul>
        {items.map((item, index) => (
          <li key={`${title}-${index}`}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function NodeInspectionCard({
  node,
  knowledgeMap,
  evidence,
  warnings,
  onClose
}: {
  node: KnowledgeNode;
  knowledgeMap: KnowledgeMap;
  evidence: Array<{ evidenceRef: string; record: EvidenceRecord | null }>;
  warnings: MapEdgeConsistencyWarning[];
  onClose: () => void;
}) {
  const state = knowledgeMap.states.find((candidate) => candidate.node_id === node.id);
  if (!state) return null;

  return (
    <aside className="node-popover" aria-label={`Knowledge map details for ${node.name}`}>
      <div className="node-popover-header">
        <div>
          <p className="eyebrow">Knowledge Node</p>
          <h3>{node.name}</h3>
        </div>
        <button type="button" className="remove-item-button" aria-label="Close node details" onClick={onClose}>
          &#215;
        </button>
      </div>

      <section>
        <h4>Graph Node</h4>
        <Meta label="ID" value={node.id} />
        <Meta label="Type" value={node.type} />
        {node.definition && <p>{node.definition}</p>}
        {node.diagnostic_goal && <p>{node.diagnostic_goal}</p>}
        <PreviewList
          title="Source Locators"
          items={node.source_locators.map((locator) =>
            `${locator.source_id}: ${locator.locator}${locator.note ? ` - ${locator.note}` : ""}`
          )}
        />
        <details>
          <summary>Rubrics and diagnostic signals</summary>
          <PreviewList title="Diagnostic Signals" items={node.diagnostic_signals} />
          <div className="rubric-list">
            {Object.entries(node.levels).map(([level, description]) => (
              <Meta key={level} label={level} value={description} />
            ))}
          </div>
        </details>
      </section>

      <section>
        <h4>User Knowledge State</h4>
        <Meta label="Mastery Level" value={state.mastery_level} />
        <PreviewList title="Misconceptions" items={state.misconceptions} />
        <PreviewList title="Unknowns" items={state.unknowns} />
      </section>

      <section>
        <h4>Evidence Records</h4>
        {evidence.length === 0 ? (
          <p className="empty">No evidence refs.</p>
        ) : (
          <div className="evidence-list">
            {evidence.map(({ evidenceRef, record }) => (
              <article key={evidenceRef} className={record ? "evidence-card" : "evidence-card missing"}>
                <strong>{evidenceRef}</strong>
                {record ? (
                  <>
                    <span>{record.evidence_kind} / {record.evidence_type} / {record.visibility}</span>
                    <p>{record.signal}</p>
                  </>
                ) : (
                  <p>Missing referenced Evidence Record.</p>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      {warnings.length > 0 && (
        <section>
          <h4>Consistency Warnings</h4>
          <div className="evidence-list">
            {warnings.map((warning) => (
              <article key={warning.edge_id} className="evidence-card warning">
                <strong>{warning.edge_id}</strong>
                <span>{warning.source_node_id} {warning.source_mastery_level} {" -> "} {warning.target_node_id} {warning.target_mastery_level}</span>
                <p>{warning.rule}</p>
              </article>
            ))}
          </div>
        </section>
      )}
    </aside>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="profile-meta map-meta">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
