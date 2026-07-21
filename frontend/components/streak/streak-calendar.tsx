"use client";

import { cn } from "@/lib/utils";
import type { StreakRecord } from "@/types";

interface StreakCalendarProps {
  records: StreakRecord[];
}

export function StreakCalendar({ records }: StreakCalendarProps) {
  // 生成最近14天的日历
  const days: { date: string; label: string; record?: StreakRecord }[] = [];
  const recordMap = new Map(records.map((r) => [r.date, r]));

  for (let i = 13; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split("T")[0];
    const weekdays = ["日", "一", "二", "三", "四", "五", "六"];
    days.push({
      date: dateStr,
      label: weekdays[d.getDay()],
      record: recordMap.get(dateStr),
    });
  }

  // 分段：第一周 + 第二周
  const week1 = days.slice(0, 7);
  const week2 = days.slice(7, 14);

  return (
    <div className="card overflow-hidden animate-fade-in">
      <h3 className="mb-3 font-display text-sm font-semibold text-ink-700">
        最近行动
      </h3>
      <div className="flex flex-col gap-3">
        {[week1, week2].map((week, wi) => (
          <div key={wi} className="flex items-center gap-1.5">
            {week.map((day) => {
              const hasRecord = !!day.record;
              const isToday = day.date === new Date().toISOString().split("T")[0];
              const isRest = day.record?.is_rest_day;
              const isRedeem = day.record?.is_redeem;
              const isMain = day.record?.action_type === "main";
              const isMicro = day.record?.action_type === "micro";

              const bgClass = isRest
                ? "bg-blue-50 border-blue-200"
                : isRedeem
                  ? "bg-purple-50 border-purple-200"
                  : isMain
                    ? "bg-brand-50 border-brand-200"
                    : isMicro
                      ? "bg-amber-50 border-amber-200"
                      : hasRecord
                        ? "bg-green-50 border-green-200"
                        : "bg-paper-50 border-paper-200";

              const textClass = isRest
                ? "text-blue-600"
                : isRedeem
                  ? "text-purple-600"
                  : isMain
                    ? "text-brand-600"
                    : isMicro
                      ? "text-amber-600"
                      : hasRecord
                        ? "text-green-600"
                        : "text-ink-300";

              return (
                <div
                  key={day.date}
                  className={cn(
                    "flex flex-1 flex-col items-center rounded-lg border px-1.5 py-1.5 transition-all",
                    bgClass,
                    isToday && "ring-2 ring-brand-400 ring-offset-1"
                  )}
                  title={day.date}
                >
                  <span className="text-[10px] leading-none text-ink-400">
                    {day.label}
                  </span>
                  <span
                    className={cn(
                      "mt-1 text-xs font-semibold leading-none",
                      textClass
                    )}
                  >
                    {hasRecord
                      ? isRest
                        ? "休"
                        : isRedeem
                          ? "赎"
                          : "●"
                      : "○"}
                  </span>
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* 图例 */}
      <div className="mt-3 flex items-center gap-3 text-[10px] text-ink-400">
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-brand-200" /> 主行动
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-amber-200" /> 微行动
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-blue-200" /> 休息
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-purple-200" /> 回赎
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-paper-200" /> 未行动
        </span>
      </div>
    </div>
  );
}