import {
  apiUrl,
  type SimulatorClientProvider,
  type SimulatorExperimentLanguage
} from "./config";

export type KnowledgeNode = {
  id: string;
  name: string;
  definition?: string | null;
  diagnostic_goal?: string | null;
  levels: Record<string, string>;
};

export type ReviewedGraphVersionSummary = {
  version: string;
  graph_id?: string | null;
  node_count?: number | null;
};

export type ReviewedGraphPayload = {
  benchmark_domain: string;
  authored_nodes: KnowledgeNode[];
};

export type BenchmarkDomainListResponse = {
  benchmark_domains: string[];
  domain_summaries: Record<string, string>;
};

export type CandidateProfileContext = {
  benchmark_domain: string;
  summary: string;
  background: string[];
  prior_experience: string[];
  goals: string[];
  preferences: string[];
};

export type ProfileContextCandidateResponse = {
  run_id: string;
  candidate_profile_context: CandidateProfileContext;
};

export type ConfirmedProfileContext = CandidateProfileContext & {
  user_id: string;
};

export type ProfileContextConfirmationResponse = {
  run_id: string;
  profile_context: ConfirmedProfileContext;
};

export type MasteryLevel = "L0" | "L1" | "L2" | "L3" | "L4" | "L5";

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
};

export type CandidateMapResponse = {
  run_id: string;
  candidate_map: KnowledgeMap;
};

export type MapManifest = {
  map_id: string;
  user_id: string;
  benchmark_domain: string;
  graph_version: string;
  promoted_from_candidate_run: string;
};

export type BilingualQuestionText = {
  en: string;
  zh_cn: string;
};

export type SimulatorExperimentQuestionBankSummary = {
  bank_id: string;
  version: string;
  benchmark_domain: string;
  title: BilingualQuestionText;
  question_count: number;
  languages: SimulatorExperimentLanguage[];
};

export type ParticipantMapStateRevision = {
  node_id: string;
  mastery_level: MasteryLevel;
  misconceptions: string[];
  unknowns: string[];
  review_note?: string | null;
};

export type ParticipantMapConfirmationResult = {
  benchmark_domain: string;
  candidate_map_run_id: string;
  map: KnowledgeMap;
  map_manifest: MapManifest;
};

export type SimulatorSelfEvaluation = {
  content_similarity: number;
  knowledge_level_similarity: number;
  boundary_similarity: number;
  style_similarity: number;
  overall_representativeness: number;
  replacement_judgement:
    | "direct_use"
    | "minor_bias"
    | "major_revision"
    | "not_representative";
  comment?: string | null;
};

export type SimulatorExperimentQuestionResult = {
  question_id: string;
  target_concept: string;
  question_type: string;
  prompts: BilingualQuestionText;
  selected_prompt: string;
  reviewed_target_node_ids: string[];
  human_answer?: string | null;
  simulator_answer?: string | null;
  observation_kind?: string | null;
  warning_codes: string[];
  debug_trace_id?: string | null;
  simulator_error?: string | null;
  self_evaluation?: SimulatorSelfEvaluation | null;
  blind_review_status: "pending";
};

export type SimulatorExperimentSession = {
  schema_version: "knowact.simulator_test_session.v1";
  session_id: string;
  participant_code: string;
  status: "in_progress" | "completed";
  benchmark_domain: string;
  graph_version: string;
  profile_context_user_id: string;
  map_id: string;
  question_bank_id: string;
  question_bank_version: string;
  language: SimulatorExperimentLanguage;
  simulator_client_provider: SimulatorClientProvider;
  sampling_seed: number;
  question_count: 20;
  questions: SimulatorExperimentQuestionResult[];
  created_at: string;
  completed_at?: string | null;
};

export class ApiRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

export async function readBenchmarkDomains(): Promise<BenchmarkDomainListResponse> {
  return requestJson<BenchmarkDomainListResponse>(
    "/api/authoring/benchmark-domains"
  );
}

export async function listReviewedGraphs(
  benchmarkDomain: string
): Promise<ReviewedGraphVersionSummary[]> {
  const payload = await requestJson<{
    benchmark_domain: string;
    graphs: ReviewedGraphVersionSummary[];
  }>(`/api/authoring/graphs/${encodeURIComponent(benchmarkDomain)}`);
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

export async function generateProfileContextCandidate(input: {
  benchmarkDomain: string;
  roughDescription: string;
  clientProvider: SimulatorClientProvider;
}): Promise<ProfileContextCandidateResponse> {
  return requestJson<ProfileContextCandidateResponse>(
    "/api/authoring/profile-context-candidates",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        benchmark_domain: input.benchmarkDomain,
        rough_description: input.roughDescription,
        client_provider: input.clientProvider
      })
    }
  );
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
  clientProvider: SimulatorClientProvider;
}): Promise<CandidateMapResponse> {
  return requestJson<CandidateMapResponse>("/api/authoring/map-candidates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      benchmark_domain: input.benchmarkDomain,
      graph_version: input.graphVersion,
      user_id: input.userId,
      run_id: null,
      client_provider: input.clientProvider,
      evidence_batch_size: 5,
      sampling_temperature: 0.7
    })
  });
}

export async function listSimulatorExperimentQuestionBanks(): Promise<
  SimulatorExperimentQuestionBankSummary[]
> {
  const payload = await requestJson<{
    question_banks: SimulatorExperimentQuestionBankSummary[];
  }>("/api/experiments/simulator-tests/question-banks");
  return payload.question_banks;
}

export async function confirmParticipantMap(input: {
  benchmarkDomain: string;
  candidateMapRunId: string;
  mapId: string;
  revisions: ParticipantMapStateRevision[];
}): Promise<ParticipantMapConfirmationResult> {
  return requestJson<ParticipantMapConfirmationResult>(
    `/api/experiments/simulator-tests/participant-maps/${encodeURIComponent(input.benchmarkDomain)}/${encodeURIComponent(input.candidateMapRunId)}/confirmation`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        map_id: input.mapId,
        revisions: input.revisions
      })
    }
  );
}

export async function readSimulatorExperimentSession(
  sessionId: string
): Promise<SimulatorExperimentSession> {
  return requestJson<SimulatorExperimentSession>(
    `/api/experiments/simulator-tests/sessions/${encodeURIComponent(sessionId)}`
  );
}

export async function createSimulatorExperimentSession(input: {
  participantCode: string;
  benchmarkDomain: string;
  mapId: string;
  questionBankId: string;
  language: SimulatorExperimentLanguage;
  simulatorClientProvider: SimulatorClientProvider;
}): Promise<SimulatorExperimentSession> {
  return requestJson<SimulatorExperimentSession>(
    "/api/experiments/simulator-tests/sessions",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        participant_code: input.participantCode,
        benchmark_domain: input.benchmarkDomain,
        map_id: input.mapId,
        question_bank_id: input.questionBankId,
        language: input.language,
        simulator_client_provider: input.simulatorClientProvider,
        sampling_seed: null,
        session_id: null
      })
    }
  );
}

export async function submitSimulatorExperimentHumanAnswer(input: {
  sessionId: string;
  questionId: string;
  humanAnswer: string;
}): Promise<SimulatorExperimentSession> {
  return requestJson<SimulatorExperimentSession>(
    `/api/experiments/simulator-tests/sessions/${encodeURIComponent(input.sessionId)}/questions/${encodeURIComponent(input.questionId)}/answer`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ human_answer: input.humanAnswer })
    }
  );
}

export async function saveSimulatorExperimentSelfEvaluation(input: {
  sessionId: string;
  questionId: string;
  evaluation: SimulatorSelfEvaluation;
}): Promise<SimulatorExperimentSession> {
  return requestJson<SimulatorExperimentSession>(
    `/api/experiments/simulator-tests/sessions/${encodeURIComponent(input.sessionId)}/questions/${encodeURIComponent(input.questionId)}/self-evaluation`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input.evaluation)
    }
  );
}

export async function completeSimulatorExperimentSession(
  sessionId: string
): Promise<SimulatorExperimentSession> {
  return requestJson<SimulatorExperimentSession>(
    `/api/experiments/simulator-tests/sessions/${encodeURIComponent(sessionId)}/completion`,
    { method: "POST" }
  );
}

async function requestJson<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(apiUrl(path), init);
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
