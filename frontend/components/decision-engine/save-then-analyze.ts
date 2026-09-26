// frontend/components/decision-engine/save-then-analyze.ts
// 保存与 AI 生成两阶段执行（R-09）。独立模块：Next.js page 文件禁止导出自定义符号
// （tsc/next build 强约束，A8 部署实锤），逻辑与页面分离才可测。
import type { decisionAnalysisApi } from "@/lib/api";
import type { DecisionAnalysisResponse } from "@/types";

export type SaveThenAnalyzeResult =
  | { ok: true; id: string; ai: string | null; aiFailed: boolean }
  | { ok: false };

/** 保存与 AI 生成两阶段执行，失败态分离（R-09）：
 * 保存失败 = { ok: false }；保存成功但 AI 上游失败 = aiFailed: true（记录已落库可回看）。 */
export async function saveThenAnalyze(
  api: Pick<typeof decisionAnalysisApi, "create" | "generateAiAnalysis">,
  payload: Parameters<typeof decisionAnalysisApi.create>[0],
): Promise<SaveThenAnalyzeResult> {
  let analysis: DecisionAnalysisResponse;
  try {
    analysis = await api.create(payload);
  } catch {
    return { ok: false };
  }
  try {
    const aiRes = await api.generateAiAnalysis(analysis.id);
    return { ok: true, id: analysis.id, ai: aiRes.ai_analysis, aiFailed: false };
  } catch {
    return { ok: true, id: analysis.id, ai: null, aiFailed: true };
  }
}
