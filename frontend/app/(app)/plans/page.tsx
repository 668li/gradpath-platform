"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Target,
  Clock,
  TrendingUp,
  CheckCircle2,
  Circle,
  Loader2,
  AlertCircle,
  ChevronRight,
  Lightbulb,
} from "lucide-react";
import { careerPlansApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Badge } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { CareerPlan, Milestone } from "@/types";

const STATUS_CONFIG: Record<
  string,
  { label: string; color: "slate" | "blue" | "green" | "amber" | "red" }
> = {
  draft: { label: "草稿", color: "slate" },
  active: { label: "进行中", color: "blue" },
  completed: { label: "已完成", color: "green" },
  archived: { label: "已归档", color: "slate" },
};

const MILESTONE_STATUS = {
  pending: { label: "待开始", icon: Circle, color: "text-slate-400" },
  in_progress: { label: "进行中", icon: Loader2, color: "text-blue-500" },
  done: { label: "已完成", icon: CheckCircle2, color: "text-green-500" },
};

const NEXT_STATUS: Record<string, string> = {
  pending: "in_progress",
  in_progress: "done",
  done: "pending",
};

export default function PlansPage() {
  const toast = useToast();
  const [plans, setPlans] = useState<CareerPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [updatingIdx, setUpdatingIdx] = useState<string | null>(null);

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    setLoading(true);
    try {
      const data = await careerPlansApi.list();
      setPlans(data);
      if (data.length > 0) setExpandedId(data[0].id);
    } catch {
      toast.push("加载规划失败", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleMilestone = async (planId: string, idx: number, currentStatus: string) => {
    const nextStatus = NEXT_STATUS[currentStatus] || "pending";
    setUpdatingIdx(`${planId}-${idx}`);
    try {
      const updated = await careerPlansApi.updateMilestone(planId, idx, nextStatus);
      setPlans((prev) => prev.map((p) => (p.id === planId ? updated : p)));
    } catch {
      toast.push("更新失败", "error");
    } finally {
      setUpdatingIdx(null);
    }
  };

  if (loading) return <LoadingState />;
  if (plans.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="page-title">职业规划</h1>
          <p className="text-sm text-slate-500 mt-1">追踪你的职业目标和里程碑进度</p>
        </div>
        <EmptyState
          title="暂无职业规划"
          description="在与 AI 管家对话时，提到「规划」「路径」等关键词，AI 会自动为你生成结构化的职业规划方案。"
          action={
            <Link
              href="/chat"
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
            >
              <Target className="h-4 w-4" />
              去对话生成规划
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">职业规划</h1>
          <p className="text-sm text-slate-500 mt-1">
            追踪你的职业目标和里程碑进度
          </p>
        </div>
        <Link
          href="/chat"
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
        >
          <Target className="h-4 w-4" />
          新建规划
        </Link>
      </div>

      {/* 统计概览 */}
      <div className="grid grid-cols-3 gap-4">
        <SummaryCard
          label="规划总数"
          value={plans.length}
          icon={<Target className="h-5 w-5" />}
          color="blue"
        />
        <SummaryCard
          label="进行中"
          value={plans.filter((p) => p.status === "active").length}
          icon={<Loader2 className="h-5 w-5" />}
          color="amber"
        />
        <SummaryCard
          label="已完成里程碑"
          value={plans.reduce(
            (sum, p) => sum + p.milestones.filter((m) => m.status === "done").length,
            0,
          )}
          icon={<CheckCircle2 className="h-5 w-5" />}
          color="green"
        />
      </div>

      {/* 规划列表 */}
      <div className="space-y-4">
        {plans.map((plan) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            expanded={expandedId === plan.id}
            onToggle={() =>
              setExpandedId(expandedId === plan.id ? null : plan.id)
            }
            onToggleMilestone={handleToggleMilestone}
            updatingIdx={updatingIdx}
          />
        ))}
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: "blue" | "amber" | "green";
}) {
  const colors = {
    blue: "bg-blue-50 text-blue-600",
    amber: "bg-amber-50 text-amber-600",
    green: "bg-green-50 text-green-600",
  };
  return (
    <div className="card flex items-center gap-3">
      <div
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-lg",
          colors[color],
        )}
      >
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800">{value}</p>
        <p className="text-xs text-slate-400">{label}</p>
      </div>
    </div>
  );
}

function PlanCard({
  plan,
  expanded,
  onToggle,
  onToggleMilestone,
  updatingIdx,
}: {
  plan: CareerPlan;
  expanded: boolean;
  onToggle: () => void;
  onToggleMilestone: (planId: string, idx: number, currentStatus: string) => void;
  updatingIdx: string | null;
}) {
  const statusConfig = STATUS_CONFIG[plan.status] || STATUS_CONFIG.draft;
  const doneCount = plan.milestones.filter((m) => m.status === "done").length;
  const totalCount = plan.milestones.length;
  const progress = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0;

  return (
    <div className="card overflow-hidden">
      {/* 卡片头部 */}
      <button
        onClick={onToggle}
        className="flex w-full items-start gap-4 p-4 text-left transition-colors hover:bg-slate-50/50"
      >
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50">
          <Target className="h-5 w-5 text-brand-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-slate-800">{plan.goal_text}</h3>
            <Badge color={statusConfig.color}>{statusConfig.label}</Badge>
          </div>
          <div className="mt-1 flex items-center gap-4 text-xs text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              预计 {plan.timeline_months} 个月
            </span>
            <span className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              {doneCount}/{totalCount} 里程碑
            </span>
            <span>创建于 {formatDate(plan.created_at)}</span>
          </div>
          {/* 进度条 */}
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        <ChevronRight
          className={cn(
            "h-5 w-5 shrink-0 text-slate-400 transition-transform",
            expanded && "rotate-90",
          )}
        />
      </button>

      {/* 展开内容 */}
      {expanded && (
        <div className="border-t border-slate-100 p-4 space-y-4">
          {/* 当前状态 vs 目标状态 */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-slate-50 p-3">
              <p className="mb-2 text-xs font-semibold text-slate-500">当前状态</p>
              <StateDisplay state={plan.current_state} />
            </div>
            <div className="rounded-lg bg-brand-50/30 p-3">
              <p className="mb-2 text-xs font-semibold text-brand-600">目标状态</p>
              <StateDisplay state={plan.target_state} />
            </div>
          </div>

          {/* 差距分析 */}
          {plan.gaps.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/30 p-3">
              <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-amber-700">
                <AlertCircle className="h-3.5 w-3.5" />
                差距分析
              </p>
              <ul className="space-y-1">
                {plan.gaps.map((gap, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber-400" />
                    {gap}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 里程碑列表 */}
          {plan.milestones.length > 0 ? (
            <div>
              <p className="mb-2 text-xs font-semibold text-slate-500">里程碑</p>
              <div className="space-y-1">
                {plan.milestones.map((m, idx) => (
                  <MilestoneItem
                    key={idx}
                    milestone={m}
                    idx={idx}
                    planId={plan.id}
                    onToggle={onToggleMilestone}
                    updating={updatingIdx === `${plan.id}-${idx}`}
                  />
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">暂无里程碑</p>
          )}

          {/* 关联对话 */}
          {plan.conversation_id && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Lightbulb className="h-3.5 w-3.5" />
              <span>此规划由 AI 对话生成</span>
              <Link
                href="/chat"
                className="text-brand-600 hover:underline"
              >
                查看对话
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StateDisplay({ state }: { state: Record<string, unknown> }) {
  const entries = Object.entries(state);
  if (entries.length === 0) {
    return <p className="text-xs text-slate-400">暂无数据</p>;
  }
  return (
    <ul className="space-y-1">
      {entries.map(([key, value]) => (
        <li key={key} className="text-sm text-slate-600">
          <span className="font-medium text-slate-700">{key}:</span>{" "}
          {Array.isArray(value) ? value.join("、") : String(value)}
        </li>
      ))}
    </ul>
  );
}

function MilestoneItem({
  milestone,
  idx,
  planId,
  onToggle,
  updating,
}: {
  milestone: Milestone;
  idx: number;
  planId: string;
  onToggle: (planId: string, idx: number, currentStatus: string) => void;
  updating: boolean;
}) {
  const statusConfig =
    MILESTONE_STATUS[milestone.status as keyof typeof MILESTONE_STATUS] ||
    MILESTONE_STATUS.pending;
  const Icon = statusConfig.icon;

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg px-3 py-2 transition-colors",
        milestone.status === "done"
          ? "bg-green-50/30"
          : milestone.status === "in_progress"
            ? "bg-blue-50/30"
            : "hover:bg-slate-50",
      )}
    >
      <button
        onClick={() => onToggle(planId, idx, milestone.status)}
        disabled={updating}
        className="mt-0.5 shrink-0 disabled:cursor-wait"
        aria-label={`切换状态（当前: ${statusConfig.label}）`}
      >
        <Icon
          className={cn(
            "h-5 w-5",
            statusConfig.color,
            milestone.status === "in_progress" && "animate-spin",
            updating && "opacity-50",
          )}
        />
      </button>
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm font-medium",
            milestone.status === "done"
              ? "text-slate-400 line-through"
              : "text-slate-700",
          )}
        >
          {milestone.title}
        </p>
        {milestone.description && (
          <p className="mt-0.5 text-xs text-slate-400">{milestone.description}</p>
        )}
        <div className="mt-0.5 flex items-center gap-2">
          <span className="text-[10px] text-slate-400">{statusConfig.label}</span>
          {milestone.target_date && (
            <span className="text-[10px] text-slate-400">
              · 目标: {formatDate(milestone.target_date)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
