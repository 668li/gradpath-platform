"use client";

import { useCallback, useEffect, useState } from "react";
import { Brain, TrendingUp, AlertCircle, Lightbulb, Target, Activity, Gauge } from "lucide-react";
import { growthPatternsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { GrowthPattern } from "@/types";

// 模式类型图标与颜色
const PATTERN_ICONS: Record<string, { icon: typeof Brain; color: string; bg: string }> = {
  skill_bias: { icon: Target, color: "text-amber-600", bg: "bg-amber-50" },
  confidence_calibration: { icon: Gauge, color: "text-purple-600", bg: "bg-purple-50" },
  momentum: { icon: Activity, color: "text-blue-600", bg: "bg-blue-50" },
  timeline_bias: { icon: TrendingUp, color: "text-brand-600", bg: "bg-brand-50" },
  domain_balance: { icon: Brain, color: "text-red-600", bg: "bg-red-50" },
};

function getScoreColor(score: number): string {
  if (score >= 80) return "text-brand-600";
  if (score >= 60) return "text-amber-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
}

function getScoreLabel(score: number): string {
  if (score >= 80) return "校准良好";
  if (score >= 60) return "轻度偏差";
  if (score >= 40) return "需要校准";
  return "严重偏差";
}

export default function GrowthPatternsPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [patterns, setPatterns] = useState<GrowthPattern[]>([]);
  const [calibrationScore, setCalibrationScore] = useState<number | null>(null);
  const [totalDataPoints, setTotalDataPoints] = useState(0);
  const [analyzing, setAnalyzing] = useState(false);

  const loadPatterns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await growthPatternsApi.analyze();
      setPatterns(res.patterns || []);
      setCalibrationScore(res.calibration_score ?? null);
      setTotalDataPoints(res.total_data_points ?? 0);
    } catch {
      toast.push("分析失败，请重试", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadPatterns();
  }, [loadPatterns]);

  const handleReanalyze = async () => {
    setAnalyzing(true);
    try {
      const res = await growthPatternsApi.analyze();
      setPatterns(res.patterns || []);
      setCalibrationScore(res.calibration_score ?? null);
      setTotalDataPoints(res.total_data_points ?? 0);
      toast.push("模式分析已刷新", "success");
    } catch {
      toast.push("分析失败，请重试", "error");
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* 头部 */}
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <Brain className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">成长模式</h1>
        <p className="text-sm text-ink-400 mt-2 leading-relaxed">
          AI 分析你的历史数据，发现你自己没注意到的行为模式
          <br />
          不是"你做了多少事"，而是"你的模式揭示了什么"
        </p>
      </div>

      {/* 校准仪表盘 */}
      {calibrationScore !== null && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Gauge className="h-5 w-5 text-brand-600" />
              <h2 className="font-display font-semibold text-ink-800">预测校准度</h2>
            </div>
            <Button variant="ghost" size="sm" onClick={handleReanalyze} loading={analyzing}>
              刷新分析
            </Button>
          </div>

          <div className="flex items-center gap-6">
            {/* 仪表盘 */}
            <div className="relative shrink-0">
              <svg width="120" height="120" viewBox="0 0 120 120" className="transform -rotate-90">
                <circle cx="60" cy="60" r="50" fill="none" stroke="#e2e8f0" strokeWidth="10" />
                <circle
                  cx="60"
                  cy="60"
                  r="50"
                  fill="none"
                  stroke={calibrationScore >= 80 ? "#0d9488" : calibrationScore >= 60 ? "#f59e0b" : calibrationScore >= 40 ? "#f97316" : "#ef4444"}
                  strokeWidth="10"
                  strokeLinecap="round"
                  strokeDasharray={`${(calibrationScore / 100) * 314} 314`}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={cn("font-display text-2xl font-bold", getScoreColor(calibrationScore))}>
                  {calibrationScore}
                </span>
                <span className="text-[10px] text-ink-400">/ 100</span>
              </div>
            </div>

            {/* 说明 */}
            <div className="flex-1 space-y-2">
              <div>
                <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", getScoreColor(calibrationScore), "bg-paper-100")}>
                  {getScoreLabel(calibrationScore)}
                </span>
              </div>
              <p className="text-xs text-ink-500 leading-relaxed">
                校准度衡量你的决策置信度与实际结果之间的偏差。分数越高，说明你的自我评估越准确。
              </p>
              {calibrationScore < 60 && (
                <p className="text-xs text-amber-600">
                  <AlertCircle className="inline h-3.5 w-3.5" />
                  建议在决策前使用「决策实验室」的预验尸功能来校准过度自信。
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 数据概览 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="card text-center py-4">
          <p className="font-display text-2xl font-bold text-ink-800">{totalDataPoints}</p>
          <p className="text-xs text-ink-400 mt-1">数据点</p>
        </div>
        <div className="card text-center py-4">
          <p className="font-display text-2xl font-bold text-ink-800">{patterns.length}</p>
          <p className="text-xs text-ink-400 mt-1">发现模式</p>
        </div>
        <div className="card text-center py-4">
          <p className={cn("font-display text-2xl font-bold", calibrationScore !== null ? getScoreColor(calibrationScore) : "text-ink-400")}>
            {calibrationScore !== null ? `${calibrationScore}%` : "-"}
          </p>
          <p className="text-xs text-ink-400 mt-1">校准度</p>
        </div>
      </div>

      {/* 模式卡片列表 */}
      {patterns.length > 0 ? (
        <div className="space-y-4">
          <h2 className="font-display font-semibold text-ink-800 flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-brand-600" />
            发现的模式
          </h2>
          {patterns.map((p, i) => {
            const config = PATTERN_ICONS[p.pattern_type] || PATTERN_ICONS.momentum;
            const Icon = config.icon;
            return (
              <div key={`${p.pattern_type}-${i}`} className="card space-y-3">
                {/* 标题行 */}
                <div className="flex items-start gap-3">
                  <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", config.bg)}>
                    <Icon className={cn("h-5 w-5", config.color)} strokeWidth={1.8} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-ink-800">{p.title}</h3>
                    <p className="text-xs text-ink-400 mt-0.5">{p.pattern_type}</p>
                  </div>
                </div>

                {/* 描述 */}
                <p className="text-sm text-ink-600 leading-relaxed">
                  {p.description}
                </p>

                {/* 数据点 */}
                {p.data_points && Object.keys(p.data_points).length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(p.data_points).slice(0, 4).map(([key, value]) => (
                      <span key={key} className="inline-flex items-center rounded-md bg-paper-100 px-2 py-0.5 text-xs text-ink-500">
                        {key}: {typeof value === "object" ? JSON.stringify(value).slice(0, 40) : String(value)}
                      </span>
                    ))}
                  </div>
                )}

                {/* 建议 */}
                <div className={cn("rounded-lg p-3 flex items-start gap-2", config.bg)}>
                  <Lightbulb className={cn("h-4 w-4 shrink-0 mt-0.5", config.color)} />
                  <p className={cn("text-xs leading-relaxed", config.color)}>
                    {p.suggestion}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title="还没有发现模式"
          description="随着你记录更多的技能、决策和执行日志，AI 将自动分析出你的行为模式。建议先使用「职业规划」和「去向决策」功能积累数据。"
          action={<Button variant="secondary" onClick={handleReanalyze} loading={analyzing}>重新分析</Button>}
        />
      )}

      {/* 底部说明 */}
      {patterns.length > 0 && (
        <div className="card bg-paper-50">
          <div className="flex items-start gap-2">
            <Brain className="h-4 w-4 text-ink-400 mt-0.5 shrink-0" />
            <p className="text-xs text-ink-400 leading-relaxed">
              这些模式由 AI 基于你的历史数据（技能、决策、里程碑日志）分析生成。
              模式越用越准——你积累的数据越多，AI 能发现的非显而易见模式就越多。
              建议每月回来查看一次，跟踪你的模式变化。
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
