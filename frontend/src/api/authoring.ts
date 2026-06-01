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

export type ApiError = {
  message: string;
};

export class ApiRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

export async function listSourceMaterials(): Promise<SourceMaterialRecord[]> {
  const payload = await requestJson<{ source_materials: SourceMaterialRecord[] }>("/api/authoring/source-materials");
  return payload.source_materials;
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

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
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
