import type {
  IntelQueryRequest,
  AIIntelResult,
  IntelSaveRequest,
  IntelResponse,
  PositioningCreateRequest,
  PositioningResponse,
  DarkKnowledgeResponse,
  DarkKnowledgeStage,
  GradYanzhaoProgram,
  GradScorelineRecord,
  GradScorelineTrend,
  GradAdjustmentInfo,
  GradSchoolDataSummary,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== 考研作战室 =====
export const gradIntelApi = {
  // 院校情报
  queryIntel: (body: IntelQueryRequest) =>
    request<AIIntelResult>("/api/grad-intel/intel/query", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  saveIntel: (body: IntelSaveRequest) =>
    request<IntelResponse>("/api/grad-intel/intel/save", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listIntel: () => request<IntelResponse[]>("/api/grad-intel/intel/list"),
  deleteIntel: (id: string) =>
    request<void>(`/api/grad-intel/intel/${id}`, { method: "DELETE" }),
  // 自我定位
  createPositioning: (body: PositioningCreateRequest, bypassCache: boolean = false) =>
    request<PositioningResponse>(`/api/grad-intel/positioning/create?bypass_cache=${bypassCache}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  clearPositioningCache: () =>
    request<{ message: string }>("/api/grad-intel/positioning/clear-cache", {
      method: "POST",
    }),
  getLatestPositioning: () =>
    request<PositioningResponse | null>("/api/grad-intel/positioning/latest"),
  getPositioningHistory: () =>
    request<PositioningResponse[]>("/api/grad-intel/positioning/history"),
  // 暗知识
  getDarkKnowledge: (params?: { stage?: string; page?: number; page_size?: number }) =>
    request<any>(
      `/api/grad-intel/dark-knowledge/list${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  getDarkKnowledgeStages: () =>
    request<DarkKnowledgeStage[]>("/api/grad-intel/dark-knowledge/stages"),
  seedDarkKnowledge: () =>
    request<{ seeded: number }>("/api/grad-intel/dark-knowledge/seed", {
      method: "POST",
    }),
  // 公开接口（无需登录）
  listPublicIntel: (params?: { school_name?: string; major_name?: string; school_tier?: string; limit?: number }) =>
    request<IntelResponse[]>(
      `/api/grad-intel/intel/public${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  // 研招网真实数据
  listYanzhaoPrograms: (params?: {
    university_name?: string;
    major_name?: string;
    department?: string;
    degree_type?: string;
    year?: number;
    limit?: number;
    offset?: number;
  }) =>
    request<GradYanzhaoProgram[]>(
      `/api/grad-intel/yanzhao-programs${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  listScorelines: (params?: {
    university_name?: string;
    major_name?: string;
    degree_type?: string;
    year?: number;
    limit?: number;
    offset?: number;
  }) =>
    request<GradScorelineRecord[]>(
      `/api/grad-intel/scorelines${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  getScorelineTrend: (params: { university_name: string; major_name: string; degree_type?: string }) =>
    request<GradScorelineTrend>(
      `/api/grad-intel/scorelines/trend${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  listAdjustments: (params?: {
    university_name?: string;
    major_name?: string;
    status?: string;
    year?: number;
    limit?: number;
    offset?: number;
  }) =>
    request<GradAdjustmentInfo[]>(
      `/api/grad-intel/adjustments${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
  getSchoolSummary: (university_name: string) =>
    request<GradSchoolDataSummary>(`/api/grad-intel/schools/${encodeURIComponent(university_name)}/summary`),
};

// ===== AI 院校分析师 =====
export interface DimensionScore {
  score: number;
  description: string;
}

export interface SixDimensionRadar {
  admission_difficulty: DimensionScore;
  first_choice_protection: DimensionScore;
  transfer_friendliness: DimensionScore;
  score_suppression_risk: DimensionScore;
  info_transparency: DimensionScore;
  cost_effectiveness: DimensionScore;
}

export interface ScorelineTrendItem {
  year: number;
  score_line: number | null;
  competition_ratio: string | null;
}

export interface AnalystReportRequest {
  school_name: string;
  major: string;
}

export interface AnalystReportResponse {
  school_name: string;
  major: string;
  six_dimension_radar: SixDimensionRadar;
  scoreline_trend: ScorelineTrendItem[];
  dark_knowledge_highlights: string[];
  similar_schools: string[];
  recommendation: string;
  summary: string;
}

// ===== 院校对比工具 =====
export interface CompareSchoolItem {
  name: string;
  major: string;
}

export interface CompareRequest {
  schools: CompareSchoolItem[];
  user_score: number;
}

export interface SchoolAnalysis {
  school_name: string;
  major: string;
  six_dimension_radar: SixDimensionRadar;
  scoreline_trend: ScorelineTrendItem[];
  recommendation: string;
  match_score: number;
}

export interface CompareResponse {
  schools: SchoolAnalysis[];
  radar_comparison: Array<{ name: string; scores: Record<string, number> }>;
  recommendation_summary: { reach: string[]; target: string[]; safe: string[] };
  ai_summary: string;
}

export const schoolAnalystApi = {
  getReport: (body: AnalystReportRequest) =>
    request<AnalystReportResponse>("/api/school-analyst/report", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export const schoolCompareApi = {
  compare: (body: CompareRequest) =>
    request<CompareResponse>("/api/school-compare/compare", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ===== 考研可视化 =====
export const gradVisualizationApi = {
  getOverview: () =>
    request<{ total_schools: number; total_programs: number; average_scoreline: number | null }>(
      "/api/grad-intel/visualization/overview",
    ),
  getScoreTrends: (university: string) =>
    request<{ university: string; years: number[]; total_score_lines: (number | null)[] }>(
      `/api/grad-intel/visualization/score-trends?university=${encodeURIComponent(university)}`,
    ),
  getSchoolComparison: (universities: string) =>
    request<{ schools: Array<{
      university_name: string;
      latest_year: number | null;
      latest_scoreline: number | null;
      program_count: number;
      adjustment_count: number;
    }> }>(`/api/grad-intel/visualization/school-comparison?universities=${encodeURIComponent(universities)}`),
  getScoreDistribution: (tier?: string) =>
    request<{
      latest_year: number | null;
      total_records: number;
      distribution: Array<{ range: string; count: number }>;
    }>(`/api/grad-intel/visualization/score-distribution${tier ? `?tier=${encodeURIComponent(tier)}` : ""}`),
  getCrawlerQuality: () =>
    request<{
      total_runs: number;
      success_runs: number;
      failed_runs: number;
      success_rate: number;
      total_fetched: number;
      total_stored: number;
      total_duplicates: number;
      dedup_rate: number;
      store_rate: number;
      total_errors: number;
    }>("/api/grad-intel/visualization/crawler-quality"),
};