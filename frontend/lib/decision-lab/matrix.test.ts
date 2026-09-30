import { describe, it, expect, beforeEach } from "vitest";
import {
  safeNumber,
  formatScore,
  normalizeMatrixResults,
  normalizeMatrixResponse,
  fillNeutralScores,
  sumWeights,
  NEUTRAL_SCORE,
} from "./matrix";
import {
  saveDecisionLabDraft,
  loadDecisionLabDraft,
  clearDecisionLabDraft,
  draftHasContent,
} from "./draft";

/** 夜班复验 TOP1：决策实验室矩阵计算崩溃（toFixed on undefined）的空值兜底回归 */
describe("safeNumber", () => {
  it("正常数字原样返回", () => {
    expect(safeNumber(7)).toBe(7);
    expect(safeNumber(0)).toBe(0);
    expect(safeNumber(-2.5)).toBe(-2.5);
  });

  it("非有限数字回退默认值", () => {
    expect(safeNumber(NaN)).toBe(0);
    expect(safeNumber(Infinity, 9)).toBe(9);
    expect(safeNumber(undefined, 3)).toBe(3);
    expect(safeNumber(null)).toBe(0);
  });

  it("数字字符串可解析，空串/垃圾串回退", () => {
    expect(safeNumber("8.5")).toBe(8.5);
    expect(safeNumber("")).toBe(0);
    expect(safeNumber("abc", 2)).toBe(2);
  });
});

describe("formatScore（toFixed 空值安全版）", () => {
  it("undefined/null/NaN 一律渲染 0.0，绝不抛异常", () => {
    expect(formatScore(undefined)).toBe("0.0");
    expect(formatScore(null)).toBe("0.0");
    expect(formatScore(NaN)).toBe("0.0");
  });

  it("正常值按位格式化", () => {
    expect(formatScore(7.25)).toBe("7.3");
    expect(formatScore("3", 0)).toBe("3");
  });
});

describe("normalizeMatrixResults（后端 option/total_score → 前端 name/total）", () => {
  it("后端 compute-matrix 实际形状（option/total_score/breakdown）正确映射", () => {
    const rows = normalizeMatrixResults([
      {
        option: "考研",
        total_score: 6.4,
        breakdown: [{ criterion: "薪资", weight: 60, score: 8, weighted: 4.8 }],
      },
    ]);
    expect(rows).toEqual([
      {
        name: "考研",
        total: 6.4,
        details: { 薪资: 4.8 },
      },
    ]);
  });

  it("前端历史形状（name/total/details）原样保留", () => {
    const rows = normalizeMatrixResults([
      { name: "就业", total: 5.1, details: { 薪资: 3.1 } },
    ]);
    expect(rows[0].name).toBe("就业");
    expect(rows[0].total).toBe(5.1);
    expect(rows[0].details).toEqual({ 薪资: 3.1 });
  });

  it("字段全缺失/单行非法也不抛异常，给中性兜底", () => {
    const rows = normalizeMatrixResults([{}, null, 42, { name: "", total: "垃圾" }]);
    expect(rows).toHaveLength(4);
    expect(rows[0]).toEqual({ name: "未命名选项", total: 0, details: {} });
    expect(rows[1]).toEqual({ name: "未命名选项", total: 0, details: {} });
    expect(rows[3].total).toBe(0);
  });

  it("非数组输入返回空数组（而非抛异常）", () => {
    expect(normalizeMatrixResults(undefined)).toEqual([]);
    expect(normalizeMatrixResults(null)).toEqual([]);
    expect(normalizeMatrixResults({})).toEqual([]);
  });

  it("breakdown 里 weighted 缺失时回退 score", () => {
    const rows = normalizeMatrixResults([
      { option: "A", total_score: 1, breakdown: [{ criterion: "x", score: 7 }] },
    ]);
    expect(rows[0].details).toEqual({ x: 7 });
  });
});

describe("normalizeMatrixResponse", () => {
  it("后端完整响应（含 winner）正确规范化", () => {
    const r = normalizeMatrixResponse({
      results: [
        { option: "考研", total_score: 6.4 },
        { option: "就业", total_score: 5.1 },
      ],
      winner: "考研",
    });
    expect(r.winner).toBe("考研");
    expect(r.results[0].name).toBe("考研");
    expect(r.results[1].total).toBe(5.1);
  });

  it("winner 缺失时取排序首位（后端按总分降序）", () => {
    const r = normalizeMatrixResponse({
      results: [
        { option: "考研", total_score: 6.4 },
        { option: "就业", total_score: 5.1 },
      ],
    });
    expect(r.winner).toBe("考研");
  });

  it("空响应/垃圾响应不抛异常", () => {
    expect(normalizeMatrixResponse(null)).toEqual({ results: [], winner: "" });
    expect(normalizeMatrixResponse({})).toEqual({ results: [], winner: "" });
    expect(normalizeMatrixResponse("垃圾").results).toEqual([]);
  });
});

describe("fillNeutralScores（未填评分按中性 5 分计）", () => {
  it("缺失/0/负数/NaN 一律补中性分", () => {
    const out = fillNeutralScores(
      [{ 薪资: 8, 成长: 0, 风险: -1, 城市: NaN }, {}],
      ["薪资", "成长", "风险", "城市", "通勤"],
    );
    expect(out[0]).toEqual({ 薪资: 8, 成长: NEUTRAL_SCORE, 风险: NEUTRAL_SCORE, 城市: NEUTRAL_SCORE, 通勤: NEUTRAL_SCORE });
    expect(out[1]).toEqual({ 薪资: NEUTRAL_SCORE, 成长: NEUTRAL_SCORE, 风险: NEUTRAL_SCORE, 城市: NEUTRAL_SCORE, 通勤: NEUTRAL_SCORE });
  });

  it("评分行整体缺失/非数组输入也不抛异常", () => {
    expect(fillNeutralScores(undefined, ["a"])).toEqual([]);
    expect(fillNeutralScores(null, ["a"])).toEqual([]);
    const out = fillNeutralScores([undefined, { a: 3 }], ["a"]);
    expect(out[0]).toEqual({ a: NEUTRAL_SCORE });
    expect(out[1]).toEqual({ a: 3 });
  });
});

describe("sumWeights（权重空值兜底求和）", () => {
  it("正常求和；非法权重按 0 计", () => {
    expect(sumWeights([{ weight: 60 }, { weight: 40 }])).toBe(100);
    expect(sumWeights([{ weight: NaN }, { weight: 40 }, {}])).toBe(40);
  });

  it("非数组输入返回 0", () => {
    expect(sumWeights(undefined)).toBe(0);
    expect(sumWeights("垃圾")).toBe(0);
  });
});

/** 草稿持久化：崩溃/误退后重进不丢向导进度 */
describe("decision-lab 草稿（localStorage）", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("保存后可完整恢复（roundtrip）", () => {
    saveDecisionLabDraft({
      title: "考研 vs 就业",
      options: ["考研", "就业"],
      step: "matrix",
      premortemReasons: ["考不上", "错过秋招", "经济压力大"],
      premortemResult: { categories: [{ category: "执行风险", reasons: ["拖延"] }], safeguards: [{ category: "执行风险", action: "周复盘" }] },
      criteria: [{ criterion: "薪资", weight: 60 }],
      matrixScores: [{ 薪资: 7 }],
      matrixResult: { results: [{ name: "考研", total: 6.4, details: {} }], winner: "考研" },
      redTeamQuestions: ["Q1"],
      redTeamAnswers: { "0": "回答" },
      aiAnalysis: null,
      savedAnalysisId: null,
    });
    const draft = loadDecisionLabDraft();
    expect(draft).not.toBeNull();
    expect(draft!.title).toBe("考研 vs 就业");
    expect(draft!.step).toBe("matrix");
    expect(draft!.criteria).toEqual([{ criterion: "薪资", weight: 60 }]);
    expect(draft!.matrixResult!.winner).toBe("考研");
    expect(draft!.redTeamAnswers["0"]).toBe("回答");
    expect(draftHasContent(draft!)).toBe(true);
  });

  it("损坏 JSON / 错误版本 / 选项不足 → 返回 null 不抛异常", () => {
    localStorage.setItem("gradpath:decision-lab:draft:v1", "{{{垃圾");
    expect(loadDecisionLabDraft()).toBeNull();

    localStorage.setItem(
      "gradpath:decision-lab:draft:v1",
      JSON.stringify({ version: 99, title: "x", options: ["a", "b"] }),
    );
    expect(loadDecisionLabDraft()).toBeNull();

    localStorage.setItem(
      "gradpath:decision-lab:draft:v1",
      JSON.stringify({ version: 1, title: "x", options: ["只有一个"] }),
    );
    expect(loadDecisionLabDraft()).toBeNull();
  });

  it("清除后读不到；空表单不值得恢复", () => {
    saveDecisionLabDraft({
      title: "",
      options: ["", ""],
      step: "setup",
      premortemReasons: [""],
      premortemResult: null,
      criteria: [{ criterion: "", weight: 30 }],
      matrixScores: [],
      matrixResult: null,
      redTeamQuestions: [],
      redTeamAnswers: {},
      aiAnalysis: null,
      savedAnalysisId: null,
    });
    const draft = loadDecisionLabDraft();
    expect(draft).not.toBeNull();
    expect(draftHasContent(draft!)).toBe(false);

    clearDecisionLabDraft();
    expect(loadDecisionLabDraft()).toBeNull();
  });
});
