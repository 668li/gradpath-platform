import type {
  RecommendationResponse,
  SchoolRecommendation,
  AdjustmentRecommendation,
  DarkKnowledgeRecommendation,
  AuditQuestion,
  SprintCreate,
  SprintResponse,
  WeeklyReviewCreate,
  WeeklyReviewResponse,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== AI 推荐系统 =====
export const recommendationApi = {
  recommendSchools: (params?: {
    target_score?: number;
    target_tier?: string;
    target_region?: string;
    target_major?: string;
    top_n?: number;
  }) =>
    request<RecommendationResponse<SchoolRecommendation>>(
      `/api/recommend/schools${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  recommendAdjustments: (params?: {
    target_score?: number;
    target_major?: string;
    target_region?: string;
    top_n?: number;
  }) =>
    request<RecommendationResponse<AdjustmentRecommendation>>(
      `/api/recommend/adjustments${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  recommendDarkKnowledge: (params?: {
    stage?: string;
    top_n?: number;
  }) =>
    request<RecommendationResponse<DarkKnowledgeRecommendation>>(
      `/api/recommend/dark-knowledge${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
};

// ===== 护城河功能：人生设计引擎 =====
export const lifeDesignApi = {
  getAuditQuestions: (focusAreas: string[] = ["career", "finance", "health", "relationships", "growth"]) =>
    request<{ domain: string; domain_name: string; question: string; answer: string }[]>("/api/life-design/audit/questions", {
      method: "POST",
      body: JSON.stringify({ focus_areas: focusAreas }),
    }),
  generateVision: (auditQa: AuditQuestion[]) =>
    request<{ vision_statement: string }>("/api/life-design/audit/generate-vision", {
      method: "POST",
      body: JSON.stringify({ audit_qa: auditQa }),
    }),
  createSprint: (body: SprintCreate) =>
    request<SprintResponse>("/api/life-design/sprints", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listSprints: () => request<SprintResponse[]>("/api/life-design/sprints"),
  getActiveSprint: () => request<SprintResponse | null>("/api/life-design/sprints/active"),
  activateSprint: (sprintId: string) =>
    request<SprintResponse>(`/api/life-design/sprints/${sprintId}/activate`, {
      method: "POST",
    }),
  generateSprintReview: (sprintId: string) =>
    request<{ ai_review: string }>(`/api/life-design/sprints/${sprintId}/review`, {
      method: "POST",
    }),
  createWeeklyReview: (body: WeeklyReviewCreate) =>
    request<WeeklyReviewResponse>("/api/life-design/weekly-reviews", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listWeeklyReviews: () => request<WeeklyReviewResponse[]>("/api/life-design/weekly-reviews"),
};