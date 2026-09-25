import type {
  AuditQuestion,
  SprintCreate,
  SprintResponse,
  BlueprintCreate,
  LifeDesignBlueprint,
  BlueprintSummary,
  WeeklyReviewCreate,
  WeeklyReviewResponse,
} from "@/types";
import { request } from "./client";

// ===== 护城河功能：人生设计引擎 =====
// 2026-09-25 ponytail 瘦身：recommendationApi 删除——对应后端 /api/recommend/*
// 端点已随 009 考研收敛下线，前端无任何组件调用。
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

  // ===== 认识自己 V1：人生设计访谈蓝图 =====
  createBlueprint: (body: BlueprintCreate) =>
    request<LifeDesignBlueprint>("/api/life-design/blueprints", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listBlueprints: () => request<BlueprintSummary[]>("/api/life-design/blueprints"),
  getLatestBlueprint: () =>
    request<LifeDesignBlueprint | null>("/api/life-design/blueprints/latest"),
  getBlueprint: (id: string) =>
    request<LifeDesignBlueprint>(`/api/life-design/blueprints/${id}`),
};