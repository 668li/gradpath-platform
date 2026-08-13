"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Footprints,
  Search,
  MessageCircle,
  Wrench,
  NotebookPen,
  CheckCircle2,
  SkipForward,
  Sparkles,
  ArrowRight,
  RotateCcw,
  Clock,
} from "lucide-react";
import { microActionApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Textarea, Badge } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type {
  MicroActionPlanResponse,
  MicroActionTaskResponse,
  MicroActionTargetPath,
} from "@/types/micro-action";

// ----------------------------------------------------------------------
// 元数据
// ----------------------------------------------------------------------
const PATH_OPTIONS: {
  value: MicroActionTargetPath;
  label: string;
  desc: string;
  icon: string;
}[] = [
  {
    value: "kaoyan",
    label: "考研",
    desc: "验证你对目标院校/专业的真实兴趣",
    icon: "🎓",
  },
  {
    value: "employment",
    label: "就业",
    desc: "验证你对目标岗位的真实匹配度",
    icon: "💼",
  },
  {
    value: "civil_service",
    label: "考公",
    desc: "验证你对目标岗位的适配感",
    icon: "🏛️",
  },
];

const TASK_TYPE_META: Record<
  string,
  { label: string; icon: typeof Search; color: string }
> = {
  research: { label: "调研", icon: Search, color: "text-blue-500" },
  interview: { label: "访谈", icon: MessageCircle, color: "text-purple-500" },
  practice: { label: "实践", icon: Wrench, color: "text-amber-500" },
  reflect: { label: "复盘", icon: NotebookPen, color: "text-brand-500" },
};

const TASK_STATUS_META: Record<
  string,
  { label: string; badge: "slate" | "green" | "amber" }
> = {
  pending: { label: "待完成", badge: "slate" },
  completed: { label: "已完成", badge: "green" },
  skipped: { label: "已跳过", badge: "amber" },
};

// ----------------------------------------------------------------------
// 页面
// ----------------------------------------------------------------------
export default function MicroActionsPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [plan, setPlan] = useState<MicroActionPlanResponse | null>(null);
  const [history, setHistory] = useState<MicroActionPlanResponse[]>([]);
  const [showCreate, setShowCreate] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [current, hist] = await Promise.all([
        microActionApi.getCurrentPlan(),
        microActionApi.getHistory().catch(() => []),
      ]);
      setPlan(current);
      setHistory(hist);
    } catch {
      toast.push("加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handlePlanCreated = useCallback(
    (newPlan: MicroActionPlanResponse) => {
      setPlan(newPlan);
      setShowCreate(false);
      toast.success("7天微行动计划已创建");
      loadData();
    },
    [toast, loadData],
  );

  const handleTaskUpdated = useCallback(() => {
    loadData();
  }, [loadData]);

  if (loading) return <LoadingState />;

  // 创建表单
  if (showCreate || (!plan && history.length === 0)) {
    return (
      <CreatePlanView
        onCreated={handlePlanCreated}
        onCancel={() => setShowCreate(false)}
        hasExistingPlan={!!plan}
      />
    );
  }

  // 有活跃计划 → 任务列表
  if (plan && plan.status === "active") {
    return (
      <ActivePlanView
        plan={plan}
        onTaskUpdated={handleTaskUpdated}
        onCreateNew={() => setShowCreate(true)}
      />
    );
  }

  // 计划已完成 → 自我发现报告
  if (plan && plan.status === "completed") {
    return (
      <ReportView
        plan={plan}
        onCreateNew={() => setShowCreate(true)}
      />
    );
  }

  // 无活跃计划但有历史 → 展示历史 + 创建入口
  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <Footprints className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">7天微行动</h1>
        <p className="text-sm text-ink-400 mt-2 leading-relaxed">
          不替你决定，而是给你 7 天低成本探索任务
          <br />
          想多了全是问题，做多了全是答案
        </p>
      </div>

      <div className="card space-y-3">
        <h2 className="font-display text-lg font-semibold text-ink-800">
          历史计划
        </h2>
        {history.length === 0 ? (
          <EmptyState
            title="还没有计划"
            description="创建第一个 7 天微行动计划，开始低成本探索"
          />
        ) : (
          <ul className="divide-y divide-paper-200">
            {history.map((p) => (
              <li
                key={p.id}
                className="flex items-center justify-between py-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-ink-800">
                    {pathLabel(p.target_path)}
                    {p.target_role && (
                      <span className="text-ink-400 ml-1">
                        · {p.target_role}
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-ink-400 mt-0.5">
                    {p.tasks.filter((t) => t.status !== "pending").length}
                    /7 完成 · {p.progress}%
                  </p>
                </div>
                <Badge
                  color={p.status === "completed" ? "green" : "amber"}
                >
                  {p.status === "completed" ? "已完成" : "已放弃"}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Button onClick={() => setShowCreate(true)} className="w-full" size="md">
        <Sparkles className="h-4 w-4" />
        创建新计划
      </Button>
    </div>
  );
}

// ----------------------------------------------------------------------
// 创建计划视图
// ----------------------------------------------------------------------
function CreatePlanView({
  onCreated,
  onCancel,
  hasExistingPlan,
}: {
  onCreated: (plan: MicroActionPlanResponse) => void;
  onCancel: () => void;
  hasExistingPlan: boolean;
}) {
  const toast = useToast();
  const [selectedPath, setSelectedPath] = useState<MicroActionTargetPath | "">(
    "",
  );
  const [targetRole, setTargetRole] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!selectedPath) {
      toast.push("请选择目标路径", "error");
      return;
    }
    setSubmitting(true);
    try {
      const newPlan = await microActionApi.createPlan({
        target_path: selectedPath,
        target_role: targetRole.trim() || null,
      });
      onCreated(newPlan);
    } catch {
      toast.push("创建失败，请重试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <Footprints className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">7天微行动</h1>
        <p className="text-sm text-ink-400 mt-2 leading-relaxed">
          不替你决定，而是给你 7 天低成本探索任务
          <br />
          想多了全是问题，做多了全是答案
        </p>
      </div>

      {hasExistingPlan && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3">
          <p className="text-sm text-amber-700">
            创建新计划将放弃当前进行中的计划。
          </p>
        </div>
      )}

      <div className="card space-y-5">
        <div className="space-y-1">
          <h2 className="font-display text-lg font-semibold text-ink-800">
            选择目标路径
          </h2>
          <p className="text-xs text-ink-400">
            7 天任务会根据你选择的路径定制，每天 15-30 分钟可完成。
          </p>
        </div>

        <div className="space-y-3">
          {PATH_OPTIONS.map((opt) => {
            const selected = selectedPath === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => setSelectedPath(opt.value)}
                className={cn(
                  "group flex w-full items-start gap-3 rounded-xl border p-4 text-left transition-all",
                  selected
                    ? "border-brand-500 bg-brand-50/50 ring-2 ring-brand-100"
                    : "border-paper-200 bg-white hover:border-paper-300 hover:bg-paper-50",
                )}
              >
                <span className="text-2xl shrink-0">{opt.icon}</span>
                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      "text-sm font-medium",
                      selected ? "text-brand-700" : "text-ink-800",
                    )}
                  >
                    {opt.label}
                  </p>
                  <p className="text-xs text-ink-400 mt-0.5 leading-relaxed">
                    {opt.desc}
                  </p>
                </div>
                {selected && (
                  <CheckCircle2 className="h-5 w-5 text-brand-600 shrink-0" />
                )}
              </button>
            );
          })}
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium text-ink-700">
            具体目标{" "}
            <span className="text-ink-400 font-normal">（可选）</span>
          </label>
          <input
            type="text"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            maxLength={100}
            placeholder={
              selectedPath === "kaoyan"
                ? "如：清华计算机"
                : selectedPath === "employment"
                  ? "如：字节前端工程师"
                  : selectedPath === "civil_service"
                    ? "如：杭州税务岗"
                    : "填写具体目标，便于任务更聚焦"
            }
            className="w-full rounded-lg border border-paper-300 bg-white px-3 py-2 text-sm text-ink-800 placeholder:text-ink-300 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 transition-colors"
          />
        </div>

        <div className="rounded-lg bg-paper-50 p-4 space-y-2">
          <p className="text-xs font-medium text-ink-500">7 天任务结构</p>
          <div className="grid grid-cols-2 gap-2 text-xs text-ink-400">
            <div className="flex items-center gap-1.5">
              <Search className="h-3.5 w-3.5" /> 2 天调研
            </div>
            <div className="flex items-center gap-1.5">
              <MessageCircle className="h-3.5 w-3.5" /> 1 天访谈
            </div>
            <div className="flex items-center gap-1.5">
              <Wrench className="h-3.5 w-3.5" /> 2 天实践
            </div>
            <div className="flex items-center gap-1.5">
              <NotebookPen className="h-3.5 w-3.5" /> 2 天复盘
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        {hasExistingPlan ? (
          <button
            onClick={onCancel}
            className="text-sm text-ink-400 hover:text-ink-600 transition-colors"
          >
            ← 返回
          </button>
        ) : (
          <span />
        )}
        <Button
          onClick={handleSubmit}
          loading={submitting}
          disabled={!selectedPath}
          size="md"
        >
          <Footprints className="h-4 w-4" />
          开始 7 天探索
        </Button>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 活跃计划视图（任务列表）
// ----------------------------------------------------------------------
function ActivePlanView({
  plan,
  onTaskUpdated,
  onCreateNew,
}: {
  plan: MicroActionPlanResponse;
  onTaskUpdated: () => void;
  onCreateNew: () => void;
}) {
  const toast = useToast();
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [userResponses, setUserResponses] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const pendingTasks = plan.tasks.filter((t) => t.status === "pending");
  const firstPending = pendingTasks[0];

  const getCurrentResponse = () => {
    const taskId = activeTaskId;
    return taskId ? (userResponses[taskId] || "") : "";
  };

  const handleResponseChange = (text: string) => {
    if (activeTaskId) {
      setUserResponses(prev => ({ ...prev, [activeTaskId]: text }));
    }
  };

  const handleComplete = async (taskId: string) => {
    const response = userResponses[taskId] || "";
    if (!response.trim()) {
      toast.push("请记录你完成本次任务的发现", "error");
      return;
    }
    setSubmitting(true);
    try {
      await microActionApi.completeTask(taskId, {
        user_response: response.trim(),
      });
      toast.success("任务已完成");
      setActiveTaskId(null);
      setUserResponses(prev => { const next = { ...prev }; delete next[taskId]; return next; });
      onTaskUpdated();
    } catch {
      toast.push("操作失败，请重试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSkip = async (taskId: string) => {
    setSubmitting(true);
    try {
      await microActionApi.skipTask(taskId);
      toast.info("已跳过该任务");
      setActiveTaskId(null);
      setUserResponses(prev => { const next = { ...prev }; delete next[taskId]; return next; });
      onTaskUpdated();
    } catch {
      toast.push("操作失败，请重试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* 头部 */}
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <Footprints className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">7天微行动</h1>
        <p className="text-sm text-ink-400 mt-2">
          {pathLabel(plan.target_path)}
          {plan.target_role && (
            <span className="text-ink-500"> · {plan.target_role}</span>
          )}
        </p>
      </div>

      {/* 进度条 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-ink-600">
            已完成 {plan.tasks.filter((t) => t.status !== "pending").length} / 7
          </span>
          <span className="text-xs text-ink-400">{plan.progress}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-paper-200">
          <div
            className="h-full rounded-full bg-brand-500 transition-all duration-300"
            style={{ width: `${plan.progress}%` }}
          />
        </div>
      </div>

      {/* 任务列表 */}
      <div className="space-y-3">
        {plan.tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            isActive={activeTaskId === task.id}
            isNext={task.id === firstPending?.id}
            userResponse={getCurrentResponse()}
            submitting={submitting}
            onToggle={() => {
              if (activeTaskId === task.id) {
                setActiveTaskId(null);
              } else {
                setActiveTaskId(task.id);
                if (task.user_response && !userResponses[task.id]) {
                  setUserResponses(prev => ({ ...prev, [task.id]: task.user_response || "" }));
                }
              }
            }}
            onResponseChange={handleResponseChange}
            onComplete={() => handleComplete(task.id)}
            onSkip={() => handleSkip(task.id)}
          />
        ))}
      </div>

      {/* 操作 */}
      <div className="flex justify-center">
        <Button variant="ghost" size="sm" onClick={onCreateNew}>
          <RotateCcw className="h-3.5 w-3.5" />
          放弃并重新开始
        </Button>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 单个任务卡片
// ----------------------------------------------------------------------
function TaskCard({
  task,
  isActive,
  isNext,
  userResponse,
  submitting,
  onToggle,
  onResponseChange,
  onComplete,
  onSkip,
}: {
  task: MicroActionTaskResponse;
  isActive: boolean;
  isNext: boolean;
  userResponse: string;
  submitting: boolean;
  onToggle: () => void;
  onResponseChange: (v: string) => void;
  onComplete: () => void;
  onSkip: () => void;
}) {
  const typeMeta = TASK_TYPE_META[task.task_type] || TASK_TYPE_META.research;
  const statusMeta =
    TASK_STATUS_META[task.status] || TASK_STATUS_META.pending;
  const TypeIcon = typeMeta.icon;
  const isDone = task.status !== "pending";

  return (
    <div
      className={cn(
        "card transition-all",
        isNext && !isDone && "border-brand-300 ring-1 ring-brand-100",
        isDone && "opacity-75",
      )}
    >
      {/* 卡片头 */}
      <button
        onClick={onToggle}
        disabled={isDone && !task.insight}
        className="flex w-full items-start gap-3 text-left"
      >
        {/* Day 标记 */}
        <div
          className={cn(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-xs font-bold",
            task.status === "completed"
              ? "bg-brand-100 text-brand-700"
              : task.status === "skipped"
                ? "bg-amber-100 text-amber-700"
                : isNext
                  ? "bg-brand-500 text-white"
                  : "bg-paper-100 text-ink-400",
          )}
        >
          {task.status === "completed" ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            `D${task.day_number}`
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-ink-800">
              {task.title}
            </span>
            <Badge color={statusMeta.badge}>{statusMeta.label}</Badge>
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-ink-400">
            <span className={cn("flex items-center gap-1", typeMeta.color)}>
              <TypeIcon className="h-3 w-3" />
              {typeMeta.label}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              约 {task.estimated_minutes} 分钟
            </span>
          </div>
        </div>
      </button>

      {/* 任务描述 */}
      <p className="text-sm text-ink-600 leading-relaxed mt-3 whitespace-pre-line">
        {task.description}
      </p>

      {/* 已完成任务的洞察 */}
      {isDone && task.insight && (
        <div className="mt-3 rounded-lg bg-brand-50/50 border border-brand-100 p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <Sparkles className="h-3.5 w-3.5 text-brand-600" />
            <span className="text-xs font-medium text-brand-700">AI 洞察</span>
          </div>
          <p className="text-xs text-ink-600 leading-relaxed whitespace-pre-line">
            {task.insight}
          </p>
        </div>
      )}

      {/* 已完成任务的用户记录 */}
      {isDone && task.user_response && (
        <div className="mt-2">
          <p className="text-xs text-ink-400 mb-0.5">你的记录：</p>
          <p className="text-xs text-ink-500 leading-relaxed">
            {task.user_response}
          </p>
        </div>
      )}

      {/* 待完成任务的展开操作区 */}
      {task.status === "pending" && isActive && (
        <div className="mt-4 space-y-3 border-t border-paper-200 pt-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-ink-700">
              记录你的发现{" "}
              <span className="text-ink-400 font-normal">
                （完成后将生成 AI 洞察）
              </span>
            </label>
            <Textarea
              value={userResponse}
              onChange={(e) => onResponseChange(e.target.value)}
              placeholder="写下你做完这个任务后的具体发现、感受或疑问…"
              className="resize-y"
              rows={3}
            />
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={onComplete}
              loading={submitting}
              size="sm"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              完成任务
            </Button>
            <Button
              onClick={onSkip}
              disabled={submitting}
              variant="ghost"
              size="sm"
            >
              <SkipForward className="h-3.5 w-3.5" />
              跳过
            </Button>
          </div>
        </div>
      )}

      {/* 下一任务提示 */}
      {task.status === "pending" && isNext && !isActive && (
        <button
          onClick={onToggle}
          className="mt-3 flex items-center gap-1.5 text-xs text-brand-600 hover:text-brand-700 transition-colors"
        >
          <ArrowRight className="h-3.5 w-3.5" />
          开始这个任务
        </button>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------
// 报告视图（计划已完成）
// ----------------------------------------------------------------------
function ReportView({
  plan,
  onCreateNew,
}: {
  plan: MicroActionPlanResponse;
  onCreateNew: () => void;
}) {
  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* 头部 */}
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <Sparkles className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">自我发现报告</h1>
        <p className="text-sm text-ink-400 mt-2">
          {pathLabel(plan.target_path)}
          {plan.target_role && (
            <span className="text-ink-500"> · {plan.target_role}</span>
          )}
          {" · "}
          完成 {plan.tasks.filter((t) => t.status !== "pending").length} / 7 项
        </p>
      </div>

      {/* 报告内容 */}
      {plan.self_discovery_report ? (
        <div className="card space-y-4">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-50">
              <NotebookPen className="h-4 w-4 text-brand-600" strokeWidth={1.8} />
            </span>
            <h2 className="font-display font-semibold text-ink-800">
              你的 7 天发现
            </h2>
          </div>
          <p className="text-sm text-ink-600 leading-relaxed whitespace-pre-line">
            {plan.self_discovery_report}
          </p>
        </div>
      ) : (
        <div className="card">
          <EmptyState
            title="报告生成中"
            description="请稍后刷新页面查看你的自我发现报告"
          />
        </div>
      )}

      {/* 7 天记录回顾 */}
      <div className="card space-y-3">
        <h2 className="font-display font-semibold text-ink-800">7 天记录回顾</h2>
        <div className="space-y-3">
          {plan.tasks.map((task) => {
            const typeMeta =
              TASK_TYPE_META[task.task_type] || TASK_TYPE_META.research;
            const statusMeta =
              TASK_STATUS_META[task.status] || TASK_STATUS_META.pending;
            const TypeIcon = typeMeta.icon;
            return (
              <div
                key={task.id}
                className="rounded-lg border border-paper-200 p-3 space-y-1"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "flex h-6 w-6 items-center justify-center rounded text-[10px] font-bold",
                      task.status === "completed"
                        ? "bg-brand-100 text-brand-700"
                        : "bg-amber-100 text-amber-700",
                    )}
                  >
                    D{task.day_number}
                  </span>
                  <span className="text-sm text-ink-800 flex-1 min-w-0 truncate">
                    {task.title}
                  </span>
                  <Badge color={statusMeta.badge}>{statusMeta.label}</Badge>
                </div>
                <div className="flex items-center gap-2 text-xs text-ink-400">
                  <span className={cn("flex items-center gap-1", typeMeta.color)}>
                    <TypeIcon className="h-3 w-3" />
                    {typeMeta.label}
                  </span>
                </div>
                {task.user_response && (
                  <p className="text-xs text-ink-500 leading-relaxed mt-1">
                    {task.user_response}
                  </p>
                )}
                {task.insight && (
                  <div className="rounded bg-brand-50/50 px-2 py-1.5 mt-1">
                    <p className="text-xs text-ink-500 leading-relaxed">
                      💡 {task.insight}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 操作 */}
      <div className="flex justify-center">
        <Button onClick={onCreateNew} variant="secondary" size="md">
          <Footprints className="h-4 w-4" />
          开始新的 7 天探索
        </Button>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 辅助函数
// ----------------------------------------------------------------------
function pathLabel(path: string): string {
  const opt = PATH_OPTIONS.find((o) => o.value === path);
  return opt ? opt.label : path;
}
