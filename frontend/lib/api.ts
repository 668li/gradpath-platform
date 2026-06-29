"use client";

import type {
  DashboardOverview,
  DecisionCreate,
  DecisionResponse,
  DecisionStats,
  DecisionUpdate,
  EmploymentSearchResult,
  EmploymentStats,
  EventCreate,
  EventResponse,
  EventUpdate,
  LoginRequest,
  RegisterRequest,
  RetroCreate,
  RetroDraft,
  RetrospectiveResponse,
  RetroUpdate,
  SchoolInfo,
  SkillCreate,
  SkillResponse,
  SkillStats,
  SkillUpdate,
  TokenResponse,
  UserResponse,
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

/**
 * fetch wrapper：自动注入 JWT、统一解析 JSON、401 跳转登录。
 * 所有请求走同源 /api/*，由 Next.js rewrites 代理到后端，避免跨域。
 */
async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(path, { ...options, headers });
  } catch (e) {
    throw makeError(0, "网络请求失败，请检查后端服务是否启动", e);
  }

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw makeError(401, "未登录或登录已过期");
  }

  // 204 无内容
  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const message =
      (data && (data.detail || data.message)) ||
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
  list: () => request<DecisionResponse[]>("/api/decisions"),
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
  list: (params?: { event_type?: string; start_date?: string; end_date?: string }) =>
    request<EventResponse[]>(`/api/events${buildQuery(params || {})}`),
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
  list: () => request<RetrospectiveResponse[]>("/api/retrospectives"),
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
