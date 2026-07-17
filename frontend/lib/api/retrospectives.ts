import type {
  PaginatedResponse,
  RetrospectiveResponse,
  RetroCreate,
  RetroUpdate,
  RetroDraft,
  AIRetroDraftRequest,
  AIRetroDraft,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== Retrospectives =====
export const retrospectivesApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    request<PaginatedResponse<RetrospectiveResponse>>(
      `/api/retrospectives${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  get: (id: string) => request<RetrospectiveResponse>(`/api/retrospectives/${id}`),
  create: (body: RetroCreate) =>
    request<RetrospectiveResponse>("/api/retrospectives", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: RetroUpdate) =>
    request<RetrospectiveResponse>(`/api/retrospectives/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    request<void>(`/api/retrospectives/${id}`, { method: "DELETE" }),
  draft: (period_start: string, period_end: string) =>
    request<RetroDraft>(
      `/api/retrospectives/draft${buildQuery({ period_start, period_end })}`,
    ),
  aiDraft: (body: AIRetroDraftRequest) =>
    request<AIRetroDraft>("/api/retrospectives/ai-draft", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};