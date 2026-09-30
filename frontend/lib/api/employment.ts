import type {
  EmploymentSearchResult,
  SchoolInfo,
  EmploymentStats,
  CommunitySubmit,
  CommunityReport,
  CommunityAggregate,
  CommunityStats,
  InterviewSubmit,
  InterviewReport,
  InterviewAggregate,
  InterviewStats,
  CompanyInfo,
  Company,
  PaginatedResponse,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== 就业数据搜索 =====
export const employmentApi = {
  search: (params: {
    school: string;
    major: string;
    year?: number;
    degree?: string;
  }) =>
    request<EmploymentSearchResult>("/api/employment/search", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  schools: () => request<SchoolInfo[]>("/api/employment/schools"),

  majors: (school: string) =>
    request<string[]>("/api/employment/majors", {
      method: "POST",
      body: JSON.stringify({ school }),
    }),

  stats: () => request<EmploymentStats>("/api/employment/stats"),

  // 批量获取公司元数据（消除前端 N+1 调用）
  batchCompanies: (ids: string[]) =>
    request<Company[]>("/api/employment/companies/batch", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),

  // 就业市场概览（B4，2026-09-26）：companies/salary_benchmarks 真实聚合
  marketOverview: () =>
    request<MarketOverview>("/api/employment/market-overview"),

  // 院校就业报告（EMP-1c，2026-09-30）：既有端点的消费面封装
  schoolsReports: () => request<SchoolReportItem[]>("/api/employment/schools"),
  schoolReportDetail: (school: string) =>
    request<EmploymentSearchData>("/api/employment/search", {
      method: "POST",
      body: JSON.stringify({ school, major: "" }),
    }),

  // 官方就业公告（EMP-3，2026-09-30）：公开只读端点，只出已审核条目
  announces: (page = 1, pageSize = 20) =>
    request<EmploymentAnnounceList>(
      `/api/employment/announces?page=${page}&page_size=${pageSize}`
    ),
};

export interface MarketOverview {
  company_total: number;
  top_industries: { industry: string; count: number }[];
  salary_total: number;
  city_salary_bands: { city: string; sample_count: number; min_wan: number | null; max_wan: number | null }[];
  school_employment_samples: {
    name: string;
    employment_rate: number | null;
    grad_school_rate: number | null;
    report_index_url: string | null;
  }[];
  school_employment_coverage: number;
  school_total: number;
}

// 院校就业报告浏览（EMP-1c）：消费既有 schools/search 端点，按校展开已发布报告
export interface SchoolReportItem {
  id: string;
  name: string;
  slug: string;
  code: string | null;
  report_count: number;
  major_count: number;
}

export interface EmploymentRecord {
  year: number;
  degree: string;
  total_graduates: number | null;
  source_url: string | null;
  rates: {
    employment: number | null;
    further_study: number | null;
    civil_service: number | null;
    abroad: number | null;
    startup: number | null;
    gap_year: number | null;
  };
  employer_ranking: { name?: string; count?: number }[];
  industry_distribution: Record<string, number>;
  destination_region: Record<string, number>;
  school_for_further_study: { name?: string; count?: number }[];
}

export interface EmploymentSearchData {
  school: { id: string; name: string; slug: string; code: string | null } | null;
  major: string | null;
  records: EmploymentRecord[];
  trend: {
    years: number[];
    employment_rate: (number | null)[];
    further_study_rate: (number | null)[];
    civil_service_rate: (number | null)[];
    abroad_rate: (number | null)[];
  } | null;
}

// 官方就业公告（EMP-3）：公开只读端点响应
export interface EmploymentAnnounceItem {
  title: string;
  source_url: string;
  source_name: string | null;
  published_at: string | null;
  credibility: string;
}

export interface EmploymentAnnounceList {
  total: number;
  items: EmploymentAnnounceItem[];
}

// ===== 社区数据 =====
export const communityApi = {
  submit: (body: CommunitySubmit) =>
    request<CommunityReport>("/api/community/submit", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  myReports: (params?: { page?: number; page_size?: number }) =>
    request<PaginatedResponse<CommunityReport>>(
      `/api/community/my-reports${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  remove: (id: string) =>
    request<void>(`/api/community/${id}`, { method: "DELETE" }),
  aggregate: (body: { school: string; major: string; year?: number }) =>
    request<CommunityAggregate>("/api/community/aggregate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  stats: () => request<CommunityStats>("/api/community/stats"),
};

// ===== 面试经验 =====
export const interviewApi = {
  submit: (body: InterviewSubmit) =>
    request<InterviewReport>("/api/interview/submit", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  myReports: (params?: { page?: number; page_size?: number }) =>
    request<PaginatedResponse<InterviewReport>>(
      `/api/interview/my-reports${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  remove: (id: string) =>
    request<void>(`/api/interview/${id}`, { method: "DELETE" }),
  aggregate: (body: { company: string; position?: string }) =>
    request<InterviewAggregate>("/api/interview/aggregate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  stats: () => request<InterviewStats>("/api/interview/stats"),
  companies: (keyword: string = "") =>
    request<CompanyInfo[]>("/api/interview/companies", {
      method: "POST",
      body: JSON.stringify({ keyword }),
    }),
};