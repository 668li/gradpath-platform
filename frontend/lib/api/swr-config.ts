"use client";

import { useCallback } from "react";
import useSWR, { type SWRConfiguration, type Key } from "swr";
import { request, ApiError } from "./client";

/**
 * SWR 全局默认配置：
 * - dedupingInterval: 2s 内同 URL 自动去重并发请求
 * - revalidateOnFocus: 浏览器重新获得焦点时不自动重新验证
 * - shouldRetryOnError: 错误时不自动重试（由调用方决定）
 * - errorRetryCount: 显式 retry 时最多重试 1 次
 */
export const SWR_GLOBAL_CONFIG: SWRConfiguration = {
  dedupingInterval: 2000,
  revalidateOnFocus: false,
  shouldRetryOnError: false,
  errorRetryCount: 1,
};

/**
 * 基于 client.ts request 的 SWR fetcher。
 *
 * - 401（未登录/Token 过期）由 request 内部已处理：尝试 refresh，失败时清除 token；
 *   这里只需捕获 401 并跳转 /login，避免各页面重复实现。
 * - 其他错误原样抛出，由 useSWR 的 error 字段透传给调用方。
 */
export async function apiFetcher<T>(url: string): Promise<T> {
  try {
    return await request<T>(url);
  } catch (err) {
    const status = (err as ApiError)?.status;
    if (status === 401 && typeof window !== "undefined") {
      // 已在 request 内清除了 token，这里跳转登录页
      // 使用 location.replace 避免在 history 中留下需登录才能访问的页面
      const redirect = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.replace(`/login?redirect=${redirect}`);
    }
    throw err;
  }
}

/**
 * 包装 useSWR，注入 apiFetcher 与全局默认配置。
 *
 * @param url 资源路径，传 null 表示暂停请求（依赖未就绪）
 * @param options SWR 配置（与全局配置合并，调用方可覆盖）
 *
 * @example
 * const { data, error, isLoading } = useApi<CompanyIntelResponse[]>(
 *   "/api/career-intel/intel",
 *   { fallbackData: [] },
 * );
 */
export function useApi<T>(
  url: string | null,
  options?: SWRConfiguration<T>,
) {
  return useSWR<T, ApiError>(
    (url ?? null) as Key,
    apiFetcher<T>,
    { ...SWR_GLOBAL_CONFIG, ...options },
  );
}

/**
 * Mutation helper：用于 POST/PUT/PATCH/DELETE 等写操作。
 *
 * SWR 的 useSWRMutation 适合「单点触发」场景，但很多业务里我们只需要一个
 * `mutate` 函数配合 useApi 使用（写完之后让某个 key 失效）。
 * 这里提供一个轻量的 hook，返回 trigger 函数，调用后通过 request 发起请求，
 * 并可选择性地 invalidate 指定的 SWR key。
 *
 * @param url 写操作目标路径
 * @param method HTTP 方法，默认 POST
 *
 * @example
 * const { trigger: saveIntel } = useApiMutation<IntelResponse, IntelSaveRequest>(
 *   "/api/career-intel/intel/save",
 * );
 * await saveIntel({ school_name: "...", major_name: "..." });
 */
export function useApiMutation<T, V = unknown>(
  url: string,
  method: "POST" | "PUT" | "PATCH" | "DELETE" = "POST",
) {
  const trigger = useCallback(
    async (body?: V, invalidateKey?: string) => {
      const data = await request<T>(url, {
        method,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      return data;
    },
    [url, method],
  );

  return { trigger };
}

/**
 * 主动让某个 SWR key 重新验证（重新请求）。
 *
 * 适合写操作完成后刷新列表：`mutate("/api/career-intel/intel/list")`。
 */
export function useInvalidate() {
  // 注：避免在每次调用都创建闭包，直接返回稳定引用
  return useCallback(async (key: string) => {
    const { mutate } = await import("swr");
    await mutate(key);
  }, []);
}
