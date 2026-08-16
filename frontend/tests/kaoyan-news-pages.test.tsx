// frontend/tests/kaoyan-news-pages.test.tsx
/** 考研资讯中心（Phase D1）页面测试 — 资讯列表页 + 详情页。
 *
 * 与 gwy 测试同款模式：mock next/navigation + swr（列表页）/
 * mock @/lib/api（详情页直接调用 kaoyanNewsApi.get）。
 * 关键日期 fixture 用「相对今天」动态生成，避免硬编码日期失效。
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, screen, waitFor } from "@testing-library/react";
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
  // Phase I 反馈闭环：登录态 + qualityFeedbackApi.post + toast
  authState: { user: null as { id: string } | null },
  feedbackPostMock: vi.fn(),
  toast: { push: vi.fn() },
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

vi.mock("@/components/ui/toast", () => ({
  useToast: () => mocks.toast,
}));

// Phase I：详情页内嵌 QualityFeedback 依赖登录态 + qualityFeedbackApi
vi.mock("@/stores/auth", () => ({
  useAuthStore: (sel: (s: { user: { id: string } | null }) => unknown) => sel(mocks.authState),
}));

vi.mock("@/lib/api/kaoyan", () => ({
  qualityFeedbackApi: { post: mocks.feedbackPostMock },
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
    mocks.authState.user = null;
    mocks.feedbackPostMock.mockReset();
    mocks.toast.push.mockClear();
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

  it("详情页渲染数据年份徽章与「提取依据」证据链（Phase I）", async () => {
    mocks.apiGetMock.mockResolvedValue(
      makeNews({
        structured_meta: {
          enrollment_count: 120,
          exam_subjects: ["408 计算机学科专业基础"],
          evidence: { enrollment_count: "拟招收 120 人" },
          confidence: { enrollment_count: 0.8 },
          effective_year: 2026,
        },
      }),
    );
    const { container } = render(<KaoyanNewsDetailPage />);
    await screen.findByText("2026 考研网上报名时间公布");
    // 年份徽章（如「2026 年数据」）
    expect(screen.getByText("2026 年数据")).toBeTruthy();
    expect(container.textContent).toContain("决策数据卡");
    // 提取依据 details：字段 · 原文「…」 · 置信度
    expect(container.textContent).toContain("提取依据（原文证据 · 置信度）");
    expect(container.textContent).toContain("enrollment_count · 原文「拟招收 120 人」 · 置信度 80%");
  });

  it("effective_year 为空时不出年份徽章（诚实降级）", async () => {
    mocks.apiGetMock.mockResolvedValue(
      makeNews({ structured_meta: { enrollment_count: 120 } }),
    );
    const { container } = render(<KaoyanNewsDetailPage />);
    await screen.findByText("2026 考研网上报名时间公布");
    expect(container.textContent).not.toContain("年数据");
  });

  it("质量徽章 hover title 显示实际扣分原因（逐行）", async () => {
    mocks.apiGetMock.mockResolvedValue(
      makeNews({
        quality_grade: "A",
        quality_score: 84,
        quality_reasons: ["内容完整度 24/30：正文约 600 字", "反软广 10/10：未命中"],
      }),
    );
    const { container } = render(<KaoyanNewsDetailPage />);
    await screen.findByText("2026 考研网上报名时间公布");
    const badge = container.querySelector('[title*="内容完整度 24/30"]');
    expect(badge).toBeTruthy();
    // reasons 以换行合并进 title
    expect(badge!.getAttribute("title")).toContain("反软广 10/10：未命中");
  });

  it("无 reasons 的质量徽章回退通用文案", async () => {
    mocks.apiGetMock.mockResolvedValue(makeNews({ quality_reasons: null }));
    const { container } = render(<KaoyanNewsDetailPage />);
    await screen.findByText("2026 考研网上报名时间公布");
    // 注：nwsapi 对含「+」的属性选择器字符串匹配异常，改用不含 + 的前缀定位
    const badge = container.querySelector('[title*="权威来源"]');
    expect(badge).toBeTruthy();
    // 回退通用文案（A 级），而非扣分原因格式（含「：」）
    expect(badge!.getAttribute("title")).toBe("权威来源 + 新鲜 + 内容完整（质量分 ≥75）");
  });

  it("详情页点「不准确」→ POST 反馈 + 成功 toast", async () => {
    mocks.authState.user = { id: "u-1" };
    mocks.feedbackPostMock.mockResolvedValue({ id: "f-1", message: "ok" });
    mocks.apiGetMock.mockResolvedValue(makeNews());
    render(<KaoyanNewsDetailPage />);
    await screen.findByText("2026 考研网上报名时间公布");
    fireEvent.click(screen.getByText("不准确"));
    await waitFor(() => expect(mocks.feedbackPostMock).toHaveBeenCalledTimes(1));
    expect(mocks.feedbackPostMock).toHaveBeenCalledWith({
      target_type: "kaoyan_news",
      target_id: mocks.paramsId,
      feedback_type: "unhelpful",
      reason: null,
    });
    expect(mocks.toast.push).toHaveBeenCalledWith("已收到反馈", "success");
  });
});
