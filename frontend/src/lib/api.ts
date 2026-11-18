import axios from "axios";
import type {
  GenerateRequest,
  GenerationMetadata,
  HealthResponse,
  HistoryResponse,
  PlanListResponse,
  PlanResponse,
  PreviewResponse,
  ReportResponse,
  AnalysisResponse,
} from "../types/api";
import { isHealthyResponse, resolveApiBaseUrl } from "./health";

export const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_URL);
export const HEALTH_CHECK_TIMEOUT_MS = 5_000;

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") return "The request timed out. Please try again.";
    if (!error.response) return "The backend is unavailable. Start the FastAPI server and retry.";
  }
  return "Something went wrong. Please try again.";
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/api/health", { timeout: HEALTH_CHECK_TIMEOUT_MS });
  if (!isHealthyResponse(data)) {
    throw new Error("The backend returned an unhealthy response.");
  }
  return data;
}

export async function getHistory(limit = 20, offset = 0): Promise<HistoryResponse> {
  const { data } = await api.get<HistoryResponse>("/api/datasets/history", {
    params: { limit, offset },
  });
  return data;
}

export async function generateDataset(payload: GenerateRequest): Promise<GenerationMetadata> {
  const { data } = await api.post<{ status: string; generation: GenerationMetadata }>(
    "/api/datasets/generate",
    payload,
  );
  return data.generation;
}

export async function getPreview(generationId: string): Promise<PreviewResponse> {
  const { data } = await api.get<PreviewResponse>(
    `/api/datasets/${generationId}/preview`,
  );
  return data;
}

export async function getDatasetDetails(generationId: string): Promise<GenerationMetadata> {
  const { data } = await api.get<GenerationMetadata>(`/api/datasets/${generationId}`);
  return data;
}

export async function getReport(generationId: string): Promise<ReportResponse> {
  const { data } = await api.get<ReportResponse>(
    `/api/datasets/${generationId}/report`,
  );
  return data;
}

export async function getAnalysis(generationId: string): Promise<AnalysisResponse> {
  const { data } = await api.get<AnalysisResponse>(`/api/datasets/${generationId}/analysis`);
  return data;
}

export function getAnalysisReportUrl(generationId: string): string {
  return `${API_BASE_URL}/api/datasets/${generationId}/analysis/report`;
}

export async function getPlans(): Promise<PlanListResponse> {
  const { data } = await api.get<PlanListResponse>("/api/plans");
  return data;
}

export async function getPlan(planId: string): Promise<PlanResponse> {
  const { data } = await api.get<PlanResponse>(`/api/plans/${planId}`);
  return data;
}

export function getDownloadUrl(generationId: string): string {
  return `${API_BASE_URL}/api/datasets/${generationId}/download`;
}
