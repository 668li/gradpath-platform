// frontend/app/(app)/decision-lab/__tests__/r09-save-then-analyze.test.ts
// R-09（spec 011）：保存与 AI 生成失败态分离——保存失败不误报，AI 失败不掩盖保存成功。
import { describe, it, expect } from "vitest";
import { saveThenAnalyze } from "@/app/(app)/decision-lab/page";
import type { DecisionAnalysisResponse } from "@/types";

const payload = { title: "测试决策", options: ["A", "B"] } as Parameters<
  typeof saveThenAnalyze
>[1];

function stubApi(
  createImpl: unknown,
  aiImpl: unknown,
): Parameters<typeof saveThenAnalyze>[0] {
  return {
    create: createImpl as never,
    generateAiAnalysis: aiImpl as never,
  } as never;
}

const savedRecord = { id: "a-1", ai_analysis: null } as unknown as DecisionAnalysisResponse;

describe("R-09 saveThenAnalyze 双态分离", () => {
  it("保存失败 → ok:false（仅此态提示保存失败）", async () => {
    const api = stubApi(() => Promise.reject(new Error("500")), () => Promise.resolve({}));
    const result = await saveThenAnalyze(api, payload);
    expect(result).toEqual({ ok: false });
  });

  it("保存成功但 AI 上游失败 → ok:true + aiFailed:true（记录已落库可回看）", async () => {
    const api = stubApi(
      () => Promise.resolve(savedRecord),
      () => Promise.reject(new Error("Arrearage")),
    );
    const result = await saveThenAnalyze(api, payload);
    expect(result).toMatchObject({ ok: true, id: "a-1", aiFailed: true, ai: null });
  });

  it("双成功 → ok:true + ai 内容 + aiFailed:false", async () => {
    const api = stubApi(
      () => Promise.resolve(savedRecord),
      () => Promise.resolve({ ai_analysis: "建议选 A" }),
    );
    const result = await saveThenAnalyze(api, payload);
    expect(result).toMatchObject({ ok: true, id: "a-1", aiFailed: false, ai: "建议选 A" });
  });
});
