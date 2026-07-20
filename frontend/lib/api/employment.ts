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
};

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