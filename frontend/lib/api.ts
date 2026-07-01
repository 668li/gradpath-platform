"use client";

import type {
  AIRetroDraft,
  AIRetroDraftRequest,
  CareerPlan,
  CommunityAggregate,
  CommunityReport,
  CommunityStats,
  CommunitySubmit,
  Company,
  CompanyInfo,
  Conversation,
  DashboardOverview,
  DataSourceCreate,
  DataSourceResponse,
  DecisionAdviceRequest,
  DecisionAdviceResponse,
  DecisionCreate,
  DecisionResponse,
  DecisionStats,
  DecisionUpdate,
  EmploymentSearchResult,
  EmploymentStats,
  EventCreate,
  EventResponse,
  EventUpdate,
  GamificationProfile,
  GrowthInsight,
  GrowthInsightRequest,
  InterviewAggregate,
  InterviewReport,
  InterviewStats,
  InterviewSubmit,
  KnowledgeArticle,
  KnowledgeArticleCreate,
  KnowledgeArticleUpdate,
  LoginRequest,
  MarketDataItem,
  Message,
  MilestoneLog,
  PaginatedResponse,
  ParseStatus,
  PipelineStats,
  PostCreate,
  PostItem,
  PostListResponse,
  RegisterRequest,
  ReminderItem,
  ReportDetail,
  ReportListResponse,
  RetroCreate,
  RetroDraft,
  RetrospectiveResponse,
  RetroUpdate,
  SalaryBenchmark,
  SchoolInfo,
  SendMessageRequest,
  SendMessageResponse,
  ShareableSkills,
  SkillCreate,
  SkillInfo,
  SkillResponse,
  SkillStats,
  SkillUpdate,
  TokenResponse,
  UserResponse,
  UserSetting,
} from "@/types";

const TOKEN_KEY = "gradpath_access_token";

/** 读取 localStorage 中的 token（仅在客户端） */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

const REFRESH_TOKEN_KEY = "gradpath_refresh_token";

/** 读取 localStorage 中的 refresh_token（仅在客户端） */
export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function clearRefreshToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export interface ApiError extends Error {
  status: number;
  detail?: unknown;
}

/** 统一 API 错误 */
function makeError(status: number, message: string, detail?: unknown): ApiError {
  const err = new Error(message) as ApiError;
  err.status = status;
  err.detail = detail;
  return err;
}

const DEFAULT_TIMEOUT = 30000; // 30 秒

let refreshPromise: Promise<boolean> | null = null;

/** 用 refresh_token 换取新的 access_token；带 Promise 锁防止并发刷新。 */
async function tryRefreshToken(): Promise<boolean> {
  // 已有刷新请求在途时，复用同一个 Promise，避免并发刷新
  if (refreshPromise) return refreshPromise;

  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  refreshPromise = (async () => {
    try {
      const resp = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!resp.ok) return false;
      const data = await resp.json();
      setToken(data.access_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * fetch wrapper：自动注入 JWT、超时控制、网络错误重试、401 自动刷新 token、
 * 统一解析 JSON（含解析保护）。所有请求走同源 /api/*，由 Next.js rewrites
 * 代理到后端，避免跨域。
 */
async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  // 离线检查
  if (typeof window !== "undefined" && !navigator.onLine) {
    throw makeError(0, "网络不可用，请检查网络连接");
  }

  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  // FormData 时让浏览器自动设置 Content-Type（含 boundary）
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // 带 AbortController 超时的实际请求
  const doFetch = async (signal: AbortSignal): Promise<Response> => {
    try {
      return await fetch(path, { ...options, headers, signal });
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        throw makeError(0, "请求超时，请稍后重试");
      }
      throw makeError(0, "网络请求失败，请检查后端服务是否启动", e);
    }
  };

  // 首次请求（带超时）
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT);

  let res: Response;
  try {
    res = await doFetch(controller.signal);
  } catch {
    // 网络错误 / 超时后重试一次
    clearTimeout(timeoutId);
    const retryController = new AbortController();
    const retryTimeoutId = setTimeout(() => retryController.abort(), DEFAULT_TIMEOUT);
    await new Promise((r) => setTimeout(r, 1000)); // 1s 延迟
    try {
      res = await doFetch(retryController.signal);
    } catch (e2) {
      clearTimeout(retryTimeoutId);
      throw e2;
    }
    clearTimeout(retryTimeoutId);
  }
  clearTimeout(timeoutId);

  // 401 处理：尝试刷新 token 后重试原请求
  if (res.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      const newToken = getToken();
      if (newToken) {
        headers["Authorization"] = `Bearer ${newToken}`;
      }
      const retryController2 = new AbortController();
      const retryTimeoutId2 = setTimeout(() => retryController2.abort(), DEFAULT_TIMEOUT);
      try {
        res = await doFetch(retryController2.signal);
      } finally {
        clearTimeout(retryTimeoutId2);
      }
    }

    if (res.status === 401) {
      clearToken();
      clearRefreshToken();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
      throw makeError(401, "未登录或登录已过期");
    }
  }

  // 204 无内容
  if (res.status === 204) {
    return undefined as T;
  }

  // 解析响应（JSON 解析保护）
  const text = await res.text();
  let data: unknown;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      throw makeError(res.status, `服务器返回了无效的响应（HTTP ${res.status}）`);
    }
  }

  if (!res.ok) {
    const message =
      (data && typeof data === "object" && ((data as Record<string, unknown>).detail || (data as Record<string, unknown>).message)) ||
      `请求失败 (${res.status})`;
    throw makeError(res.status, typeof message === "string" ? message : "请求失败", data);
  }

  return data as T;
}

function buildQuery(params: Record<string, string | undefined | null>): string {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.append(k, v);
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

// ===== Auth =====
export const authApi = {
  register: (body: RegisterRequest) =>
    request<UserResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  login: (body: LoginRequest) =>
    request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  me: () => request<UserResponse>("/api/auth/me"),
};

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

// ===== Events =====
export const eventsApi = {
  list: (params?: {
    event_type?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }) =>
    request<PaginatedResponse<EventResponse>>(
      `/api/events${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  get: (id: string) => request<EventResponse>(`/api/events/${id}`),
  create: (body: EventCreate) =>
    request<EventResponse>("/api/events", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: EventUpdate) =>
    request<EventResponse>(`/api/events/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    request<void>(`/api/events/${id}`, { method: "DELETE" }),
};

// ===== Skills =====
export const skillsApi = {
  tree: () => request<SkillResponse[]>("/api/skills"),
  get: (id: string) => request<SkillResponse>(`/api/skills/${id}`),
  create: (body: SkillCreate) =>
    request<SkillResponse>("/api/skills", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: SkillUpdate) =>
    request<SkillResponse>(`/api/skills/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    request<void>(`/api/skills/${id}`, { method: "DELETE" }),
  stats: () => request<SkillStats>("/api/skills/stats"),
};

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

// ===== Dashboard =====
export const dashboardApi = {
  overview: () => request<DashboardOverview>("/api/dashboard/overview"),
};

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

// ===== 数据管道 =====
export const pipelineApi = {
  // 接入
  ingestUrl: (body: { school_slug: string; year: number; url: string }) =>
    request<ReportDetail>("/api/pipeline/ingest/url", {
      method: "POST",
      body: JSON.stringify({ ...body, source_type: "crawl" }),
    }),

  ingestFile: (file: File, schoolSlug: string, year: number) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("school_slug", schoolSlug);
    formData.append("year", String(year));
    return request<ReportDetail>("/api/pipeline/ingest/file", {
      method: "POST",
      body: formData,
      headers: {}, // 让浏览器自动设置 Content-Type
    });
  },

  ingestApi: (body: { school_slug: string; year: number; api_source_id: string }) =>
    request<ReportDetail>("/api/pipeline/ingest/api", {
      method: "POST",
      body: JSON.stringify({ ...body, source_type: "api" }),
    }),

  // 报告管理
  reports: (params?: { status?: string; page?: number; page_size?: number }) =>
    request<ReportListResponse>(
      `/api/pipeline/reports${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),

  reportDetail: (id: string) =>
    request<ReportDetail>(`/api/pipeline/reports/${id}`),

  deleteReport: (id: string) =>
    request<void>(`/api/pipeline/reports/${id}`, { method: "DELETE" }),

  reparse: (id: string) =>
    request<ReportDetail>(`/api/pipeline/reports/${id}/reparse`, {
      method: "POST",
    }),

  publish: (id: string) =>
    request<ReportDetail>(`/api/pipeline/reports/${id}/publish`, {
      method: "POST",
    }),

  stats: () => request<PipelineStats>("/api/pipeline/stats"),

  // 数据源管理
  sources: () => request<DataSourceResponse[]>("/api/pipeline/sources"),

  createSource: (body: DataSourceCreate) =>
    request<DataSourceResponse>("/api/pipeline/sources", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateSource: (id: string, body: Partial<DataSourceCreate>) =>
    request<DataSourceResponse>(`/api/pipeline/sources/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  deleteSource: (id: string) =>
    request<void>(`/api/pipeline/sources/${id}`, { method: "DELETE" }),
};

// ===== 讨论帖 =====
export const postsApi = {
  list: (params: {
    topic_type: string;
    topic_key: string;
    page?: number;
    page_size?: number;
  }) =>
    request<PostListResponse>("/api/posts/list", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  create: (body: PostCreate) =>
    request<PostItem>("/api/posts", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  update: (id: string, content: string) =>
    request<PostItem>(`/api/posts/${id}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),

  remove: (id: string) =>
    request<void>(`/api/posts/${id}`, { method: "DELETE" }),
};

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

// ===== 外部数据 =====
export const externalDataApi = {
  companies: (params?: { name?: string; industry?: string }) =>
    request<Company[]>(
      `/api/companies${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  salaryBenchmarks: (params?: { company?: string; position?: string; city?: string }) =>
    request<SalaryBenchmark[]>(
      `/api/salary-benchmarks${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  marketData: (params?: { category?: string; year?: number; industry?: string }) =>
    request<MarketDataItem[]>(
      `/api/market-data${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
};

// ===== 游戏化 =====
export const gamificationApi = {
  profile: () => request<GamificationProfile>("/api/gamification/profile"),
  getSettings: () => request<UserSetting>("/api/gamification/settings"),
  updateSettings: (body: { share_skills_enabled: boolean }) =>
    request<UserSetting>("/api/gamification/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
};

// ===== 导出 =====
export const exportApi = {
  /** PDF 时间线下载地址（需带 Authorization 头，由组件侧 fetch + blob） */
  timelinePdf: () => "/api/export/timeline.pdf",
  /** JSON 备份下载地址（需带 Authorization 头，由组件侧 fetch + blob） */
  profileJson: () => "/api/export/profile.json",
  /** 公开技能分享地址（无需鉴权） */
  shareSkills: (token: string) => `/api/share/skills/${token}`,
  /** 拉取公开技能分享数据；链接无效/已关闭返回 null */
  fetchShareSkills: async (token: string): Promise<ShareableSkills | null> => {
    try {
      const res = await fetch(exportApi.shareSkills(token));
      if (!res.ok) return null;
      return (await res.json()) as ShareableSkills;
    } catch {
      return null;
    }
  },
};

// ===== AI 职业管家 — 对话 =====
export const chatApi = {
  createConversation: (title?: string) =>
    request<Conversation>("/api/chat/conversations", {
      method: "POST",
      body: JSON.stringify({ title: title || "新对话" }),
    }),
  listConversations: (params?: { page?: number; page_size?: number }) =>
    request<PaginatedResponse<Conversation>>(
      `/api/chat/conversations${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  getMessages: (conversationId: string) =>
    request<Message[]>(`/api/chat/conversations/${conversationId}/messages`),
  sendMessage: (conversationId: string, body: SendMessageRequest) =>
    request<SendMessageResponse>(
      `/api/chat/conversations/${conversationId}/messages`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  updateTitle: (conversationId: string, title: string) =>
    request<Conversation>(`/api/chat/conversations/${conversationId}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteConversation: (conversationId: string) =>
    request<void>(`/api/chat/conversations/${conversationId}`, {
      method: "DELETE",
    }),
  listSkills: () => request<SkillInfo[]>("/api/chat/skills"),
};

// ===== 知识库 =====
export const knowledgeApi = {
  list: (params?: {
    category?: string;
    page?: number;
    page_size?: number;
  }) =>
    request<PaginatedResponse<KnowledgeArticle>>(
      `/api/knowledge${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  get: (id: string) => request<KnowledgeArticle>(`/api/knowledge/${id}`),
  search: (query: string) =>
    request<KnowledgeArticle[]>("/api/knowledge/search", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  create: (body: KnowledgeArticleCreate) =>
    request<KnowledgeArticle>("/api/knowledge", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: KnowledgeArticleUpdate) =>
    request<KnowledgeArticle>(`/api/knowledge/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  delete: (id: string) =>
    request<void>(`/api/knowledge/${id}`, { method: "DELETE" }),
};

// ===== 职业规划 =====
export const careerPlansApi = {
  list: () => request<CareerPlan[]>("/api/career-plans"),
  get: (id: string) => request<CareerPlan>(`/api/career-plans/${id}`),
  updateMilestone: (planId: string, milestoneIdx: number, status: string) =>
    request<CareerPlan>(
      `/api/career-plans/${planId}/milestones/${milestoneIdx}`,
      { method: "PATCH", body: JSON.stringify({ status }) },
    ),
  addLog: (planId: string, idx: number, content: string) =>
    request<MilestoneLog>(
      `/api/career-plans/${planId}/milestones/${idx}/logs`,
      { method: "POST", body: JSON.stringify({ content }) },
    ),
  listLogs: (planId: string, idx: number) =>
    request<MilestoneLog[]>(
      `/api/career-plans/${planId}/milestones/${idx}/logs`,
    ),
  deleteLog: (planId: string, logId: string) =>
    request<void>(`/api/career-plans/${planId}/logs/${logId}`, {
      method: "DELETE",
    }),
  getReminders: () => request<ReminderItem[]>("/api/career-plans/reminders"),
};
