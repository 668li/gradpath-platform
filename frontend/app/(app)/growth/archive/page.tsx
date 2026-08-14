"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  TrendingUp,
  Flame,
  Trophy,
  Target,
  GitBranch,
  Circle,
  Clock,
  RotateCcw,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  NotebookPen,
  RefreshCw,
  ListChecks,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi, growthApi } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge, Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type {
  GrowthArchiveVO,
  GrowthStatsVO,
  GrowthTrajectoryVO,
} from "@/types/growth-center";
import type {
  GamificationProfile,
  StreakStats,
  GrowthPatternResponse,
} from "@/types";

// 成长快照历史项（/api/growth-patterns/history → { items: [...] }）
interface GrowthSnapshotItem {
  id: string;
  period: string;
  growth_score: number;
  pattern_count: number;
  created_at: string | null;
}

export default function GrowthArchivePage() {
  const { data: gamification, isLoading: gLoading } = useApi<GamificationProfile>("/api/gamification/profile");
  const { data: streaks, isLoading: sLoading } = useApi<StreakStats>("/api/streaks/stats");
  const { data: growth, isLoading: grLoading } = useApi<GrowthPatternResponse>("/api/growth-patterns/analyze");
  const { data: history, isLoading: hLoading } = useApi<{ items: GrowthSnapshotItem[] }>("/api/growth-patterns/history");

  const isLoading = gLoading || sLoading || grLoading;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/15 text-brand-500">
          <TrendingUp className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-800">
            成长档案
          </h1>
          <p className="text-sm text-ink-500">
            聚合你的成长数据，见证每一次进步
          </p>
        </div>
      </header>

      {/* 三中心档案（v1 契约：行动任务中心 → 成长档案中心） */}
      <ThreeCenterArchiveSection />

      {/* 核心数据卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 text-center">
          <Target className="mx-auto h-5 w-5 text-brand-500 mb-2" />
          <p className="font-display text-2xl font-bold text-ink-800">
            {gamification?.level ?? 1}
          </p>
          <p className="text-xs text-ink-400">等级</p>
        </div>
        <div className="card p-4 text-center">
          <Flame className="mx-auto h-5 w-5 text-orange-500 mb-2" />
          <p className="font-display text-2xl font-bold text-ink-800">
            {streaks?.current_streak ?? 0}
          </p>
          <p className="text-xs text-ink-400">连续行动 / 天</p>
        </div>
        <div className="card p-4 text-center">
          <Trophy className="mx-auto h-5 w-5 text-amber-500 mb-2" />
          <p className="font-display text-2xl font-bold text-ink-800">
            {gamification?.earned_badges?.length ?? 0}
          </p>
          <p className="text-xs text-ink-400">已解锁徽章</p>
        </div>
        <div className="card p-4 text-center">
          <Sparkles className="mx-auto h-5 w-5 text-purple-500 mb-2" />
          <p className="font-display text-2xl font-bold text-ink-800">
            {gamification?.xp ?? 0}
          </p>
          <p className="text-xs text-ink-400">总XP</p>
        </div>
      </div>

      {/* 连胜里程碑 */}
      {streaks?.milestones && (
        <div className="card">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink-700 flex items-center gap-2">
            <Flame className="h-4 w-4 text-orange-500" />
            连胜里程碑
          </h2>
          <div className="flex items-center gap-1 overflow-x-auto pb-1">
            {streaks.milestones.map((m, i) => (
              <div
                key={m.days}
                className={cn(
                  "flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-all",
                  m.unlocked
                    ? "bg-brand-50 text-brand-700 border border-brand-200"
                    : "bg-paper-100 text-ink-400 border border-paper-200"
                )}
              >
                {m.unlocked ? (
                  <Trophy className="h-3 w-3 text-brand-500" />
                ) : (
                  <span className="h-3 w-3 rounded-full border border-paper-300" />
                )}
                <span>{m.days}d</span>
                {m.unlocked && <span>{m.name}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 成长分数趋势 */}
      {history?.items && history.items.length > 0 && (
        <div className="card">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink-700 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-brand-500" />
            成长分数趋势
          </h2>
          <div className="flex items-end gap-2 h-32">
            {history.items.map((snap, i) => {
              const maxScore = Math.max(...history.items.map((s) => s.growth_score ?? 0), 1);
              const height = ((snap.growth_score ?? 0) / maxScore) * 100;
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-xs font-medium text-ink-700">
                    {snap.growth_score ?? 0}
                  </span>
                  <div
                    className="w-full rounded-t bg-gradient-to-t from-brand-400 to-brand-300 transition-all"
                    style={{ height: `${height}%` }}
                  />
                  <span className="text-[10px] text-ink-400">
                    {snap.period?.slice(0, 7) ?? ""}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 已解锁徽章 */}
      {(gamification?.earned_badges?.length ?? 0) > 0 && (
        <div className="card">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink-700 flex items-center gap-2">
            <Trophy className="h-4 w-4 text-amber-500" />
            已解锁徽章
          </h2>
          <div className="flex flex-wrap gap-2">
            {gamification?.earned_badges.map((b, i) => (
              <Badge key={i} color="amber">
                {b.icon ?? "🏅"} {b.name ?? b}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* 快捷入口 */}
      <div className="grid gap-4 md:grid-cols-2">
        <Link
          href="/dashboard"
          className="card p-4 hover:shadow-md transition-shadow flex items-center gap-3"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-100 text-blue-500">
            <Target className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-ink-700">个人看板</p>
            <p className="text-xs text-ink-400">总览成长数据与目标进度</p>
          </div>
          <ArrowRight className="h-4 w-4 text-ink-300 shrink-0" />
        </Link>
        <Link
          href="/retrospectives/weekly"
          className="card p-4 hover:shadow-md transition-shadow flex items-center gap-3"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-purple-100 text-purple-500">
            <RotateCcw className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-ink-700">周报草稿</p>
            <p className="text-xs text-ink-400">AI自动生成的每周复盘</p>
          </div>
          <ArrowRight className="h-4 w-4 text-ink-300 shrink-0" />
        </Link>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 三中心档案区块（/api/growth：stats + archive + trajectory）
// ----------------------------------------------------------------------
const TRAJECTORY_TYPE_META: Record<
  string,
  { label: string; icon: typeof CheckCircle2; color: string; bg: string }
> = {
  action_checkin: {
    label: "行动打卡",
    icon: CheckCircle2,
    color: "text-green-500",
    bg: "bg-green-100",
  },
  review_completed: {
    label: "复盘完成",
    icon: NotebookPen,
    color: "text-purple-500",
    bg: "bg-purple-100",
  },
  milestone: {
    label: "里程碑",
    icon: Trophy,
    color: "text-amber-500",
    bg: "bg-amber-100",
  },
};

function ThreeCenterArchiveSection() {
  const toast = useToast();
  const [stats, setStats] = useState<GrowthStatsVO | null>(null);
  const [archive, setArchive] = useState<GrowthArchiveVO | null>(null);
  const [trajectory, setTrajectory] = useState<GrowthTrajectoryVO[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [s, a, t] = await Promise.all([
        growthApi.getStats(),
        growthApi.getArchive(),
        growthApi.getTrajectory(),
      ]);
      setStats(s);
      setArchive(a);
      setTrajectory(t.items);
    } catch {
      toast.push("三中心档案加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const [a, s, t] = await Promise.all([
        growthApi.refreshArchive(),
        growthApi.getStats(),
        growthApi.getTrajectory(),
      ]);
      setArchive(a);
      setStats(s);
      setTrajectory(t.items);
      toast.success("档案已刷新");
    } catch {
      toast.push("刷新失败，请重试", "error");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 区块头 + 刷新 */}
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-display text-lg font-semibold text-ink-800">
          <ListChecks className="h-5 w-5 text-brand-500" />
          三中心档案
        </h2>
        <Button size="sm" variant="ghost" onClick={handleRefresh} loading={refreshing}>
          <RefreshCw className="h-3.5 w-3.5" />
          重新聚合
        </Button>
      </div>

      {loading ? (
        <Skeleton className="h-32 rounded-xl" />
      ) : (
        <>
          {/* 实时 stats 卡 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCell
              icon={<Target className="h-5 w-5 text-brand-500" />}
              value={`${Math.round((stats?.action_completion_rate ?? 0) * 100)}%`}
              label="行动完成率"
            />
            <StatCell
              icon={<Flame className="h-5 w-5 text-orange-500" />}
              value={stats?.current_streak_days ?? 0}
              label="当前连击 / 天"
            />
            <StatCell
              icon={<Trophy className="h-5 w-5 text-amber-500" />}
              value={stats?.longest_streak_days ?? 0}
              label="最长连击 / 天"
            />
            <StatCell
              icon={<Sparkles className="h-5 w-5 text-purple-500" />}
              value={archive?.weighted_action_score ?? 0}
              label="加权行动分"
            />
          </div>

          {/* archive 聚合卡 */}
          {archive && (
            <div className="card space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-ink-700">
                  档案聚合
                </h3>
                <div className="flex items-center gap-2">
                  <Badge color={archive.archive_status === "ACTIVE" ? "green" : "amber"}>
                    {archive.archive_status === "ACTIVE" ? "ACTIVE" : "STALE"}
                  </Badge>
                  <span className="text-xs text-ink-400">
                    更新于 {fmtDateTime(archive.updated_at)}
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                <div>
                  <p className="font-display text-xl font-bold text-ink-800">
                    {archive.total_actions}
                  </p>
                  <p className="text-xs text-ink-400">累计行动</p>
                </div>
                <div>
                  <p className="font-display text-xl font-bold text-ink-800">
                    {archive.completed_actions}
                  </p>
                  <p className="text-xs text-ink-400">已完成行动</p>
                </div>
                <div>
                  <p className="font-display text-xl font-bold text-ink-800">
                    {archive.streak_days}
                  </p>
                  <p className="text-xs text-ink-400">Streak Days</p>
                </div>
                <div>
                  <p className="font-display text-xl font-bold text-ink-800">
                    {Math.round((archive.action_completion_rate ?? 0) * 100)}%
                  </p>
                  <p className="text-xs text-ink-400">行动完成率</p>
                </div>
              </div>
            </div>
          )}

          {/* 成长轨迹时间轴 */}
          <div className="card space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-ink-700">
              <GitBranch className="h-4 w-4 text-brand-500" />
              成长轨迹
            </h3>
            {trajectory.length === 0 ? (
              <p className="text-sm text-ink-400">
                还没有轨迹事件 —— 去「行动任务中心」完成一次打卡，这里就会出现记录。
              </p>
            ) : (
              <ul className="space-y-0">
                {trajectory.map((t, i) => (
                  <TrajectoryRow key={t.id} traj={t} isLast={i === trajectory.length - 1} />
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function StatCell({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: React.ReactNode;
  label: string;
}) {
  return (
    <div className="card p-4 text-center">
      <div className="mx-auto mb-2 flex h-9 w-9 items-center justify-center rounded-xl bg-paper-100">
        {icon}
      </div>
      <p className="font-display text-2xl font-bold text-ink-800">{value}</p>
      <p className="text-xs text-ink-400">{label}</p>
    </div>
  );
}

function TrajectoryRow({
  traj,
  isLast,
}: {
  traj: GrowthTrajectoryVO;
  isLast: boolean;
}) {
  const meta = TRAJECTORY_TYPE_META[traj.event_type] || TRAJECTORY_TYPE_META.milestone;
  const payload = traj.event_payload as Record<string, unknown>;
  const TypeIcon = meta.icon;

  const title =
    traj.event_type === "action_checkin"
      ? String(payload.title ?? "行动打卡")
      : traj.event_type === "review_completed"
        ? `${String(payload.review_type ?? "周")}复盘 · ${String(payload.period_start ?? "").slice(5)}`
        : meta.label;

  return (
    <li className="relative flex gap-3 pb-4 last:pb-0">
      {!isLast && (
        <span className="absolute left-[11px] top-7 bottom-0 w-px bg-paper-200" />
      )}
      <span
        className={cn(
          "relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
          meta.bg,
        )}
      >
        <TypeIcon className={cn("h-3.5 w-3.5", meta.color)} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-ink-800">{title}</span>
          <Badge color="slate">{meta.label}</Badge>
        </div>
        <p className="mt-0.5 text-xs text-ink-400">
          {fmtDateTime(traj.occurred_at)}
          {traj.source_event_id && (
            <span className="ml-2 text-ink-300">#{traj.source_event_id.slice(0, 8)}</span>
          )}
        </p>
      </div>
    </li>
  );
}

function fmtDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, "0")}:${String(
    d.getMinutes(),
  ).padStart(2, "0")}`;
}