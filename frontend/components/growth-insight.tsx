"use client";

import { useCallback, useEffect, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  XCircle,
  Circle,
  Loader2,
  AlertTriangle,
  Sparkles,
  Lightbulb,
} from "lucide-react";
import { aiApi, type ApiError } from "@/lib/api";
import { todayISO, cn } from "@/lib/utils";
import { Button } from "@/components/ui/form-controls";
import type { GrowthInsight } from "@/types";

/**
 * 成长洞察面板：
 * - 选择时间段后调用 AI 生成成长洞察
 * - 展示成长分数、趋势、优势、差距、建议与总结
 * - 挂载时尝试加载最近一次洞察结果
 */
export function GrowthInsight() {
  const [periodStart, setPeriodStart] = useState(todayISO().slice(0, 8) + "01");
  const [periodEnd, setPeriodEnd] = useState(todayISO());
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GrowthInsight | null>(null);

  // 挂载时加载最近一次洞察
  const loadLatest = useCallback(async () => {
    setInitialLoading(true);
    try {
      const latest = await aiApi.getLatestInsight();
      setResult(latest);
    } catch {
      // 暂无历史洞察，静默忽略
    } finally {
      setInitialLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLatest();
  }, [loadLatest]);

  const handleGenerate = async () => {
    if (!periodStart || !periodEnd) return;
    if (periodStart > periodEnd) {
      setError("开始日期不能晚于结束日期");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await aiApi.growthInsight({
        period_start: periodStart,
        period_end: periodEnd,
      });
      setResult(res);
    } catch (err) {
      const status = (err as ApiError).status;
      if (status === 503) {
        setError("AI 服务未配置，请联系管理员");
      } else if (status === 504) {
        setError("分析超时，请稍后重试");
      } else {
        setError(err instanceof Error ? err.message : "分析失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card space-y-4">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
          <Sparkles className="h-5 w-5" />
        </span>
        <div>
          <h2 className="font-semibold text-slate-800">AI 成长洞察</h2>
          <p className="text-xs text-slate-500">
            选择时间段，AI 基于你的职业数据生成成长分析
          </p>
        </div>
      </div>

      {/* 时间段选择 */}
      <div className="flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-slate-700">
            开始日期
          </span>
          <input
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-slate-700">
            结束日期
          </span>
          <input
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          />
        </label>
        <Button onClick={handleGenerate} loading={loading} disabled={loading}>
          <Sparkles className="h-4 w-4" /> 生成成长洞察
        </Button>
      </div>

      {/* 加载中 */}
      {loading && (
        <div className="flex items-center gap-2 text-brand-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="animate-pulse text-sm font-medium">AI 分析中…</span>
        </div>
      )}

      {/* 错误 */}
      {error && !loading && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <AlertTriangle className="h-5 w-5 shrink-0 text-red-600" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* 初次加载骨架 */}
      {initialLoading && !result && !loading && !error && (
        <div className="space-y-3">
          <div className="h-24 animate-pulse rounded-lg bg-slate-100" />
          <div className="h-32 animate-pulse rounded-lg bg-slate-100" />
        </div>
      )}

      {/* 结果展示 */}
      {result && !loading && <InsightResult result={result} />}
    </div>
  );
}

/** 成长分数仪表盘颜色判定 */
function scoreColor(score: number): { ring: string; text: string; bg: string } {
  if (score > 70) {
    return { ring: "text-green-500", text: "text-green-600", bg: "bg-green-50" };
  }
  if (score >= 40) {
    return { ring: "text-amber-500", text: "text-amber-600", bg: "bg-amber-50" };
  }
  return { ring: "text-red-500", text: "text-red-600", bg: "bg-red-50" };
}

/** 趋势图标与颜色 */
function TrendDisplay({ trend }: { trend: string }) {
  const t = trend.toLowerCase();
  if (t === "rising" || t === "up" || t === "上升") {
    return (
      <span className="inline-flex items-center gap-1 text-green-600">
        <TrendingUp className="h-4 w-4" /> 上升
      </span>
    );
  }
  if (t === "declining" || t === "down" || t === "下降") {
    return (
      <span className="inline-flex items-center gap-1 text-red-600">
        <TrendingDown className="h-4 w-4" /> 下降
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-amber-500">
      <Minus className="h-4 w-4" /> 平稳
    </span>
  );
}

/** 洞察结果展示 */
function InsightResult({ result }: { result: GrowthInsight }) {
  const { growth_score, trend, strengths, gaps, recommendations, summary } =
    result;
  const safeScore = Math.max(0, Math.min(100, Math.round(growth_score)));
  const colors = scoreColor(safeScore);

  // 圆形仪表盘
  const size = 100;
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - safeScore / 100);

  return (
    <div className="space-y-4 border-t border-slate-100 pt-4">
      {/* 成长分数 + 趋势 */}
      <div className="flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-4">
          <div className="relative" style={{ width: size, height: size }}>
            <svg
              width={size}
              height={size}
              className="-rotate-90"
              aria-hidden="true"
            >
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                strokeWidth={strokeWidth}
                className="text-slate-100"
                stroke="currentColor"
              />
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                className={cn("transition-all duration-500", colors.ring)}
                stroke="currentColor"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={cn("text-2xl font-bold", colors.text)}>
                {safeScore}
              </span>
              <span className="text-[10px] text-slate-400">成长分数</span>
            </div>
          </div>
        </div>
        <div className="space-y-1">
          <p className="text-sm text-slate-500">成长趋势</p>
          <p className="text-lg font-semibold">
            <TrendDisplay trend={trend} />
          </p>
        </div>
      </div>

      {/* 总结 */}
      <div className={cn("rounded-lg px-4 py-3", colors.bg)}>
        <p className="text-sm leading-relaxed text-slate-700">{summary}</p>
      </div>

      {/* 优势 / 差距 两列 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-green-200 bg-green-50/50 p-3">
          <div className="mb-2 flex items-center gap-2 text-green-700">
            <CheckCircle2 className="h-4 w-4" />
            <span className="text-sm font-semibold">优势</span>
          </div>
          {strengths.length === 0 ? (
            <p className="text-sm text-slate-400">暂无明显优势数据</p>
          ) : (
            <ul className="space-y-1.5">
              {strengths.map((s, i) => (
                <li
                  key={i}
                  className="flex items-start gap-1.5 text-sm text-slate-600"
                >
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-500" />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50/50 p-3">
          <div className="mb-2 flex items-center gap-2 text-red-700">
            <XCircle className="h-4 w-4" />
            <span className="text-sm font-semibold">差距</span>
          </div>
          {gaps.length === 0 ? (
            <p className="text-sm text-slate-400">暂无明显差距</p>
          ) : (
            <ul className="space-y-1.5">
              {gaps.map((g, i) => (
                <li
                  key={i}
                  className="flex items-start gap-1.5 text-sm text-slate-600"
                >
                  <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
                  <span>{g}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* 建议 */}
      {recommendations.length > 0 && (
        <div>
          <div className="mb-2 flex items-center gap-2 text-slate-700">
            <Lightbulb className="h-4 w-4 text-blue-500" />
            <span className="text-sm font-semibold">建议</span>
          </div>
          <ul className="space-y-1.5">
            {recommendations.map((r, i) => (
              <li
                key={i}
                className="flex items-start gap-1.5 text-sm text-slate-600"
              >
                <Circle className="mt-0.5 h-3 w-3 shrink-0 fill-blue-500 text-blue-500" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
