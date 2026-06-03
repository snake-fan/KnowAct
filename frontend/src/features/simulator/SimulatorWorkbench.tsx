import { useEffect, useMemo, useState } from "react";
import {
  ReviewedGraphPayload,
  ReviewedMapPayload,
  ReviewedMapSummary,
  listBenchmarkDomains,
  listReviewedMaps,
  readReviewedGraph,
  readReviewedMap
} from "../../api/authoring";
import { MapPreviewCanvas } from "../mapAuthoring/MapPreviewCanvas";
import {
  MapLegend,
  MapMeta,
  MapNodeInspectionCard
} from "../mapAuthoring/MapPreviewDetails";

type SimulatorMapPreviewContext = {
  benchmarkDomain: string;
  graph: ReviewedGraphPayload;
  reviewedMap: ReviewedMapPayload;
};

export function SimulatorWorkbench() {
  const [benchmarkDomains, setBenchmarkDomains] = useState<string[]>([]);
  const [benchmarkDomain, setBenchmarkDomain] = useState("");
  const [reviewedMaps, setReviewedMaps] = useState<ReviewedMapSummary[]>([]);
  const [selectedMapId, setSelectedMapId] = useState("");
  const [previewContext, setPreviewContext] = useState<SimulatorMapPreviewContext | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refreshBenchmarkDomains();
  }, []);

  useEffect(() => {
    if (!benchmarkDomain) return;
    void refreshReviewedMapList(benchmarkDomain);
  }, [benchmarkDomain]);

  const selectedNode = useMemo(() => {
    if (!previewContext || !selectedNodeId) return null;
    return previewContext.graph.authored_nodes.find((node) => node.id === selectedNodeId) ?? null;
  }, [previewContext, selectedNodeId]);

  async function refreshBenchmarkDomains() {
    await runTask("domains", async () => {
      const domains = await listBenchmarkDomains();
      setBenchmarkDomains(domains);
      setBenchmarkDomain((current) => current || domains[0] || "");
    });
  }

  async function refreshReviewedMapList(domain: string) {
    await runTask("reviewed maps", async () => {
      const nextMaps = await listReviewedMaps(domain);
      const nextSelectedMapId = nextMaps.some((candidate) => candidate.map_id === selectedMapId)
        ? selectedMapId
        : nextMaps[0]?.map_id ?? "";
      setReviewedMaps(nextMaps);
      setSelectedMapId(nextSelectedMapId);
      setSelectedNodeId(null);
      if (!nextSelectedMapId) {
        setPreviewContext(null);
        return;
      }
      setPreviewContext(await loadPreviewContext(domain, nextSelectedMapId));
    });
  }

  async function handleLoadReviewedMap(summary: ReviewedMapSummary) {
    await runTask("preview map", async () => {
      setSelectedMapId(summary.map_id);
      setSelectedNodeId(null);
      setPreviewContext(await loadPreviewContext(benchmarkDomain, summary.map_id));
      setNotice(`Loaded Reviewed Map ${summary.map_id}.`);
    });
  }

  async function loadPreviewContext(
    domain: string,
    mapId: string
  ): Promise<SimulatorMapPreviewContext> {
    const reviewedMap = await readReviewedMap(domain, mapId);
    const graph = await readReviewedGraph(domain, reviewedMap.map_manifest.graph_version);
    return {
      benchmarkDomain: domain,
      graph,
      reviewedMap
    };
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

  return (
    <main className="simulator-workbench">
      <section className="topbar simulator-topbar">
        <div>
          <p className="eyebrow">Simulator</p>
          <h1>Simulation Preview</h1>
          <p>Select a reviewed Knowledge Map to inspect the hidden user state basis that future simulator episodes will use.</p>
        </div>
        <div className="status-strip" aria-live="polite">
          {busy && <span className="status busy">Working: {busy}</span>}
          {notice && <span className="status ok">{notice}</span>}
          {error && <span className="status error">{error}</span>}
        </div>
      </section>

      <div className="simulator-preview-stage">
        <section className="map-runs-panel simulator-map-list-panel">
          <div className="map-runs-header">
            <div>
              <p className="eyebrow">Reviewed Maps</p>
              <h2>Map List</h2>
            </div>
            <button
              type="button"
              className="secondary"
              onClick={() => benchmarkDomain && void refreshReviewedMapList(benchmarkDomain)}
              disabled={busy !== null || !benchmarkDomain}
            >
              Refresh
            </button>
          </div>

          <label>
            Benchmark Domain
            <select value={benchmarkDomain} onChange={(event) => setBenchmarkDomain(event.target.value)} disabled={busy !== null}>
              <option value="">Select domain</option>
              {benchmarkDomains.map((domain) => (
                <option key={domain} value={domain}>{domain}</option>
              ))}
            </select>
          </label>

          {reviewedMaps.length === 0 ? (
            <p className="empty">No reviewed maps for this domain.</p>
          ) : (
            <div className="map-run-list">
              {reviewedMaps.map((reviewedMap) => (
                <button
                  type="button"
                  key={reviewedMap.map_id}
                  className={reviewedMap.map_id === selectedMapId ? "list-row map-run-row active" : "list-row map-run-row"}
                  onClick={() => void handleLoadReviewedMap(reviewedMap)}
                >
                  <strong>{reviewedMap.map_id}</strong>
                  <span>{reviewedMap.graph_version ?? "unknown graph"} / {reviewedMap.user_id ?? "unknown user"}</span>
                  <small>{reviewedMap.state_count ?? 0} states / {reviewedMap.evidence_count ?? 0} evidence</small>
                </button>
              ))}
            </div>
          )}
        </section>

        {previewContext ? (
          <section className="map-review-stage simulator-preview-panel">
            <div className="map-review-header">
              <div>
                <p className="eyebrow">Reviewed Knowledge Map</p>
                <h2>{previewContext.reviewedMap.map_manifest.map_id}</h2>
                <p>
                  {previewContext.benchmarkDomain} / {previewContext.reviewedMap.map_manifest.graph_version} / {previewContext.reviewedMap.map_manifest.user_id}
                </p>
              </div>
              <div className="map-review-actions">
                <span className="lifecycle-badge confirmed">Reviewed</span>
                <span className="warning-count">Runtime pending</span>
              </div>
            </div>

            <div className="simulator-map-summary">
              <MapMeta label="States" value={String(previewContext.reviewedMap.map.states.length)} />
              <MapMeta label="Evidence" value={String(previewContext.reviewedMap.map.evidence.length)} />
              <MapMeta label="Promoted From" value={previewContext.reviewedMap.map_manifest.promoted_from_candidate_run} />
            </div>

            <MapLegend />

            <div className="map-review-canvas-shell">
              <div className="map-preview-canvas-frame">
                <MapPreviewCanvas
                  graph={previewContext.graph}
                  knowledgeMap={previewContext.reviewedMap.map}
                  selectedNodeId={selectedNodeId}
                  onSelectNode={setSelectedNodeId}
                  ariaLabel="Reviewed knowledge map simulator preview graph"
                />
                {selectedNode && (
                  <MapNodeInspectionCard
                    node={selectedNode}
                    knowledgeMap={previewContext.reviewedMap.map}
                    onClose={() => setSelectedNodeId(null)}
                  />
                )}
              </div>
            </div>
          </section>
        ) : (
          <section className="simulator-empty-panel">
            <p className="eyebrow">Reviewed Map Preview</p>
            <h2>Select a map</h2>
            <p>Reviewed maps published from User Map authoring will appear in the list when available.</p>
          </section>
        )}
      </div>
    </main>
  );
}
