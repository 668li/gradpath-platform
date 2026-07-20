"use client";

import { request } from "./client";

/**
 * 轻量请求缓存层。
 * - TTL 内存缓存：同一路径在 TTL 内直接返回缓存，避免重复网络请求。
 * - 请求去重：同一路径并发请求只发一次网络，其余复用结果。
 * 仅用于 GET 类只读查询；写操作（POST/PUT/DELETE）不走缓存。
 */

interface CacheEntry<T> {
  data: T;
  expiresAt: number;
}

const DEFAULT_TTL = 30_000; // 30s
const cache = new Map<string, CacheEntry<unknown>>();
const inflight = new Map<string, Promise<unknown>>();

export function cachedRequest<T>(
  path: string,
  options: RequestInit = {},
  ttl: number = DEFAULT_TTL,
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();

  // 写操作不走缓存
  if (method !== "GET") {
    return request<T>(path, options);
  }

  const now = Date.now();
  const hit = cache.get(path) as CacheEntry<T> | undefined;
  if (hit && hit.expiresAt > now) {
    return Promise.resolve(hit.data);
  }

  // 去重：同一路径已有在途请求则复用
  const existing = inflight.get(path) as Promise<T> | undefined;
  if (existing) return existing;

  const p = request<T>(path, options)
    .then((data) => {
      cache.set(path, { data, expiresAt: Date.now() + ttl });
      return data;
    })
    .finally(() => {
      inflight.delete(path);
    });

  inflight.set(path, p);
  return p;
}

/** 手动失效某个路径（如数据变更后强制刷新） */
export function invalidateCache(pathPrefix: string): void {
  for (const key of cache.keys()) {
    if (key.startsWith(pathPrefix)) cache.delete(key);
  }
  for (const key of inflight.keys()) {
    if (key.startsWith(pathPrefix)) inflight.delete(key);
  }
}

/** 清空全部缓存（如登出时） */
export function clearQueryCache(): void {
  cache.clear();
  inflight.clear();
}
