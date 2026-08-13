import type {
  PaginatedResponse,
  DecisionResponse,
  DecisionCreate,
  DecisionUpdate,
  DecisionStats,
  DecisionAnalysisCreate,
  DecisionAnalysisResponse,
  PremortemAnalyzeRequest,
  RedTeamGenerateRequest,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== Decisions =====
export const decisionsApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    request<PaginatedResponse<DecisionResponse>>(
      `/api/decisions${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  get: (id: string) => request<DecisionResponse>(`/api/decisions/${id}`),
  create: (body: DecisionCreate) =>
    request<DecisionResponse>("/api/decisions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: DecisionUpdate) =>
    request<DecisionResponse>(`/api/decisions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    request<void>(`/api/decisions/${id}`, { method: "DELETE" }),
  stats: () => request<DecisionStats>("/api/decisions/stats"),
};

// ===== 护城河功能：决策日志与回溯 =====
export interface TimeCapsuleResponse {
  has_capsule: boolean;
  can_open: boolean;
  letter: string | null;
  sealed_at?: string;
  opens_on?: string | null;
  opened?: boolean;
  message?: string;
}

export const decisionJournalApi = {
  getPendingReviews: () =>
    request<DecisionResponse[]>("/api/decision-journal/pending-reviews"),
  getReviewed: () =>
    request<DecisionResponse[]>("/api/decision-journal/reviewed"),
  completeReview: (decisionId: string, body: { actual_outcome: string; review_notes?: string }) =>
    request<DecisionResponse>(`/api/decision-journal/${decisionId}/review`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  // 决策时间胶囊 — 写给未来自己的信
  sealTimeCapsule: (decisionId: string, letter: string) =>
    request<{ sealed: boolean; sealed_at: string }>(
      `/api/decision-journal/${decisionId}/time-capsule`,
      { method: "POST", body: JSON.stringify({ letter }) },
    ),
  openTimeCapsule: (decisionId: string) =>
    request<TimeCapsuleResponse>(`/api/decision-journal/${decisionId}/time-capsule`),
};

// ===== 护城河功能：决策深度分析 =====
export const decisionAnalysisApi = {
  list: () => request<DecisionAnalysisResponse[]>("/api/decision-analysis/list"),
  create: (body: DecisionAnalysisCreate) =>
    request<DecisionAnalysisResponse>("/api/decision-analysis/create", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  get: (id: string) => request<DecisionAnalysisResponse>(`/api/decision-analysis/${id}`),
  computeMatrix: (body: { criteria: { criterion: string; weight: number }[]; matrix_scores: { name: string; scores: Record<string, number> }[] }) =>
    request<{ results: { name: string; total: number; details: Record<string, number> }[]; winner: string }>("/api/decision-analysis/compute-matrix", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  analyzePremortem: (body: PremortemAnalyzeRequest) =>
    request<{ categories: { category: string; reasons: string[] }[]; safeguards: { category: string; action: string }[] }>("/api/decision-analysis/premortem-analyze", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  generateRedTeamQuestions: (body: RedTeamGenerateRequest) =>
    request<{ questions: string[] }>("/api/decision-analysis/red-team-questions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  generateAiAnalysis: (id: string) =>
    request<{ ai_analysis: string }>(`/api/decision-analysis/${id}/ai-analysis`, {
      method: "POST",
    }),
};