"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ListChecks,
  Plus,
  Flame,
  BookOpen,
  GraduationCap,
  FileText,
  MessageSquare,
  Send,
  Trophy,
  Sparkles,
  CheckCircle2,
  CalendarDays,
} from "lucide-react";
import { actionsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Badge, Input, Textarea, Select, Field } from "@/components/ui/form-controls";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import type {
  ActionType,
  ActionVO,
  ActionWeightVO,
  CheckinVO,
  StreakVO,
} from "@/types/action-center";

// ----------------------------------------------------------------------
// 元数据
// ----------------------------------------------------------------------
const ACTION_TYPE_META: Record<
  ActionType,
  { label: string; icon: typeof BookOpen; color: string }
> = {
  read_article: { label: "阅读干货", icon: BookOpen, color: "text-blue-500" },
  finish_course: { label: "完成课程", icon: GraduationCap, color: "text-purple-500" },
  resume_revise: { label: "简历修改", icon: FileText, color: "text-amber-500" },
  mock_interview: { label: "模拟面试", icon: MessageSquare, color: "text-green-500" },
  real_apply: { label: "真实投递", icon: Send, color: "text-red-500" },
  get_offer: { label: "拿到 Offer", icon: Trophy, color: "text-brand-500" },
  custom: { label: "自定义行动", icon: Sparkles, color: "text-ink-400" },
};

const ACTION_STATUS_META: Record<
  string,
  { label: string; badge: "slate" | "green" | "amber" | "red" }
> = {
  PENDING: { label: "待完成", badge: "slate" },
  DONE: { label: "已完成", badge: "green" },
  EXPIRED: { label: "已过期", badge: "red" },
  CANCELED: { label: "已取消", badge: "amber" },
};

const STREAK_STATUS_META: Record<
  string,
  { label: string; badge: "slate" | "green" | "red"; desc: string }
> = {
  ACTIVE: { label: "连击中", badge: "green", desc: "坚持就是胜利，保持节奏" },
  BROKEN: { label: "已中断", badge: "red", desc: "从断点重新开始，今天动起来" },
  NEVER: { label: "尚未开始", badge: "slate", desc: "创建今日行动，点燃第一把火" },
};

// ----------------------------------------------------------------------
// 页面
// ----------------------------------------------------------------------
export default function ActionsPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [actions, setActions] = useState<ActionVO[]>([]);
  const [weights, setWeights] = useState<ActionWeightVO[]>([]);
  const [streak, setStreak] = useState<StreakVO | null>(null);
  const [checkinsByAction, setCheckinsByAction] = useState<Record<number, CheckinVO[]>>({});
  const [showCreate, setShowCreate] = useState(false);
  const [checkinTarget, setCheckinTarget] = useState<ActionVO | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [today, weightList, streakVO] = await Promise.all([
        actionsApi.getToday(),
        actionsApi.getWeights(),
        actionsApi.getStreak(),
      ]);
      setActions(today.items);
      setWeights(weightList.items);
      setStreak(streakVO);

      // 并行拉取每个行动的历史打卡（计数展示）
      const records = await Promise.all(
        today.items.map(async (a) => {
          const res = await actionsApi.getCheckins(a.id).catch(() => null);
          return [a.id, res?.items ?? []] as const;
        }),
      );
      setCheckinsByAction(Object.fromEntries(records));
    } catch {
      toast.push("加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreated = useCallback(() => {
    setShowCreate(false);
    toast.success("行动项已创建");
    loadData();
  }, [toast, loadData]);

  const handleCheckin = useCallback(
    async (note?: string) => {
      if (!checkinTarget) return;
      try {
        await actionsApi.checkin(checkinTarget.id, {
          completed_at: new Date().toISOString(),
          note: note?.trim() || null,
        });
        toast.success(`「${checkinTarget.title}」已打卡`);
        setCheckinTarget(null);
        loadData();
      } catch {
        toast.push("打卡失败，请重试", "error");
      }
    },
    [checkinTarget, toast, loadData],
  );

  if (loading) return <LoadingState />;

  const doneCount = actions.filter((a) => a.status === "DONE").length;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* 头部 */}
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <ListChecks className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">行动任务中心</h1>
        <p className="text-sm text-ink-400 mt-2 leading-relaxed">
          把规划拆成今天能做的行动，做完一件事，就点亮一个格子
          <br />
          累计行动 {actions.length} 项 · 已完成 {doneCount} 项
        </p>
      </div>

      {/* 连击卡片 */}
      <StreakCard streak={streak} />

      {/* 今日行动 */}
      <div className="card space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-ink-800">
            今日行动
          </h2>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-3.5 w-3.5" />
            创建行动
          </Button>
        </div>

        {actions.length === 0 ? (
          <EmptyState
            title="今天还没有行动"
            description="创建第一个行动项，按下执行键"
          />
        ) : (
          <ul className="divide-y divide-paper-200">
            {actions.map((a) => (
              <ActionItem
                key={a.id}
                action={a}
                checkinCount={checkinsByAction[a.id]?.length ?? 0}
                onCheckin={() => setCheckinTarget(a)}
              />
            ))}
          </ul>
        )}
      </div>

      {/* 权重说明 */}
      <WeightsCard weights={weights} />

      {/* 创建行动 Modal */}
      <CreateActionModal
        open={showCreate}
        weights={weights}
        onClose={() => setShowCreate(false)}
        onCreated={handleCreated}
      />

      {/* 打卡确认 Modal */}
      <CheckinModal
        action={checkinTarget}
        onClose={() => setCheckinTarget(null)}
        onConfirm={handleCheckin}
      />
    </div>
  );
}

// ----------------------------------------------------------------------
// 连击卡片（/api/actions/streaks）
// ----------------------------------------------------------------------
function StreakCard({ streak }: { streak: StreakVO | null }) {
  if (!streak) return null;
  const meta = STREAK_STATUS_META[streak.streak_status] || STREAK_STATUS_META.NEVER;

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div
          className={cn(
            "flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl text-white shadow-lg transition-all",
            streak.streak_status === "ACTIVE"
              ? "bg-gradient-to-br from-brand-500 to-orange-500 shadow-orange-500/25"
              : "bg-gradient-to-br from-ink-400 to-ink-500 shadow-ink-400/25",
          )}
        >
          <Flame className="h-8 w-8" strokeWidth={2.2} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-4xl font-bold leading-none text-ink-800">
              {streak.current_streak_days}
            </span>
            <span className="text-sm text-ink-500">天连续行动</span>
            <Badge color={meta.badge}>{meta.label}</Badge>
          </div>
          <p className="mt-1.5 text-xs text-ink-500">{meta.desc}</p>
        </div>
        <div className="flex gap-6 sm:gap-8 sm:border-l sm:border-paper-200 sm:pl-6">
          <div>
            <p className="font-display text-xl font-bold leading-none text-ink-800">
              {streak.longest_streak_days}
            </p>
            <p className="mt-1 text-xs text-ink-400">最长连胜 / 天</p>
          </div>
          {streak.last_checkin_date && (
            <div>
              <p className="font-display text-xl font-bold leading-none text-ink-800">
                {streak.last_checkin_date.slice(5)}
              </p>
              <p className="mt-1 text-xs text-ink-400">最近打卡</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 单行动项
// ----------------------------------------------------------------------
function ActionItem({
  action,
  checkinCount,
  onCheckin,
}: {
  action: ActionVO;
  checkinCount: number;
  onCheckin: () => void;
}) {
  const typeMeta = ACTION_TYPE_META[action.action_type] || ACTION_TYPE_META.custom;
  const statusMeta = ACTION_STATUS_META[action.status] || ACTION_STATUS_META.PENDING;
  const TypeIcon = typeMeta.icon;
  const isDone = action.status === "DONE";

  return (
    <li className="flex items-center gap-3 py-3">
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
          isDone ? "bg-brand-100" : "bg-paper-100",
        )}
      >
        <TypeIcon className={cn("h-4 w-4", typeMeta.color)} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-ink-800">{action.title}</span>
          <Badge color={statusMeta.badge}>{statusMeta.label}</Badge>
          {isDone && checkinCount > 0 && (
            <span className="text-xs text-ink-400">打卡 {checkinCount} 次</span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-1 text-xs text-ink-400">
          <span className="flex items-center gap-1">
            <CalendarDays className="h-3 w-3" />
            {fmtDate(action.due_date)}
          </span>
          <span className="flex items-center gap-1">
            <Flame className="h-3 w-3 text-orange-400" />
            权重 {action.weight}
          </span>
          <span className="text-ink-300">{typeMeta.label}</span>
        </div>
      </div>
      {isDone ? (
        <CheckCircle2 className="h-5 w-5 shrink-0 text-brand-500" />
      ) : (
        <Button size="sm" variant="secondary" onClick={onCheckin}>
          <CheckCircle2 className="h-3.5 w-3.5" />
          打卡
        </Button>
      )}
    </li>
  );
}

// ----------------------------------------------------------------------
// 创建行动 Modal
// ----------------------------------------------------------------------
function CreateActionModal({
  open,
  weights,
  onClose,
  onCreated,
}: {
  open: boolean;
  weights: ActionWeightVO[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const toast = useToast();
  const [actionType, setActionType] = useState<ActionType>("read_article");
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const enabledWeights = useMemo(
    () => weights.filter((w) => w.enabled),
    [weights],
  );

  const handleSubmit = async () => {
    if (!title.trim()) {
      toast.push("请填写行动标题", "error");
      return;
    }
    if (!dueDate) {
      toast.push("请选择计划完成日期", "error");
      return;
    }
    setSubmitting(true);
    try {
      await actionsApi.create({
        action_type: actionType,
        title: title.trim(),
        due_date: dueDate,
      });
      onCreated();
    } catch {
      toast.push("创建失败，请重试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="创建行动项">
      <div className="space-y-4">
        <Field label="行动类型" required>
          <Select
            value={actionType}
            onChange={(e) => setActionType(e.target.value as ActionType)}
          >
            {enabledWeights.length > 0 ? (
              enabledWeights.map((w) => (
                <option key={w.id} value={w.action_type}>
                  {ACTION_TYPE_META[w.action_type]?.label || w.weight_label}
                  {w.weight_label ? `（${w.weight_label}）` : ""}
                </option>
              ))
            ) : (
              Object.keys(ACTION_TYPE_META).map((t) => (
                <option key={t} value={t}>
                  {ACTION_TYPE_META[t as ActionType].label}
                </option>
              ))
            )}
          </Select>
        </Field>

        <Field label="行动标题" required>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
            placeholder="如：读完《认知觉醒》第三章并做笔记"
          />
        </Field>

        <Field label="计划完成日期" required>
          <Input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </Field>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button onClick={handleSubmit} loading={submitting}>
            <Plus className="h-4 w-4" />
            创建
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ----------------------------------------------------------------------
// 打卡确认 Modal
// ----------------------------------------------------------------------
function CheckinModal({
  action,
  onClose,
  onConfirm,
}: {
  action: ActionVO | null;
  onClose: () => void;
  onConfirm: (note?: string) => void;
}) {
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!action) setNote("");
  }, [action]);

  return (
    <Modal
      open={!!action}
      onClose={onClose}
      title="确认打卡"
    >
      {action && (
        <div className="space-y-4">
          <div>
            <p className="text-sm text-ink-600">
              「<span className="font-medium text-ink-800">{action.title}</span>」
            </p>
            <p className="text-xs text-ink-400 mt-1">
              打卡后将计入今日行动进度，并写入成长轨迹
            </p>
          </div>
          <Field label="打卡备注（可选）">
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              placeholder="写下完成情况或证据链接…"
            />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={onClose}>
              取消
            </Button>
            <Button onClick={() => onConfirm(note)}>
              <CheckCircle2 className="h-4 w-4" />
              确认打卡
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

// ----------------------------------------------------------------------
// 权重说明
// ----------------------------------------------------------------------
function WeightsCard({ weights }: { weights: ActionWeightVO[] }) {
  return (
    <div className="card space-y-3">
      <h2 className="font-display text-lg font-semibold text-ink-800">
        行动权重说明
      </h2>
      <p className="text-xs text-ink-400 leading-relaxed">
        不同行动对职业推进的贡献不同，权重越高价值越大；今日行动按权重降序展示。
      </p>
      <div className="grid grid-cols-2 gap-2">
        {weights.map((w) => (
          <div
            key={w.id}
            className="flex items-center justify-between rounded-lg border border-paper-200 px-3 py-2"
          >
            <span className="text-xs text-ink-600">
              {ACTION_TYPE_META[w.action_type]?.label || w.weight_label}
            </span>
            <span className="text-xs font-semibold text-brand-600">
              {w.weight} 分
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 辅助函数
// ----------------------------------------------------------------------
function fmtDate(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${Number(m)}月${Number(d)}日`;
}
