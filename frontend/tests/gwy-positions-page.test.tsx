// frontend/tests/gwy-positions-page.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import GwyPositionsPage from "@/app/(app)/civil-service/positions/page";
import { useGwyCompareStore } from "@/stores/gwy-compare";
import type {
  GwyPositionListResponse,
  GwyPositionResponse,
  GwyPositionStatsResponse,
  GwyScoreLineListResponse,
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
  position_desc: "负责税收征管及相关涉税业务处理",
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
  dept_website: "https://guangdong.chinatax.gov.cn",
  phone1: "0755-12345678",
  phone2: null,
  phone3: null,
  sheet_name: "中央国家行政机关省级以下直属机构",
  source_url: "http://bm.scs.gov.cn/pp/gkweb/core/web/ui/business/auth/login.html",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
  ...overrides,
});

const listData: GwyPositionListResponse = {
  items: [
    makePosition(),
    makePosition({
      id: "pos-2",
      position_name: "一级行政执法员（二）",
      position_code: "130101002",
      dept_name: "国家税务总局北京市税务局",
      work_location: "北京市西城区",
      recruit_count: 3,
    }),
  ],
  total: 20714,
  page: 1,
  page_size: 12,
};

const statsData: GwyPositionStatsResponse = {
  total: 20714,
  by_province: [
    { key: "广东", count: 1283 },
    { key: "北京", count: 1146 },
  ],
  by_education: [{ key: "本科及以上", count: 15200 }],
  by_org_level: [{ key: "县（区）级及以下", count: 11000 }],
  by_exam_category: [{ key: "行政执法类", count: 14000 }],
};

const scoreLinesData: GwyScoreLineListResponse = {
  items: [
    {
      id: "sl-1",
      year: 2026,
      batch: "首批",
      dept_name: "国家税务总局广东省税务局",
      dept_code: "130101",
      bureau: null,
      position_name: "一级行政执法员（一）",
      position_code: "130101001",
      min_score: 122.8,
      source_url: "http://dl.scs.gov.cn/download/x",
      created_at: "2026-01-01T00:00:00",
      updated_at: "2026-01-01T00:00:00",
    },
    {
      id: "sl-2",
      year: 2026,
      batch: "补充录用",
      dept_name: "国家税务总局广东省税务局",
      dept_code: "130101",
      bureau: null,
      position_name: "一级行政执法员（一）",
      position_code: "130101001",
      min_score: 146.7,
      source_url: "http://dl.scs.gov.cn/download/x",
      created_at: "2026-01-01T00:00:00",
      updated_at: "2026-01-01T00:00:00",
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

function stubSwr(list: GwyPositionListResponse, stats: GwyPositionStatsResponse) {
  mocks.swrMock.mockImplementation((key: string | null) => {
    if (key == null) return { data: undefined, error: undefined, isLoading: false };
    if (String(key).includes("/stats")) {
      return { data: stats, error: undefined, isLoading: false };
    }
    if (String(key).includes("/gwy-score-lines")) {
      return { data: scoreLinesData, error: undefined, isLoading: false };
    }
    return { data: list, error: undefined, isLoading: false };
  });
}

describe("国考职位检索页", () => {
  beforeEach(() => {
    localStorage.clear();
    useGwyCompareStore.setState({ ids: [] });
    mocks.getMock.mockImplementation((k: string) => "");
    mocks.replaceMock.mockClear();
    stubSwr(listData, statsData);
  });

  it("渲染标题与统计概览卡片", () => {
    const { container } = render(<GwyPositionsPage />);
    expect(container.textContent).toContain("2026 国考职位检索");
    expect(container.textContent).toContain("职位总数");
    expect(container.textContent).toContain("20714");
  });

  it("渲染筛选控件与职位卡片", () => {
    const { container } = render(<GwyPositionsPage />);
    expect(container.textContent).toContain("全部地区");
    expect(container.textContent).toContain("全部学历");
    expect(container.textContent).toContain("一级行政执法员（一）");
    expect(container.textContent).toContain("招 2 人");
    expect(container.textContent).toContain("国家税务总局北京市税务局");
    // 分页信息：20714 / 12 = 1727 页
    expect(container.textContent).toContain("共 20714 个职位");
    expect(container.textContent).toContain("第 1 / 1727 页");
  });

  it("点击职位卡片展开详情", () => {
    const { container, getByText } = render(<GwyPositionsPage />);
    expect(container.textContent).not.toContain("咨询电话1");
    fireEvent.click(getByText("一级行政执法员（一）"));
    expect(container.textContent).toContain("招录机关");
    expect(container.textContent).toContain("专业要求");
    expect(container.textContent).toContain("0755-12345678");
    expect(container.textContent).toContain("负责税收征管及相关涉税业务处理");
  });

  it("展开详情后展示按职位代码关联的进面最低分", () => {
    const { container, getByText } = render(<GwyPositionsPage />);
    expect(container.textContent).not.toContain("进面最低分");
    fireEvent.click(getByText("一级行政执法员（一）"));
    // 首批 122.8 + 补充录用 146.7 聚合为一行
    expect(container.textContent).toContain("进面最低分");
    expect(container.textContent).toContain("首批 122.8 分 · 补充录用 146.7 分");
  });

  it("无进面数据时详情不显示分数线区块", () => {
    mocks.swrMock.mockImplementation((key: string | null) => {
      if (key == null) return { data: undefined, error: undefined, isLoading: false };
      if (String(key).includes("/stats")) {
        return { data: statsData, error: undefined, isLoading: false };
      }
      if (String(key).includes("/gwy-score-lines")) {
        return { data: { ...scoreLinesData, items: [], total: 0 }, error: undefined, isLoading: false };
      }
      return { data: listData, error: undefined, isLoading: false };
    });
    const { container, getByText } = render(<GwyPositionsPage />);
    fireEvent.click(getByText("一级行政执法员（一）"));
    expect(container.textContent).toContain("招录机关");
    expect(container.textContent).not.toContain("进面最低分");
  });

  it("勾选职位后显示底部对比栏", () => {
    const { container, getAllByText } = render(<GwyPositionsPage />);
    expect(container.textContent).not.toContain("已选");
    fireEvent.click(getAllByText("对比")[0]);
    expect(container.textContent).toContain("已选 1 / 6 个职位");
    expect(container.textContent).toContain("对比职位");
    expect(container.textContent).toContain("清空");
  });

  it("再点一次取消勾选，对比栏消失", () => {
    const { container, getAllByText } = render(<GwyPositionsPage />);
    const firstChip = getAllByText("对比")[0];
    fireEvent.click(firstChip);
    expect(container.textContent).toContain("已选 1 / 6 个职位");
    fireEvent.click(getAllByText("已对比")[0]);
    expect(container.textContent).not.toContain("已选");
  });

  it("列表为空时显示空状态", () => {
    stubSwr({ ...listData, items: [], total: 0 }, statsData);
    const { container } = render(<GwyPositionsPage />);
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
    const { container } = render(<GwyPositionsPage />);
    expect(container.textContent).toContain("加载失败");
  });
});
