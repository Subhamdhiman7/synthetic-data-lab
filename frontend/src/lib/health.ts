import type { HealthResponse } from "../types/api";

export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8001";

export function resolveApiBaseUrl(value?: string): string {
  const configured = value?.trim();
  return (configured || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export function isHealthyResponse(value: unknown): value is HealthResponse {
  if (!value || typeof value !== "object") return false;
  const response = value as Partial<HealthResponse>;
  return response.status === "ok"
    && typeof response.api_version === "string"
    && response.api_version.length > 0
    && response.engine_available === true;
}
