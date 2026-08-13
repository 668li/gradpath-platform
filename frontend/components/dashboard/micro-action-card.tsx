"use client";

import Link from "next/link";
import {
  ArrowRight,
  Footprints,
  Clock,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { MicroActionPlanResponse } from "@/types/micro-action";

/** 微行动卡片：7 天进度 + 今日任务 + 快速完成 */
export function MicroActionCard({
  plan,
  onQuickComplete,
}: {
  plan: MicroActionPlanResponse | null;
  onQuickComplete: (taskId: string) => void;
}) {
  // 无活跃计划 → 引导创建
  if (!plan || plan.status !== "active") {
    return (
      <section className="card p-5 animate-fade-in">
        <div className="mb-3 flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <Footprints className="h-4 w-4" />
          </div>
          <h2 className="font-display font-semibold text-ink-800">本周成长微行动</h2>
        </div>
        <div className="flex flex-col items-center gap-3 py-4 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <Footprints className="h-5 w-5" />
          </div>
          <div>
            <p className="font-display text-sm font-medium text-ink-700">
              还没有进行中的微行动计划
            </p>
            <p className="mt-0.5 text-xs text-ink-400">
              7 天低成本探索任务，每天 15-30 分钟
            </p>
          </div>
          <Link
            href="/micro-actions"
            className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 transition-colors"
          >
            <Footprints className="h-3.5 w-3.5" />
            开始 7 天探索
          </Link>
        </div>
      </section>
    );
  }

  // 今日任务 = 第一个待完成
  const todayTask = plan.tasks.find((t) => t.status === "pending");
  const completedCount = plan.tasks.filter((t) => t.status !== "pending").length;

  return (
    <section className="card p-5 animate-fade-in">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <Footprints className="h-4 w-4" />
          </div>
          <h2 className="font-display font-semibold text-ink-800">本周成长微行动</h2>
        </div>
        <Link
          href="/micro-actions"
          className="text-xs text-brand-600 hover:text-brand-700 transition-colors inline-flex items-center"
        >
          全部 <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {/* 7 天进度条 */}
      <div className="mb-4">
        <div className="mb-1.5 flex items-center justify-between">
          <span className="text-xs font-medium text-ink-600">
            已完成 {completedCount} / 7
          </span>
          <span className="text-xs text-ink-400">{plan.progress}%</span>
        </div>
        <div className="flex gap-1">
          {plan.tasks.map((task) => (
            <div
              key={task.id}
              className={cn(
                "h-2 flex-1 rounded-full transition-colors",
                task.status === "completed"
                  ? "bg-brand-500"
                  : task.status === "skipped"
                    ? "bg-amber-300"
                    : "bg-paper-200",
              )}
              title={`Day ${task.day_number}: ${task.title}`}
            />
          ))}
        </div>
      </div>

      {/* 今日任务 */}
      {todayTask ? (
        <div className="rounded-lg border border-paper-200 bg-paper-50/50 p-3">
          <div className="flex items-start gap-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-500 text-xs font-bold text-white">
              D{todayTask.day_number}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-ink-800">{todayTask.title}</p>
              <p className="mt-0.5 text-xs text-ink-400 line-clamp-2">
                {todayTask.description}
              </p>
              <div className="mt-2 flex items-center gap-2">
                <span className="flex items-center gap-1 text-xs text-ink-400">
                  <Clock className="h-3 w-3" />
                  约 {todayTask.estimated_minutes} 分钟
                </span>
                <button
                  onClick={() => onQuickComplete(todayTask.id)}
                  className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-brand-700 transition-colors"
                >
                  <CheckCircle2 className="h-3 w-3" />
                  快速完成
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 rounded-lg bg-brand-50/50 px-3 py-2.5 text-sm text-brand-700">
          <CheckCircle2 className="h-4 w-4" />
          <span>7 天任务已全部处理，查看自我发现报告</span>
          <Link
            href="/micro-actions"
            className="ml-auto text-xs text-brand-600 hover:underline"
          >
            去查看
          </Link>
        </div>
      )}
    </section>
  );
}
