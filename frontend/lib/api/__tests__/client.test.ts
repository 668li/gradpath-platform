// frontend/lib/api/__tests__/client.test.ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  getToken,
  setToken,
  clearToken,
  getRefreshToken,
  setRefreshToken,
  clearRefreshToken,
  request,
  buildQuery,
  TOKEN_COOKIE,
  ApiError,
} from "../client";

// fetch mock
const fetchMock = vi.fn();
global.fetch = fetchMock as unknown as typeof fetch;

describe("client.ts — token storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    // 清空 cookie
    document.cookie = "";
    fetchMock.mockReset();
  });

  it("setToken / getToken / clearToken 操作 localStorage 与 cookie", () => {
    setToken("abc123");
    expect(getToken()).toBe("abc123");
    // cookie 也应同步写入
    expect(document.cookie).toContain(TOKEN_COOKIE);
    clearToken();
    expect(getToken()).toBeNull();
    // cookie 已被清除（Max-Age=0）
    expect(document.cookie).not.toContain("gradpath_token=abc123");
  });

  it("refresh token 存取", () => {
    setRefreshToken("refresh-xyz");
    expect(getRefreshToken()).toBe("refresh-xyz");
    clearRefreshToken();
    expect(getRefreshToken()).toBeNull();
  });

  it("getToken 在 SSR 环境返回 null", () => {
    // 临时模拟 SSR
    const originalWindow = global.window;
    // @ts-expect-error 模拟 SSR 无 window
    delete global.window;
    expect(getToken()).toBeNull();
    global.window = originalWindow;
  });
});

describe("client.ts — buildQuery", () => {
  it("空参数返回空字符串", () => {
    expect(buildQuery({})).toBe("");
  });

  it("忽略 null / undefined / 空字符串", () => {
    expect(buildQuery({ a: 1, b: undefined, c: null, d: "" })).toBe("?a=1");
  });

  it("组合多个参数", () => {
    const q = buildQuery({ a: 1, b: "hello", c: 0 });
    // URLSearchParams 顺序按插入
    expect(q).toBe("?a=1&b=hello&c=0");
  });

  it("数字 0 被保留", () => {
    expect(buildQuery({ page: 0 })).toBe("?page=0");
  });
});

describe("client.ts — request", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.cookie = "";
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("成功返回 JSON 数据", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const data = await request<{ ok: boolean }>("/api/test");
    expect(data).toEqual({ ok: true });
  });

  it("204 No Content 返回 undefined", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    const data = await request<void>("/api/no-content");
    expect(data).toBeUndefined();
  });

  it("携带 Authorization 头（当 token 存在）", async () => {
    setToken("tok-123");
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 200 }),
    );
    await request("/api/test");
    const callOpts = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = callOpts.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer tok-123");
  });

  it("HTTP 4xx 错误抛出 ApiError 含 status 与 detail", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: "Bad request", code: "INVALID" }),
        { status: 400, headers: { "Content-Type": "application/json" } },
      ),
    );
    await expect(request("/api/test")).rejects.toMatchObject({
      status: 400,
      message: "Bad request",
    });
  });

  it("HTTP 500 错误抛出 ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Server error" }), { status: 500 }),
    );
    await expect(request("/api/test")).rejects.toMatchObject({
      status: 500,
    });
  });

  it("非 JSON 响应抛出可读错误", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("<html>not json</html>", {
        status: 200,
        headers: { "Content-Type": "text/html" },
      }),
    );
    await expect(request("/api/test")).rejects.toThrow(/无效的响应/);
  });

  it("FormData 请求不设置 Content-Type（让浏览器自动加 boundary）", async () => {
    const fd = new FormData();
    fd.append("file", new Blob(["content"]), "test.txt");
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    await request("/api/upload", { method: "POST", body: fd });
    const headers = (fetchMock.mock.calls[0][1] as RequestInit)
      .headers as Record<string, string>;
    expect(headers["Content-Type"]).toBeUndefined();
  });
});
