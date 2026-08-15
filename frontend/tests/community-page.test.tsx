// frontend/tests/community-page.test.tsx
/** 考研社区页（Phase G/H）测试 — 质量徽章 / 软广标注 / 分类 tab / 空态。
 *
 * 模式同 kaoyan-news-pages：mock next/navigation + @/lib/api（页面用
 * useState+useEffect 直连 API，不走 swr）+ @/components/ui/toast。
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, screen } from "@testing-library/react";
import CommunityPage from "@/app/(app)/kaoyan/community/page";
import type { ExperiencePostResponse } from "@/types";

const mocks = vi.hoisted(() => ({
  pushMock: vi.fn(),
  getMock: vi.fn((k: string) => ""),
  // toast 对象保持稳定引用：页面 useCallback 依赖 toast，新对象会触发 effect 重跑
  toast: { push: vi.fn() },
  experienceListMock: vi.fn(),
  qaListMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.pushMock }),
  useSearchParams: () => ({ get: mocks.getMock, toString: () => "" }),
}));

vi.mock("@/components/ui/toast", () => ({
  useToast: () => mocks.toast,
}));

vi.mock("@/lib/api", () => ({
  kaoyanCommunityApi: {
    experiencePosts: { list: mocks.experienceListMock },
    qa: { list: mocks.qaListMock },
  },
}));

function makePost(overrides: Partial<ExperiencePostResponse> = {}): ExperiencePostResponse {
  return {
    id: "p-1",
    user_id: "u-1",
    author_name: "上岸学长",
    author_avatar: null,
    title: "408 一战上岸 985 经验",
    summary: "完整备考路线与避坑指南",
    content: "从 3 月开始复习，数据结构刷了 3 遍真题……",
    tags: ["408", "备考"],
    category: "备考",
    view_count: 12,
    like_count: 5,
    comment_count: 2,
    is_pinned: false,
    is_anonymous: false,
    status: "approved",
    source_platform: "user",
    source_url: null,
    external_view_count: 0,
    external_like_count: 0,
    is_verified: false,
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
    ...overrides,
  };
}

/** 按调用参数区分：source_platform=external → 外部经验列表，否则站内列表。 */
function stubExperienceList(externalItems: ExperiencePostResponse[], userItems: ExperiencePostResponse[]) {
  mocks.experienceListMock.mockImplementation((params: { source_platform?: string }) => {
    const items = params.source_platform === "external" ? externalItems : userItems;
    return Promise.resolve({ items, total: items.length, page: 1, page_size: 10 });
  });
}

describe("考研社区页（Phase G/H）", () => {
  beforeEach(() => {
    mocks.pushMock.mockClear();
    mocks.toast.push.mockClear();
    mocks.experienceListMock.mockReset();
    mocks.qaListMock.mockReset();
    mocks.qaListMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 });
  });

  it("站内经验贴渲染 A/B 质量徽章与分类 tab", async () => {
    stubExperienceList([], [
      makePost({ id: "p-a", title: "政治 80 分心得", quality_grade: "A", quality_score: 88 }),
      makePost({ id: "p-b", title: "二战心态调整", quality_grade: "B", quality_score: 60 }),
    ]);
    const { container } = render(<CommunityPage />);
    // 默认 tab=experience，等待异步列表渲染
    await screen.findByText("政治 80 分心得");
    expect(container.textContent).toContain("A 优质");
    expect(container.textContent).toContain("88");
    expect(container.textContent).toContain("B 良好");
    expect(container.textContent).toContain("60");
    // 三个 tab 均渲染
    expect(container.textContent).toContain("经验贴");
    expect(container.textContent).toContain("问答互助");
    expect(container.textContent).toContain("外部经验精选");
  });

  it("无质量分的历史贴不渲染徽章（诚实降级）", async () => {
    stubExperienceList([], [makePost({ title: "旧经验贴", quality_grade: undefined, quality_score: undefined })]);
    const { container } = render(<CommunityPage />);
    await screen.findByText("旧经验贴");
    expect(container.textContent).not.toContain("A 优质");
    expect(container.textContent).not.toContain("B 良好");
  });

  it("外部 tab：软广标注 + 结构化决策 chips（学科/院校/目标分）", async () => {
    stubExperienceList(
      [
        makePost({
          id: "e-promo",
          title: "保过班内部资料免费领",
          source_platform: "bilibili",
          external_view_count: 50000,
          external_like_count: 1200,
          is_promotion: true,
          promotion_confidence: 0.6,
          promotion_reason: "疑似软广:领资料,保过",
          structured_meta: { subject: "408", school: "北京理工大学", target_score: 380, audience: "一战" },
        }),
      ],
      [],
    );
    const { container } = render(<CommunityPage />);
    await screen.findByText("考研社区");
    // 切到外部经验 tab
    fireEvent.click(screen.getByText("外部经验精选"));
    await screen.findByText("保过班内部资料免费领");
    // 疑似推广标注（不隐藏）
    expect(container.textContent).toContain("疑似推广");
    // 标注原因在 title 属性（悬停提示）
    expect(screen.getByTitle("命中：疑似软广:领资料,保过")).toBeTruthy();
    // 结构化决策 chips
    expect(container.textContent).toContain("学科 408");
    expect(container.textContent).toContain("北京理工大学");
    expect(container.textContent).toContain("目标 380 分");
    expect(container.textContent).toContain("一战");
    // 外部互动数展示
    expect(container.textContent).toContain("50000");
  });

  it("外部 tab 分类下拉含「心态」「避坑」（Phase H 新分类）", async () => {
    stubExperienceList([], []);
    render(<CommunityPage />);
    await screen.findByText("考研社区");
    fireEvent.click(screen.getByText("外部经验精选"));
    await screen.findByText("共 0 条外部经验");
    const select = document.querySelector("select") as HTMLSelectElement;
    expect(select).toBeTruthy();
    const options = Array.from(select.options).map((o) => o.textContent);
    expect(options).toContain("心态");
    expect(options).toContain("避坑");
    expect(options).toContain("择校");
  });

  it("站内经验贴空态显示「暂无经验贴」", async () => {
    stubExperienceList([], []);
    render(<CommunityPage />);
    await screen.findByText("暂无经验贴");
    expect(screen.getByText("成为第一个分享经验的人吧")).toBeTruthy();
  });

  it("外部经验空态显示「暂无外部经验」", async () => {
    stubExperienceList([], []);
    render(<CommunityPage />);
    await screen.findByText("考研社区");
    fireEvent.click(screen.getByText("外部经验精选"));
    await screen.findByText("暂无外部经验");
  });
});
