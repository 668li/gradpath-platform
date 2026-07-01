"use client";

import { useEffect, useState, useCallback } from "react";
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
  Send,
  Trash2,
  MessageSquare,
  Sparkles,
  Check,
} from "lucide-react";
import { careerPlansApi, planTemplatesApi } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { CareerPlan, Milestone, MilestoneLog, PlanTemplate } from "@/types";

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
  pending: { label: "待开始", icon: Circle, color: "text-ink-300" },
  in_progress: { label: "进行中", icon: Loader2, color: "text-brand-500" },
  done: { label: "已完成", icon: CheckCircle2, color: "text-brand-600" },
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
    return <EmptyPlansState onCreated={loadPlans} toast={toast} />;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">职业规划</h1>
          <p className="text-sm text-ink-400 mt-1.5">
            追踪你的职业目标和里程碑进度
          </p>
        </div>
        <Link
          href="/chat"
          className="inline-flex items-center gap-1.5 rounded-lg border border-paper-300 bg-white px-4 py-2 text-sm font-medium text-ink-700 transition-all hover:bg-paper-100 hover:border-ink-200"
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
          color="brand"
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
            toast={toast}
            onPlanUpdate={(updated) =>
              setPlans((prev) => prev.map((p) => (p.id === updated.id ? updated : p)))
            }
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
  color: "brand" | "amber" | "green";
}) {
  const colors = {
    brand: "bg-brand-50 text-brand-600",
    amber: "bg-amber-50 text-amber-600",
    green: "bg-brand-100 text-brand-700",
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
        <p className="font-display text-2xl font-bold text-ink-800">{value}</p>
        <p className="text-xs text-ink-400">{label}</p>
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
  toast,
  onPlanUpdate,
}: {
  plan: CareerPlan;
  expanded: boolean;
  onToggle: () => void;
  onToggleMilestone: (planId: string, idx: number, currentStatus: string) => void;
  updatingIdx: string | null;
  toast: ReturnType<typeof useToast>;
  onPlanUpdate: (plan: CareerPlan) => void;
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
        className="flex w-full items-start gap-4 p-4 text-left transition-colors hover:bg-paper-50/50"
      >
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50">
          <Target className="h-5 w-5 text-brand-600" strokeWidth={2} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-display font-semibold text-ink-800">{plan.goal_text}</h3>
            <Badge color={statusConfig.color}>{statusConfig.label}</Badge>
          </div>
          <div className="mt-1 flex items-center gap-4 text-xs text-ink-400">
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
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-paper-200">
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        <ChevronRight
          className={cn(
            "h-5 w-5 shrink-0 text-ink-300 transition-transform",
            expanded && "rotate-90",
          )}
        />
      </button>

      {/* 展开内容 */}
      {expanded && (
        <div className="border-t border-paper-200 p-4 space-y-4 animate-fade-in">
          {/* 当前状态 vs 目标状态 */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-paper-50 p-3">
              <p className="mb-2 text-xs font-semibold text-ink-500">当前状态</p>
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
                  <li key={i} className="flex items-start gap-2 text-sm text-ink-600">
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
              <p className="mb-2 text-xs font-semibold text-ink-500">里程碑</p>
              <div className="space-y-2">
                {plan.milestones.map((m, idx) => (
                  <MilestoneItem
                    key={idx}
                    milestone={m}
                    idx={idx}
                    planId={plan.id}
                    onToggle={onToggleMilestone}
                    updating={updatingIdx === `${plan.id}-${idx}`}
                    toast={toast}
                  />
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-ink-400">暂无里程碑</p>
          )}

          {/* 关联对话 */}
          {plan.conversation_id && (
            <div className="flex items-center gap-2 text-xs text-ink-400">
              <Lightbulb className="h-3.5 w-3.5" />
              <span>此规划由 AI 对话生成</span>
              <Link
                href="/chat"
                className="text-brand-600 hover:text-brand-700 transition-colors"
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

/** 空状态 + 规划模板选择器 */
function EmptyPlansState({
  onCreated,
  toast,
}: {
  onCreated: () => void;
  toast: ReturnType<typeof useToast>;
}) {
  const [templates, setTemplates] = useState<PlanTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [creatingId, setCreatingId] = useState<string | null>(null);

  useEffect(() => {
    planTemplatesApi
      .list()
      .then(setTemplates)
      .catch(() => {})
      .finally(() => setLoadingTemplates(false));
  }, []);

  const handleCreateFromTemplate = async (tpl: PlanTemplate) => {
    setCreatingId(tpl.id);
    try {
      // 通过对话 API 创建一个带模板数据的规划
      // 直接调用 career-plans 的方式不存在，我们通过 chat API 间接创建
      // 或者直接在前端构造一个请求 — 但后端没有创建 plan 的端点
      // 使用 chat API: 创建对话 → 发送模板内容 → 获取 plan
      const { chatApi } = await import("@/lib/api");
      const conv = await chatApi.createConversation(`规划：${tpl.name}`);
      // 发送一条消息让 AI 保存这个规划
      const msg = `请帮我创建一个职业规划：目标 - ${tpl.goal_text}，时间线 - ${tpl.timeline_months}个月。以下是参考里程碑：\n${tpl.milestones.map((m, i) => `${i + 1}. ${m.title}：${m.description}`).join("\n")}`;
      const res = await chatApi.sendMessage(conv.id, { content: msg });
      if (res.career_plan) {
        toast.push("规划已创建", "success");
        onCreated();
      } else {
        // AI 没有自动生成规划，提示用户
        toast.push("AI 正在生成规划，请稍后到列表查看", "success");
        onCreated();
      }
    } catch {
      toast.push("创建失败，请重试", "error");
    } finally {
      setCreatingId(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="page-title">职业规划</h1>
        <p className="text-sm text-ink-400 mt-1.5">追踪你的职业目标和里程碑进度</p>
      </div>

      {/* 规划模板 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="h-5 w-5 text-brand-600" />
          <h2 className="font-display font-semibold text-ink-800">从模板创建规划</h2>
        </div>
        <p className="text-sm text-ink-400 mb-4">
          选择一个常见职业路径模板，一键生成结构化规划方案
        </p>

        {loadingTemplates ? (
          <LoadingState text="加载模板…" />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {templates.map((tpl) => (
              <button
                key={tpl.id}
                onClick={() => handleCreateFromTemplate(tpl)}
                disabled={creatingId !== null}
                className="group relative flex flex-col rounded-xl border border-paper-300 bg-white p-4 text-left transition-all hover:border-brand-300 hover:shadow-card-hover disabled:opacity-50"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{tpl.icon}</span>
                  <h3 className="font-display font-semibold text-ink-800">{tpl.name}</h3>
                </div>
                <p className="text-xs text-ink-400 flex-1 line-clamp-2 mb-3">
                  {tpl.description}
                </p>
                <div className="flex items-center gap-3 text-[11px] text-ink-400">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {tpl.timeline_months} 个月
                  </span>
                  <span className="flex items-center gap-1">
                    <Check className="h-3 w-3" />
                    {tpl.milestones.length} 个里程碑
                  </span>
                </div>
                {creatingId === tpl.id && (
                  <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-white/80">
                    <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-brand-200 border-t-brand-500" />
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* AI 对话入口 */}
      <div className="flex items-center gap-4 rounded-xl border border-brand-200 bg-gradient-to-r from-brand-50 to-paper-50 p-4 transition-all hover:shadow-card-hover">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white shadow-brand-sm">
          <Target className="h-6 w-6" strokeWidth={2} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-display font-semibold text-ink-800">与 AI 管家对话生成规划</p>
          <p className="text-sm text-ink-400">
            不想用模板？直接和 AI 对话，提到「规划」「路径」等关键词，AI 会根据你的画像个性化生成方案
          </p>
        </div>
        <Link
          href="/chat"
          className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-brand-sm transition-all hover:bg-brand-700 hover:shadow-brand"
        >
          <Target className="h-4 w-4" />
          去对话
        </Link>
      </div>
    </div>
  );
}

function StateDisplay({ state }: { state: Record<string, unknown> }) {
  const entries = Object.entries(state);
  if (entries.length === 0) {
    return <p className="text-xs text-ink-300">暂无数据</p>;
  }
  return (
    <ul className="space-y-1">
      {entries.map(([key, value]) => (
        <li key={key} className="text-sm text-ink-600">
          <span className="font-medium text-ink-700">{key}:</span>{" "}
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
  toast,
}: {
  milestone: Milestone;
  idx: number;
  planId: string;
  onToggle: (planId: string, idx: number, currentStatus: string) => void;
  updating: boolean;
  toast: ReturnType<typeof useToast>;
}) {
  const [logs, setLogs] = useState<MilestoneLog[]>([]);
  const [logInput, setLogInput] = useState("");
  const [showLogs, setShowLogs] = useState(false);
  const [addingLog, setAddingLog] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState(false);

  const statusConfig =
    MILESTONE_STATUS[milestone.status as keyof typeof MILESTONE_STATUS] ||
    MILESTONE_STATUS.pending;
  const Icon = statusConfig.icon;

  const loadLogs = useCallback(async () => {
    setLoadingLogs(true);
    try {
      const data = await careerPlansApi.listLogs(planId, idx);
      setLogs(data);
    } catch {
      toast.push("加载日志失败", "error");
    } finally {
      setLoadingLogs(false);
    }
  }, [planId, idx, toast]);

  const handleToggleLogs = () => {
    if (!showLogs && logs.length === 0) {
      loadLogs();
    }
    setShowLogs(!showLogs);
  };

  const handleAddLog = async () => {
    const content = logInput.trim();
    if (!content || addingLog) return;
    setAddingLog(true);
    try {
      const log = await careerPlansApi.addLog(planId, idx, content);
      setLogs((prev) => [...prev, log]);
      setLogInput("");
    } catch {
      toast.push("添加日志失败", "error");
    } finally {
      setAddingLog(false);
    }
  };

  const handleDeleteLog = async (logId: string) => {
    try {
      await careerPlansApi.deleteLog(planId, logId);
      setLogs((prev) => prev.filter((l) => l.id !== logId));
    } catch {
      toast.push("删除失败", "error");
    }
  };

  const handleLogKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAddLog();
    }
  };

  return (
    <div
      className={cn(
        "rounded-lg border transition-colors",
        milestone.status === "done"
          ? "border-brand-100 bg-brand-50/20"
          : milestone.status === "in_progress"
            ? "border-brand-200 bg-brand-50/30"
            : "border-paper-200 bg-white",
      )}
    >
      <div className="flex items-start gap-3 px-3 py-2.5">
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
                ? "text-ink-400 line-through"
                : "text-ink-700",
            )}
          >
            {milestone.title}
          </p>
          {milestone.description && (
            <p className="mt-0.5 text-xs text-ink-400">{milestone.description}</p>
          )}
          <div className="mt-1 flex items-center gap-3">
            <span className="text-[10px] text-ink-400">{statusConfig.label}</span>
            {milestone.target_date && (
              <span className="text-[10px] text-ink-400">
                · 目标: {formatDate(milestone.target_date)}
              </span>
            )}
            {/* 执行日志切换按钮 */}
            <button
              onClick={handleToggleLogs}
              className="flex items-center gap-1 text-[10px] text-ink-400 hover:text-brand-600 transition-colors"
            >
              <MessageSquare className="h-3 w-3" />
              {showLogs ? "收起日志" : "执行日志"}
              {logs.length > 0 && (
                <span className="rounded-full bg-brand-100 px-1.5 text-brand-600">
                  {logs.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 执行日志区域 */}
      {showLogs && (
        <div className="border-t border-paper-200 px-3 py-2.5 space-y-2 animate-fade-in">
          {loadingLogs ? (
            <p className="text-xs text-ink-300">加载日志…</p>
          ) : (
            <>
              {/* 日志列表 */}
              {logs.length > 0 ? (
                <div className="space-y-1.5">
                  {logs.map((log) => (
                    <div
                      key={log.id}
                      className="group flex items-start gap-2 rounded-md bg-paper-50 px-2.5 py-1.5"
                    >
                      <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-ink-700">{log.content}</p>
                        <p className="text-[10px] text-ink-300 mt-0.5">
                          {formatDate(log.created_at)}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDeleteLog(log.id)}
                        className="opacity-0 group-hover:opacity-100 text-ink-300 hover:text-red-500 transition-all"
                        aria-label="删除日志"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-ink-300">暂无执行记录</p>
              )}

              {/* 日志输入框 */}
              <div className="flex items-center gap-1.5">
                <input
                  value={logInput}
                  onChange={(e) => setLogInput(e.target.value)}
                  onKeyDown={handleLogKeyDown}
                  placeholder="记录执行进度…"
                  className="flex-1 rounded-md border border-paper-300 bg-white px-2.5 py-1.5 text-xs text-ink-700 placeholder:text-ink-300 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-100"
                  disabled={addingLog}
                />
                <button
                  onClick={handleAddLog}
                  disabled={!logInput.trim() || addingLog}
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-brand-600 text-white transition-colors hover:bg-brand-700 disabled:bg-brand-300"
                  aria-label="添加日志"
                >
                  <Send className="h-3 w-3" />
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
