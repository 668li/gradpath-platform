// frontend/components/__tests__/interpret-card.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { InterpretCard } from "@/components/assessment/interpret-card";
import type { AssessmentInterpretResponse } from "@/types";
import type { PathMetrics } from "@/types/path-comparison";

const metric: PathMetrics = {
  path_type: "kaoyan",
  target_role: "学术深造",
  income_1y: "—",
  income_3y: "—",
  income_5y: "硕士起薪中位",
  risk_level: "medium",
  risk_description: "统考竞争",
  growth_score: 70,
  time_cost_months: 36,
  match_score: 80,
  match_description: "研究型偏好契合",
  pros: ["学历跃迁"],
  cons: ["时间成本"],
  evidence: [],
};

const fullData: AssessmentInterpretResponse = {
  has_assessment: true,
  assessment: { type: "holland", result_code: "ISA", scores: {}, result_summary: "s" },
  profile: { major: "软件工程", target_direction: "考研" },
  interpretation: {
    primary_lean: "kaoyan",
    lean_scores: { kaoyan: 3 },
    reason: "你的研究型兴趣与考研深造路径契合。",
  },
  paths: [metric],
  recommendation: "建议主攻考研",
  position_analysis: null,
  school_analysis: null,
  peer_destinations: { has_data: false, peer_count: 0, distribution: [] },
  major_prospect: {},
  data_notes: ["测评类型只提供方向偏好，不作为报考结论；岗位可报数/进面线/薪资/院校均来自真实专有数据。"],
};

describe("InterpretCard", () => {
  it("加载中显示诚实等待文案", () => {
    render(<InterpretCard data={null} loading error={null} />);
    expect(screen.getByText(/正在结合你的真实报考数据生成专属解读/)).toBeDefined();
  });

  it("无测评时显示引导 message", () => {
    render(
      <InterpretCard
        data={{ has_assessment: false, message: "完成一次职业测评后解锁" }}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByText("完成一次职业测评后解锁")).toBeDefined();
  });

  it("倒置：无测评但 profile 出了路径 → 渲染完整卡 + 测评入口，不伪造偏好", () => {
    const profileOnly: AssessmentInterpretResponse = {
      has_assessment: false,
      assessment: null,
      profile: { major: "计算机科学与技术" },
      interpretation: {
        primary_lean: null,
        lean_scores: null,
        reason: "暂无测评信号：下方路径由你的专业与身份直接生成；完成 60 秒职业测评可让方向偏好更稳。",
      },
      paths: [metric],
      recommendation: "建议主攻考研",
      position_analysis: null,
      school_analysis: null,
      peer_destinations: { has_data: false, peer_count: 0, distribution: [] },
      major_prospect: {},
      data_notes: [],
    };
    render(<InterpretCard data={profileOnly} loading={false} error={null} />);
    expect(screen.getByText("学术深造")).toBeDefined(); // PathResultCard 真实渲染
    const cta = screen.getByText("完成 60 秒职业测评，兴趣信号更准 →");
    expect(cta.closest("a")?.getAttribute("href")).toBe("/assessment");
    expect(screen.queryByText(/^偏好：/)).toBeNull(); // 无测评不伪造 lean 标签
    expect(screen.queryByText("测评只提供方向偏好，不作报考结论")).toBeNull();
  });

  it("接口失败时不编造，显示降级说明", () => {
    render(<InterpretCard data={null} loading={false} error="网络异常" />);
    expect(screen.getByText(/专属解读暂时没能生成/)).toBeDefined();
  });

  it("完整数据渲染 lean 标签、解读理由、三路卡与溯源脚注", () => {
    render(<InterpretCard data={fullData} loading={false} error={null} />);
    expect(screen.getByText("偏好：考研深造")).toBeDefined();
    expect(screen.getByText(fullData.interpretation!.reason)).toBeDefined();
    expect(screen.getByText("学术深造")).toBeDefined(); // PathResultCard 内容
    expect(screen.getByText(/均来自真实专有数据/)).toBeDefined();
  });

  it("paths 为空时显示 recommendation 并引导补档案，不出现假三路", () => {
    const noPaths: AssessmentInterpretResponse = {
      ...fullData,
      paths: [],
      recommendation: "专业未在个人档案填写，暂时无法生成具体岗位/院校/进面线分析。",
    };
    render(<InterpretCard data={noPaths} loading={false} error={null} />);
    expect(screen.getByText(/专业未在个人档案填写/)).toBeDefined();
    expect(screen.getByText("前往个人档案补全 →")).toBeDefined();
    expect(screen.queryByText("学术深造")).toBeNull();
  });

  it("paths 非空时提供通往完整三路报告的入口，空态不出现", () => {
    const { unmount } = render(<InterpretCard data={fullData} loading={false} error={null} />);
    const cta = screen.getByText("查看完整三路报告 →");
    expect(cta.closest("a")?.getAttribute("href")).toBe("/decision-engine");
    unmount();

    const noPaths: AssessmentInterpretResponse = {
      ...fullData,
      paths: [],
      recommendation: "专业未在个人档案填写，暂时无法生成具体岗位/院校/进面线分析。",
    };
    render(<InterpretCard data={noPaths} loading={false} error={null} />);
    expect(screen.queryByText("查看完整三路报告 →")).toBeNull();
  });

  it("同分人群无样本时诚实占位", () => {
    render(<InterpretCard data={fullData} loading={false} error={null} />);
    expect(screen.getByText(/你是最早回传结果的一批/)).toBeDefined();
  });

  it("同分人群有样本时渲染真实分布", () => {
    const withPeer: AssessmentInterpretResponse = {
      ...fullData,
      peer_destinations: {
        has_data: true,
        peer_count: 12,
        distribution: [{ label: "上岸 985", count: 6, rate: 0.5 }],
      },
    };
    render(<InterpretCard data={withPeer} loading={false} error={null} />);
    expect(screen.getByText("上岸 985")).toBeDefined();
    expect(screen.getByText(/6 人 · 50%/)).toBeDefined();
  });
});
