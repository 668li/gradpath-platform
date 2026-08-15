// frontend/tests/gwy-compare-page.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, screen } from "@testing-library/react";
import { gwyPositionsApi, gwyScoreLinesApi } from "@/lib/api/gwy";
import { useGwyCompareStore } from "@/stores/gwy-compare";
import type { GwyPositionResponse } from "@/types";

// 对比页依赖 gwyPositionsApi.get 与 gwyScoreLinesApi.list，mock 掉网络层
vi.mock("@/lib/api/gwy", () => ({
  gwyPositionsApi: {
    list: vi.fn(),
    get: vi.fn(),
    stats: vi.fn(),
  },
  gwyScoreLinesApi: {
    list: vi.fn(),
    stats: vi.fn(),
  },
}));

const makeScoreLine = (
  code: string,
  batch: string,
  minScore: number,
  positionName = "一级行政执法员（一）",
) => ({
  id: `sl-${code}-${batch}`,
  year: 2026,
  batch,
  dept_name: "国家税务总局广东省税务局",
  dept_code: "130101",
  bureau: null,
  position_name: positionName,
  position_code: code,
  min_score: minScore,
  source_url: "http://dl.scs.gov.cn/download/x",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
});

const makePosition = (
  overrides: Partial<GwyPositionResponse> = {},
): GwyPositionResponse => ({
  id: "pos-1",
  year: 2026,
  exam_type: "国考",
  dept_code: "130101",
  dept_name: "国家税务总局广东省税务局",
  bureau: "深圳市税务局",
  agency_type: "中央国家行政机关省级以下直属机构",
  position_name: "一级行政执法员（一）",
  position_attr: "普通职位",
  position_distribution: "其他职位",
  position_desc: null,
  position_code: "130101001",
  org_level: "县（区）级及以下",
  exam_category: "行政执法类",
  recruit_count: 2,
  major_req: "经济学类、财政学类",
  education_req: "本科及以上",
  degree_req: "学士",
  political_status: "不限",
  min_work_years: "无限制",
  grassroots_exp_req: "无限制",
  professional_test: "否",
  interview_ratio: "3:1",
  work_location: "广东省深圳市",
  settle_location: "广东省深圳市",
  remarks: null,
  dept_website: null,
  phone1: "0755-12345678",
  phone2: null,
  phone3: null,
  sheet_name: "中央国家行政机关省级以下直属机构",
  source_url: "http://bm.scs.gov.cn",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
  ...overrides,
});

const pos1 = makePosition();
const pos2 = makePosition({
  id: "pos-2",
  dept_name: "国家税务总局北京市税务局",
  bureau: "西城区税务局",
  position_name: "一级行政执法员（二）",
  position_code: "130101002",
  recruit_count: 3,
  education_req: "仅限本科",
  work_location: "北京市西城区",
  political_status: "中共党员",
});

const byId: Record<string, GwyPositionResponse> = { "pos-1": pos1, "pos-2": pos2 };

function seedCompareIds(ids: string[]) {
  // zustand persist 的存储格式：{ state, version }
  localStorage.setItem("gwy-compare-ids", JSON.stringify({ state: { ids }, version: 0 }));
}

async function loadComparePage() {
  const { default: GwyComparePage } = await import("@/app/(app)/civil-service/positions/compare/page");
  return GwyComparePage;
}

describe("国考职位对比页", () => {
  beforeEach(() => {
    localStorage.clear();
    useGwyCompareStore.setState({ ids: [] });
    vi.mocked(gwyPositionsApi.get).mockImplementation((id: string) =>
      Promise.resolve(byId[id]),
    );
    // 默认无进面分数线数据；需要时按职位代码覆盖 mock
    vi.mocked(gwyScoreLinesApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
  });

  it("无选中职位时显示空状态", async () => {
    const GwyComparePage = await loadComparePage();
    render(<GwyComparePage />);
    expect(await screen.findByText("暂无对比职位")).toBeDefined();
    expect(screen.getByText("去挑选职位")).toBeDefined();
  });

  it("从 localStorage 恢复清单并渲染对比表格", async () => {
    seedCompareIds(["pos-1", "pos-2"]);
    const GwyComparePage = await loadComparePage();
    render(<GwyComparePage />);
    // 部门名出现在表头与"招录机关"行两处
    expect(await screen.findAllByText("国家税务总局广东省税务局")).toHaveLength(2);
    expect(screen.getAllByText("国家税务总局北京市税务局")).toHaveLength(2);
    // 字段维度渲染
    expect(screen.getByText("招录机关")).toBeDefined();
    expect(screen.getByText("学历要求")).toBeDefined();
    // 两个职位的差异化字段都在表里
    expect(screen.getByText("本科及以上")).toBeDefined();
    expect(screen.getByText("仅限本科")).toBeDefined();
    expect(screen.getByText("中共党员")).toBeDefined();
  });

  it("点击移除按钮后该职位列消失", async () => {
    seedCompareIds(["pos-1", "pos-2"]);
    const GwyComparePage = await loadComparePage();
    render(<GwyComparePage />);
    await screen.findAllByText("国家税务总局广东省税务局");
    fireEvent.click(screen.getByLabelText("移除 一级行政执法员（一）"));
    // pos-1 移除后只剩 pos-2
    await screen.findAllByText("国家税务总局北京市税务局");
    expect(screen.queryByText("国家税务总局广东省税务局")).toBeNull();
    expect(screen.queryByText("一级行政执法员（一）")).toBeNull();
  });

  it("展示按职位代码关联的进面最低分", async () => {
    seedCompareIds(["pos-1", "pos-2"]);
    vi.mocked(gwyScoreLinesApi.list).mockImplementation((params) => {
      const code = params?.position_code;
      const items =
        code === "130101001"
          ? [makeScoreLine(code, "首批", 122.8), makeScoreLine(code, "补充录用", 146.7)]
          : code === "130101002"
            ? [makeScoreLine(code, "首批", 128.5, "一级行政执法员（二）")]
            : [];
      return Promise.resolve({ items, total: items.length, page: 1, page_size: 20 });
    });
    const GwyComparePage = await loadComparePage();
    render(<GwyComparePage />);
    await screen.findAllByText("国家税务总局广东省税务局");
    // 进面最低分维度行
    expect(screen.getByText("进面最低分")).toBeDefined();
    // pos-1：首批 + 补充录用两批次聚合展示
    expect(screen.getByText("首批 122.8 分 · 补充录用 146.7 分")).toBeDefined();
    // pos-2：仅首批
    expect(screen.getByText("首批 128.5 分")).toBeDefined();
  });

  it("清空对比后显示空状态", async () => {
    seedCompareIds(["pos-1"]);
    const GwyComparePage = await loadComparePage();
    render(<GwyComparePage />);
    await screen.findAllByText("国家税务总局广东省税务局");
    fireEvent.click(screen.getByText("清空对比"));
    expect(await screen.findByText("暂无对比职位")).toBeDefined();
  });

  it("选中职位不存在时自动移出清单", async () => {
    seedCompareIds(["pos-1", "ghost"]);
    vi.mocked(gwyPositionsApi.get).mockImplementation((id: string) =>
      id === "ghost" ? Promise.reject(new Error("404")) : Promise.resolve(byId[id]),
    );
    const GwyComparePage = await loadComparePage();
    render(<GwyComparePage />);
    await screen.findAllByText("国家税务总局广东省税务局");
    expect(useGwyCompareStore.getState().ids).toEqual(["pos-1"]);
  });
});
