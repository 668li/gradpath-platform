"use client";

import Link from "next/link";
import { Hourglass, AlertTriangle, ArrowRight, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/lib/api/swr-config";
import { peerInsightsApi } from "@/lib/api/peer-insights";
import type { ProcrastinationResponse } from "@/lib/api/peer-insights";

/** 紧迫度 → 视觉配色 */
const URGENCY_STYLES: Record<
  string,
  { border: string; badge: string; icon: string }
> = {
  critical: {
    border: "border-l-red-500",
    badge: "bg-red-50 text-red-700",
    icon: "text-red-500",
  },
  high: {
    border: "border-l-amber-500",
    badge: "bg-amber-50 text-amber-700",
    icon: "text-amber-500",
  },
  medium: {
    border: "border-l-brand-500",
    badge: "bg-brand-50 text-brand-700",
    icon: "text-brand-500",
  },
  low: {
    border: "border-l-ink-300",
    badge: "bg-paper-100 text-ink-600",
    icon: "text-ink-400",
  },
};

/**
 * 决策拖延成本 — 创意功能。
 * 量化用户停留在"计划中"状态决策的真实代价：
 * 每犹豫一天 = 损失 3 小时有效准备时间。
 * 用具体数字对抗拖延心理。
 */
export function ProcrastinationCostCard() {
  const { data, isLoading } = useApi<ProcrastinationResponse>(
    "/api/peer-insights/procrastination",
  );

  if (isLoading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-40 rounded bg-paper-200 mb-4" />
        <div className="space-y-3">
          <div className="h-3 w-full rounded bg-paper-200" />
          <div className="h-3 w-2/3 rounded bg-paper-200" />
        </div>
      </div>
    );
  }

  if (!data || !data.has_pending) {
    return null;
  }

  return (
    <div className="card border-l-4 border-l-amber-400 p-5 animate-fade-in">
      <div className="mb-1 flex items-center gap-2">
        <Hourglass className="h-4 w-4 text-amber-500" />
        <h2 className="font-display font-semibold text-ink-800">
          犹豫的真实成本
        </h2>
      </div>
      <p className="mb-4 text-xs text-ink-400">
        还在"计划中"的决策，每天都在消耗你的准备时间
      </p>

      {/* 总成本摘要 */}
      <div className="mb-4 flex items-center gap-4 rounded-lg bg-amber-50/60 px-4 py-3">
        <div className="text-center">
          <p className="font-display text-2xl font-bold text-amber-600">
            {data.total_stale_days}
          </p>
          <p className="text-[11px] text-amber-700">累计犹豫天数</p>
        </div>
        <div className="h-8 w-px bg-amber-200" />
        <div className="text-center">
          <p className="font-display text-2xl font-bold text-amber-600">
            {data.total_lost_hours}
          </p>
          <p className="text-[11px] text-amber-700">损失准备小时</p>
        </div>
      </div>

      {/* 逐条决策成本 */}
      <div className="space-y-2">
        {data.items.map((item) => {
          const style = URGENCY_STYLES[item.urgency] || URGENCY_STYLES.low;
          return (
            <div
              key={item.decision_id}
              className={cn(
                "flex items-center justify-between gap-3 rounded-lg border border-l-4 border-paper-200 px-3 py-2.5",
                style.border,
              )}
            >
              <div className="flex min-w-0 items-center gap-2">
                <AlertTriangle className={cn("h-4 w-4 shrink-0", style.icon)} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-ink-700">
                    {item.destination_label}
                  </p>
                  <p className="truncate text-xs text-ink-400">{item.message}</p>
                </div>
              </div>
              <Link
                href={`/decision-lab?decision_id=${item.decision_id}`}
                className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
              >
                去分析
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          );
        })}
      </div>

      <p className="mt-3 flex items-center gap-1 text-[11px] text-ink-400">
        <Clock className="h-3 w-3" />
        决策不需要完美，需要发生 — 做完分析就确认，别让"再想想"偷走你的时间
      </p>
    </div>
  );
}
