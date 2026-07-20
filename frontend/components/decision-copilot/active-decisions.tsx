"use client";

import { memo } from "react";
import Link from "next/link";
import { Compass, ArrowRight, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { DESTINATION_TYPE_LABEL } from "@/lib/constants";
import type { PulseActiveDecision } from "@/types";

interface Props {
  items: PulseActiveDecision[];
  loading?: boolean;
}

const STATUS_LABEL: Record<string, string> = {
  planned: "规划中",
  confirmed: "已确认",
  executed: "已执行",
  changed: "已变更",
};

const STATUS_COLOR: Record<string, string> = {
  planned: "bg-blue-50 text-blue-700 border-blue-200",
  confirmed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  executed: "bg-paper-100 text-ink-600 border-paper-200",
  changed: "bg-amber-50 text-amber-700 border-amber-200",
};

/** 进行中决策列表 — 显示活跃决策及预测信息 */
export const ActiveDecisionsSection = memo(function ActiveDecisionsSection({ items, loading }: Props) {
  if (loading) return <LoadingState text="加载决策中…" />;

  return (
    <section className="card space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Compass className="h-4 w-4 text-brand-600" />
          <h3 className="font-display font-semibold text-ink-800">进行中决策</h3>
          {items.length > 0 && (
            <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-600">
              {items.length}
            </span>
          )}
        </div>
        <Link
          href="/decisions"
          className="text-xs text-brand-600 hover:text-brand-700 inline-flex items-center"
        >
          全部 <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="暂无进行中决策"
          description="创建一条去向决策，平台将自动跟踪并安排回顾"
          action={
            <Link
              href="/decisions"
              className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
            >
              创建决策 <ArrowRight className="h-3 w-3" />
            </Link>
          }
        />
      ) : (
        <ul className="space-y-2">
          {items.slice(0, 5).map((d) => {
            const destLabel =
              DESTINATION_TYPE_LABEL[
                d.destination_type as keyof typeof DESTINATION_TYPE_LABEL
              ] ?? d.destination_type;
            return (
              <li key={d.id}>
                <Link
                  href={`/decisions?id=${d.id}`}
                  className="block rounded-lg border border-paper-200 bg-white px-3 py-2.5 transition-all hover:border-brand-300 hover:bg-brand-50/30"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-display font-semibold text-ink-800 text-sm">
                        {destLabel}
                      </span>
                      <span
                        className={cn(
                          "rounded-full border px-2 py-0.5 text-[10px] font-medium",
                          STATUS_COLOR[d.status] ?? STATUS_COLOR.planned,
                        )}
                      >
                        {STATUS_LABEL[d.status] ?? d.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <span className="text-xs text-ink-400">置信度</span>
                      <span className="text-sm font-semibold text-brand-600">
                        {d.confidence}/5
                      </span>
                    </div>
                  </div>
                  {d.prediction && (
                    <p className="mt-1.5 text-xs text-ink-500 line-clamp-2">
                      <span className="text-ink-400">预测：</span>
                      {d.prediction}
                    </p>
                  )}
                  {d.review_date && (
                    <p className="mt-1 flex items-center gap-1 text-[11px] text-ink-400">
                      <Calendar className="h-3 w-3" />
                      回顾日期：{d.review_date.slice(0, 10)}
                    </p>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
});
