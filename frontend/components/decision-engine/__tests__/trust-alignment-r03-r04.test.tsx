// frontend/components/decision-engine/__tests__/trust-alignment-r03-r04.test.tsx
// R-03/R-04（spec 011 信任对齐第一批）：行动时间线与回传/模板/分享面
// 对用户不可见任何退役考公路分支；历史数据兼容为中性"已退役去向"。
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { buildTimeline } from "@/components/decision-engine/decision-report";
import { buildShareText } from "@/components/decision-engine/share-report-actions";
import { PATH_OPTIONS, OutcomeForm } from "@/components/decision-engine/outcome-form";
import { DECISION_TEMPLATES } from "@/components/decision-engine/decision-templates";
import type { DecisionEngineResponse } from "@/types/path-comparison";

const RETIRED_WORDS = ["考公", "国考", "省考", "行测", "申论", "进面", "入面", "三条路", "三路"];

describe("R-03 行动时间线（buildTimeline）", () => {
  it("任何毕业年份下不含退役线节点", () => {
    for (const gy of [2026, 2027, 2028]) {
      const items = buildTimeline(gy);
      const text = items.map((i) => `${i.title} ${i.desc}`).join("\n");
      for (const w of RETIRED_WORDS) {
        expect(text).not.toContain(w);
      }
    }
  });

  it("保留考研与就业节点，毕业条目不引用考公窗口", () => {
    const items = buildTimeline(2027);
    const titles = items.map((i) => i.title).join("|");
    expect(titles).toContain("考研报名");
    expect(titles).toContain("考研初试");
    expect(titles).toContain("秋招投递");
    expect(titles).toContain("春招");
    const grad = items.find((i) => i.title === "毕业");
    expect(grad).toBeDefined();
    expect(grad!.desc).not.toContain("考公");
  });
});

describe("R-04 回传/模板/分享考公面摘除", () => {
  it("回传去向选项不含考公", () => {
    expect(PATH_OPTIONS.some((o) => o.value === "civil_service")).toBe(false);
    expect(PATH_OPTIONS.every((o) => !o.label.includes("考公"))).toBe(true);
  });

  it("回传表单渲染不含考公字样（历史已回传态兼容中性展示）", () => {
    render(<OutcomeForm decisionId="x" outcome={null} onSaved={() => {}} />);
    const body = document.body.textContent ?? "";
    for (const w of RETIRED_WORDS) {
      expect(body).not.toContain(w);
    }
  });

  it("示例决策模板画廊不含考公模板", () => {
    expect(DECISION_TEMPLATES.some((t) => t.destination_type === "civil_service")).toBe(false);
    const text = JSON.stringify(DECISION_TEMPLATES);
    for (const w of RETIRED_WORDS) {
      expect(text).not.toContain(w);
    }
  });

  it("分享摘要文案不含考公（含 position_analysis 历史字段输入）", () => {
    const result = {
      id: "r1",
      input: { major: "计算机", graduation_year: 2027 },
      metrics: [
        { path_type: "kaoyan", match_score: 80, risk_level: "medium", target_role: "学术深造" },
        { path_type: "employment", match_score: 70, risk_level: "low", target_role: "软件开发" },
      ],
      position_analysis: { personalized_level: "中上" },
      recommendation: "建议主攻考研",
    } as unknown as DecisionEngineResponse;
    const text = buildShareText(result);
    for (const w of RETIRED_WORDS) {
      expect(text).not.toContain(w);
    }
    expect(text).toContain("考研");
    expect(text).toContain("就业");
  });
});
