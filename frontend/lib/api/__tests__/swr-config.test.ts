// frontend/lib/api/__tests__/swr-config.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SWR_GLOBAL_CONFIG, apiFetcher, buildQuery } from "../index";

// 模拟 client.ts 的 request
vi.mock("../client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../client")>();
  return {
    ...actual,
    request: vi.fn(),
    getToken: vi.fn(() => "fake-token"),
    setToken: vi.fn(),
    clearToken: vi.fn(),
    getRefreshToken: vi.fn(() => null),
    setRefreshToken: vi.fn(),
    clearRefreshToken: vi.fn(),
    ApiError: class ApiError extends Error {
      status: number;
      detail?: unknown;
      constructor(message: string, status: number, detail?: unknown) {
        super(message);
        this.status = status;
        this.detail = detail;
      }
    },
  };
});

// 捕获 location.replace 调用
const replaceSpy = vi.fn();
Object.defineProperty(window, "location", {
  value: {
    pathname: "/dashboard",
    search: "",
    replace: replaceSpy,
  },
  writable: true,
});

describe("SWR_GLOBAL_CONFIG", () => {
  it("包含去重 / revalidate / retry 默认值", () => {
    expect(SWR_GLOBAL_CONFIG.dedupingInterval).toBe(2000);
    expect(SWR_GLOBAL_CONFIG.revalidateOnFocus).toBe(false);
    expect(SWR_GLOBAL_CONFIG.shouldRetryOnError).toBe(false);
  });
});

describe("apiFetcher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("成功路径返回 data", async () => {
    const { request } = await import("../client");
    (request as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ ok: true });
    const data = await apiFetcher("/api/test");
    expect(data).toEqual({ ok: true });
  });

  it("401 错误跳转 /login 并携带 redirect", async () => {
    const { request } = await import("../client");
    const { ApiError } = await import("../client");
    (request as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new (ApiError as unknown as new (
        msg: string,
        status: number,
      ) => InstanceType<typeof Error>)("未登录", 401),
    );
    await expect(apiFetcher("/api/test")).rejects.toBeDefined();
    expect(replaceSpy).toHaveBeenCalled();
    const target = replaceSpy.mock.calls[0][0] as string;
    expect(target).toContain("/login?redirect=");
  });

  it("非 401 错误原样抛出", async () => {
    const { request } = await import("../client");
    const { ApiError } = await import("../client");
    const err = new (ApiError as unknown as new (
      msg: string,
      status: number,
    ) => InstanceType<typeof Error>)("Server Error", 500);
    (request as ReturnType<typeof vi.fn>).mockRejectedValueOnce(err);
    await expect(apiFetcher("/api/test")).rejects.toBe(err);
    expect(replaceSpy).not.toHaveBeenCalled();
  });
});

describe("buildQuery", () => {
  it("空对象", () => {
    expect(buildQuery({})).toBe("");
  });
  it("多参数", () => {
    expect(buildQuery({ a: 1, b: "x" })).toBe("?a=1&b=x");
  });
});
