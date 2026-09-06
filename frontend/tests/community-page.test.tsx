// frontend/tests/community-page.test.tsx
/** 考研社区页测试 — 质量徽章 / tab / 空态 / 用户内容纯净性。
 *
 * 模式同 kaoyan-news-pages：mock next/navigation + @/lib/api（页面用
 * useState+useEffect 直连 API，不走 swr）+ @/components/ui/toast。
 *
 * 2026-09-05 社区假数据清理：外部经验 tab / ExternalExperienceCard /
 * Trae 灵感案例已按"社区只能有用户自己发的信息"拍板移除，
 * 原外部 tab（软广标注/决策 chips/Phase I 证据链）测试随之删除，
 * 新增「社区页不渲染外部内容」的结构免疫断言。
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
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

function stubExperienceList(items: ExperiencePostResponse[]) {
  // 模拟真实契约：后端 source_platform=user 只返回用户内容，external 只在显式请求时返回
  mocks.experienceListMock.mockImplementation((params: { source_platform?: string } = {}) => {
    const filtered =
      params.source_platform === "user"
        ? items.filter((p) => (p.source_platform ?? "user") === "user")
        : params.source_platform === "external"
          ? items.filter((p) => p.source_platform && p.source_platform !== "user")
          : items.filter((p) => (p.source_platform ?? "user") === "user");
    return Promise.resolve({ items: filtered, total: filtered.length, page: 1, page_size: 10 });
  });
}

describe("考研社区页", () => {
  beforeEach(() => {
    mocks.pushMock.mockClear();
    mocks.toast.push.mockClear();
    mocks.experienceListMock.mockReset();
    mocks.qaListMock.mockReset();
    mocks.qaListMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 });
  });

  it("站内经验贴渲染 A/B 质量徽章与分类 tab", async () => {
    stubExperienceList([
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
    // 两个 tab 均渲染（外部经验 tab 已按 2026-09-05 拍板移除）
    expect(container.textContent).toContain("经验贴");
    expect(container.textContent).toContain("问答互助");
  });

  it("社区页不渲染外部内容（结构免疫：假数据即使入表也不出现在社区）", async () => {
    // 模拟污染场景：表里混入外部爬虫内容（API 层持有全量）
    stubExperienceList([
      makePost({ id: "u-ok", title: "真实用户经验", source_platform: "user" }),
      makePost({ id: "e-bad", title: "爬虫搬运内容", source_platform: "bilibili" }),
    ]);
    const { container } = render(<CommunityPage />);
    await screen.findByText("真实用户经验");
    // 免疫链第一环：页面必须以 source_platform=user 请求（后端契约据此过滤）
    expect(mocks.experienceListMock).toHaveBeenCalledWith(
      expect.objectContaining({ source_platform: "user" }),
    );
    // 免疫链第二环：契约过滤生效，外部内容不出现在页面
    expect(container.textContent).not.toContain("爬虫搬运内容");
    // 外部经验相关 UI 不再存在
    expect(container.textContent).not.toContain("外部经验精选");
    expect(container.textContent).not.toContain("Trae");
  });

  it("无质量分的历史贴不渲染徽章（诚实降级）", async () => {
    stubExperienceList([makePost({ title: "旧经验贴", quality_grade: undefined, quality_score: undefined })]);
    const { container } = render(<CommunityPage />);
    await screen.findByText("旧经验贴");
    expect(container.textContent).not.toContain("A 优质");
    expect(container.textContent).not.toContain("B 良好");
  });

  it("站内经验贴空态显示「暂无经验贴」", async () => {
    stubExperienceList([]);
    render(<CommunityPage />);
    await screen.findByText("暂无经验贴");
    expect(screen.getByText("成为第一个分享经验的人吧")).toBeTruthy();
  });
});
