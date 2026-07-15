import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ReviewedMapPayload,
  ReviewedMapSummary,
  listBenchmarkDomains,
  listReviewedMaps,
  readReviewedMap
} from "../../api/authoring";
import {
  EpisodeModelCatalog,
  RUNTIME_INTERACTION_RULE,
  RUNTIME_SCORING_PROFILE,
  RuntimeEpisodeDetail,
  RuntimeEpisodeSummary,
  SimulatorClientProvider,
  TestedAgentClientProvider,
  listRuntimeEpisodes,
  readRuntimeEpisode,
  readRuntimeEpisodeOptions,
  registerRuntimeEpisode
} from "../../api/runtime";

export function EpisodesWorkbench() {
  const [catalog, setCatalog] = useState<EpisodeModelCatalog | null>(null);
  const [benchmarkDomains, setBenchmarkDomains] = useState<string[]>([]);
  const [benchmarkDomain, setBenchmarkDomain] = useState("");
  const [reviewedMaps, setReviewedMaps] = useState<ReviewedMapSummary[]>([]);
  const [selectedMapId, setSelectedMapId] = useState("");
  const [selectedReviewedMap, setSelectedReviewedMap] = useState<ReviewedMapPayload | null>(null);
  const [episodeId, setEpisodeId] = useState("");
  const [maxTurns, setMaxTurns] = useState(3);
  const [testedAgentProvider, setTestedAgentProvider] = useState<TestedAgentClientProvider>("openai");
  const [testedAgentModel, setTestedAgentModel] = useState("");
  const [simulatorProvider, setSimulatorProvider] = useState<SimulatorClientProvider>("openai");
  const [simulatorModel, setSimulatorModel] = useState("");
  const [temperature, setTemperature] = useState(0);
  const [maxToolRetries, setMaxToolRetries] = useState(3);
  const [episodes, setEpisodes] = useState<RuntimeEpisodeSummary[]>([]);
  const [selectedEpisodeId, setSelectedEpisodeId] = useState("");
  const [episodeDetail, setEpisodeDetail] = useState<RuntimeEpisodeDetail | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refreshInitialData();
  }, []);

  useEffect(() => {
    if (!benchmarkDomain) return;
    void refreshReviewedMaps(benchmarkDomain);
  }, [benchmarkDomain]);

  useEffect(() => {
    if (!benchmarkDomain || !selectedMapId) {
      setSelectedReviewedMap(null);
      return;
    }
    void loadReviewedMap(benchmarkDomain, selectedMapId);
  }, [benchmarkDomain, selectedMapId]);

  const selectedMapSummary = useMemo(
    () => reviewedMaps.find((map) => map.map_id === selectedMapId) ?? null,
    [reviewedMaps, selectedMapId]
  );
  const derivedGraphVersion = selectedReviewedMap?.map_manifest.graph_version
    ?? selectedMapSummary?.graph_version
    ?? "";
  const testedProviderOption = catalog?.providers.find((item) => item.provider === testedAgentProvider) ?? null;
  const simulatorProviderOption = catalog?.providers.find((item) => item.provider === simulatorProvider) ?? null;
  const executionOptionsAvailable = Boolean(testedProviderOption?.available && simulatorProviderOption?.available);

  async function refreshInitialData() {
    await runTask("initial data", async () => {
      const [domains, runtimeEpisodes, options] = await Promise.all([
        listBenchmarkDomains(),
        listRuntimeEpisodes(),
        readRuntimeEpisodeOptions()
      ]);
      setBenchmarkDomains(domains);
      setBenchmarkDomain((current) => current || domains[0] || "");
      setEpisodes(runtimeEpisodes);
      setSelectedEpisodeId((current) =>
        runtimeEpisodes.some((episode) => episode.episode_id === current)
          ? current
          : runtimeEpisodes[0]?.episode_id ?? ""
      );
      setCatalog(options);
      const defaultProvider = options.providers.find((item) => item.available) ?? options.providers[0];
      if (defaultProvider) {
        setTestedAgentProvider(defaultProvider.provider);
        setTestedAgentModel(defaultProvider.default_model);
        setSimulatorProvider(defaultProvider.provider);
        setSimulatorModel(defaultProvider.default_model);
      }
      setTemperature(options.default_tested_agent_temperature);
      setMaxToolRetries(options.default_max_tool_retries);
    });
  }

  async function refreshReviewedMaps(domain: string) {
    await runTask("reviewed maps", async () => {
      const maps = await listReviewedMaps(domain);
      const nextSelectedMapId = maps.some((map) => map.map_id === selectedMapId)
        ? selectedMapId
        : maps[0]?.map_id ?? "";
      setReviewedMaps(maps);
      setSelectedMapId(nextSelectedMapId);
      if (!nextSelectedMapId) setSelectedReviewedMap(null);
    });
  }

  async function refreshEpisodes() {
    await runTask("episodes", async () => {
      const runtimeEpisodes = await listRuntimeEpisodes();
      setEpisodes(runtimeEpisodes);
      setSelectedEpisodeId((current) =>
        runtimeEpisodes.some((episode) => episode.episode_id === current)
          ? current
          : runtimeEpisodes[0]?.episode_id ?? ""
      );
    });
  }

  async function loadReviewedMap(domain: string, mapId: string) {
    await runTask("reviewed map", async () => {
      setSelectedReviewedMap(await readReviewedMap(domain, mapId));
    });
  }

  function changeTestedAgentProvider(provider: TestedAgentClientProvider) {
    const option = catalog?.providers.find((item) => item.provider === provider);
    setTestedAgentProvider(provider);
    setTestedAgentModel(option?.default_model ?? "");
  }

  function changeSimulatorProvider(provider: SimulatorClientProvider) {
    const option = catalog?.providers.find((item) => item.provider === provider);
    setSimulatorProvider(provider);
    setSimulatorModel(option?.default_model ?? "");
  }

  async function handleRegisterEpisode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedEpisodeId = episodeId.trim();
    if (!trimmedEpisodeId) {
      setError("Episode ID is required.");
      return;
    }
    if (!benchmarkDomain || !selectedMapId || !derivedGraphVersion) {
      setError("Select a benchmark domain and reviewed map.");
      return;
    }
    if (!executionOptionsAvailable || !testedAgentModel || !simulatorModel) {
      setError("Select configured tested-agent and simulator model options.");
      return;
    }
    await runTask("register episode", async () => {
      const detail = await registerRuntimeEpisode({
        episode_id: trimmedEpisodeId,
        benchmark_domain: benchmarkDomain,
        graph_version: derivedGraphVersion,
        hidden_map_id: selectedMapId,
        max_turns: maxTurns,
        agent_kind: "simple_llm_agent",
        tested_agent_client_provider: testedAgentProvider,
        tested_agent_model: testedAgentModel,
        simulator_client_provider: simulatorProvider,
        simulator_model: simulatorModel,
        tested_agent_temperature: temperature,
        max_tool_retries: maxToolRetries
      });
      const runtimeEpisodes = await listRuntimeEpisodes();
      setEpisodes(runtimeEpisodes);
      setSelectedEpisodeId(detail.manifest.episode_id);
      setEpisodeDetail(detail);
      setEpisodeId("");
      setNotice(`Registered Evaluation Episode ${detail.manifest.episode_id}.`);
    });
  }

  async function handleLoadEpisode(episode: RuntimeEpisodeSummary) {
    await runTask("episode detail", async () => {
      setSelectedEpisodeId(episode.episode_id);
      setEpisodeDetail(await readRuntimeEpisode(episode.episode_id));
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

  return (
    <main className="episodes-workbench">
      <section className="topbar episodes-topbar">
        <div>
          <p className="eyebrow">Runtime</p>
          <h1>Episodes</h1>
          <p>Register immutable Evaluation Episode manifests and inspect reviewed bindings. Execution lives in Run Queue.</p>
        </div>
        <div className="status-strip" aria-live="polite">
          {busy && <span className="status busy">Working: {busy}</span>}
          {notice && <span className="status ok">{notice}</span>}
          {error && <span className="status error">{error}</span>}
        </div>
      </section>

      <div className="episodes-stage">
        <section className="episodes-control-panel">
          <form className="episode-registration-form" onSubmit={handleRegisterEpisode}>
            <div className="map-runs-header">
              <div>
                <p className="eyebrow">Episode Manifest Registration</p>
                <h2>Create Episode</h2>
              </div>
              <button type="button" className="secondary" onClick={() => benchmarkDomain && void refreshReviewedMaps(benchmarkDomain)} disabled={busy !== null || !benchmarkDomain}>
                Refresh
              </button>
            </div>

            <label>
              Benchmark Domain
              <select value={benchmarkDomain} onChange={(event) => setBenchmarkDomain(event.target.value)} disabled={busy !== null}>
                <option value="">Select domain</option>
                {benchmarkDomains.map((domain) => <option key={domain} value={domain}>{domain}</option>)}
              </select>
            </label>
            <label>
              Reviewed Map
              <select value={selectedMapId} onChange={(event) => setSelectedMapId(event.target.value)} disabled={busy !== null || reviewedMaps.length === 0}>
                <option value="">Select map</option>
                {reviewedMaps.map((reviewedMap) => (
                  <option key={reviewedMap.map_id} value={reviewedMap.map_id}>
                    {reviewedMap.map_id} / {reviewedMap.graph_version ?? "unknown graph"}
                  </option>
                ))}
              </select>
            </label>

            <div className="episode-derived-grid">
              <EpisodeMeta label="Graph Version" value={derivedGraphVersion || "Not selected"} />
              <EpisodeMeta label="Hidden Map ID" value={selectedMapId || "Not selected"} />
              <EpisodeMeta label="Interaction Rule" value={RUNTIME_INTERACTION_RULE} />
              <EpisodeMeta label="Scoring Profile" value={RUNTIME_SCORING_PROFILE} />
            </div>

            <label>
              Episode ID
              <input value={episodeId} onChange={(event) => setEpisodeId(event.target.value)} placeholder="episode_classical_ml_001" pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,127}" disabled={busy !== null} required />
            </label>
            <label>
              Max Turns
              <input type="number" min={1} value={maxTurns} onChange={(event) => setMaxTurns(Math.max(1, Number(event.target.value) || 1))} disabled={busy !== null} />
            </label>

            <div className="episode-configuration-block">
              <div>
                <p className="eyebrow">Immutable Execution Configuration</p>
                <p>Changing any option requires a new Episode ID.</p>
              </div>
              <label>
                Tested agent provider
                <select value={testedAgentProvider} onChange={(event) => changeTestedAgentProvider(event.target.value as TestedAgentClientProvider)} disabled={busy !== null}>
                  {catalog?.providers.map((provider) => (
                    <option key={provider.provider} value={provider.provider} disabled={!provider.available}>
                      {provider.provider}{provider.available ? "" : " (unavailable)"}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Tested agent model
                <select value={testedAgentModel} onChange={(event) => setTestedAgentModel(event.target.value)} disabled={busy !== null || !testedProviderOption?.available}>
                  {testedProviderOption?.models.map((model) => <option key={model} value={model}>{model}</option>)}
                </select>
              </label>
              <label>
                Simulator provider
                <select value={simulatorProvider} onChange={(event) => changeSimulatorProvider(event.target.value as SimulatorClientProvider)} disabled={busy !== null}>
                  {catalog?.providers.map((provider) => (
                    <option key={provider.provider} value={provider.provider} disabled={!provider.available}>
                      {provider.provider}{provider.available ? "" : " (unavailable)"}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Simulator model
                <select value={simulatorModel} onChange={(event) => setSimulatorModel(event.target.value)} disabled={busy !== null || !simulatorProviderOption?.available}>
                  {simulatorProviderOption?.models.map((model) => <option key={model} value={model}>{model}</option>)}
                </select>
              </label>
              <label>
                Tested agent temperature
                <select value={temperature} onChange={(event) => setTemperature(Number(event.target.value))} disabled={busy !== null}>
                  {catalog?.tested_agent_temperature_options.map((value) => <option key={value} value={value}>{value}</option>)}
                </select>
              </label>
              <label>
                Max tool retries
                <select value={maxToolRetries} onChange={(event) => setMaxToolRetries(Number(event.target.value))} disabled={busy !== null}>
                  {catalog?.max_tool_retry_options.map((value) => <option key={value} value={value}>{value}</option>)}
                </select>
              </label>
            </div>

            <div className="episode-registration-actions">
              <button type="submit" disabled={busy !== null || !benchmarkDomain || !selectedMapId || !derivedGraphVersion || !executionOptionsAvailable}>
                Register Episode
              </button>
            </div>
          </form>

          <section className="episode-list-panel">
            <div className="map-runs-header">
              <div>
                <p className="eyebrow">Runtime Registry</p>
                <h2>Registered Episodes</h2>
              </div>
              <button type="button" className="secondary" onClick={() => void refreshEpisodes()} disabled={busy !== null}>Refresh</button>
            </div>
            {episodes.length === 0 ? <p className="empty">No runtime episodes are registered.</p> : (
              <div className="map-run-list">
                {episodes.map((episode) => (
                  <button type="button" key={episode.episode_id} className={episode.episode_id === selectedEpisodeId ? "list-row episode-row active" : "list-row episode-row"} onClick={() => void handleLoadEpisode(episode)}>
                    <strong>{episode.episode_id}</strong>
                    <span>{episode.benchmark_domain} / {episode.graph_version}</span>
                    <small>{episode.max_turns} turns / {episode.configuration_status === "configured" ? "queue ready" : "legacy"}</small>
                  </button>
                ))}
              </div>
            )}
          </section>
        </section>

        {episodeDetail ? <EpisodeDetailPanel detail={episodeDetail} /> : (
          <section className="episode-empty-panel">
            <p className="eyebrow">Episode Detail</p>
            <h2>Select an episode</h2>
            <p>Runtime details show immutable configuration, reviewed artifact binding, and the tested-agent-visible context preview.</p>
          </section>
        )}
      </div>
    </main>
  );
}

function EpisodeDetailPanel({ detail }: { detail: RuntimeEpisodeDetail }) {
  const preview = detail.tested_agent_visible_context_preview;
  const configuration = detail.manifest.execution_configuration;
  return (
    <section className="episode-detail-panel">
      <div className="episode-detail-header">
        <div>
          <p className="eyebrow">Evaluation Episode</p>
          <h2>{detail.manifest.episode_id}</h2>
          <p>{detail.manifest.benchmark_domain} / {detail.manifest.graph_version}</p>
        </div>
        <div className="map-review-actions">
          <span className="lifecycle-badge confirmed">Registered</span>
          <span className={configuration ? "warning-count" : "warning-count active"}>{configuration ? "Configured" : "Legacy"}</span>
        </div>
      </div>

      {detail.warnings.map((warning) => (
        <div key={warning.code} className="status error">{warning.message}</div>
      ))}

      <div className="episode-detail-grid">
        <EpisodeMeta label="Max Turns" value={String(detail.manifest.max_turns)} />
        <EpisodeMeta label="Hidden Map ID" value={detail.manifest.hidden_map_id} />
        <EpisodeMeta label="Interaction Rule" value={detail.manifest.interaction_rule} />
        <EpisodeMeta label="Scoring Profile" value={detail.manifest.scoring_profile} />
      </div>

      {configuration && (
        <section className="episode-preview-card">
          <div><p className="eyebrow">Execution Configuration</p><h3>{configuration.agent_kind}</h3></div>
          <div className="episode-detail-grid compact">
            <EpisodeMeta label="Tested Agent" value={`${configuration.tested_agent_client_provider} / ${configuration.tested_agent_model}`} />
            <EpisodeMeta label="Simulator" value={`${configuration.simulator_client_provider} / ${configuration.simulator_model}`} />
            <EpisodeMeta label="Temperature" value={String(configuration.tested_agent_temperature)} />
            <EpisodeMeta label="Tool Retries" value={String(configuration.max_tool_retries)} />
          </div>
        </section>
      )}

      <div className="episode-binding-grid">
        <section className="episode-preview-card">
          <div><p className="eyebrow">Reviewed Graph Binding</p><h3>{detail.reviewed_artifacts.graph.graph_id}</h3></div>
          <div className="episode-detail-grid compact">
            <EpisodeMeta label="Status" value={detail.reviewed_artifacts.graph.status} />
            <EpisodeMeta label="Version" value={detail.reviewed_artifacts.graph.version} />
            <EpisodeMeta label="Nodes" value={String(detail.reviewed_artifacts.graph.node_count)} />
            <EpisodeMeta label="Edges" value={String(detail.reviewed_artifacts.graph.edge_count)} />
          </div>
        </section>
        <section className="episode-preview-card">
          <div><p className="eyebrow">Reference Map Binding</p><h3>{detail.reviewed_artifacts.reference_map.kind}</h3></div>
          <div className="episode-detail-grid compact">
            <EpisodeMeta label="Status" value={detail.reviewed_artifacts.reference_map.status} />
            <EpisodeMeta label="Domain" value={detail.reviewed_artifacts.reference_map.benchmark_domain} />
            <EpisodeMeta label="Graph Version" value={detail.reviewed_artifacts.reference_map.graph_version} />
            <EpisodeMeta label="Covered Nodes" value={String(detail.reviewed_artifacts.reference_map.covered_node_count)} />
          </div>
        </section>
      </div>

      <section className="episode-preview-card episode-visible-context">
        <div><p className="eyebrow">Tested-Agent-Visible Context</p><h3>{preview.graph.nodes.length} nodes / {preview.graph.edges.length} edges</h3></div>
        <div className="episode-node-list">
          {preview.graph.nodes.slice(0, 8).map((node) => (
            <article key={node.id} className="episode-node-card">
              <strong>{node.name}</strong><span>{node.id}</span><p>{node.diagnostic_goal ?? node.definition ?? "No diagnostic goal."}</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

function EpisodeMeta({ label, value }: { label: string; value: string }) {
  return <div className="map-meta episode-meta"><span>{label}</span><strong>{value}</strong></div>;
}
