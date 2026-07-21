"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Target,
  Lightbulb,
  BarChart3,
  ListChecks,
  Sparkles,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button, Badge } from "@/components/ui/form-controls";
import { Skeleton } from "@/components/ui/skeleton";

interface WeeklyDraft {
  week_start: string;
  week_end: string;
  data_layer: {
    active_days: number;
    total_actions: number;
    main_actions: number;
    micro_actions: number;
    rest_days: number;
    total_xp: number;
    type_distribution: Record<string, number>;
    key_events: string[];
    streak_start: number;
    streak_end: number;
    streak_change: number;
  };
  comparison_layer: {
    vs_last_week: {
      active_days: number;
      total_actions: number;
      total_xp: number;
    };
    vs_last_week_active: number;
    vs_last_week_actions: number;
  };
  insight_layer: Array<{
    text: string;
    evidence: string;
    action_link: string | null;
  }>;
  action_layer: Array<{
    action: string;
    why: string;
    deadline: string;
    source: string;
  }>;
}

function CollapsibleSection({
  title,
  icon: Icon,
  defaultOpen = true,
  children,
}: {
  title: string;
  icon: React.ElementType;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-5 py-4 text-left"
      >
        <Icon className="h-4 w-4 text-brand-500" />
        <span className="font-display text-sm font-semibold text-ink-700 flex-1">
          {title}
        </span>
        {open ? (
          <ChevronUp className="h-4 w-4 text-ink-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-ink-400" />
        )}
      </button>
      {open && <div className="px-5 pb-4">{children}</div>}
    </div>
  );
}

export default function WeeklyReviewPage() {
  const router = useRouter();
  const { data, error, isLoading } = useApi<WeeklyDraft>("/api/retrospectives/weekly-draft");
  const [confirmedInsights, setConfirmedInsights] = useState<Set<number>>(new Set());
  const [dismissedInsights, setDismissedInsights] = useState<Set<number>>(new Set());

  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-64" />
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="card p-8 text-center">
          <Sparkles className="mx-auto h-12 w-12 text-ink-300" />
          <h2 className="mt-4 font-display text-lg font-semibold text-ink-700">
            本周数据不足
          </h2>
          <p className="mt-2 text-sm text-ink-500">
            需要至少完成几次行动后，AI 才能生成有意义的周报草稿。
          </p>
          <Button
            variant="primary"
            size="sm"
            className="mt-4"
            onClick={() => router.push("/dashboard")}
          >
            回到看板
          </Button>
        </div>
      </div>
    );
  }

  const { data_layer, comparison_layer, insight_layer, action_layer } = data;
  const vs = comparison_layer.vs_last_week;

  const handleToggleInsight = (index: number, dismiss: boolean) => {
    if (dismiss) {
      setDismissedInsights((prev) => {
        const next = new Set(prev);
        next.has(index) ? next.delete(index) : next.add(index);
        return next;
      });
    } else {
      setConfirmedInsights((prev) => {
        const next = new Set(prev);
        next.has(index) ? next.delete(index) : next.add(index);
        return next;
      });
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 space-y-4">
      {/* 头部 */}
      <div className="flex items-center gap-3">
        <Link href="/dashboard" className="text-ink-400 hover:text-ink-600">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="font-display text-xl font-bold text-ink-800">
            周报草稿
          </h1>
          <p className="text-xs text-ink-400">
            {data_layer.active_days > 0
              ? `${data.week_start} ~ ${data.week_end} · AI 自动生成`
              : "本周暂无数据"}
          </p>
        </div>
      </div>

      {/* 数据层 */}
      <CollapsibleSection title="数据快照" icon={BarChart3}>
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg bg-paper-50 p-3 text-center">
              <p className="font-display text-2xl font-bold text-ink-800">
                {data_layer.active_days}
              </p>
              <p className="text-xs text-ink-400">活跃天数</p>
            </div>
            <div className="rounded-lg bg-paper-50 p-3 text-center">
              <p className="font-display text-2xl font-bold text-ink-800">
                {data_layer.total_actions}
              </p>
              <p className="text-xs text-ink-400">完成行动</p>
            </div>
            <div className="rounded-lg bg-paper-50 p-3 text-center">
              <p className="font-display text-2xl font-bold text-ink-800">
                {data_layer.total_xp}
              </p>
              <p className="text-xs text-ink-400">获得XP</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {data_layer.main_actions > 0 && (
              <Badge color="blue">主行动 {data_layer.main_actions}次</Badge>
            )}
            {data_layer.micro_actions > 0 && (
              <Badge color="amber">微行动 {data_layer.micro_actions}次</Badge>
            )}
            {data_layer.rest_days > 0 && (
              <Badge color="slate">休息 {data_layer.rest_days}天</Badge>
            )}
          </div>

          {data_layer.key_events.length > 0 && (
            <div className="rounded-lg bg-paper-50 p-3">
              <p className="text-xs font-medium text-ink-500 mb-1.5">关键事件</p>
              <ul className="space-y-1">
                {data_layer.key_events.map((e, i) => (
                  <li key={i} className="text-sm text-ink-700">
                    · {e}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* 对比层 */}
      {comparison_layer.vs_last_week_active > 0 && (
        <CollapsibleSection title="对比上周" icon={TrendingUp}>
          <div className="space-y-2">
            <div className="flex items-center justify-between rounded-lg bg-paper-50 p-3">
              <span className="text-sm text-ink-600">活跃天数</span>
              <span className="inline-flex items-center gap-1 text-sm font-medium">
                {vs.active_days > 0 ? (
                  <TrendingUp className="h-4 w-4 text-brand-500" />
                ) : vs.active_days < 0 ? (
                  <TrendingDown className="h-4 w-4 text-amber-500" />
                ) : null}
                {vs.active_days > 0 ? "+" : ""}
                {vs.active_days}天
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-paper-50 p-3">
              <span className="text-sm text-ink-600">完成行动</span>
              <span className="text-sm font-medium">
                {vs.total_actions > 0 ? "+" : ""}
                {vs.total_actions}个
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-paper-50 p-3">
              <span className="text-sm text-ink-600">获得XP</span>
              <span className="text-sm font-medium">
                {vs.total_xp > 0 ? "+" : ""}
                {vs.total_xp}XP
              </span>
            </div>
          </div>
        </CollapsibleSection>
      )}

      {/* 洞察层 */}
      {insight_layer.length > 0 && (
        <CollapsibleSection title="AI 洞察" icon={Lightbulb}>
          <div className="space-y-3">
            {insight_layer.map((insight, i) => (
              <div
                key={i}
                className={cn(
                  "rounded-lg border p-3 transition-all",
                  dismissedInsights.has(i)
                    ? "border-red-200 bg-red-50/50 opacity-60"
                    : confirmedInsights.has(i)
                      ? "border-brand-200 bg-brand-50/50"
                      : "border-paper-200 bg-paper-50"
                )}
              >
                <p className="text-sm text-ink-700">{insight.text}</p>

                {/* 依据气泡 */}
                <div className="mt-2 rounded bg-white/80 px-2 py-1 text-xs text-ink-400">
                  <span className="font-medium text-ink-500">AI依据：</span>
                  {insight.evidence}
                </div>

                <div className="mt-2 flex items-center gap-2">
                  {insight.action_link && (
                    <Link
                      href={insight.action_link}
                      className="text-xs font-medium text-brand-600 hover:text-brand-700"
                    >
                      查看详情 →
                    </Link>
                  )}
                  <div className="ml-auto flex gap-1">
                    <button
                      onClick={() => handleToggleInsight(i, false)}
                      className={cn(
                        "rounded px-2 py-0.5 text-xs transition-colors",
                        confirmedInsights.has(i)
                          ? "bg-brand-100 text-brand-700"
                          : "text-ink-400 hover:text-brand-600"
                      )}
                    >
                      <CheckCircle2 className="inline h-3 w-3 mr-0.5" />
                      有用
                    </button>
                    <button
                      onClick={() => handleToggleInsight(i, true)}
                      className={cn(
                        "rounded px-2 py-0.5 text-xs transition-colors",
                        dismissedInsights.has(i)
                          ? "bg-red-100 text-red-700"
                          : "text-ink-400 hover:text-red-600"
                      )}
                    >
                      不准确
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* 行动层 */}
      {action_layer.length > 0 && (
        <CollapsibleSection title="下周建议" icon={ListChecks}>
          <div className="space-y-2">
            {action_layer.map((act, i) => (
              <div key={i} className="flex items-start gap-3 rounded-lg bg-paper-50 p-3">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-600 text-xs font-bold">
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-ink-700">{act.action}</p>
                  <p className="mt-1 text-xs text-ink-400">
                    为什么：{act.why}
                  </p>
                  <div className="mt-1.5 flex items-center gap-2">
                    <Badge color={act.source === "goal" ? "purple" : "blue"}>
                      {act.source === "goal" ? "目标锚定" : "AI推荐"}
                    </Badge>
                    <span className="text-xs text-ink-400">
                      截止：{act.deadline}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* 底部 */}
      <div className="flex items-center justify-between pt-4">
        <p className="text-xs text-ink-400">
          这是AI自动生成的草稿，你可以随时回到这里查看
        </p>
        <Button
          variant="primary"
          size="sm"
          onClick={() => router.push("/dashboard")}
        >
          <Target className="h-3.5 w-3.5" />
          回到看板
        </Button>
      </div>
    </div>
  );
}