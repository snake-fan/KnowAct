export type SimulatorClientProvider = "openai" | "deepseek";
export type SimulatorExperimentLanguage = "en" | "zh-CN";

function envValue(name: keyof ImportMetaEnv): string {
  return String(import.meta.env[name] ?? "").trim();
}

function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

function configuredProvider(value: string): SimulatorClientProvider {
  return value === "deepseek" ? "deepseek" : "openai";
}

function configuredLanguage(value: string): SimulatorExperimentLanguage {
  return value === "en" ? "en" : "zh-CN";
}

export const studyConfig = Object.freeze({
  apiBaseUrl: normalizeApiBaseUrl(envValue("VITE_API_BASE_URL")),
  studyId: envValue("VITE_STUDY_ID") || "simulator-personal-fidelity-v1",
  studyTitle: envValue("VITE_STUDY_TITLE") || "Simulator 个人一致性实验",
  simulatorProvider: configuredProvider(
    envValue("VITE_SIMULATOR_PROVIDER")
  ),
  defaultLanguage: configuredLanguage(envValue("VITE_DEFAULT_LANGUAGE"))
});

export function apiUrl(path: string): string {
  return `${studyConfig.apiBaseUrl}${path}`;
}

export function sessionStorageKey(): string {
  return `knowact:${studyConfig.studyId}:session-id`;
}
