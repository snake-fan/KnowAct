import { useEffect, useMemo, useState } from "react";
import {
  RuntimeRunQueueEnqueueOutcome,
  RuntimeRunQueueEpisodeDetail,
  RuntimeRunQueueResponse,
  RuntimeRunQueueRow,
  cancelRuntimeEpisode,
  enqueueRuntimeEpisodes,
  readRuntimeRunQueue,
  readRuntimeRunQueueEpisode,
  readRuntimeRunTranscript,
  updateRuntimeRunQueueConcurrency
} from "../../api/runtime";
import type { VisibleDialogueContext } from "../../api/simulator";
import { EpisodeRunResultPanel } from "../episodes/EpisodeRunResultPanel";

const CONCURRENCY_OPTIONS = [3, 4, 5, 6, 7, 8];

export function RunQueueWorkbench() {
  const [queue, setQueue] = useState<RuntimeRunQueueResponse | null>(null);
  const [selectedEpisodeIds, setSelectedEpisodeIds] = useState<string[]>([]);
  const [focusedEpisodeId, setFocusedEpisodeId] = useState("");
  const [detail, setDetail] = useState<RuntimeRunQueueEpisodeDetail | null>(null);
  const [transcript, setTranscript] = useState<VisibleDialogueContext | null>(null);
  const [outcomes, setOutcomes] = useState<RuntimeRunQueueEnqueueOutcome[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const hasActiveEpisodes = useMemo(
    () => queue?.episodes.some((episode) => episode.status === "queued" || episode.status === "running") ?? false,
    [queue]
  );

  useEffect(() => {
    void refreshQueue(false);
  }, []);

  useEffect(() => {
    if (!hasActiveEpisodes) return;
    const timer = window.setTimeout(() => void refreshQueue(true), 2000);
    return () => window.clearTimeout(timer);
  }, [hasActiveEpisodes, queue]);

  async function refreshQueue(silent: boolean) {
    if (!silent) {
      setBusy("queue");
      setError(null);
    }
    try {
      const nextQueue = await readRuntimeRunQueue();
      setQueue(nextQueue);
      setSelectedEpisodeIds((current) => current.filter((episodeId) =>
        nextQueue.episodes.some((episode) => episode.episode_id === episodeId && episode.selectable)
      ));
      const nextFocused = nextQueue.episodes.some((episode) => episode.episode_id === focusedEpisodeId)
        ? focusedEpisodeId
        : nextQueue.episodes[0]?.episode_id ?? "";
      setFocusedEpisodeId(nextFocused);
      if (nextFocused) await loadDetail(nextFocused, true);
    } catch (taskError) {
      setError(taskError instanceof Error ? taskError.message : String(taskError));
    } finally {
      if (!silent) setBusy(null);
    }
  }

  async function loadDetail(episodeId: string, silent = false) {
    if (!silent) {
      setBusy("episode detail");
      setError(null);
    }
    try {
      const nextDetail = await readRuntimeRunQueueEpisode(episodeId);
      setFocusedEpisodeId(episodeId);
      setDetail(nextDetail);
      if (nextDetail.result) {
        setTranscript(await readRuntimeRunTranscript(nextDetail.result.run_id));
      } else {
        setTranscript(null);
      }
    } catch (taskError) {
      setError(taskError instanceof Error ? taskError.message : String(taskError));
    } finally {
      if (!silent) setBusy(null);
    }
  }

  function toggleEpisode(episode: RuntimeRunQueueRow) {
    if (!episode.selectable) return;
    setSelectedEpisodeIds((current) =>
      current.includes(episode.episode_id)
        ? current.filter((episodeId) => episodeId !== episode.episode_id)
        : [...current, episode.episode_id]
    );
  }

  async function handleEnqueue() {
    if (!queue || selectedEpisodeIds.length === 0) return;
    setBusy("enqueue");
    setError(null);
    try {
      const selected = new Set(selectedEpisodeIds);
      const response = await enqueueRuntimeEpisodes(
        queue.episodes
          .filter((episode) => selected.has(episode.episode_id))
          .map((episode) => ({
            episode_id: episode.episode_id,
            action: episode.checkpoint_health === "missing" || episode.checkpoint_health === "invalid"
              ? "restart" as const
              : "start_or_resume" as const
          }))
      );
      setOutcomes(response.outcomes);
      setSelectedEpisodeIds([]);
      await refreshQueue(true);
    } catch (taskError) {
      setError(taskError instanceof Error ? taskError.message : String(taskError));
    } finally {
      setBusy(null);
    }
  }

  async function handleConcurrency(concurrency: number) {
    setBusy("concurrency");
    setError(null);
    try {
      setQueue(await updateRuntimeRunQueueConcurrency(concurrency));
    } catch (taskError) {
      setError(taskError instanceof Error ? taskError.message : String(taskError));
    } finally {
      setBusy(null);
    }
  }

  async function handleCancel(episodeId: string) {
    setBusy("cancel");
    setError(null);
    try {
      await cancelRuntimeEpisode(episodeId);
      await refreshQueue(true);
    } catch (taskError) {
      setError(taskError instanceof Error ? taskError.message : String(taskError));
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="episodes-workbench run-queue-workbench">
      <section className="topbar episodes-topbar">
        <div>
          <p className="eyebrow">Runtime</p>
          <h1>Run Queue</h1>
          <p>Select eligible episodes, run them with bounded backend concurrency, and inspect one result per episode.</p>
        </div>
        <div className="status-strip" aria-live="polite">
          {busy && <span className="status busy">Working: {busy}</span>}
          {error && <span className="status error">{error}</span>}
        </div>
      </section>

      <div className="run-queue-toolbar">
        <label>
          Concurrency
          <select value={queue?.concurrency ?? 3} onChange={(event) => void handleConcurrency(Number(event.target.value))} disabled={busy !== null}>
            {CONCURRENCY_OPTIONS.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
        <div>
          <span>{selectedEpisodeIds.length} selected</span>
          <button type="button" onClick={() => void handleEnqueue()} disabled={busy !== null || selectedEpisodeIds.length === 0}>
            Add to Run Queue
          </button>
          <button type="button" className="secondary" onClick={() => void refreshQueue(false)} disabled={busy !== null}>Refresh</button>
        </div>
      </div>

      {outcomes.length > 0 && (
        <div className="run-queue-outcomes" aria-live="polite">
          {outcomes.map((outcome) => (
            <span key={outcome.episode_id} className={outcome.accepted ? "status ok" : "status error"}>
              {outcome.episode_id}: {outcome.accepted ? "queued" : outcome.message ?? outcome.error_code}
            </span>
          ))}
        </div>
      )}

      <div className="episodes-stage run-queue-stage">
        <section className="run-queue-list-panel">
          <div className="map-runs-header">
            <div><p className="eyebrow">Episodes</p><h2>Execution Status</h2></div>
            <span className="warning-count">FIFO</span>
          </div>
          {!queue || queue.episodes.length === 0 ? <p className="empty">No configured episodes are available.</p> : (
            <div className="run-queue-list">
              {queue.episodes.map((episode) => {
                const checked = selectedEpisodeIds.includes(episode.episode_id);
                const restartRequired = episode.checkpoint_health === "missing" || episode.checkpoint_health === "invalid";
                return (
                  <article key={episode.episode_id} className={episode.episode_id === focusedEpisodeId ? "run-queue-row active" : "run-queue-row"} onClick={() => void loadDetail(episode.episode_id)}>
                    <div className="run-queue-row-main">
                      {episode.selectable && (
                        <input type="checkbox" checked={checked} onChange={() => toggleEpisode(episode)} onClick={(event) => event.stopPropagation()} aria-label={`Select ${episode.episode_id}`} />
                      )}
                      <div><strong>{episode.episode_id}</strong><span>{episode.benchmark_domain} / {episode.graph_version}</span></div>
                      <StatusBadge status={episode.status} />
                    </div>
                    <div className="run-queue-row-progress">
                      {episode.status === "queued" && <span>Queue position {episode.queue_position}</span>}
                      {episode.status === "running" && <span>Turn {episode.completed_turns} / {episode.max_turns}</span>}
                      {restartRequired && <span className="restart-required">Selected action: restart with new run ID</span>}
                      {episode.cancel_requested && <span>Cancellation requested</span>}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {detail ? (
          <RunQueueDetail detail={detail} transcript={transcript} busy={busy !== null} onCancel={handleCancel} />
        ) : (
          <section className="episode-empty-panel"><p className="eyebrow">Episode Detail</p><h2>Select an episode</h2><p>Progress, recovery state, failures, and completed results are shown here.</p></section>
        )}
      </div>
    </main>
  );
}

function RunQueueDetail({
  detail,
  transcript,
  busy,
  onCancel
}: {
  detail: RuntimeRunQueueEpisodeDetail;
  transcript: VisibleDialogueContext | null;
  busy: boolean;
  onCancel: (episodeId: string) => Promise<void>;
}) {
  const episode = detail.episode;
  const configuration = detail.manifest.execution_configuration;
  return (
    <section className="episode-detail-panel run-queue-detail-panel">
      <div className="episode-detail-header">
        <div><p className="eyebrow">Evaluation Episode</p><h2>{episode.episode_id}</h2><p>{episode.benchmark_domain} / {episode.graph_version}</p></div>
        <div className="map-review-actions">
          <StatusBadge status={episode.status} />
          {(episode.status === "queued" || episode.status === "running") && (
            <button type="button" className="secondary" onClick={() => void onCancel(episode.episode_id)} disabled={busy || episode.cancel_requested}>
              {episode.cancel_requested ? "Cancelling..." : "Cancel"}
            </button>
          )}
        </div>
      </div>

      <div className="episode-detail-grid">
        <EpisodeMeta label="Run ID" value={episode.run_id ?? "Not allocated"} />
        <EpisodeMeta label="Progress" value={`${episode.completed_turns} / ${episode.max_turns} turns`} />
        <EpisodeMeta label="Checkpoint" value={episode.checkpoint_health} />
        <EpisodeMeta label="Queue Position" value={episode.queue_position ? String(episode.queue_position) : "-"} />
      </div>

      {episode.failure && (
        <section className="episode-preview-card run-queue-failure">
          <div><p className="eyebrow">Failure</p><h3>{episode.failure.code}</h3></div>
          <p>{episode.failure.message}</p>
          {(episode.checkpoint_health === "missing" || episode.checkpoint_health === "invalid") && <p className="restart-required">Select this episode to explicitly restart it with a new run ID. Existing artifacts are preserved.</p>}
        </section>
      )}

      {configuration && !detail.result && (
        <section className="episode-preview-card">
          <div><p className="eyebrow">Immutable Configuration</p><h3>{configuration.agent_kind}</h3></div>
          <div className="episode-detail-grid compact">
            <EpisodeMeta label="Tested Agent" value={`${configuration.tested_agent_client_provider} / ${configuration.tested_agent_model}`} />
            <EpisodeMeta label="Simulator" value={`${configuration.simulator_client_provider} / ${configuration.simulator_model}`} />
            <EpisodeMeta label="Temperature" value={String(configuration.tested_agent_temperature)} />
            <EpisodeMeta label="Tool Retries" value={String(configuration.max_tool_retries)} />
          </div>
        </section>
      )}

      {detail.result && <EpisodeRunResultPanel runResult={detail.result} transcript={transcript} />}
    </section>
  );
}

function StatusBadge({ status }: { status: RuntimeRunQueueRow["status"] }) {
  return <span className={`run-status-badge ${status}`}>{status}</span>;
}

function EpisodeMeta({ label, value }: { label: string; value: string }) {
  return <div className="map-meta episode-meta"><span>{label}</span><strong>{value}</strong></div>;
}
