"use client";

import { useState } from "react";
import Link from "next/link";
import {
  TrendingUp,
  Flame,
  Trophy,
  Target,
  GitBranch,
  Circle,
  Clock,
  RotateCcw,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/form-controls";

export default function GrowthArchivePage() {
  const { data: gamification, isLoading: gLoading } = useApi<any>("/api/gamification/profile");
  const { data: streaks, isLoading: sLoading } = useApi<any>("/api/streaks/stats");
  const { data: growth, isLoading: grLoading } = useApi<any>("/api/growth-patterns/analyze");
  const { data: history, isLoading: hLoading } = useApi<any>("/api/growth-patterns/history");

  const isLoading = gLoading || sLoading || grLoading;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/15 text-brand-500">
          <TrendingUp className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-800">
            成长档案
          </h1>
          <p className="text-sm text-ink-500">
            聚合你的成长数据，见证每一次进步
          </p>
        </div>
      </header>

      {/* 核心数据卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 text-center">
          <Target className="mx-auto h-5 w-5 text-brand-500 mb-2" />
          <p className="font-display text-2xl font-bold text-ink-800">
            {gamification?.level ?? 1}
          </p>
          <p className="text-xs text-ink-400">等级</p>
        </div>
        <div className="card p-4 text-center">
          <Flame className="mx-auto h-5 w-5 text-orange-500 mb-2" />
          <p className="font-display text-2xl font-bold text-ink-800">
            {streaks?.current_streak ?? 0}
          </p>
          <p className="text-xs text-ink-400">连续行动 / 天</p>
        </div>
        <div className="card p-4 text-center">
          <Trophy className="mx-auto h-5 w-5 text-amber-500 mb-2" />
          <p className="font-display text-2xl font-bold text-ink-800">
            {gamification?.earned_badges?.length ?? 0}
          </p>
          <p className="text-xs text-ink-400">已解锁徽章</p>
        </div>
        <div className="card p-4 text-center">
          <Sparkles className="mx-auto h-5 w-5 text-purple-500 mb-2" />
          <p className="font-display text-2xl font-bold text-ink-800">
            {gamification?.xp ?? 0}
          </p>
          <p className="text-xs text-ink-400">总XP</p>
        </div>
      </div>

      {/* 连胜里程碑 */}
      {streaks?.milestones && (
        <div className="card">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink-700 flex items-center gap-2">
            <Flame className="h-4 w-4 text-orange-500" />
            连胜里程碑
          </h2>
          <div className="flex items-center gap-1 overflow-x-auto pb-1">
            {streaks.milestones.map((m: any, i: number) => (
              <div
                key={m.days}
                className={cn(
                  "flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-all",
                  m.unlocked
                    ? "bg-brand-50 text-brand-700 border border-brand-200"
                    : "bg-paper-100 text-ink-400 border border-paper-200"
                )}
              >
                {m.unlocked ? (
                  <Trophy className="h-3 w-3 text-brand-500" />
                ) : (
                  <span className="h-3 w-3 rounded-full border border-paper-300" />
                )}
                <span>{m.days}d</span>
                {m.unlocked && <span>{m.name}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 成长分数趋势 */}
      {history?.length > 0 && (
        <div className="card">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink-700 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-brand-500" />
            成长分数趋势
          </h2>
          <div className="flex items-end gap-2 h-32">
            {history.map((snap: any, i: number) => {
              const maxScore = Math.max(...history.map((s: any) => s.growth_score ?? 0), 1);
              const height = ((snap.growth_score ?? 0) / maxScore) * 100;
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-xs font-medium text-ink-700">
                    {snap.growth_score ?? 0}
                  </span>
                  <div
                    className="w-full rounded-t bg-gradient-to-t from-brand-400 to-brand-300 transition-all"
                    style={{ height: `${height}%` }}
                  />
                  <span className="text-[10px] text-ink-400">
                    {snap.period?.slice(0, 7) ?? ""}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 已解锁徽章 */}
      {gamification?.earned_badges?.length > 0 && (
        <div className="card">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink-700 flex items-center gap-2">
            <Trophy className="h-4 w-4 text-amber-500" />
            已解锁徽章
          </h2>
          <div className="flex flex-wrap gap-2">
            {gamification.earned_badges.map((b: any, i: number) => (
              <Badge key={i} color="amber">
                {b.icon ?? "🏅"} {b.name ?? b}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* 快捷入口 */}
      <div className="grid gap-4 md:grid-cols-2">
        <Link
          href="/dashboard"
          className="card p-4 hover:shadow-md transition-shadow flex items-center gap-3"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-100 text-blue-500">
            <Target className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-ink-700">个人看板</p>
            <p className="text-xs text-ink-400">总览成长数据与目标进度</p>
          </div>
          <ArrowRight className="h-4 w-4 text-ink-300 shrink-0" />
        </Link>
        <Link
          href="/retrospectives/weekly"
          className="card p-4 hover:shadow-md transition-shadow flex items-center gap-3"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-purple-100 text-purple-500">
            <RotateCcw className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-ink-700">周报草稿</p>
            <p className="text-xs text-ink-400">AI自动生成的每周复盘</p>
          </div>
          <ArrowRight className="h-4 w-4 text-ink-300 shrink-0" />
        </Link>
      </div>
    </div>
  );
}