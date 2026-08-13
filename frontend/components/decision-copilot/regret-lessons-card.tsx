"use client";

import { useState } from "react";
import { BookOpen, Quote, CheckCircle2, Shuffle, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/lib/api/swr-config";
import { peerInsightsApi } from "@/lib/api/peer-insights";
import type { RegretLessonsResponse } from "@/lib/api/peer-insights";

/** 结果类型 → 视觉配色 */
const TONE_STYLES: Record<
  string,
  { chip: string; icon: typeof CheckCircle2; iconColor: string; accent: string }
> = {
  success: {
    chip: "bg-green-50 text-green-700 border-green-200",
    icon: CheckCircle2,
    iconColor: "text-green-500",
    accent: "border-l-green-400",
  },
  mixed: {
    chip: "bg-amber-50 text-amber-700 border-amber-200",
    icon: Shuffle,
    iconColor: "text-amber-500",
    accent: "border-l-amber-400",
  },
  caution: {
    chip: "bg-red-50 text-red-700 border-red-200",
    icon: AlertTriangle,
    iconColor: "text-red-500",
    accent: "border-l-red-400",
  },
  neutral: {
    chip: "bg-paper-100 text-ink-600 border-paper-300",
    icon: BookOpen,
    iconColor: "text-ink-400",
    accent: "border-l-ink-300",
  },
};

/**
 * 前车之鉴 — 创意功能。
 * 展示"已经走过这条路的人"的真实后悔与教训，按上岸/调剂/未上岸三种视角分组。
 * 用过来人的回望，帮助正在犹豫的人提前看清每条路的真实代价。
 */
export function RegretLessonsCard() {
  const { data, isLoading } = useApi<RegretLessonsResponse>(
    "/api/peer-insights/regret-lessons",
  );
  const [activeGroup, setActiveGroup] = useState(0);

  if (isLoading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-32 rounded bg-paper-200 mb-4" />
        <div className="space-y-3">
          <div className="h-3 w-full rounded bg-paper-200" />
          <div className="h-3 w-4/5 rounded bg-paper-200" />
        </div>
      </div>
    );
  }

  if (!data || !data.has_lessons || data.groups.length === 0) {
    return null;
  }

  const group = data.groups[Math.min(activeGroup, data.groups.length - 1)];
  const tone = TONE_STYLES[group.tone] || TONE_STYLES.neutral;
  const ToneIcon = tone.icon;

  return (
    <div className="card p-5 animate-fade-in">
      <div className="mb-1 flex items-center gap-2">
        <BookOpen className="h-4 w-4 text-brand-600" />
        <h2 className="font-display font-semibold text-ink-800">前车之鉴</h2>
      </div>
      <p className="mb-4 text-xs text-ink-400">
        已经走过这条路的人，最后悔什么、最想提醒你什么
      </p>

      {/* 结果类型切换 */}
      <div className="mb-4 flex flex-wrap gap-2">
        {data.groups.map((g, i) => {
          const t = TONE_STYLES[g.tone] || TONE_STYLES.neutral;
          return (
            <button
              key={g.outcome_type}
              onClick={() => setActiveGroup(i)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-xs font-medium transition-all",
                i === activeGroup
                  ? t.chip
                  : "border-paper-200 bg-white text-ink-500 hover:bg-paper-50",
              )}
            >
              {g.label}
            </button>
          );
        })}
      </div>

      {/* 教训列表 */}
      <div className="space-y-3">
        {group.lessons.map((lesson, i) => (
          <div
            key={i}
            className={cn(
              "rounded-lg border border-l-4 border-paper-200 bg-paper-50/40 p-3.5",
              tone.accent,
            )}
          >
            <div className="flex items-start gap-2.5">
              <Quote className={cn("mt-0.5 h-4 w-4 shrink-0", tone.iconColor)} />
              <div className="min-w-0 flex-1">
                <p className="text-sm leading-relaxed text-ink-700">{lesson.text}</p>
                <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink-400">
                  {lesson.year && <span>{lesson.year} 届</span>}
                  {lesson.target_school && <span>{lesson.target_school}</span>}
                  {lesson.target_major && <span>{lesson.target_major}</span>}
                  {lesson.score_total != null && <span>{lesson.score_total} 分</span>}
                  {lesson.satisfaction_after != null && (
                    <span className="flex items-center gap-1">
                      <ToneIcon className={cn("h-3 w-3", tone.iconColor)} />
                      满意度 {lesson.satisfaction_after}/10
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="mt-3 text-[11px] text-ink-400">
        来自真实上岸报告的匿名分享 — 别人的遗憾，是你最好的避坑地图
      </p>
    </div>
  );
}
