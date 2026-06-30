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

export type RuntimeEpisodeAgentKind =
  | "fixed_question_baseline"
  | "random_question_baseline"
  | "simple_llm_agent";

export type RuntimeEpisodeRunRequest = {
  run_id?: string | null;
  agent_kind: RuntimeEpisodeAgentKind;
  client_provider?: SimulatorClientProvider | null;
};

export type RuntimeEpisodeRunStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed";

export type RuntimeEpisodeRunSummary = {
  run_id: string;
  episode_id: string;
  status: RuntimeEpisodeRunStatus;
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
}): Promise<RuntimeEpisodeRunSummary> {
  return requestJson<RuntimeEpisodeRunSummary>(
    `/api/runtime/episodes/${encodeURIComponent(input.episodeId)}/runs`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input.request)
    }
  );
}
