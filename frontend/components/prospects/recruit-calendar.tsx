"use client";

// 秋招春招日历（RN-5c，2026-10-03）：纯静态节点表零爬取（数据供给总纲拍板口径）。
// 作用：一眼看清"现在是什么窗口、下一个窗口多远"——前置焦虑消解器。
// 数据为公开招生/招聘常识性周期，非爬取数据；具体院校节点以时间线功能为准。

import { CalendarClock, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface RecruitWindow {
  name: string;
  months: number[]; // 1-12
  track: "employment" | "kaoyan" | "common";
  note: string;
}

const WINDOWS: RecruitWindow[] = [
  { name: "秋招提前批", months: [6, 7, 8], track: "employment", note: "大厂提前批陆续开放，早投占坑" },
  { name: "秋招正式批", months: [9, 10, 11], track: "employment", note: "校招主战场，金九银十" },
  { name: "春招（补录）", months: [3, 4], track: "employment", note: "岗位量少于秋招，捡漏窗口" },
  { name: "考研报名", months: [10], track: "kaoyan", note: "研招网正式报名（下旬截止）" },
  { name: "考研初试", months: [12], track: "kaoyan", note: "下旬统考初试" },
  { name: "出分与复试调剂", months: [2, 3, 4], track: "kaoyan", note: "出分→国家线→复试→调剂" },
  { name: "国考", months: [10, 11], track: "common", note: "10 月报名，11 月底笔试" },
  { name: "省考联考", months: [2, 3], track: "common", note: "多数省份 2 月报名 3 月笔试" },
];

const TRACK_LABEL: Record<RecruitWindow["track"], string> = {
  employment: "就业",
  kaoyan: "考研",
  common: "考公",
};

const TRACK_STYLE: Record<RecruitWindow["track"], string> = {
  employment: "bg-emerald-50 text-emerald-700",
  kaoyan: "bg-blue-50 text-blue-700",
  common: "bg-purple-50 text-purple-700",
};

const MONTH_LABEL = ["", "1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

function monthsUntil(current: number, targetMonths: number[]): number {
  // 距离最近的下一个目标月还有几个月（0=本月进行中）
  let best = 12;
  for (const m of targetMonths) {
    const d = (m - current + 12) % 12;
    if (d < best) best = d;
  }
  return best;
}

export function RecruitCalendar() {
  const now = new Date();
  const currentMonth = now.getMonth() + 1;

  const active = WINDOWS.filter((w) => w.months.includes(currentMonth));
  const upcoming = WINDOWS.filter((w) => !w.months.includes(currentMonth)).sort(
    (a, b) => monthsUntil(currentMonth, a.months) - monthsUntil(currentMonth, b.months),
  );

  return (
    <div className="rounded-xl border border-paper-200 bg-white p-5">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50">
          <CalendarClock className="h-5 w-5 text-brand-600" />
        </div>
        <div>
          <h3 className="font-display font-bold text-ink-800">秋招春招日历</h3>
          <p className="text-xs text-ink-400">
            现在是 {currentMonth} 月——看清当前窗口与下一个节点，规划不慌
          </p>
        </div>
      </div>

      {active.length > 0 && (
        <div className="mb-3 space-y-2">
          {active.map((w) => (
            <div
              key={w.name}
              className="flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-2.5 ring-1 ring-brand-200"
            >
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-600 px-2 py-0.5 text-xs font-semibold text-white">
                进行中
              </span>
              <span className="text-sm font-medium text-ink-800">{w.name}</span>
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[11px] font-medium",
                  TRACK_STYLE[w.track],
                )}
              >
                {TRACK_LABEL[w.track]}
              </span>
              <span className="ml-auto hidden text-xs text-ink-500 sm:block">{w.note}</span>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {upcoming.slice(0, 6).map((w) => {
          const dist = monthsUntil(currentMonth, w.months);
          return (
            <div key={w.name} className="flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-paper-50">
              <ChevronRight className="h-3.5 w-3.5 shrink-0 text-ink-300" />
              <span className="text-sm text-ink-700">{w.name}</span>
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[11px] font-medium",
                  TRACK_STYLE[w.track],
                )}
              >
                {TRACK_LABEL[w.track]}
              </span>
              <span className="ml-auto shrink-0 text-xs text-ink-400">
                {MONTH_LABEL[w.months[0]]} 开始 · {dist === 0 ? "本月" : `${dist} 个月后`}
              </span>
            </div>
          );
        })}
      </div>

      <p className="mt-3 text-[11px] leading-relaxed text-ink-400">
        周期为公开常识性时间节点，具体院校与岗位截止日以官方公告和站内时间线为准。
      </p>
    </div>
  );
}
