// 续学卡组件测试（P1）— dashboard 页渲染「上次停在第 N 天」并链接到微行动页
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import DashboardPage from "@/app/(app)/dashboard/page";
import type { MicroActionPlanResponse } from "@/types/micro-action";

const mocks = vi.hoisted(() => ({
  toast: { push: vi.fn(), success: vi.fn() },
  overviewMock: vi.fn(),
  streakMock: vi.fn(),
  remindersMock: vi.fn(),
  pulseMock: vi.fn(),
  microPlanMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/dashboard",
}));

vi.mock("@/components/ui/toast", () => ({
  useToast: () => mocks.toast,
}));

// useApi mock：按 url 分发，未匹配的返回 undefined（次要数据不渲染）
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    useApi: (url: string | null) => {
      if (url === "/api/dashboard/overview")
        return { data: mocks.overviewMock(), error: undefined, isLoading: false, mutate: vi.fn() };
      if (url === "/api/streaks/stats")
        return { data: mocks.streakMock(), error: undefined, isLoading: false, mutate: vi.fn() };
      if (url === "/api/career-plans/reminders")
        return { data: [], error: undefined, isLoading: false, mutate: vi.fn() };
      if (url === "/api/decision-pulse")
        return { data: mocks.pulseMock(), error: undefined, isLoading: false, mutate: vi.fn() };
      if (url === "/api/micro-actions/plans/current")
        return { data: mocks.microPlanMock(), error: undefined, isLoading: false, mutate: vi.fn() };
      return { data: undefined, error: undefined, isLoading: false, mutate: vi.fn() };
    },
    microActionApi: actual.microActionApi,
  };
});

function makePlan(overrides: Partial<MicroActionPlanResponse> = {}): MicroActionPlanResponse {
  return {
    id: "plan-1",
    target_path: "employment",
    target_role: null,
    status: "active",
    started_at: "2026-09-01T00:00:00Z",
    completed_at: null,
    progress: 0,
    self_discovery_report: null,
    tasks: [
      { id: "t1", day_number: 1, task_type: "research", title: "查 3 个目标 JD", description: "", estimated_minutes: 20, status: "completed", completed_at: null, user_response: null, insight: null },
      { id: "t2", day_number: 2, task_type: "research", title: "看 2 个岗位 vlog", description: "", estimated_minutes: 20, status: "pending", completed_at: null, user_response: null, insight: null },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.overviewMock.mockReturnValue({
    decisions_count: 1,
    events_count: 1,
    skills_count: 1,
    retrospectives_count: 1,
    latest_decision: null,
    recent_events: [],
    skill_categories: {},
    latest_retrospective: null,
    timeline: [],
    condition_ledger: null,
  });
  mocks.streakMock.mockReturnValue(null);
  mocks.pulseMock.mockReturnValue(null);
  mocks.microPlanMock.mockReturnValue(null);
});

describe("dashboard 续学卡", () => {
  it("有未完成任务时显示「上次停在第 N 天：任务名」并链接 /micro-actions", async () => {
    mocks.microPlanMock.mockReturnValue(makePlan());
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText(/上次停在第 2 天：看 2 个岗位 vlog/)).toBeTruthy();
    });
    const link = screen.getByText(/上次停在第 2 天/).closest("a");
    expect(link?.getAttribute("href")).toBe("/micro-actions");
  });

  it("无未完成任务时不渲染续学卡", () => {
    mocks.microPlanMock.mockReturnValue(
      makePlan({ tasks: makePlan().tasks.map((t) => ({ ...t, status: "completed" as const })) }),
    );
    render(<DashboardPage />);
    expect(screen.queryByText(/上次停在第/)).toBeNull();
  });

  it("无当前 plan 时不渲染续学卡", () => {
    mocks.microPlanMock.mockReturnValue(null);
    render(<DashboardPage />);
    expect(screen.queryByText(/上次停在第/)).toBeNull();
  });
});
