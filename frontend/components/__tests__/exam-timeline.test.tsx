import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExamTimelineTab, STATUS_BADGE, dateLabel } from "@/components/civil-service/exam-timeline";
import type { TimelineExamDetail, TimelineNode } from "@/types/exam-timeline";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams("tab=timeline"),
}));
vi.mock("@/lib/api/client", () => ({
  getToken: () => null,
  setToken: vi.fn(),
  TOKEN_COOKIE: "gradpath_token",
}));

const _node = (over: Partial<TimelineNode>): TimelineNode => ({
  id: "n1",
  stage_key: "announce",
  title: "公告发布",
  seq: 1,
  date_status: "UNKNOWN",
  planned_date: null,
  planned_end_date: null,
  predict_basis: null,
  official_entry_url: null,
  source_url: null,
  collected_at: null,
  evidence_id: null,
  materials: [],
  action_guide: "关注公告",
  verifiable: false,
  dark_knowledge: [],
  ...over,
});

const _detail: TimelineExamDetail = {
  id: "e1",
  code: "guokao-2027",
  name: "2027 国考",
  track: "guokao",
  year: 2027,
  status: "upcoming",
  official_home_url: "http://bm.scs.gov.cn/",
  next_node: { stage_key: "announce", planned_date: null, date_status: "UNKNOWN", is_predictive: false },
  nodes: [
    _node({
      id: "n1",
      stage_key: "announce",
      date_status: "PREDICTED",
      planned_date: "2026-10-15",
      predict_basis: "按 2026 已证日期平移",
      verifiable: true,
    }),
    _node({ id: "n2", stage_key: "interview", title: "面试" }),
  ],
};

vi.mock("@/lib/api/exam-timeline", () => ({
  examTimelineApi: {
    listExams: vi.fn(async () => [_detail]),
    getExam: vi.fn(async () => _detail),
    mine: vi.fn(async () => []),
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    feedback: vi.fn(),
    getNode: vi.fn(),
  },
}));

describe("时间线诚实展示层（宪法 4）", () => {
  it("dateLabel：UNKNOWN 绝不显示日期，输出'暂无可核验来源'口径", () => {
    const label = dateLabel(_node({ verifiable: false }));
    expect(label).toBe("暂无可核验来源");
    expect(label).not.toMatch(/\d{4}-\d{2}/);
  });

  it("dateLabel：PREDICTED 必须带'预计'前缀（界面标注预测）", () => {
    expect(dateLabel(_node({ date_status: "PREDICTED", planned_date: "2026-10-15", verifiable: true }))).toBe(
      "预计 2026-10-15",
    );
  });

  it("OFFICIAL 状态徽章='官方'", () => {
    expect(STATUS_BADGE.OFFICIAL.label).toBe("官方");
    expect(STATUS_BADGE.PREDICTED.label).toBe("预测");
  });

  it("渲染环节骨架：预测行显示预计日期，无源行不出现任何日期", async () => {
    render(<ExamTimelineTab />);
    expect(await screen.findByText("公告发布")).toBeTruthy();
    expect(screen.getByText("面试")).toBeTruthy();
    expect(screen.getByText(/预计 2026-10-15/)).toBeTruthy();
    expect(screen.getAllByText("暂无可核验来源").length).toBe(1); // 仅 UNKNOWN 行的日期位
    expect(screen.getByText("无来源")).toBeTruthy();
    // UNKNOWN 行不得出现编造日期
    expect(screen.queryByText(/2027-\d{2}-\d{2}/)).toBeNull();
  });
});
