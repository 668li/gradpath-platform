// 与后端 _validate_answers → result_summary 的拼接格式冻结对应：
// result_summary += "\n\n【作答提示】" + "；".join(warnings)
// 改后端这段文案前必须同步本文件（契约：标记串「【作答提示】」五个字不得变）。
export const ANSWER_HINT_MARKER = "【作答提示】";

export interface ExtractedWarnings {
  /** 去掉【作答提示】段后的正文（无提示时与原文一致） */
  cleanSummary: string;
  /** 逐条信度/完整性提示（无提示时空数组） */
  warnings: string[];
}

/** 从 result_summary 中拆出【作答提示】段，正文与提示各归各位。 */
export function extractWarnings(summary: string): ExtractedWarnings {
  const idx = summary.indexOf(ANSWER_HINT_MARKER);
  if (idx === -1) {
    return { cleanSummary: summary, warnings: [] };
  }
  const cleanSummary = summary.slice(0, idx).replace(/\s+$/, "");
  const raw = summary.slice(idx + ANSWER_HINT_MARKER.length).trim();
  const warnings = raw
    ? raw
        .split("；")
        .map((w) => w.trim())
        .filter(Boolean)
    : [];
  return { cleanSummary, warnings };
}
