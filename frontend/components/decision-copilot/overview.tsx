"use client";

import { memo, useMemo } from "react";
import Link from "next/link";
import {
  Compass,
  Clock,
  CheckCircle2,
  Brain,
  Bell,
  TrendingUp,
  ArrowRight,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import type { PulseOverview } from "@/types";

interface Props {
  overview: PulseOverview | null;
  loading?: boolean;
}

/** 决策副驾驶看板总览 — 5 项核心指标 */
export const PulseOverviewSection = memo(function PulseOverviewSection({ overview, loading }: Props) {
  const items = useMemo(() => {
    if (!overview) return [];
    return [
      {
        label: "进行中决策",
        value: overview.active_decisions,
        icon: Compass,
        color: "text-blue-600 bg-blue-50",
        href: "/decisions",
        hint: "规划/已确认",
      },
      {
        label: "待回顾决策",
        value: overview.due_reviews,
        icon: Clock,
        color: "text-amber-600 bg-amber-50",
        href: "/decision-lab",
        hint: "已到期需复盘",
        alert: overview.due_reviews > 0,
      },
      {
        label: "未读暗知识",
        value: overview.unread_pushes,
        icon: Bell,
        color: "text-rose-600 bg-rose-50",
        href: "/kaoyan/dark-knowledge",
        hint: "主动推送",
        alert: overview.unread_pushes > 0,
      },
      {
        label: "完成回顾",
        value: overview.completed_reviews,
        icon: CheckCircle2,
        color: "text-emerald-600 bg-emerald-50",
        href: "/decision-lab",
        hint: `累计 ${overview.total_decisions} 决策`,
      },
      {
        label: "决策准确率",
        value: `${overview.avg_decision_accuracy.toFixed(1)}%`,
        icon: TrendingUp,
        color: "text-purple-600 bg-purple-50",
        href: "/decision-lab",
        hint: "AI 复盘评分",
      },
      {
        label: "AI 记忆",
        value: overview.memory_count,
        icon: Brain,
        color: "text-brand-600 bg-brand-50",
        href: "/profile",
        hint: "已知事实条数",
      },
    ];
  }, [overview]);

  if (loading) return <LoadingState text="加载看板总览…" />;
  if (!overview) return null;

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
          <Activity className="h-4 w-4" />
        </div>
        <h2 className="font-display font-semibold text-ink-800">决策副驾驶</h2>
        <span className="text-xs text-ink-400">
          最后更新 {formatRelativeTime(overview.last_updated)}
        </span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {items.map((it) => {
          const Icon = it.icon;
          return (
            <Link
              key={it.label}
              href={it.href}
              className={cn(
                "group card flex flex-col gap-2 p-3 transition-all hover:shadow-card-hover hover:border-brand-200",
                it.alert && "border-amber-200 bg-amber-50/30",
              )}
            >
              <div className="flex items-center justify-between">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-lg",
                    it.color,
                  )}
                >
                  <Icon className="h-4 w-4" strokeWidth={1.8} />
                </div>
                {it.alert && (
                  <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                )}
              </div>
              <div>
                <p className="font-display text-xl font-bold text-ink-800 leading-none">
                  {it.value}
                </p>
                <p className="mt-1 text-xs text-ink-500">{it.label}</p>
                <p className="mt-0.5 text-[10px] text-ink-400">{it.hint}</p>
              </div>
              <ArrowRight className="h-3 w-3 text-ink-300 opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>
          );
        })}
      </div>
    </section>
  );
});

function formatRelativeTime(iso: string): string {
  try {
    const t = new Date(iso).getTime();
    const now = Date.now();
    const diff = Math.max(0, now - t);
    const sec = Math.floor(diff / 1000);
    if (sec < 60) return "刚刚";
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min} 分钟前`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr} 小时前`;
    return `${Math.floor(hr / 24)} 天前`;
  } catch {
    return "";
  }
}
