"use client";

import { useRouter } from "next/navigation";
import { Flame, Trophy, Coffee } from "lucide-react";
import type { StreakStats } from "@/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/form-controls";

interface StreakBarProps {
  stats: StreakStats;
  onRestDay: () => void;
  restDayLoading: boolean;
}

export function StreakBar({ stats, onRestDay, restDayLoading }: StreakBarProps) {
  const router = useRouter();
  const {
    current_streak,
    longest_streak,
    total_active_days,
    today_active,
    milestones,
    rest_day_available,
    redeem_available,
  } = stats;

  const nextMilestone = milestones.find((m) => !m.unlocked);
  const progressToNext = nextMilestone
    ? Math.min((current_streak / nextMilestone.days) * 100, 100)
    : 100;

  return (
    <div className="card overflow-hidden animate-fade-in">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        {/* 火焰图标 + 天数 */}
        <div
          className={cn(
            "flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl text-white shadow-lg transition-all duration-500",
            today_active
              ? "bg-gradient-to-br from-brand-500 to-orange-500 shadow-orange-500/25"
              : "bg-gradient-to-br from-slate-400 to-slate-500 shadow-slate-400/25"
          )}
        >
          <Flame
            className={cn(
              "h-8 w-8 transition-all",
              today_active && "animate-pulse"
            )}
            strokeWidth={2.2}
          />
        </div>

        {/* 核心数据 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-4xl font-bold leading-none text-ink-800">
              {current_streak}
            </span>
            <span className="text-sm text-ink-500">天连续行动</span>
          </div>

          {/* 断签时显示进度还在 */}
          {!today_active && current_streak > 0 && (
            <p className="mt-1.5 text-xs font-medium text-ink-500">
              你 {current_streak} 天的进度还在，从断点继续
            </p>
          )}

          {today_active && (
            <p className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-brand-600">
              <Flame className="h-3 w-3" /> 今日已行动，连胜延续中
            </p>
          )}

          {/* 进度条到下个里程碑 */}
          {nextMilestone && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-ink-400">
                <span>距离「{nextMilestone.name}」</span>
                <span>
                  {current_streak}/{nextMilestone.days}天
                </span>
              </div>
              <div className="mt-1 h-1.5 w-full rounded-full bg-paper-200">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-brand-400 to-orange-400 transition-all duration-700"
                  style={{ width: `${progressToNext}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* 补充数据 */}
        <div className="flex gap-6 sm:gap-8 sm:border-l sm:border-paper-200 sm:pl-6">
          <div>
            <p className="font-display text-xl font-bold leading-none text-ink-800">
              {longest_streak}
            </p>
            <p className="mt-1 text-xs text-ink-400">最长连胜 / 天</p>
          </div>
          <div>
            <p className="font-display text-xl font-bold leading-none text-ink-800">
              {total_active_days}
            </p>
            <p className="mt-1 text-xs text-ink-400">累计活跃 / 天</p>
          </div>
        </div>
      </div>

      {/* 里程碑徽章行 */}
      <div className="mt-4 flex items-center gap-1 overflow-x-auto pb-1">
        {milestones.map((m, i) => (
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
            {m.unlocked && <span className="hidden sm:inline">{m.name}</span>}
          </div>
        ))}
      </div>

      {/* 操作按钮 */}
      <div className="mt-4 flex items-center gap-2 border-t border-paper-100 pt-3">
        {!today_active ? (
          <Button
            variant="primary"
            size="sm"
            className="gap-1.5"
            onClick={() => router.push("/retrospectives/weekly")}
          >
            <Flame className="h-3.5 w-3.5" /> 完成今日行动
          </Button>
        ) : (
          <div className="flex items-center gap-1 text-xs text-brand-600">
            <Trophy className="h-3.5 w-3.5" />
            今天已打卡
          </div>
        )}

        {!today_active && rest_day_available && (
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 text-ink-500"
            onClick={onRestDay}
            loading={restDayLoading}
          >
            <Coffee className="h-3.5 w-3.5" /> 今天休息
          </Button>
        )}

        {redeem_available && (
          <div className="ml-auto flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700">
            <Flame className="h-3 w-3" />
            可回赎断签
          </div>
        )}
      </div>
    </div>
  );
}