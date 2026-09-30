/**
 * 决策实验室 — 矩阵结果规范化与数值空值兜底（纯函数，可单测）。
 *
 * 背景（夜班复验 TOP1）：后端 /api/decision-analysis/compute-matrix 实际返回
 * { results: [{ option, total_score, breakdown }], winner }（见
 * backend/app/services/decision_analysis_service.py compute_matrix），
 * 而页面历史契约按 { results: [{ name, total, details }] } 渲染——
 * r.total 为 undefined 时 toFixed 直接抛异常 → 错误边界接管 → 5 步向导草稿全丢。
 * 这里把两种形状统一收敛为前端契约，且任何字段缺失/非法都给中性兜底，
 * 保证任何操作顺序、任何后端返回形状都不抛异常。
 */

export interface MatrixResultRow {
  name: string;
  total: number;
  details: Record<string, number>;
}

export interface NormalizedMatrixResult {
  results: MatrixResultRow[];
  winner: string;
}

/** 任意值 → 有限数字，否则回退 fallback */
export function safeNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number") return Number.isFinite(value) ? value : fallback;
  if (typeof value === "string" && value.trim() !== "") {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
  return fallback;
}

/** toFixed 的空值安全版：非有限数字按 0 处理，任何输入都不抛异常 */
export function formatScore(value: unknown, digits = 1): string {
  return safeNumber(value, 0).toFixed(digits);
}

/** 取第一个非空字符串 */
function pickString(...candidates: unknown[]): string {
  for (const c of candidates) {
    if (typeof c === "string" && c.trim() !== "") return c;
  }
  return "";
}

/** details/breakdown 两种历史形状 → { 指标名: 加权分 } */
function normalizeDetails(raw: unknown): Record<string, number> {
  const details: Record<string, number> = {};
  if (Array.isArray(raw)) {
    // 后端 breakdown 形状: [{ criterion, weight, score, weighted }]
    for (const item of raw) {
      if (!item || typeof item !== "object") continue;
      const rec = item as Record<string, unknown>;
      const key = pickString(rec.criterion, rec.name);
      if (!key) continue;
      details[key] = safeNumber(rec.weighted ?? rec.total ?? rec.score, 0);
    }
  } else if (raw && typeof raw === "object") {
    for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
      details[k] = safeNumber(v, 0);
    }
  }
  return details;
}

/**
 * 把 compute-matrix 响应 / 存库 weighted_results 的多种历史形状
 * （{name,total} 与 {option,total_score}）统一为 { name, total, details }[]，
 * 单行/字段缺失返回中性兜底而非 undefined，绝不抛异常。
 */
export function normalizeMatrixResults(raw: unknown): MatrixResultRow[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    const rec = (item && typeof item === "object" ? item : {}) as Record<string, unknown>;
    return {
      name: pickString(rec.name, rec.option) || "未命名选项",
      total: safeNumber(rec.total ?? rec.total_score, 0),
      details: normalizeDetails(rec.details ?? rec.breakdown),
    };
  });
}

/**
 * 规范化 compute-matrix 接口响应；winner 缺失时取排序首位
 * （后端按总分降序排列，results[0] 即最高分）。
 */
export function normalizeMatrixResponse(raw: unknown): NormalizedMatrixResult {
  const rec = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const results = normalizeMatrixResults(rec.results);
  let winner = pickString(rec.winner);
  if (!winner && results.length > 0) winner = results[0].name;
  return { results, winner };
}

/** 中性默认评分：1-10 分制，未填写的格子按 5 计（等权中性，不偏向任何选项） */
export const NEUTRAL_SCORE = 5;

/**
 * 矩阵评分空值兜底：空白/非法（含 0——数字输入清空会得到 0）的格子
 * 一律补成中性 5 分，避免后端按 0 分计拉低该选项排名。
 * 行缺失/行对象非法同样兜底，保证任何填写顺序都安全。
 */
export function fillNeutralScores(
  matrixScores: unknown,
  criteriaNames: string[],
): Record<string, number>[] {
  const rows = Array.isArray(matrixScores) ? matrixScores : [];
  return rows.map((row) => {
    const source = row && typeof row === "object" ? (row as Record<string, unknown>) : {};
    const next: Record<string, number> = {};
    for (const name of criteriaNames) {
      const v = safeNumber(source[name], 0);
      next[name] = v > 0 ? v : NEUTRAL_SCORE;
    }
    return next;
  });
}

/** 权重求和（非数字/缺失按 0），用于「总和=100」校验与提示 */
export function sumWeights(criteria: unknown): number {
  if (!Array.isArray(criteria)) return 0;
  return criteria.reduce(
    (sum, c) => sum + safeNumber(c && typeof c === "object" ? (c as { weight?: unknown }).weight : null, 0),
    0,
  );
}
