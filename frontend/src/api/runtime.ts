import type { KnowledgeEdge, KnowledgeNode } from "./authoring";
import { requestJson } from "./authoring";
import type { SimulatorClientProvider, VisibleDialogueContext } from "./simulator";

export const RUNTIME_INTERACTION_RULE = "single_diagnostic_question_per_turn";
export const RUNTIME_SCORING_PROFILE = "squared_mastery_distance_v1";

export type RuntimeInteractionRule = typeof RUNTIME_INTERACTION_RULE;
export type RuntimeScoringProfile = typeof RUNTIME_SCORING_PROFILE;

export type RuntimeEpisodeSummary = {
  episode_id: string;
  benchmark_domain: string;
  graph_version: string;
  max_turns: number;
  interaction_rule: RuntimeInteractionRule;
  scoring_profile: RuntimeScoringProfile;
};

export type RuntimeEpisodeManagementManifestSummary = RuntimeEpisodeSummary & {
  hidden_map_id: string;
};

export type RuntimeReviewedGraphBindingSummary = {
  status: "loaded";
  graph_id: string;
  benchmark_domain: string;
  version: string;
  node_count: number;
  edge_count: number;
};

export type RuntimeReferenceMapBindingSummary = {
  status: "loaded";
  map_id: string;
  user_id: string;
  benchmark_domain: string;
  graph_version: string;
  kind: "ground_truth";
  covered_node_count: number;
  profile_context_status: "loaded" | "missing_optional";
};

export type RuntimeReviewedArtifactBindingSummary = {
  graph: RuntimeReviewedGraphBindingSummary;
  reference_map: RuntimeReferenceMapBindingSummary;
};

export type RuntimeEpisodeWarningSummary = {
  code: string;
  message: string;
};

export type TestedAgentVisibleEpisodeContext = {
  episode_id: string;
  benchmark_domain: string;
  graph_version: string;
  max_turns: number;
  interaction_rule: RuntimeInteractionRule;
  scoring_profile: RuntimeScoringProfile;
  graph: {
    nodes: KnowledgeNode[];
    edges: KnowledgeEdge[];
  };
  visible_dialogue_context: VisibleDialogueContext;
};

export type RuntimeEpisodeDetail = {
  manifest: RuntimeEpisodeManagementManifestSummary;
  reviewed_artifacts: RuntimeReviewedArtifactBindingSummary;
  warnings: RuntimeEpisodeWarningSummary[];
  tested_agent_visible_context_preview: TestedAgentVisibleEpisodeContext;
};

export type RuntimeEpisodeRegistrationRequest = {
  episode_id: string;
  benchmark_domain: string;
  graph_version: string;
  hidden_map_id: string;
  max_turns: number;
};

export type TestedAgentClientProvider = "openai" | "deepseek";

export type RuntimeEpisodeAgentKind = "simple_llm_agent";

export type RuntimeEpisodeRunRequest = {
  run_id?: string | null;
  agent_kind: RuntimeEpisodeAgentKind;
  tested_agent_client_provider?: TestedAgentClientProvider | null;
  simulator_client_provider?: SimulatorClientProvider | null;
  tested_agent_temperature?: number | null;
  max_tool_retries?: number | null;
};

export type RuntimeNodeComparison = {
  node_id: string;
  ground_truth_mastery: string;
  predicted_mastery: string | null;
  mastery_distance: number;
  signed_mastery_error: number | null;
  missing_prediction: boolean;
  unsupported_inference: boolean;
  exact_match: boolean;
};

export type RuntimeEpisodeScoreReport = {
  episode_id: string;
  scoring_profile: RuntimeScoringProfile;
  per_node: RuntimeNodeComparison[];
  episode_mastery_distance: number;
  missing_prediction_rate: number;
  unsupported_inference_rate: number;
  exact_match_rate: number;
};

export type RuntimeEpisodeRunArtifactsSummary = {
  run_dir: string;
  episode_manifest_snapshot: string;
  turns: string;
  transcript: string;
  working_map: string;
  agent_tool_trace: string;
  agent_output: string;
  scoring_report: string;
};

export type RuntimeEpisodeRunResponse = {
  run_id: string;
  episode_id: string;
  agent_kind: RuntimeEpisodeAgentKind;
  turn_count: number;
  forced_finalization: boolean;
  forced_finalization_fallback: boolean;
  artifacts: RuntimeEpisodeRunArtifactsSummary;
  scoring_report: RuntimeEpisodeScoreReport;
};

export async function listRuntimeEpisodes(): Promise<RuntimeEpisodeSummary[]> {
  return requestJson<RuntimeEpisodeSummary[]>("/api/runtime/episodes");
}

export async function readRuntimeEpisode(
  episodeId: string
): Promise<RuntimeEpisodeDetail> {
  return requestJson<RuntimeEpisodeDetail>(
    `/api/runtime/episodes/${encodeURIComponent(episodeId)}`
  );
}

export async function registerRuntimeEpisode(
  input: RuntimeEpisodeRegistrationRequest
): Promise<RuntimeEpisodeDetail> {
  return requestJson<RuntimeEpisodeDetail>("/api/runtime/episodes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
}

export async function startRuntimeEpisodeRun(input: {
  episodeId: string;
  request: RuntimeEpisodeRunRequest;
}): Promise<RuntimeEpisodeRunResponse> {
  return requestJson<RuntimeEpisodeRunResponse>(
    `/api/runtime/episodes/${encodeURIComponent(input.episodeId)}/runs`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input.request)
    }
  );
}

export async function readRuntimeRunTranscript(
  runId: string
): Promise<VisibleDialogueContext> {
  return requestJson<VisibleDialogueContext>(
    `/api/runtime/runs/${encodeURIComponent(runId)}/transcript`
  );
}
