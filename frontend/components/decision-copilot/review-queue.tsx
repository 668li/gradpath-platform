"use client";

import { memo } from "react";
import Link from "next/link";
import { Clock, AlertCircle, Calendar, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import type { PulseReviewItem } from "@/types";

interface Props {
  items: PulseReviewItem[];
  loading?: boolean;
}

/** 待回顾决策队列 — 决策飞轮护城河核心 UI */
export const ReviewQueueSection = memo(function ReviewQueueSection({ items, loading }: Props) {
  if (loading) return <LoadingState text="加载回顾队列…" />;

  return (
    <section className="card space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-amber-600" />
          <h3 className="font-display font-semibold text-ink-800">待回顾决策</h3>
          {items.length > 0 && (
            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
              {items.length}
            </span>
          )}
        </div>
        <Link
          href="/decision-lab"
          className="text-xs text-brand-600 hover:text-brand-700 inline-flex items-center"
        >
          决策实验室 <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="暂无待回顾决策"
          description="决策到期后，平台会自动提醒你进行复盘"
        />
      ) : (
        <ul className="space-y-2">
          {items.slice(0, 5).map((r) => (
            <li key={r.id}>
              <Link
                href={`/decision-lab?decision_id=${r.decision_id}`}
                className={cn(
                  "block rounded-lg border px-3 py-2.5 transition-all hover:shadow-card",
                  r.is_overdue
                    ? "border-red-200 bg-red-50/40 hover:bg-red-50/60"
                    : "border-paper-200 bg-white hover:bg-paper-50",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    {r.is_overdue ? (
                      <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />
                    ) : (
                      <Calendar className="h-4 w-4 text-ink-400 shrink-0" />
                    )}
                    <span className="text-sm font-medium text-ink-700">
                      决策回顾
                    </span>
                    {r.is_overdue && (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-700">
                        已逾期
                      </span>
                    )}
                  </div>
                  <span
                    className={cn(
                      "text-xs font-medium shrink-0",
                      r.is_overdue ? "text-red-600" : "text-amber-600",
                    )}
                  >
                    {r.days_until_due === null
                      ? "—"
                      : r.is_overdue
                        ? `逾期 ${Math.abs(r.days_until_due)} 天`
                        : r.days_until_due === 0
                          ? "今天到期"
                          : `${r.days_until_due} 天后`}
                  </span>
                </div>
                {r.scheduled_at && (
                  <p className="mt-1 text-[11px] text-ink-400">
                    计划回顾日：{r.scheduled_at.slice(0, 10)}
                  </p>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
});
