"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, MapPin, Sparkles, Timer } from "lucide-react";
import { goalDecomposeApi, type GoalStep } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

const PATHS = [
  { value: "kaoyan", label: "考研" },
  { value: "employment", label: "就业" },
  { value: "civil_service", label: "考公" },
];

const MOTIVATION_LABELS: Record<number, string> = {
  1: "很低，需要极小的开始",
  2: "偏低",
  3: "一般",
  4: "比较想做成",
  5: "非常强烈",
};

/**
 * 目标拆解卡（#14 用户拍板）：输入大目标 → 福格 B=MAP 约束的 7 天微行动 →
 * 一键存入现有微行动计划（接入 streak/提醒闭环）。
 */
export function GoalDecomposeCard() {
  const toast = useToast();
  const [goal, setGoal] = useState("");
  const [path, setPath] = useState("kaoyan");
  const [motivation, setMotivation] = useState(3);
  const [loading, setLoading] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [steps, setSteps] = useState<GoalStep[] | null>(null);
  const [note, setNote] = useState("");
  const [committed, setCommitted] = useState<string | null>(null);

  const handlePreview = async () => {
    if (goal.trim().length < 2) {
      toast.push("先写下你的大目标", "error");
      return;
    }
    setLoading(true);
    setSteps(null);
    setCommitted(null);
    try {
      const res = await goalDecomposeApi.preview({
        goal: goal.trim(),
        path_type: path,
        motivation,
      });
      setSteps(res.steps);
      setNote(res.note);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "拆解失败，请稍后再试", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleCommit = async () => {
    if (!steps) return;
    setCommitting(true);
    try {
      const res = await goalDecomposeApi.commit({
        goal: goal.trim(),
        path_type: path,
        steps,
      });
      setCommitted(res.plan_id);
      toast.push(`已创建 ${res.task_count} 天微行动计划`, "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "保存失败", "error");
    } finally {
      setCommitting(false);
    }
  };

  return (
    <div className="card space-y-4">
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-brand-600" />
        <h2 className="font-display text-lg font-semibold text-ink-800">
          目标拆解
        </h2>
        <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-600">
          福格微行动
        </span>
      </div>

      {committed ? (
        <div className="space-y-3 text-center py-4">
          <p className="text-sm font-medium text-green-700">
            ✓ 7 天微行动计划已创建
          </p>
          <p className="text-xs text-ink-500">
            第 1 步已在今日行动里等你，完成后自动点亮连击。
          </p>
          <Link
            href="/micro-actions"
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            去做第一步
          </Link>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            <input
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              maxLength={120}
              placeholder="写下大目标，如：考上浙大计算机研"
              className="w-full rounded-lg border border-paper-300 bg-white px-3 py-2.5 text-sm text-ink-800 placeholder:text-ink-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex rounded-lg border border-paper-300 bg-white p-0.5">
                {PATHS.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setPath(p.value)}
                    className={cn(
                      "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                      path === p.value
                        ? "bg-brand-600 text-white"
                        : "text-ink-600 hover:bg-paper-100",
                    )}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <label className="flex flex-1 min-w-[180px] items-center gap-2 text-xs text-ink-500">
                动机
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={motivation}
                  onChange={(e) => setMotivation(parseInt(e.target.value))}
                  className="h-1.5 flex-1 accent-brand-600"
                />
                <span className="w-28 text-right">
                  {motivation}/5 · {MOTIVATION_LABELS[motivation]}
                </span>
              </label>
            </div>
            <button
              type="button"
              onClick={handlePreview}
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> 拆解中（约 10-30 秒）…
                </>
              ) : (
                <>拆成 7 天微行动</>
              )}
            </button>
          </div>

          {steps && steps.length > 0 && (
            <div className="space-y-2">
              {note && (
                <p className="rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700">
                  {note}
                </p>
              )}
              {steps.map((s) => (
                <div
                  key={s.day_number}
                  className="rounded-lg border border-paper-200 p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-ink-800">
                      <span className="mr-1.5 rounded bg-paper-200 px-1.5 py-0.5 text-[10px] font-semibold text-ink-500">
                        Day {s.day_number}
                      </span>
                      {s.title}
                    </p>
                    <span className="inline-flex shrink-0 items-center gap-1 text-[11px] text-ink-400">
                      <Timer className="h-3 w-3" />
                      {s.estimated_minutes} 分钟
                    </span>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-ink-600">
                    {s.description}
                  </p>
                  {s.anchor && (
                    <p className="mt-1 flex items-center gap-1 text-[11px] text-brand-600">
                      <MapPin className="h-3 w-3" /> 锚点：{s.anchor}
                    </p>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={handleCommit}
                disabled={committing}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-brand-300 bg-brand-50 px-4 py-2.5 text-sm font-medium text-brand-700 hover:bg-brand-100 disabled:opacity-60"
              >
                {committing && <Loader2 className="h-4 w-4 animate-spin" />}
                就这套了，存为我的 7 天微行动
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
