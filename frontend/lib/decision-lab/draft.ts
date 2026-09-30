/**
 * 决策实验室 5 步向导草稿 — localStorage 持久化（与测评草稿同模式）。
 *
 * 背景（夜班复验 TOP1）：矩阵计算崩溃后错误边界接管整页，
 * 向导状态全丢、重进从零开始。这里把每步输入即时落 localStorage，
 * 重进（含崩溃后返回）自动恢复，完成/重置时清除。
 * 所有读写都吞异常：隐私模式/存储满不阻断主流程。
 */
import type { NormalizedMatrixResult } from "./matrix";

export type DecisionLabDraftStep =
  | "setup"
  | "premortem"
  | "matrix"
  | "redteam"
  | "summary";

export interface DecisionLabDraft {
  version: 1;
  title: string;
  options: string[];
  step: DecisionLabDraftStep;
  premortemReasons: string[];
  premortemResult: {
    categories: { category: string; reasons: string[] }[];
    safeguards: { category: string; action: string }[];
  } | null;
  criteria: { criterion: string; weight: number }[];
  matrixScores: Record<string, number>[];
  matrixResult: NormalizedMatrixResult | null;
  redTeamQuestions: string[];
  redTeamAnswers: Record<string, string>;
  aiAnalysis: string | null;
  savedAnalysisId: string | null;
  savedAt: string;
}

const KEY = "gradpath:decision-lab:draft:v1";

const VALID_STEPS: DecisionLabDraftStep[] = ["setup", "premortem", "matrix", "redteam", "summary"];

function strArray(value: unknown, fallback: string[]): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : fallback;
}

function strRecord(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object") return {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (typeof v === "string") out[k] = v;
  }
  return out;
}

function criteriaArray(value: unknown): DecisionLabDraft["criteria"] | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const out: DecisionLabDraft["criteria"] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") continue;
    const rec = item as Record<string, unknown>;
    if (typeof rec.criterion !== "string") continue;
    const weight = typeof rec.weight === "number" && Number.isFinite(rec.weight) ? rec.weight : 0;
    out.push({ criterion: rec.criterion, weight });
  }
  return out.length > 0 ? out : null;
}

export function saveDecisionLabDraft(
  draft: Omit<DecisionLabDraft, "version" | "savedAt">,
): void {
  try {
    const payload: DecisionLabDraft = {
      ...draft,
      version: 1,
      savedAt: new Date().toISOString(),
    };
    window.localStorage.setItem(KEY, JSON.stringify(payload));
  } catch {
    // 存储满/隐私模式：草稿持久化失败不阻断向导
  }
}

/** 读取草稿；形状不合法/损坏一律返回 null（不抛异常、不用脏数据污染向导） */
export function loadDecisionLabDraft(): DecisionLabDraft | null {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<DecisionLabDraft> | null;
    if (!parsed || parsed.version !== 1) return null;
    if (typeof parsed.title !== "string" || !Array.isArray(parsed.options)) return null;
    const options = parsed.options.map((o) => (typeof o === "string" ? o : ""));
    if (options.length < 2) return null;
    const step = VALID_STEPS.includes(parsed.step as DecisionLabDraftStep)
      ? (parsed.step as DecisionLabDraftStep)
      : "setup";
    return {
      version: 1,
      title: parsed.title,
      options,
      step,
      premortemReasons: strArray(parsed.premortemReasons, [""]),
      premortemResult:
        parsed.premortemResult && typeof parsed.premortemResult === "object"
          ? (parsed.premortemResult as DecisionLabDraft["premortemResult"])
          : null,
      criteria: criteriaArray(parsed.criteria) ?? [{ criterion: "", weight: 30 }],
      matrixScores: Array.isArray(parsed.matrixScores)
        ? (parsed.matrixScores as DecisionLabDraft["matrixScores"])
        : [],
      matrixResult:
        parsed.matrixResult && typeof parsed.matrixResult === "object"
          ? (parsed.matrixResult as NormalizedMatrixResult)
          : null,
      redTeamQuestions: strArray(parsed.redTeamQuestions, []),
      redTeamAnswers: strRecord(parsed.redTeamAnswers),
      aiAnalysis: typeof parsed.aiAnalysis === "string" ? parsed.aiAnalysis : null,
      savedAnalysisId: typeof parsed.savedAnalysisId === "string" ? parsed.savedAnalysisId : null,
      savedAt: typeof parsed.savedAt === "string" ? parsed.savedAt : "",
    };
  } catch {
    return null;
  }
}

export function clearDecisionLabDraft(): void {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // 忽略：清除失败最多留下旧草稿，不影响功能
  }
}

/** 草稿是否有实质内容（纯空表单不值得恢复弹回向导） */
export function draftHasContent(d: Pick<DecisionLabDraft, "title" | "options">): boolean {
  return d.title.trim() !== "" || d.options.some((o) => o.trim() !== "");
}
