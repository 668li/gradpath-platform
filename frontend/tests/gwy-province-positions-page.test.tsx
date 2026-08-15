// frontend/tests/gwy-province-positions-page.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import GwyProvincePositionsPage from "@/app/(app)/civil-service/province-positions/page";
import type {
  GwyProvincePositionListResponse,
  GwyProvincePositionResponse,
  GwyProvincePositionStatsResponse,
} from "@/types";

// vi.mock 工厂在 import 时执行，模块级变量需用 vi.hoisted 避免 TDZ
const mocks = vi.hoisted(() => ({
  replaceMock: vi.fn(),
  pushMock: vi.fn(),
  getMock: vi.fn((k: string) => ""),
  swrMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replaceMock, push: mocks.pushMock }),
  useSearchParams: () => ({
    get: mocks.getMock,
    toString: () => "",
  }),
}));

vi.mock("swr", () => ({
  default: mocks.swrMock,
}));

const makePosition = (
  overrides: Partial<GwyProvincePositionResponse> = {},
): GwyProvincePositionResponse => ({
  id: "pos-1",
  year: 2026,
  province: "广东",
  dept_name: "中共广东省委老干部局",
  dept_code: "1990007",
  position_name: "综合岗一级主任科员以下",
  position_code: "19900072641001",
  position_desc: "负责机关综合事务管理",
  position_type: "综合管理类",
  recruit_count: 2,
  education_req: "研究生",
  degree_req: "硕士",
  major_req_grad: "哲学(A01),政治学(A0302)",
  major_req_undergrad: "不限",
  major_req_junior: null,
  grassroots_exp_req: "否",
  psych_test: null,
  fresh_grad_only: "否",
  other_requirements: null,
  exam_region: "广州",
  sheet_name: "县以上机关",
  source_url: "https://www.gdzz.gov.cn/public/广东省2026年考试录用公务员公告附件.zip",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
  ...overrides,
});

const listData: GwyProvincePositionListResponse = {
  items: [
    makePosition(),
    makePosition({
      id: "pos-2",
      position_name: "执法勤务岗",
      position_code: "19900072641002",
      dept_name: "广东省公安厅",
      education_req: "本科",
      sheet_name: "公安",
      position_type: "执法勤务类",
      recruit_count: 3,
      fresh_grad_only: "应届毕业生",
      psych_test: "是",
    }),
  ],
  total: 9344,
  page: 1,
  page_size: 12,
};

const statsData: GwyProvincePositionStatsResponse = {
  total: 9344,
  total_recruit: 11779,
  by_sheet: [
    { key: "县以上机关", count: 5027 },
    { key: "乡镇机关", count: 2343 },
    { key: "公安", count: 863 },
  ],
  by_education: [
    { key: "本科以上", count: 4919 },
    { key: "本科", count: 2243 },
  ],
  by_region: [
    { key: "广州", count: 1359 },
    { key: "湛江", count: 679 },
  ],
  by_fresh_grad_only: [
    { key: "否", count: 5036 },
    { key: "应届毕业生", count: 2847 },
  ],
};

function stubSwr(list: GwyProvincePositionListResponse, stats: GwyProvincePositionStatsResponse) {
  mocks.swrMock.mockImplementation((key: string | null) => {
    if (key == null) return { data: undefined, error: undefined, isLoading: false };
    if (String(key).includes("/stats")) {
      return { data: stats, error: undefined, isLoading: false };
    }
    return { data: list, error: undefined, isLoading: false };
  });
}

describe("省考职位检索页", () => {
  beforeEach(() => {
    localStorage.clear();
    mocks.getMock.mockImplementation((k: string) => "");
    mocks.replaceMock.mockClear();
    stubSwr(listData, statsData);
  });

  it("渲染标题与统计概览卡片", () => {
    const { container } = render(<GwyProvincePositionsPage />);
    expect(container.textContent).toContain("2026 省考职位检索");
    expect(container.textContent).toContain("职位总数");
    expect(container.textContent).toContain("9344");
    expect(container.textContent).toContain("11779");
  });

  it("渲染筛选控件与职位卡片", () => {
    const { container } = render(<GwyProvincePositionsPage />);
    expect(container.textContent).toContain("全部招录系统");
    expect(container.textContent).toContain("全部学历");
    expect(container.textContent).toContain("全部考区");
    expect(container.textContent).toContain("综合岗一级主任科员以下");
    expect(container.textContent).toContain("招 2 人");
    expect(container.textContent).toContain("广东省公安厅");
    // 分页信息：9344 / 12 = 779 页
    expect(container.textContent).toContain("共 9344 个职位");
    expect(container.textContent).toContain("第 1 / 779 页");
  });

  it("筛选选项来自 stats 真实分布", () => {
    const { container } = render(<GwyProvincePositionsPage />);
    expect(container.textContent).toContain("县以上机关（5027）");
    expect(container.textContent).toContain("本科以上（4919）");
    expect(container.textContent).toContain("广州（1359）");
  });

  it("点击职位卡片展开详情", () => {
    const { container, getByText } = render(<GwyProvincePositionsPage />);
    expect(container.textContent).not.toContain("研究生专业");
    fireEvent.click(getByText("综合岗一级主任科员以下"));
    expect(container.textContent).toContain("单位代码");
    expect(container.textContent).toContain("研究生专业");
    expect(container.textContent).toContain("哲学(A01),政治学(A0302)");
    expect(container.textContent).toContain("负责机关综合事务管理");
  });

  it("应届限制与心理测评徽章按需展示", () => {
    const { container } = render(<GwyProvincePositionsPage />);
    // pos-1 非应届且无心理测评 → 不显示徽章；pos-2 应届 + 心理测评 → 显示
    const badges = container.querySelectorAll(".bg-amber-50");
    expect(badges.length).toBeGreaterThan(0);
    expect(container.textContent).toContain("应届毕业生");
  });

  it("列表为空时显示空状态", () => {
    stubSwr({ ...listData, items: [], total: 0 }, statsData);
    const { container } = render(<GwyProvincePositionsPage />);
    expect(container.textContent).toContain("没有匹配的职位");
  });

  it("加载失败时显示错误提示", () => {
    mocks.swrMock.mockImplementation((key: string | null) => {
      if (key == null) return { data: undefined, error: undefined, isLoading: false };
      if (String(key).includes("/stats")) {
        return { data: statsData, error: undefined, isLoading: false };
      }
      return { data: undefined, error: new Error("boom"), isLoading: false };
    });
    const { container } = render(<GwyProvincePositionsPage />);
    expect(container.textContent).toContain("加载失败");
  });
});
