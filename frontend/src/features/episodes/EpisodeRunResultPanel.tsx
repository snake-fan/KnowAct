import type { RuntimeEpisodeRunResponse } from "../../api/runtime";
import type { VisibleDialogueContext } from "../../api/simulator";

export function EpisodeRunResultPanel({
  runResult,
  transcript
}: {
  runResult: RuntimeEpisodeRunResponse;
  transcript: VisibleDialogueContext | null;
}) {
  const report = runResult.scoring_report;
  const artifacts = [
    ["Run Dir", runResult.artifacts.run_dir],
    ["Transcript", runResult.artifacts.transcript],
    ["Working Map", runResult.artifacts.working_map],
    ["Agent Tool Trace", runResult.artifacts.agent_tool_trace],
    ["Agent Output", runResult.artifacts.agent_output],
    ["Scoring Report", runResult.artifacts.scoring_report],
    ["Manifest Snapshot", runResult.artifacts.episode_manifest_snapshot]
  ];

  return (
    <section className="episode-preview-card episode-run-result-panel">
      <div className="episode-run-result-header">
        <div>
          <p className="eyebrow">Episode Result</p>
          <h3>{runResult.run_id}</h3>
        </div>
        <div className="map-review-actions">
          <span className="lifecycle-badge confirmed">{runResult.agent_kind}</span>
          <span className={runResult.forced_finalization ? "warning-count active" : "warning-count"}>
            {runResult.forced_finalization ? "Forced Final" : "Finalized"}
          </span>
        </div>
      </div>

      <div className="episode-run-metrics">
        <EpisodeMetric label="Turns" value={String(runResult.turn_count)} />
        <EpisodeMetric label="Mastery Distance" value={formatScore(report.episode_mastery_distance)} />
        <EpisodeMetric label="Exact Match" value={formatRatio(report.exact_match_rate)} />
        <EpisodeMetric label="Missing Prediction" value={formatRatio(report.missing_prediction_rate)} />
        <EpisodeMetric label="Unsupported Inference" value={formatRatio(report.unsupported_inference_rate)} />
        <EpisodeMetric label="Forced Fallback" value={runResult.forced_finalization_fallback ? "Yes" : "No"} />
      </div>

      <div className="episode-run-transcript">
        <div className="episode-run-subheader">
          <div>
            <p className="eyebrow">Run Transcript</p>
            <h4>{transcript?.turns.length ?? 0} visible turns</h4>
          </div>
          <span className="warning-count">Visible Only</span>
        </div>
        {transcript && transcript.turns.length > 0 ? (
          <div className="episode-run-transcript-list">
            {transcript.turns.map((turn, index) => (
              <article key={turn.turn_id ?? index} className="episode-run-turn">
                <div>
                  <strong>{turn.turn_id ?? `turn_${String(index + 1).padStart(3, "0")}`}</strong>
                  <span className="simulator-turn-kind">{turn.observation.kind}</span>
                </div>
                <p className="episode-run-question">{turn.question.text}</p>
                <p>{turn.answer.text}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty">No visible transcript turns are available for this run.</p>
        )}
      </div>

      <div className="episode-score-table-wrap">
        <table className="episode-score-table">
          <thead>
            <tr>
              <th>Node</th>
              <th>Ground Truth</th>
              <th>Prediction</th>
              <th>Distance</th>
              <th>Error</th>
              <th>Flags</th>
            </tr>
          </thead>
          <tbody>
            {report.per_node.map((node) => (
              <tr key={node.node_id}>
                <td>{node.node_id}</td>
                <td>{node.ground_truth_mastery}</td>
                <td>{node.predicted_mastery ?? "Missing"}</td>
                <td>{formatScore(node.mastery_distance)}</td>
                <td>{node.signed_mastery_error === null ? "-" : formatScore(node.signed_mastery_error)}</td>
                <td>
                  <ScoreFlags
                    exactMatch={node.exact_match}
                    missingPrediction={node.missing_prediction}
                    unsupportedInference={node.unsupported_inference}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="episode-run-artifacts">
        <p className="eyebrow">Artifacts</p>
        {artifacts.map(([label, value]) => (
          <div key={label} className="episode-run-artifact-row">
            <span>{label}</span>
            <code>{value}</code>
          </div>
        ))}
      </div>
    </section>
  );
}

function EpisodeMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="episode-run-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ScoreFlags({
  exactMatch,
  missingPrediction,
  unsupportedInference
}: {
  exactMatch: boolean;
  missingPrediction: boolean;
  unsupportedInference: boolean;
}) {
  const flags = [
    exactMatch ? "Exact" : null,
    missingPrediction ? "Missing" : null,
    unsupportedInference ? "Unsupported" : null
  ].filter((flag): flag is string => flag !== null);
  if (flags.length === 0) {
    return <span className="score-flag neutral">Distance</span>;
  }
  return (
    <span className={exactMatch ? "score-flag ok" : "score-flag warning"}>
      {flags.join(" / ")}
    </span>
  );
}

function formatScore(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(3);
}

function formatRatio(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}
