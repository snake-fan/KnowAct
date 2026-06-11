import { requestJson } from "./authoring";

export type SimulatorClientProvider = "openai" | "deepseek";

export type DiagnosticQuestion = {
  question_id?: string | null;
  text: string;
};

export type VisibleSimulatorAnswer = {
  text: string;
};

export type VisibleObservationKind =
  | "answer"
  | "clarification"
  | "non_answer"
  | "safe_non_answer";

export type CoarseObservationMetadata = {
  kind: VisibleObservationKind;
};

export type VisibleDialogueTurn = {
  turn_id: string;
  question: DiagnosticQuestion;
  answer: VisibleSimulatorAnswer;
  observation: CoarseObservationMetadata;
};

export type VisibleDialogueContext = {
  turns: VisibleDialogueTurn[];
};

export type SimulatorTurnWarning = {
  code: "missing_profile_context" | "simulator_configuration";
  message: string;
};

export type SimulatorTurnResponse = {
  answer: VisibleSimulatorAnswer;
  observation: CoarseObservationMetadata;
  warnings: SimulatorTurnWarning[];
  debug_trace_id?: string | null;
  debug_trace_available?: boolean | null;
};

export type SimulatorTurnTestResponse = SimulatorTurnResponse & {
  grounded_node_ids: string[];
};

export async function answerSimulatorTurn(input: {
  benchmarkDomain: string;
  mapId: string;
  clientProvider: SimulatorClientProvider;
  question: DiagnosticQuestion;
  visibleDialogueContext?: VisibleDialogueContext | null;
  includeDebugTrace?: boolean;
}): Promise<SimulatorTurnResponse> {
  return requestJson<SimulatorTurnResponse>("/api/simulator/turn", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      benchmark_domain: input.benchmarkDomain,
      map_id: input.mapId,
      client_provider: input.clientProvider,
      question: input.question,
      visible_dialogue_context: input.visibleDialogueContext ?? null,
      turn_options: {
        include_debug_trace: input.includeDebugTrace ?? false
      }
    })
  });
}

export async function answerSimulatorTurnTest(input: {
  benchmarkDomain: string;
  mapId: string;
  clientProvider: SimulatorClientProvider;
  question: DiagnosticQuestion;
  visibleDialogueContext?: VisibleDialogueContext | null;
  includeDebugTrace?: boolean;
}): Promise<SimulatorTurnTestResponse> {
  return requestJson<SimulatorTurnTestResponse>("/api/simulator/turn-test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      benchmark_domain: input.benchmarkDomain,
      map_id: input.mapId,
      client_provider: input.clientProvider,
      question: input.question,
      visible_dialogue_context: input.visibleDialogueContext ?? null,
      turn_options: {
        include_debug_trace: input.includeDebugTrace ?? false
      }
    })
  });
}
