import type {
  DecisionAdviceRequest,
  DecisionAdviceResponse,
  GrowthInsightRequest,
  GrowthInsight,
  AICompanyIntelResult,
  CompanyIntelSaveRequest,
  CompanyIntelResponse,
  CareerPositioningCreateRequest,
  CareerPositioningResponse,
  CareerDarkKnowledgeResponse,
  CareerDarkKnowledgeStage,
  PostIntelQueryRequest,
  AIPostIntelResult,
  PostIntelSaveRequest,
  PostIntelResponse,
  CivilServicePositioningCreateRequest,
  CivilServicePositioningResponse,
  CivilServiceDarkKnowledgeStage,
  CivilServiceDarkKnowledgeResponse,
  ProactiveInsightSummary,
  ProactiveInsight,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== AI 决策指导 =====
export const aiApi = {
  decisionAdvice: (body: DecisionAdviceRequest) =>
    request<DecisionAdviceResponse>("/api/ai/decision-advice", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  growthInsight: (body: GrowthInsightRequest) =>
    request<GrowthInsight>("/api/ai/growth-insight", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getLatestInsight: () =>
    request<GrowthInsight>("/api/ai/growth-insight/latest"),
};

// ===== 求职作战室 =====
export const careerIntelApi = {
  // 公司情报
  queryIntel: (body: { company_name: string; position_name: string }) =>
    request<AICompanyIntelResult>("/api/career-intel/intel/query", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  saveIntel: (body: CompanyIntelSaveRequest) =>
    request<CompanyIntelResponse>("/api/career-intel/intel/save", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listIntel: () => request<CompanyIntelResponse[]>("/api/career-intel/intel/list"),
  deleteIntel: (id: string) =>
    request<void>(`/api/career-intel/intel/${id}`, { method: "DELETE" }),
  // 求职定位
  createPositioning: (body: CareerPositioningCreateRequest) =>
    request<CareerPositioningResponse>("/api/career-intel/positioning/create", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getLatestPositioning: () =>
    request<CareerPositioningResponse | null>("/api/career-intel/positioning/latest"),
  getPositioningHistory: () =>
    request<CareerPositioningResponse[]>("/api/career-intel/positioning/history"),
  // 求职暗知识
  getDarkKnowledge: (stage?: string) =>
    request<CareerDarkKnowledgeResponse[]>(
      `/api/career-intel/dark-knowledge/list${buildQuery({ stage })}`,
    ),
  getDarkKnowledgeStages: () =>
    request<CareerDarkKnowledgeStage[]>("/api/career-intel/dark-knowledge/stages"),
  seedDarkKnowledge: () =>
    request<{ seeded: number }>("/api/career-intel/dark-knowledge/seed", {
      method: "POST",
    }),
};

export const civilServiceIntelApi = {
  queryPostIntel: (data: PostIntelQueryRequest) =>
    request<{ success: boolean; data: AIPostIntelResult }>("/api/civil-service/post-intel/query", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  savePostIntel: (data: PostIntelSaveRequest) =>
    request<PostIntelResponse>("/api/civil-service/post-intel", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listPostIntel: () => request<PostIntelResponse[]>("/api/civil-service/post-intel"),
  deletePostIntel: (id: string) =>
    request<void>(`/api/civil-service/post-intel/${id}`, { method: "DELETE" }),

  createPositioning: (data: CivilServicePositioningCreateRequest) =>
    request<CivilServicePositioningResponse>("/api/civil-service/positioning", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getLatestPositioning: () =>
    request<CivilServicePositioningResponse | null>("/api/civil-service/positioning/latest"),
  getPositioningHistory: () =>
    request<CivilServicePositioningResponse[]>("/api/civil-service/positioning/history"),

  getDarkKnowledgeStages: () =>
    request<CivilServiceDarkKnowledgeStage[]>("/api/civil-service/dark-knowledge/stages"),
  getDarkKnowledge: (stage?: string) => {
    const qs = stage ? `?stage=${encodeURIComponent(stage)}` : "";
    return request<CivilServiceDarkKnowledgeResponse[]>(`/api/civil-service/dark-knowledge${qs}`);
  },
  // 公开接口（无需登录）
  listPublicPostIntel: (params?: { region?: string; department?: string; exam_type?: string; department_tier?: string; limit?: number }) =>
    request<PostIntelResponse[]>(
      `/api/civil-service/post-intel/public${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
};

// ===== 护城河功能：AI 主动洞察 =====
export const proactiveInsightsApi = {
  getSummary: () => request<ProactiveInsightSummary>("/api/proactive-insights/summary"),
  list: (params?: { unread_only?: boolean; limit?: number }) =>
    request<ProactiveInsight[]>(
      `/api/proactive-insights/list${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  generate: () =>
    request<ProactiveInsight[]>("/api/proactive-insights/generate", {
      method: "POST",
    }),
  markAsRead: (id: string) =>
    request<void>(`/api/proactive-insights/${id}/read`, { method: "PATCH" }),
};