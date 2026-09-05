import { describe, expect, it } from "vitest";

import { extractWarnings } from "@/components/assessment/warning-utils";

describe("extractWarnings", () => {
  it("无【作答提示】标记时原样返回且 warnings 为空", () => {
    const summary = "你的霍兰德代码是 RIA，倾向于……";
    const { cleanSummary, warnings } = extractWarnings(summary);
    expect(cleanSummary).toBe(summary);
    expect(warnings).toEqual([]);
  });

  it("单条提示：正文与提示分离", () => {
    const summary = "你的霍兰德代码是 RIA。\n\n【作答提示】你的作答几乎都为同一选项，结果可能偏颇，解读时请留意。";
    const { cleanSummary, warnings } = extractWarnings(summary);
    expect(cleanSummary).toBe("你的霍兰德代码是 RIA。");
    expect(warnings).toEqual(["你的作答几乎都为同一选项，结果可能偏颇，解读时请留意。"]);
  });

  it("多条提示按「；」拆分并去首尾空白", () => {
    const summary = "正文内容。【作答提示】提示一；提示二；存在 2 个未知题号（['q49', 'q50']），已忽略。";
    const { cleanSummary, warnings } = extractWarnings(summary);
    expect(cleanSummary).toBe("正文内容。");
    expect(warnings).toEqual(["提示一", "提示二", "存在 2 个未知题号（['q49', 'q50']），已忽略。"]);
  });

  it("标记后为空串时 warnings 为空且正文保留", () => {
    const summary = "只有正文。【作答提示】";
    const { cleanSummary, warnings } = extractWarnings(summary);
    expect(cleanSummary).toBe("只有正文。");
    expect(warnings).toEqual([]);
  });
});
