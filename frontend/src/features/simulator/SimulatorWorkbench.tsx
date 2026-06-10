import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction
} from "react";
import {
  ReviewedGraphPayload,
  ReviewedMapPayload,
  ReviewedMapSummary,
  listBenchmarkDomains,
  listReviewedMaps,
  readReviewedGraph,
  readReviewedMap
} from "../../api/authoring";
import {
  SimulatorClientProvider,
  VisibleDialogueTurn,
  answerSimulatorTurn
} from "../../api/simulator";
import { MapPreviewCanvas } from "../mapAuthoring/MapPreviewCanvas";
import {
  MapLegend,
  MapMeta,
  MapNodeInspectionCard
} from "../mapAuthoring/MapPreviewDetails";

type SimulatorMapContext = {
  benchmarkDomain: string;
  graph: ReviewedGraphPayload;
  reviewedMap: ReviewedMapPayload;
};

type RunTask = (label: string, task: () => Promise<void>) => Promise<void>;

export function SimulatorWorkbench() {
  const [benchmarkDomains, setBenchmarkDomains] = useState<string[]>([]);
  const [benchmarkDomain, setBenchmarkDomain] = useState("");
  const [reviewedMaps, setReviewedMaps] = useState<ReviewedMapSummary[]>([]);
  const [selectedMapId, setSelectedMapId] = useState("");
  const [simulatorContext, setSimulatorContext] = useState<SimulatorMapContext | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [conversationResetKey, setConversationResetKey] = useState(0);
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

  const handleSelectNode = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  }, []);

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
      resetSimulatorConversation();
      if (!nextSelectedMapId) {
        setSimulatorContext(null);
        return;
      }
      setSimulatorContext(await loadSimulatorContext(domain, nextSelectedMapId));
    });
  }

  async function handleLoadReviewedMap(summary: ReviewedMapSummary) {
    await runTask("load map", async () => {
      setSelectedMapId(summary.map_id);
      setSelectedNodeId(null);
      resetSimulatorConversation();
      setSimulatorContext(await loadSimulatorContext(benchmarkDomain, summary.map_id));
      setNotice(`Loaded Reviewed Map ${summary.map_id}.`);
    });
  }

  async function loadSimulatorContext(
    domain: string,
    mapId: string
  ): Promise<SimulatorMapContext> {
    const reviewedMap = await readReviewedMap(domain, mapId);
    const graph = await readReviewedGraph(domain, reviewedMap.map_manifest.graph_version);
    return {
      benchmarkDomain: domain,
      graph,
      reviewedMap
    };
  }

  function resetSimulatorConversation() {
    setConversationResetKey((current) => current + 1);
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
          <h1>Simulator</h1>
          <p>Select a reviewed Knowledge Map and run diagnostic turns against the hidden user state.</p>
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

          <SimulatorTurnPanel
            key={conversationResetKey}
            simulatorContext={simulatorContext}
            selectedMapId={selectedMapId}
            busy={busy}
            runTask={runTask}
            setNotice={setNotice}
            setError={setError}
          />
        </section>

        {simulatorContext ? (
          <SimulatorMapPreviewPanel
            simulatorContext={simulatorContext}
            selectedNodeId={selectedNodeId}
            onSelectNode={handleSelectNode}
          />
        ) : (
          <section className="simulator-empty-panel">
            <p className="eyebrow">Simulator</p>
            <h2>Select a map</h2>
            <p>Reviewed maps published from User Map authoring will appear in the list when available.</p>
          </section>
        )}
      </div>
    </main>
  );
}

function SimulatorTurnPanel({
  simulatorContext,
  selectedMapId,
  busy,
  runTask,
  setNotice,
  setError
}: {
  simulatorContext: SimulatorMapContext | null;
  selectedMapId: string;
  busy: string | null;
  runTask: RunTask;
  setNotice: Dispatch<SetStateAction<string | null>>;
  setError: Dispatch<SetStateAction<string | null>>;
}) {
  const [clientProvider, setClientProvider] = useState<SimulatorClientProvider>("openai");
  const [questionText, setQuestionText] = useState("");
  const [includeDebugTrace, setIncludeDebugTrace] = useState(false);
  const [dialogueTurns, setDialogueTurns] = useState<VisibleDialogueTurn[]>([]);
  const [latestTrace, setLatestTrace] = useState<{ id: string; available: boolean } | null>(null);
  const hasQuestion = questionText.trim().length > 0;

  async function handleAskSimulator() {
    const question = questionText.trim();
    if (!simulatorContext || !selectedMapId) {
      setError("Select a reviewed map before asking the simulator.");
      return;
    }
    if (!question) {
      setError("Enter one diagnostic question.");
      return;
    }

    const visibleDialogueContext = dialogueTurns.length > 0
      ? { turns: dialogueTurns }
      : null;
    const turnIndex = dialogueTurns.length + 1;

    await runTask("simulator turn", async () => {
      const response = await answerSimulatorTurn({
        benchmarkDomain: simulatorContext.benchmarkDomain,
        mapId: selectedMapId,
        clientProvider,
        question: { text: question },
        visibleDialogueContext,
        includeDebugTrace
      });
      const turnId = response.debug_trace_id || `turn_${String(turnIndex).padStart(2, "0")}`;
      setDialogueTurns((currentTurns) => [
        ...currentTurns,
        {
          turn_id: turnId,
          question: { text: question },
          answer: response.answer,
          observation: response.observation
        }
      ]);
      setLatestTrace(
        response.debug_trace_id && response.debug_trace_available !== null
          ? {
              id: response.debug_trace_id,
              available: response.debug_trace_available === true
            }
          : null
      );
      setQuestionText("");
      const warningSuffix = response.warnings.length > 0
        ? ` ${response.warnings.map((warning) => warning.message).join(" ")}`
        : "";
      setNotice(`Simulator returned ${response.observation.kind}.${warningSuffix}`);
    });
  }

  function clearSimulatorConversation() {
    setDialogueTurns([]);
    setLatestTrace(null);
  }

  return (
    <>
      <div className="simulator-turn-form">
        <div>
          <p className="eyebrow">Turn</p>
          <h2>Ask Simulator</h2>
        </div>
        <label>
          Provider
          <select value={clientProvider} onChange={(event) => setClientProvider(event.target.value as SimulatorClientProvider)} disabled={busy !== null}>
            <option value="openai">OpenAI</option>
            <option value="deepseek">DeepSeek</option>
          </select>
        </label>
        <label>
          Diagnostic Question
          <textarea
            value={questionText}
            onChange={(event) => setQuestionText(event.target.value)}
            disabled={busy !== null || !simulatorContext}
            placeholder="How would you decide whether a train/test split is appropriate?"
          />
        </label>
        <label className="simulator-debug-toggle">
          <input
            type="checkbox"
            checked={includeDebugTrace}
            onChange={(event) => setIncludeDebugTrace(event.target.checked)}
            disabled={busy !== null}
          />
          <span>Return debug trace handle</span>
        </label>
        <div className="button-row">
          <button
            type="button"
            onClick={() => void handleAskSimulator()}
            disabled={busy !== null || !simulatorContext || !hasQuestion}
          >
            Ask Simulator
          </button>
          <button
            type="button"
            onClick={clearSimulatorConversation}
            disabled={busy !== null || dialogueTurns.length === 0}
          >
            Clear History
          </button>
        </div>
        {latestTrace && (
          <p className="simulator-trace-note">
            Trace {latestTrace.id}: {latestTrace.available ? "available" : "unavailable"}
          </p>
        )}
      </div>

      <div className="simulator-transcript" aria-live="polite">
        <div>
          <p className="eyebrow">Visible Turns</p>
          <h2>History</h2>
        </div>
        {dialogueTurns.length === 0 ? (
          <p className="empty">No simulator turns yet.</p>
        ) : (
          dialogueTurns.map((turn, index) => (
            <article key={`${turn.turn_id}-${index}`} className="simulator-turn-record">
              <div>
                <span>{turn.observation.kind}</span>
                <strong>{turn.turn_id}</strong>
              </div>
              <p className="simulator-question">{turn.question.text}</p>
              <p>{turn.answer.text}</p>
            </article>
          ))
        )}
      </div>
    </>
  );
}

const SimulatorMapPreviewPanel = memo(function SimulatorMapPreviewPanel({
  simulatorContext,
  selectedNodeId,
  onSelectNode
}: {
  simulatorContext: SimulatorMapContext;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string | null) => void;
}) {
  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return simulatorContext.graph.authored_nodes.find((node) => node.id === selectedNodeId) ?? null;
  }, [simulatorContext, selectedNodeId]);

  return (
    <section className="map-review-stage simulator-preview-panel">
      <div className="map-review-header">
        <div>
          <p className="eyebrow">Reviewed Knowledge Map</p>
          <h2>{simulatorContext.reviewedMap.map_manifest.map_id}</h2>
          <p>
            {simulatorContext.benchmarkDomain} / {simulatorContext.reviewedMap.map_manifest.graph_version} / {simulatorContext.reviewedMap.map_manifest.user_id}
          </p>
        </div>
        <div className="map-review-actions">
          <span className="lifecycle-badge confirmed">Reviewed</span>
          <span className="warning-count">Turn API Ready</span>
        </div>
      </div>

      <div className="simulator-map-summary">
        <MapMeta label="States" value={String(simulatorContext.reviewedMap.map.states.length)} />
        <MapMeta label="Evidence" value={String(simulatorContext.reviewedMap.map.evidence.length)} />
        <MapMeta label="Promoted From" value={simulatorContext.reviewedMap.map_manifest.promoted_from_candidate_run} />
      </div>

      <MapLegend />

      <div className="map-review-canvas-shell">
        <div className="map-preview-canvas-frame">
          <MapPreviewCanvas
            graph={simulatorContext.graph}
            knowledgeMap={simulatorContext.reviewedMap.map}
            selectedNodeId={selectedNodeId}
            onSelectNode={onSelectNode}
            ariaLabel="Reviewed knowledge map simulator graph"
          />
          {selectedNode && (
            <MapNodeInspectionCard
              node={selectedNode}
              knowledgeMap={simulatorContext.reviewedMap.map}
              onClose={() => onSelectNode(null)}
            />
          )}
        </div>
      </div>
    </section>
  );
});
