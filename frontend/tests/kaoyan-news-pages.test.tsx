// frontend/tests/kaoyan-news-pages.test.tsx
/** 考研资讯中心（Phase D1）页面测试 — 资讯列表页 + 详情页。
 *
 * 与 gwy 测试同款模式：mock next/navigation + swr（列表页）/
 * mock @/lib/api（详情页直接调用 kaoyanNewsApi.get）。
 * 关键日期 fixture 用「相对今天」动态生成，避免硬编码日期失效。
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import KaoyanNewsPage from "@/app/(app)/kaoyan/news/page";
import KaoyanNewsDetailPage from "@/app/(app)/kaoyan/news/[id]/page";
import type {
  KaoyanKeyDate,
  KaoyanNewsListResponse,
  KaoyanNewsResponse,
} from "@/types";

// vi.mock 工厂在 import 时执行，模块级变量需用 vi.hoisted 避免 TDZ
const mocks = vi.hoisted(() => ({
  pushMock: vi.fn(),
  getMock: vi.fn((k: string) => ""),
  paramsId: "11111111-1111-1111-1111-111111111111",
  swrMock: vi.fn(),
  apiListMock: vi.fn(),
  apiCategoriesMock: vi.fn(),
  apiGetMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.pushMock }),
  useSearchParams: () => ({ get: mocks.getMock, toString: () => "" }),
  useParams: () => ({ id: mocks.paramsId }),
}));

vi.mock("swr", () => ({
  default: mocks.swrMock,
}));

vi.mock("@/lib/api", () => ({
  kaoyanNewsApi: {
    list: mocks.apiListMock,
    categories: mocks.apiCategoriesMock,
    get: mocks.apiGetMock,
  },
}));

/** 今天 +days 天的 yyyy-mm-dd（本地时区，与 key-dates.daysUntil 同基准）。 */
function isoDaysFromNow(days: number): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + days);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function makeNews(
  overrides: Partial<KaoyanNewsResponse> = {},
): KaoyanNewsResponse {
  return {
    id: mocks.paramsId,
    title: "2026 考研网上报名时间公布",
    summary: "网上报名 10 月 15 日启动",
    content: "网上报名时间为2025年10月15日至10月28日，逾期不再补报。",
    source_platform: "eol",
    source_url: "https://kaoyan.eol.cn/news/20260815/1.shtml",
    published_at: "2026-08-15T00:00:00Z",
    crawled_at: "2026-08-15T08:00:00Z",
    category: "政策",
    tags: [],
    status: "approved",
    created_at: "2026-08-15T08:00:00Z",
    updated_at: "2026-08-15T08:00:00Z",
    ai_summary: "多校公布报名时间，考生需及时完成网上报名。",
    quality_score: 90,
    quality_grade: "A",
    key_dates: [{ label: "报名", date: isoDaysFromNow(3) }],
    is_expired: false,
    ...overrides,
  };
}

/** 列表页 swr stub：/categories → 分类数据；其余 → 列表数据。 */
function stubSwr(list: KaoyanNewsListResponse, categories: string[]) {
  mocks.swrMock.mockImplementation((key: string | null) => {
    if (key == null) return { data: undefined, error: undefined, isLoading: false };
    if (String(key).includes("/categories")) {
      return { data: { categories }, error: undefined, isLoading: false };
    }
    return { data: list, error: undefined, isLoading: false };
  });
}

describe("考研资讯中心列表页", () => {
  beforeEach(() => {
    mocks.getMock.mockImplementation((k: string) => "");
    mocks.pushMock.mockClear();
  });

  it("渲染分类 tab（API 分类 + 兜底分类）", () => {
    stubSwr(
      { items: [], total: 0, page: 1, page_size: 10 },
      ["调剂", "复试线"],
    );
    const { container } = render(<KaoyanNewsPage />);
    expect(container.textContent).toContain("调剂");
    expect(container.textContent).toContain("复试线");
    // 兜底分类与 API 分类合并展示
    expect(container.textContent).toContain("招生简章");
    expect(container.textContent).toContain("政策");
  });

  it("渲染 A/B 质量徽章", () => {
    stubSwr(
      {
        items: [
          makeNews({ id: "n-a", quality_grade: "A", quality_score: 90 }),
          makeNews({ id: "n-b", quality_grade: "B", quality_score: 60 }),
        ],
        total: 2,
        page: 1,
        page_size: 10,
      },
      ["调剂"],
    );
    const { container } = render(<KaoyanNewsPage />);
    expect(container.textContent).toContain("A 优质");
    expect(container.textContent).toContain("B 良好");
    expect(container.textContent).toContain("90");
    expect(container.textContent).toContain("60");
  });

  it("渲染关键日期倒计时文案「距报名 3 天」", () => {
    stubSwr(
      {
        items: [makeNews({ key_dates: [{ label: "报名", date: isoDaysFromNow(3) }] })],
        total: 1,
        page: 1,
        page_size: 10,
      },
      ["调剂"],
    );
    const { container } = render(<KaoyanNewsPage />);
    expect(container.textContent).toContain("距报名 3 天");
  });

  it("已过期条目显示「已过期」徽章", () => {
    stubSwr(
      {
        items: [makeNews({ is_expired: true, key_dates: [{ label: "调剂", date: isoDaysFromNow(-3) }] })],
        total: 1,
        page: 1,
        page_size: 10,
      },
      ["调剂"],
    );
    const { container } = render(<KaoyanNewsPage />);
    expect(container.textContent).toContain("已过期");
  });

  it("total 超过 page_size 时渲染分页", () => {
    stubSwr(
      {
        items: [makeNews()],
        total: 25,
        page: 1,
        page_size: 10,
      },
      ["调剂"],
    );
    const { container } = render(<KaoyanNewsPage />);
    expect(container.textContent).toContain("第 1 / 3 页");
    expect(container.textContent).toContain("共 25 条");
  });

  it("空列表显示空状态", () => {
    stubSwr(
      { items: [], total: 0, page: 1, page_size: 10 },
      ["调剂"],
    );
    const { container } = render(<KaoyanNewsPage />);
    expect(container.textContent).toContain("暂无相关资讯");
  });
});

describe("考研资讯详情页", () => {
  beforeEach(() => {
    mocks.apiGetMock.mockReset();
  });

  it("渲染 AI 解读、关键时间点与来源溯源卡", async () => {
    const keyDates: KaoyanKeyDate[] = [
      { label: "报名", date: isoDaysFromNow(3) },
      { label: "调剂", date: isoDaysFromNow(-3) },
    ];
    mocks.apiGetMock.mockResolvedValue(makeNews({ key_dates: keyDates }));

    render(<KaoyanNewsDetailPage />);
    await screen.findByText("AI 解读");
    expect(screen.getByText("关键时间点")).toBeTruthy();
    expect(screen.getByText("来源溯源")).toBeTruthy();
    // 关键日期倒计时：未来 →「距报名 3 天」；已过 →「已过 3 天」
    expect(screen.getByText("距报名 3 天")).toBeTruthy();
    expect(screen.getByText("已过 3 天")).toBeTruthy();
    // 来源溯源卡展示来源地址链接
    expect(screen.getByText("https://kaoyan.eol.cn/news/20260815/1.shtml")).toBeTruthy();
    // AI 解读正文
    expect(screen.getByText("多校公布报名时间，考生需及时完成网上报名。")).toBeTruthy();
  });

  it("无 AI 摘要时不渲染 AI 解读区块", async () => {
    mocks.apiGetMock.mockResolvedValue(makeNews({ ai_summary: null }));
    render(<KaoyanNewsDetailPage />);
    // 等待加载完成（标题出现）
    await screen.findByText("2026 考研网上报名时间公布");
    expect(screen.queryByText("AI 解读")).toBeNull();
  });

  it("详情 404 显示「资讯不存在」空态", async () => {
    mocks.apiGetMock.mockRejectedValue(new Error("404"));
    render(<KaoyanNewsDetailPage />);
    await screen.findByText("资讯不存在");
    expect(screen.getByText("返回资讯中心")).toBeTruthy();
  });
});
