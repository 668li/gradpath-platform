"use client";

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
export async function request<T>(
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

export function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.append(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}