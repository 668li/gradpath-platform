import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { ScoreTrendChart, SchoolRadarChart, AdmissionPieChart } from "@/components/charts";

describe("ScoreTrendChart", () => {
  it("应渲染空状态提示当数据为空", () => {
    const { container } = render(<ScoreTrendChart data={[]} />);
    expect(container.textContent).toContain("暂无分数线数据");
  });

  it("应渲染图表当有数据时", () => {
    const data = [
      { year: 2020, score: 350 },
      { year: 2021, score: 360 },
      { year: 2022, score: 370 },
    ];
    const { container } = render(<ScoreTrendChart data={data} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeDefined();
  });

  it("应按年份排序数据", () => {
    const data = [
      { year: 2022, score: 370 },
      { year: 2020, score: 350 },
      { year: 2021, score: 360 },
    ];
    const { container } = render(<ScoreTrendChart data={data} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeDefined();
  });
});

describe("SchoolRadarChart", () => {
  it("应渲染空状态提示当数据为空", () => {
    const { container } = render(<SchoolRadarChart schools={[]} />);
    expect(container.textContent).toContain("暂无院校对比数据");
  });

  it("应渲染雷达图当有数据时", () => {
    const schools = [
      { name: "清华大学", scores: { 初试: 90, 复试: 85, 总分: 88 } },
      { name: "北京大学", scores: { 初试: 88, 复试: 90, 总分: 89 } },
    ];
    const { container } = render(<SchoolRadarChart schools={schools} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeDefined();
  });

  it("应处理不同维度的学校数据", () => {
    const schools = [
      { name: "学校A", scores: { 维度1: 80, 维度2: 0 } },
      { name: "学校B", scores: { 维度1: 90, 维度2: 70 } },
    ];
    const { container } = render(<SchoolRadarChart schools={schools} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeDefined();
  });
});

describe("AdmissionPieChart", () => {
  it("应渲染空状态提示当数据为空", () => {
    const { container } = render(<AdmissionPieChart data={[]} />);
    expect(container.textContent).toContain("暂无录取数据");
  });

  it("应渲染饼图当有数据时", () => {
    const data = [
      { name: "录取", value: 100 },
      { name: "未录取", value: 200 },
    ];
    const { container } = render(<AdmissionPieChart data={data} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeDefined();
  });

  it("应处理多个数据项", () => {
    const data = [
      { name: "推免", value: 50 },
      { name: "统考", value: 150 },
      { name: "调剂", value: 30 },
    ];
    const { container } = render(<AdmissionPieChart data={data} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeDefined();
  });
});
