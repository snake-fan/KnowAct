export type SourceLocator = {
  source_id: string;
  locator: string;
  note?: string | null;
};

export type KnowledgeNode = {
  id: string;
  name: string;
  type: string;
  definition?: string | null;
  source_locators: SourceLocator[];
  diagnostic_goal?: string | null;
  levels: Record<string, string>;
  diagnostic_signals: string[];
  simulator_behavior?: string | null;
};

export type KnowledgeEdge = {
  id: string;
  source: string;
  target: string;
  type: "part_of" | "prerequisite_for" | "supports" | "contrasts_with";
  rationale: string;
  weight: number;
  curation_confidence: number;
};

export type SourceMaterialRecord = {
  source_id: string;
  title: string;
  storage_path: string;
  storage_uri: string;
  filename: string;
  size_bytes: number;
  uploaded_at: string;
  citation?: string | null;
};

export type GraphCandidateArtifactPaths = {
  output_dir_uri: string;
  candidate_nodes_uri: string;
  candidate_edges_uri: string;
  workflow_log_uri: string;
};

export type CandidateGraphPayload = {
  benchmark_domain: string;
  run_id: string;
  candidate_nodes: KnowledgeNode[];
  candidate_edges: KnowledgeEdge[];
  artifact_paths: GraphCandidateArtifactPaths;
};

export type GraphManifest = {
  graph_id: string;
  domain: string;
  version: string;
  promoted_from_candidate_run: string;
  nodes_file: string;
  edges_file: string;
  source: {
    source_id: string;
    title: string;
    citation?: string | null;
  }[];
};

export type ReviewedGraphArtifactPaths = {
  output_dir_uri: string;
  graph_manifest_uri: string;
  authored_nodes_uri: string;
  authored_edges_uri: string;
};

export type CandidateGraphPromotionResponse = {
  benchmark_domain: string;
  run_id: string;
  graph_manifest: GraphManifest;
  artifact_paths: ReviewedGraphArtifactPaths;
};

export type ReviewedGraphVersionSummary = {
  version: string;
  graph_id?: string | null;
  node_count?: number | null;
  edge_count?: number | null;
};

export type ReviewedGraphPayload = {
  benchmark_domain: string;
  graph_manifest: GraphManifest;
  authored_nodes: KnowledgeNode[];
  authored_edges: KnowledgeEdge[];
  artifact_paths: ReviewedGraphArtifactPaths;
};

export type GraphCandidateResponse = {
  workflow: string;
  material: {
    storage_uri: string;
    filename: string;
    size_bytes: number;
    markdown_storage_uri: string;
    markdown_filename: string;
    markdown_size_bytes: number;
    markdown_cache_status: string;
    source_id: string;
    title: string;
  };
  run_log_summary: {
    run_id: string;
    workflow_name: string;
    status: string;
    output_counts: Record<string, number>;
  };
  source_grounded_node_skeletons: unknown[];
  candidate_nodes: KnowledgeNode[];
  candidate_edges: KnowledgeEdge[];
  artifact_paths: GraphCandidateArtifactPaths | null;
};

export type BenchmarkDomainListResponse = {
  benchmark_domains: string[];
};

export type CandidateProfileContext = {
  benchmark_domain: string;
  summary: string;
  background: string[];
  prior_experience: string[];
  goals: string[];
  preferences: string[];
};

export type CandidateProfileContextArtifactPaths = {
  output_dir_uri: string;
  candidate_profile_context_uri: string;
  workflow_log_uri: string;
  model_raw_output_uri: string;
  parser_output_uri: string;
};

export type ProfileContextCandidateResponse = {
  run_id: string;
  candidate_profile_context: CandidateProfileContext;
  artifact_paths: CandidateProfileContextArtifactPaths;
};

export type ConfirmedProfileContext = CandidateProfileContext & {
  user_id: string;
};

export type ConfirmedProfileContextArtifactPaths = {
  output_dir_uri: string;
  profile_context_uri: string;
};

export type ProfileContextConfirmationResponse = {
  run_id: string;
  profile_context: ConfirmedProfileContext;
  artifact_paths: ConfirmedProfileContextArtifactPaths;
};

export type ConfirmedProfileContextSummary = {
  user_id: string;
  summary?: string | null;
};

export type MasteryLevel = "L0" | "L1" | "L2" | "L3" | "L4" | "L5";

export type EvidenceRecord = {
  id: string;
  node_id: string;
  evidence_type: "ground_truth_profile" | "interaction_observation";
  evidence_kind:
    | "prior_answer"
    | "worked_example"
    | "self_report"
    | "misconception_trace"
    | "background_fact";
  visibility: "simulator_only" | "tested_agent";
  signal: string;
  turn_id?: string | null;
};

export type UserKnowledgeState = {
  node_id: string;
  mastery_level: MasteryLevel;
  evidence_refs: string[];
  misconceptions: string[];
  unknowns: string[];
};

export type KnowledgeMap = {
  user_id: string;
  kind: "candidate" | "ground_truth" | "reconstructed";
  states: UserKnowledgeState[];
  evidence: EvidenceRecord[];
};

export type CandidateMapEvidenceBatchArtifactPaths = {
  batch_name: string;
  model_raw_output_uri: string;
  parser_output_uri: string;
};

export type CandidateMapArtifactPaths = {
  output_dir_uri: string;
  candidate_map_uri: string;
  consistency_warnings_uri: string;
  workflow_log_uri: string;
  state_outline_uri: string;
  ground_truth_evidence_uri: string;
  outline_model_raw_output_uri: string;
  outline_parser_output_uri: string;
  evidence_model_raw_output_uri: string;
  evidence_parser_output_uri: string;
  evidence_batch_artifacts: CandidateMapEvidenceBatchArtifactPaths[];
};

export type CandidateMapResponse = {
  run_id: string;
  candidate_map: KnowledgeMap;
  artifact_paths: CandidateMapArtifactPaths;
};

export type CandidateMapRunSummary = {
  run_id: string;
  status: string;
  graph_version?: string | null;
  user_id?: string | null;
  has_candidate_map: boolean;
  warning_count?: number | null;
  error?: string | null;
};

export type MapEdgeConsistencyWarning = {
  edge_id: string;
  source_node_id: string;
  source_mastery_level: MasteryLevel;
  target_node_id: string;
  target_mastery_level: MasteryLevel;
  rule: "prerequisite_target_mastery_exceeds_source_by_at_least_two_levels";
};

export type MapEdgeConsistencyWarningListResponse = {
  warnings: MapEdgeConsistencyWarning[];
};

export type MapManifest = {
  map_id: string;
  user_id: string;
  benchmark_domain: string;
  graph_version: string;
  promoted_from_candidate_run: string;
};

export type ReviewedMapArtifactPaths = {
  output_dir_uri: string;
  map_uri: string;
  map_manifest_uri: string;
};

export type CandidateMapPromotionResponse = {
  benchmark_domain: string;
  run_id: string;
  map: KnowledgeMap;
  map_manifest: MapManifest;
  artifact_paths: ReviewedMapArtifactPaths;
};

export type ReviewedMapSummary = {
  map_id: string;
  user_id?: string | null;
  graph_version?: string | null;
  state_count?: number | null;
  evidence_count?: number | null;
};

export type ReviewedMapPayload = {
  benchmark_domain: string;
  map: KnowledgeMap;
  map_manifest: MapManifest;
  artifact_paths: ReviewedMapArtifactPaths;
};

export class ApiRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

export async function listBenchmarkDomains(): Promise<string[]> {
  const payload = await requestJson<BenchmarkDomainListResponse>("/api/authoring/benchmark-domains");
  return payload.benchmark_domains;
}

export async function listSourceMaterials(): Promise<SourceMaterialRecord[]> {
  const payload = await requestJson<{ source_materials: SourceMaterialRecord[] }>("/api/authoring/source-materials");
  return payload.source_materials;
}

export async function listReviewedGraphs(benchmarkDomain: string): Promise<ReviewedGraphVersionSummary[]> {
  const payload = await requestJson<{ benchmark_domain: string; graphs: ReviewedGraphVersionSummary[] }>(
    `/api/authoring/graphs/${encodeURIComponent(benchmarkDomain)}`
  );
  return payload.graphs;
}

export async function readReviewedGraph(
  benchmarkDomain: string,
  graphVersion: string
): Promise<ReviewedGraphPayload> {
  return requestJson<ReviewedGraphPayload>(
    `/api/authoring/graphs/${encodeURIComponent(benchmarkDomain)}/${encodeURIComponent(graphVersion)}`
  );
}

export async function listConfirmedProfileContexts(
  benchmarkDomain: string
): Promise<ConfirmedProfileContextSummary[]> {
  const payload = await requestJson<{ benchmark_domain: string; users: ConfirmedProfileContextSummary[] }>(
    `/api/authoring/users/${encodeURIComponent(benchmarkDomain)}`
  );
  return payload.users;
}

export async function readConfirmedProfileContext(
  benchmarkDomain: string,
  userId: string
): Promise<ProfileContextConfirmationResponse> {
  const payload = await requestJson<{
    benchmark_domain: string;
    user_id: string;
    profile_context: ConfirmedProfileContext;
    artifact_paths: ConfirmedProfileContextArtifactPaths;
  }>(`/api/authoring/users/${encodeURIComponent(benchmarkDomain)}/${encodeURIComponent(userId)}`);
  return {
    run_id: "",
    profile_context: payload.profile_context,
    artifact_paths: payload.artifact_paths
  };
}

export async function listReviewedMaps(
  benchmarkDomain: string
): Promise<ReviewedMapSummary[]> {
  const payload = await requestJson<{ benchmark_domain: string; maps: ReviewedMapSummary[] }>(
    `/api/authoring/maps/${encodeURIComponent(benchmarkDomain)}`
  );
  return payload.maps;
}

export async function readReviewedMap(
  benchmarkDomain: string,
  mapId: string
): Promise<ReviewedMapPayload> {
  return requestJson<ReviewedMapPayload>(
    `/api/authoring/maps/${encodeURIComponent(benchmarkDomain)}/${encodeURIComponent(mapId)}`
  );
}

export async function uploadSourceMaterial(input: {
  file: File;
  sourceId: string;
  title: string;
  citation?: string;
}): Promise<SourceMaterialRecord> {
  const form = new FormData();
  form.append("file", input.file);
  form.append("source_id", input.sourceId);
  form.append("title", input.title);
  if (input.citation?.trim()) {
    form.append("citation", input.citation.trim());
  }
  return requestJson<SourceMaterialRecord>("/api/authoring/source-materials", {
    method: "POST",
    body: form
  });
}

export async function generateCandidateGraph(input: {
  sourceId: string;
  benchmarkDomain: string;
  runId?: string;
  clientProvider: "openai" | "deepseek";
}): Promise<GraphCandidateResponse> {
  return requestJson<GraphCandidateResponse>("/api/authoring/graph-candidates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_id: input.sourceId,
      benchmark_domain: input.benchmarkDomain,
      run_id: input.runId || null,
      client_provider: input.clientProvider,
      write_artifacts: true
    })
  });
}

export type CandidateGraphRunSummary = {
  run_id: string;
};

export type CandidateGraphRunListResponse = {
  benchmark_domain: string;
  runs: CandidateGraphRunSummary[];
};

export async function listCandidateGraphRuns(
  benchmarkDomain: string
): Promise<CandidateGraphRunListResponse> {
  return requestJson<CandidateGraphRunListResponse>(
    `/api/authoring/candidate-graphs/${encodeURIComponent(benchmarkDomain)}`
  );
}

export async function readCandidateGraph(
  benchmarkDomain: string,
  runId: string
): Promise<CandidateGraphPayload> {
  return requestJson<CandidateGraphPayload>(
    `/api/authoring/candidate-graphs/${encodeURIComponent(benchmarkDomain)}/${encodeURIComponent(runId)}`
  );
}

export async function saveCandidateGraph(
  graph: CandidateGraphPayload
): Promise<CandidateGraphPayload> {
  return requestJson<CandidateGraphPayload>(
    `/api/authoring/candidate-graphs/${encodeURIComponent(graph.benchmark_domain)}/${encodeURIComponent(graph.run_id)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        candidate_nodes: graph.candidate_nodes,
        candidate_edges: graph.candidate_edges
      })
    }
  );
}

export async function promoteCandidateGraph(
  graph: CandidateGraphPayload,
  version: string
): Promise<CandidateGraphPromotionResponse> {
  return requestJson<CandidateGraphPromotionResponse>(
    `/api/authoring/candidate-graphs/${encodeURIComponent(graph.benchmark_domain)}/${encodeURIComponent(graph.run_id)}/promotion`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version })
    }
  );
}

export async function generateProfileContextCandidate(input: {
  benchmarkDomain: string;
  roughDescription: string;
  domainSummary?: string;
  clientProvider: "openai" | "deepseek";
}): Promise<ProfileContextCandidateResponse> {
  return requestJson<ProfileContextCandidateResponse>("/api/authoring/profile-context-candidates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      benchmark_domain: input.benchmarkDomain,
      rough_description: input.roughDescription,
      domain_summary: input.domainSummary?.trim() || null,
      client_provider: input.clientProvider
    })
  });
}

export async function saveProfileContextCandidate(
  runId: string,
  profileContext: CandidateProfileContext
): Promise<ProfileContextCandidateResponse> {
  return requestJson<ProfileContextCandidateResponse>(
    `/api/authoring/candidate-profile-contexts/${encodeURIComponent(profileContext.benchmark_domain)}/${encodeURIComponent(runId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        summary: profileContext.summary,
        background: profileContext.background,
        prior_experience: profileContext.prior_experience,
        goals: profileContext.goals,
        preferences: profileContext.preferences
      })
    }
  );
}

export async function confirmProfileContextCandidate(
  runId: string,
  benchmarkDomain: string,
  userId: string
): Promise<ProfileContextConfirmationResponse> {
  return requestJson<ProfileContextConfirmationResponse>(
    `/api/authoring/candidate-profile-contexts/${encodeURIComponent(benchmarkDomain)}/${encodeURIComponent(runId)}/confirmation`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId })
    }
  );
}

export async function generateCandidateMap(input: {
  benchmarkDomain: string;
  graphVersion: string;
  userId: string;
  runId?: string;
  clientProvider: "openai" | "deepseek";
  evidenceBatchSize?: number;
  samplingTemperature?: number;
}): Promise<CandidateMapResponse> {
  return requestJson<CandidateMapResponse>("/api/authoring/map-candidates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      benchmark_domain: input.benchmarkDomain,
      graph_version: input.graphVersion,
      user_id: input.userId,
      run_id: input.runId?.trim() || null,
      client_provider: input.clientProvider,
      evidence_batch_size: input.evidenceBatchSize ?? 5,
      sampling_temperature: input.samplingTemperature ?? 0.7
    })
  });
}

export async function listCandidateMapRuns(
  benchmarkDomain: string
): Promise<CandidateMapRunSummary[]> {
  const payload = await requestJson<{ benchmark_domain: string; runs: CandidateMapRunSummary[] }>(
    `/api/authoring/candidate-maps/${encodeURIComponent(benchmarkDomain)}`
  );
  return payload.runs;
}

export async function readCandidateMap(
  benchmarkDomain: string,
  runId: string
): Promise<CandidateMapResponse> {
  return requestJson<CandidateMapResponse>(
    `/api/authoring/candidate-maps/${encodeURIComponent(benchmarkDomain)}/${encodeURIComponent(runId)}`
  );
}

export async function readCandidateMapWarnings(
  benchmarkDomain: string,
  runId: string
): Promise<MapEdgeConsistencyWarning[]> {
  const payload = await requestJson<MapEdgeConsistencyWarningListResponse>(
    `/api/authoring/candidate-maps/${encodeURIComponent(benchmarkDomain)}/${encodeURIComponent(runId)}/warnings`
  );
  return payload.warnings;
}

export async function promoteCandidateMap(input: {
  benchmarkDomain: string;
  runId: string;
  mapId: string;
}): Promise<CandidateMapPromotionResponse> {
  return requestJson<CandidateMapPromotionResponse>(
    `/api/authoring/candidate-maps/${encodeURIComponent(input.benchmarkDomain)}/${encodeURIComponent(input.runId)}/promotion`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ map_id: input.mapId })
    }
  );
}

export async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const detail = await readError(response);
    throw new ApiRequestError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

async function readError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (payload.detail?.message) {
      return payload.detail.message;
    }
    return JSON.stringify(payload.detail ?? payload);
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}
