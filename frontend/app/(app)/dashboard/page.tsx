"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Compass,
  History as TimelineIcon,
  Network,
  ClipboardList,
  Plus,
  ArrowRight,
  MapPin,
  Bot,
  Flame,
  Sparkles,
  Lightbulb,
  Bell,
  AlertTriangle,
  PartyPopper,
  Search,
} from "lucide-react";
import {
  proactiveInsightsApi,
  decisionPulseApi,
  useApi,
} from "@/lib/api";
import { formatDate, cn } from "@/lib/utils";
import {
  DESTINATION_TYPE_LABEL,
  EVENT_TYPE_LABEL,
} from "@/lib/constants";
import { StatCard } from "@/components/stat-card";
import { SkillRadar } from "@/components/charts";
import { LevelProgress } from "@/components/gamification/level-progress";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { Skeleton } from "@/components/ui/skeleton";
import {
  PulseOverviewSection,
  ActiveDecisionsSection,
  ReviewQueueSection,
  DarkKnowledgeFeedSection,
  MemoryFactsSection,
} from "@/components/decision-copilot";
import type {
  DashboardOverview,
  GamificationProfile,
  ReminderItem,
  DailyFocusItem,
  WeeklyRecap,
  StreakStats,
  ProactiveInsight,
  ProactiveInsightSummary,
  LifeWheelSnapshot,
  PulseOverview,
  PulseActiveDecision,
  PulseReviewItem,
  PulseDarkKnowledgeItem,
  PulseMemoryFact,
  PulseFull,
} from "@/types";
import { AlertCircle, Clock, Target, Zap, CalendarCheck, TrendingUp } from "lucide-react";
import { useToast } from "@/components/ui/toast";

/** Dashboard骨架屏 — 结构化占位，替代空白spinner */
function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="flex items-center justify-between">
        <div><Skeleton className="h-8 w-32 mb-2" /><Skeleton className="h-4 w-48" /></div>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => (
          <div key={`skel-${i}`} className="card p-5">
            <Skeleton className="h-10 w-10 rounded-lg mb-3" />
            <Skeleton className="h-4 w-16 mb-1" />
            <Skeleton className="h-6 w-12" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const toast = useToast();
  const [generating, setGenerating] = useState(false);

  // 第一批：核心数据（overview + streak + reminders + focus + pulse）— SWR 并行获取
  const { data, error: overviewError, isLoading: overviewLoading } = useApi<DashboardOverview>("/api/dashboard/overview");
  const { data: streakData, error: streakError, isLoading: streakLoading } = useApi<StreakStats>("/api/streaks/stats");
  const { data: remindersData, error: remindersError, isLoading: remindersLoading } = useApi<ReminderItem[]>("/api/career-plans/reminders");
  const { data: focusData, error: focusError, isLoading: focusLoading } = useApi<DailyFocusItem[]>("/api/career-plans/daily-focus");
  const { data: pulseData, error: pulseError, isLoading: pulseLoading, mutate: mutatePulse } = useApi<PulseFull>("/api/decision-pulse");

  const coreLoading = overviewLoading || streakLoading || remindersLoading || focusLoading || pulseLoading;

  // 数组兜底，避免 undefined 导致渲染崩溃
  const streakStats = streakData ?? null;
  const reminders = remindersData ?? [];
  const dailyFocus = focusData ?? [];

  // 决策副驾驶看板数据（护城河）— 从 pulseData 派生
  const pulseOverview = pulseData?.overview ?? null;
  const pulseActiveDecisions = pulseData?.active_decisions ?? [];
  const pulseReviewQueue = pulseData?.review_queue ?? [];
  const pulseDarkFeed = pulseData?.dark_knowledge_feed ?? [];
  const pulseMemory = pulseData?.memory_facts ?? [];

  // 第二批：次要数据 — 等核心数据就绪后再触发（保持两批加载语义）
  const batch1Ready = !coreLoading;
  const { data: gameProfile } = useApi<GamificationProfile>(batch1Ready ? "/api/gamification/profile" : null);
  const { data: insightsSummary, mutate: mutateInsights } = useApi<ProactiveInsightSummary>(batch1Ready ? "/api/proactive-insights/summary" : null);
  const { data: lifeWheel } = useApi<LifeWheelSnapshot | null>(batch1Ready ? "/api/life-wheel/latest" : null);
  const { data: weeklyRecap } = useApi<WeeklyRecap>(batch1Ready ? "/api/dashboard/weekly-recap" : null);
  const { data: personalIntel } = useApi<any>(batch1Ready ? "/api/dashboard/personal-intel" : null);

  // 错误提示（核心接口失败时提示用户）
  useEffect(() => {
    if (overviewError) toast.push(overviewError.message || "加载看板失败", "error");
  }, [overviewError, toast]);
  useEffect(() => {
    if (pulseError) toast.push(pulseError.message || "加载决策副驾驶数据失败", "error");
  }, [pulseError, toast]);

  // 刷新 AI 记忆面板
  const refreshMemory = async () => {
    try {
      const res = await decisionPulseApi.getMemoryFacts(20);
      mutatePulse(
        (prev) => (prev ? { ...prev, memory_facts: res.items } : prev),
        { revalidate: false },
      );
    } catch {
      // 静默
    }
  };

  // 刷新暗知识流（乐观更新本地缓存）
  const refreshDarkFeed = (pushId: string) => {
    mutatePulse(
      (prev) => prev ? {
        ...prev,
        dark_knowledge_feed: prev.dark_knowledge_feed.map((it) =>
          it.push_id === pushId ? { ...it, is_read: true, read_at: new Date().toISOString() } : it,
        ),
        overview: prev.overview ? { ...prev.overview, unread_pushes: Math.max(0, prev.overview.unread_pushes - 1) } : prev.overview,
      } : prev,
      { revalidate: false },
    );
  };

  if (coreLoading) return <DashboardSkeleton />;
  if (!data) return null;

  const isEmpty =
    data.decisions_count === 0 &&
    data.events_count === 0 &&
    data.skills_count === 0 &&
    data.retrospectives_count === 0;

  const radarData = Object.entries(data.skill_categories).map(
    ([category, count]) => ({ category, count }),
  );

  const insights = insightsSummary?.latest_insights ?? [];
  const unreadInsightCount =
    insightsSummary?.unread_count ??
    insights.filter((i) => !i.is_read).length;

  // 点击洞察卡片标记为已读（乐观更新，失败静默回滚）
  const handleMarkAsRead = async (id: string) => {
    mutateInsights(
      (prev) => prev ? {
        ...prev,
        unread_count: Math.max(0, prev.unread_count - 1),
        latest_insights: prev.latest_insights.map((i) => (i.id === id ? { ...i, is_read: true } : i)),
      } : prev,
      { revalidate: false },
    );
    try {
      await proactiveInsightsApi.markAsRead(id);
    } catch {
      // 静默失败：重新拉取最新状态
      mutateInsights();
    }
  };

  // 生成 AI 洞察并刷新列表
  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await proactiveInsightsApi.generate();
      await mutateInsights();
    } catch {
      // 静默失败
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">个人看板</h1>
          <p className="text-sm text-ink-400 mt-1.5">
            一览你的职业轨迹全貌
          </p>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="去向决策"
          value={data.decisions_count}
          icon={<Compass className="h-6 w-6" />}
          color="blue"
          hint={data.latest_decision ? DESTINATION_TYPE_LABEL[data.latest_decision.destination_type as keyof typeof DESTINATION_TYPE_LABEL] ?? data.latest_decision.destination_type : "暂无"}
        />
        <StatCard
          label="成长事件"
          value={data.events_count}
          icon={<TimelineIcon className="h-6 w-6" />}
          color="green"
          hint={data.recent_events[0]?.title ?? "暂无"}
        />
        <StatCard
          label="技能节点"
          value={data.skills_count}
          icon={<Network className="h-6 w-6" />}
          color="amber"
          hint={`${Object.keys(data.skill_categories).length} 个分类`}
        />
        <StatCard
          label="阶段复盘"
          value={data.retrospectives_count}
          icon={<ClipboardList className="h-6 w-6" />}
          color="purple"
          hint={data.latest_retrospective?.title ?? "暂无"}
        />
      </div>

      {/* 决策副驾驶护城河看板 */}
      <PulseOverviewSection overview={pulseOverview} loading={pulseLoading} />

      {/* 决策副驾驶：四象限 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ActiveDecisionsSection items={pulseActiveDecisions} loading={pulseLoading} />
        <ReviewQueueSection items={pulseReviewQueue} loading={pulseLoading} />
        <DarkKnowledgeFeedSection
          items={pulseDarkFeed}
          loading={pulseLoading}
          onMarkRead={refreshDarkFeed}
        />
        <MemoryFactsSection
          items={pulseMemory}
          loading={pulseLoading}
          onRefresh={refreshMemory}
        />
      </div>

      {/* 个人情报总览（护城河：跨库聚合） */}
      {personalIntel && (
        <section className="card p-5 animate-fade-in">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-ink-800">
              <Sparkles className="h-5 w-5 text-brand-500" />
              个人情报总览
            </h2>
            <span className="text-xs text-ink-400">
              档案完整度 {personalIntel.profile_completeness}%
            </span>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            {/* 三大方向进度 */}
            <div>
              <p className="mb-2 text-sm font-medium text-ink-600">三大方向进度</p>
              <div className="space-y-2">
                {personalIntel.directions?.map((d: any) => (
                  <div key={d.name}>
                    <div className="flex justify-between text-xs text-ink-500">
                      <span>{d.name}</span>
                      <span>{d.progress}%</span>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-paper-200">
                      <div
                        className="h-2 rounded-full bg-brand-500"
                        style={{ width: `${d.progress}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 竞争力雷达（简易条） */}
            <div>
              <p className="mb-2 text-sm font-medium text-ink-600">竞争力雷达</p>
              <div className="space-y-2">
                {personalIntel.competitiveness_radar?.map((r: any) => (
                  <div key={r.axis}>
                    <div className="flex justify-between text-xs text-ink-500">
                      <span>{r.axis}</span>
                      <span>{r.value}</span>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-paper-200">
                      <div
                        className="h-2 rounded-full bg-emerald-500"
                        style={{ width: `${r.value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 待办风险 */}
            <div>
              <p className="mb-2 flex items-center gap-1 text-sm font-medium text-ink-600">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                待办风险
              </p>
              {personalIntel.risks?.length > 0 ? (
                <ul className="space-y-1.5 text-sm text-ink-600">
                  {personalIntel.risks.map((risk: string, i: number) => (
                    <li key={`${risk}-${i}`} className="flex gap-1.5">
                      <span className="text-amber-500">•</span>
                      <span>{risk}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-emerald-600">暂无显著风险，保持节奏 🎉</p>
              )}
              {personalIntel.profile_gaps?.length > 0 && (
                <p className="mt-2 text-xs text-ink-400">
                  待补全档案：{personalIntel.profile_gaps.join("、")}
                </p>
              )}
            </div>
          </div>
        </section>
      )}

      {/* 连续打卡 */}
      {streakStats && (
        <div className="card overflow-hidden animate-fade-in">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-orange-500 text-white shadow-lg shadow-orange-500/25">
              <Flame className="h-8 w-8" strokeWidth={2.2} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2">
                <span className="font-display text-4xl font-bold leading-none text-ink-800">
                  {streakStats.current_streak}
                </span>
                <span className="text-sm text-ink-500">天连续打卡</span>
              </div>
              {streakStats.today_active ? (
                <p className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-brand-600">
                  <Flame className="h-3 w-3" /> 今日已打卡，连胜延续中
                </p>
              ) : (
                <p className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-amber-600">
                  <Flame className="h-3 w-3" /> 今天还没打卡，别让连胜中断
                </p>
              )}
            </div>
            <div className="flex gap-6 sm:gap-8 sm:border-l sm:border-paper-200 sm:pl-6">
              <div>
                <p className="font-display text-xl font-bold leading-none text-ink-800">
                  {streakStats.longest_streak}
                </p>
                <p className="mt-1 text-xs text-ink-400">最长连胜 / 天</p>
              </div>
              <div>
                <p className="font-display text-xl font-bold leading-none text-ink-800">
                  {streakStats.total_active_days}
                </p>
                <p className="mt-1 text-xs text-ink-400">累计活跃 / 天</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI 主动洞察 */}
      <div className="space-y-3 animate-fade-in">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <Sparkles className="h-4 w-4" />
          </div>
          <h2 className="font-display font-semibold text-ink-800">AI 洞察</h2>
          {unreadInsightCount > 0 && (
            <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-600">
              {unreadInsightCount} 条未读
            </span>
          )}
        </div>
        {insights.length > 0 ? (
          <div className="space-y-2">
            {insights.slice(0, 3).map((insight) => (
              <InsightCard
                key={insight.id}
                insight={insight}
                onRead={handleMarkAsRead}
              />
            ))}
          </div>
        ) : (
          <div className="card flex flex-col items-center gap-3 py-8 text-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="font-display text-sm font-medium text-ink-700">
                暂无洞察
              </p>
              <p className="mt-0.5 text-xs text-ink-400">
                让 AI 根据你的数据生成个性化洞察与建议
              </p>
            </div>
            <Button onClick={handleGenerate} loading={generating}>
              {!generating && <Sparkles className="h-4 w-4" />}
              {generating ? "生成中…" : "生成洞察"}
            </Button>
          </div>
        )}
      </div>

      {/* 成长进度预览 */}
      {gameProfile && (
        <div className="card flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <LevelProgress
            xp={gameProfile.xp}
            level={gameProfile.level}
            levelName={gameProfile.level_name}
            progress={gameProfile.progress}
            compact
          />
          <Link
            href="/achievements"
            className="inline-flex items-center gap-1.5 rounded-lg border border-paper-300 bg-white px-4 py-2 text-sm font-medium text-ink-700 transition-all hover:bg-paper-100 hover:border-ink-200"
          >
            查看成就 <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}

      {isEmpty && (
        <EmptyState
          title="欢迎来到 GradPath"
          description="开始记录你的第一条职业轨迹吧。建议从「去向决策」开始，记录你的毕业方向选择。"
          action={
            <Link href="/decisions">
              <Button>
                <Plus className="h-4 w-4" /> 创建第一条决策
              </Button>
            </Link>
          }
        />
      )}

      {/* AI 职业管家入口 */}
      <Link
        href="/chat"
        className="flex items-center gap-4 rounded-xl border border-brand-200 bg-gradient-to-r from-brand-50 to-paper-50 p-4 transition-all hover:shadow-card-hover hover:border-brand-300"
      >
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white shadow-brand-sm">
          <Bot className="h-6 w-6" strokeWidth={2} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-display font-semibold text-ink-800">与 AI 职业管家对话</p>
          <p className="text-sm text-ink-400">
            个性化职业规划、简历诊断、面试模拟 — 基于你的数据智能匹配
          </p>
        </div>
        <ArrowRight className="h-5 w-5 shrink-0 text-brand-400" />
      </Link>

      {/* 每日重点 + 周回顾 双栏 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 每日重点 */}
        {dailyFocus.length > 0 && (
          <div className="card space-y-3 animate-fade-in">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-brand-600" />
              <h2 className="font-display font-semibold text-ink-800">今日重点</h2>
            </div>
            <div className="space-y-2">
              {dailyFocus.map((item, i) => (
                <Link
                  key={`${item.plan_id}-${item.milestone_index}`}
                  href="/plans"
                  className="flex items-start gap-3 rounded-lg border border-paper-200 bg-paper-50/50 px-3 py-2.5 transition-colors hover:border-brand-300 hover:bg-brand-50/30"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-600">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-ink-700 truncate">
                      {item.milestone_title}
                    </p>
                    <p className="text-xs text-ink-400 truncate">{item.plan_goal}</p>
                  </div>
                  {item.status === "in_progress" ? (
                    <span className="shrink-0 rounded-full bg-brand-100 px-2 py-0.5 text-[10px] font-medium text-brand-600">
                      进行中
                    </span>
                  ) : (
                    <span className="shrink-0 rounded-full bg-paper-200 px-2 py-0.5 text-[10px] font-medium text-ink-400">
                      待开始
                    </span>
                  )}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* 周回顾 */}
        {weeklyRecap && (
          <div className="card space-y-3 animate-fade-in">
            <div className="flex items-center gap-2">
              <CalendarCheck className="h-4 w-4 text-brand-600" />
              <h2 className="font-display font-semibold text-ink-800">本周回顾</h2>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              <RecapStat value={weeklyRecap.logs_this_week} label="执行记录" />
              <RecapStat value={weeklyRecap.completed_this_week} label="完成里程碑" />
              <RecapStat value={weeklyRecap.active_plans} label="进行中规划" />
            </div>
            <div className="rounded-lg bg-brand-50/40 px-3 py-2.5">
              <p className="flex items-center gap-1.5 text-xs text-brand-700">
                <TrendingUp className="h-3.5 w-3.5" />
                {weeklyRecap.encouragement}
              </p>
            </div>
            {weeklyRecap.total_milestones > 0 && (
              <div>
                <div className="flex items-center justify-between mb-1 text-xs text-ink-400">
                  <span>总体进度</span>
                  <span>{weeklyRecap.total_milestones_done}/{weeklyRecap.total_milestones}</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-paper-200">
                  <div
                    className="h-full rounded-full bg-brand-500 transition-all duration-500"
                    style={{
                      width: `${weeklyRecap.total_milestones > 0
                        ? Math.round((weeklyRecap.total_milestones_done / weeklyRecap.total_milestones) * 100)
                        : 0}%`,
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 人生平衡轮迷你概览 */}
      {lifeWheel && (
        <div className="card space-y-3 animate-fade-in">
          <div className="flex items-center justify-between">
            <h2 className="font-display font-semibold text-ink-800">
              人生平衡轮
            </h2>
            <Link
              href="/life-wheel"
              className="inline-flex items-center text-sm text-brand-600 transition-colors hover:text-brand-700"
            >
              完整评估 <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="flex shrink-0 flex-col items-center justify-center rounded-xl bg-brand-50 px-6 py-3">
              <p className="font-display text-3xl font-bold leading-none text-brand-700">
                {lifeWheel.overall_score.toFixed(1)}
              </p>
              <p className="mt-1 text-xs text-ink-400">综合得分</p>
            </div>
            <div className="grid flex-1 grid-cols-1 gap-x-6 gap-y-2.5 sm:grid-cols-2">
              {Object.entries(lifeWheel.scores).map(([key, score]) => (
                <div key={key}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-ink-500">{prettifyKey(key)}</span>
                    <span className="text-ink-400">{score}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-paper-200">
                    <div
                      className="h-full rounded-full bg-brand-500 transition-all duration-500"
                      style={{
                        width: `${Math.min(100, Math.round((score / 10) * 100))}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 规划提醒 */}
      {reminders.length > 0 && (
        <div className="card space-y-3 animate-fade-in">
          <div className="flex items-center justify-between">
            <h2 className="font-display font-semibold text-ink-800 flex items-center gap-2">
              <Target className="h-4 w-4 text-brand-600" />
              规划提醒
            </h2>
            <Link
              href="/plans"
              className="text-sm text-brand-600 hover:text-brand-700 transition-colors inline-flex items-center"
            >
              查看全部 <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="space-y-2">
            {reminders.slice(0, 5).map((r, i) => (
              <Link
                key={`${r.plan_id}-${r.milestone_index}-${i}`}
                href="/plans"
                className={cn(
                  "flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors hover:shadow-card",
                  r.type === "overdue"
                    ? "border-red-200 bg-red-50/30 hover:bg-red-50/50"
                    : "border-amber-200 bg-amber-50/30 hover:bg-amber-50/50",
                )}
              >
                <div
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                    r.type === "overdue"
                      ? "bg-red-100 text-red-600"
                      : "bg-amber-100 text-amber-600",
                  )}
                >
                  {r.type === "overdue" ? (
                    <AlertCircle className="h-4 w-4" />
                  ) : (
                    <Clock className="h-4 w-4" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-ink-700 truncate">
                    {r.milestone_title}
                  </p>
                  <p className="text-xs text-ink-400 truncate">{r.plan_goal}</p>
                </div>
                <span
                  className={cn(
                    "shrink-0 text-xs font-medium",
                    r.type === "overdue" ? "text-red-600" : "text-amber-600",
                  )}
                >
                  {r.type === "overdue"
                    ? `逾期 ${r.days_remaining ?? 0} 天`
                    : `${r.days_remaining} 天后到期`}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 职业旅程时间线 */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold text-ink-800">职业旅程时间线</h2>
            <Link
              href="/timeline"
              className="text-sm text-brand-600 hover:underline inline-flex items-center"
            >
              查看全部 <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          {data.timeline.length === 0 ? (
            <EmptyState title="暂无时间线数据" description="创建决策或事件后将出现在这里" />
          ) : (
            <TimelineList items={data.timeline.slice(0, 10)} />
          )}
        </div>

        {/* 技能分类雷达图 */}
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-display font-semibold text-ink-800">技能分类分布</h2>
            <Link
              href="/skills"
              className="text-sm text-brand-600 hover:underline"
            >
              管理
            </Link>
          </div>
          {radarData.length === 0 ? (
            <EmptyState title="暂无技能" description="在技能树页面添加你的技能" />
          ) : (
            <SkillRadar data={radarData} />
          )}
        </div>
      </div>

      {/* 最近事件 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display font-semibold text-ink-800">最近事件</h2>
          <Link
            href="/timeline"
            className="text-sm text-brand-600 hover:underline inline-flex items-center"
          >
            查看全部 <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        {data.recent_events.length === 0 ? (
          <EmptyState title="暂无事件" description="记录入职、晋升、项目等职业事件" />
        ) : (
          <ul className="divide-y divide-paper-100">
            {data.recent_events.map((e) => (
              <li key={e.id} className="flex items-center gap-3 py-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  <TimelineIcon className="h-4 w-4" />
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-ink-800 truncate">
                    {e.title}
                  </p>
                  <p className="text-xs text-ink-400">
                    {EVENT_TYPE_LABEL[e.event_type as keyof typeof EVENT_TYPE_LABEL] ?? e.event_type}
                    {" · "}
                    {formatDate(e.event_date)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function RecapStat({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-lg bg-paper-50 px-2 py-2.5">
      <p className="font-display text-xl font-bold text-brand-700">{value}</p>
      <p className="text-[10px] text-ink-400">{label}</p>
    </div>
  );
}

function TimelineList({
  items,
}: {
  items: DashboardOverview["timeline"];
}) {
  return (
    <ol className="relative space-y-4 before:absolute before:left-[7px] before:top-2 before:bottom-2 before:w-px before:bg-paper-300">
      {items.map((item) => {
        const isDecision = item.type === "decision";
        return (
          <li key={`${item.type}-${item.id}`} className="relative pl-7">
            <span
              className={cn(
                "absolute left-0 top-1.5 flex h-[15px] w-[15px] items-center justify-center rounded-full ring-4 ring-white",
                isDecision ? "bg-brand-500" : "bg-brand-300",
              )}
            />
            <div className="flex items-baseline justify-between gap-2">
              <p className="text-sm font-medium text-ink-800">
                {isDecision
                  ? `去向决策: ${DESTINATION_TYPE_LABEL[item.title.replace("去向决策: ", "") as keyof typeof DESTINATION_TYPE_LABEL] ?? item.title.replace("去向决策: ", "")}`
                  : item.title}
                {item.subtitle && (
                  <span className="ml-2 text-ink-400 font-normal">
                    {isDecision
                      ? item.subtitle
                      : EVENT_TYPE_LABEL[item.subtitle as keyof typeof EVENT_TYPE_LABEL] ?? item.subtitle}
                  </span>
                )}
              </p>
              <span className="text-xs text-ink-400 whitespace-nowrap">
                {formatDate(item.date)}
              </span>
            </div>
            <p className="text-xs text-ink-400 mt-0.5 flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {isDecision ? "去向决策" : "成长事件"}
            </p>
          </li>
        );
      })}
    </ol>
  );
}

// ===== AI 主动洞察：辅助函数 =====

/** 洞察类型对应图标 */
function getInsightIcon(type: ProactiveInsight["insight_type"]) {
  switch (type) {
    case "pattern":
      return <Search className="h-4 w-4" />;
    case "reminder":
      return <Bell className="h-4 w-4" />;
    case "celebration":
      return <PartyPopper className="h-4 w-4" />;
    case "warning":
      return <AlertTriangle className="h-4 w-4" />;
    case "suggestion":
      return <Lightbulb className="h-4 w-4" />;
    default:
      return <Sparkles className="h-4 w-4" />;
  }
}

/** 洞察类型对应的图标背景配色 */
function getInsightIconBg(type: ProactiveInsight["insight_type"]) {
  switch (type) {
    case "pattern":
      return "bg-blue-50 text-blue-600";
    case "reminder":
      return "bg-amber-50 text-amber-600";
    case "celebration":
      return "bg-green-50 text-green-600";
    case "warning":
      return "bg-red-50 text-red-600";
    case "suggestion":
      return "bg-brand-50 text-brand-600";
    default:
      return "bg-paper-100 text-ink-500";
  }
}

/** 优先级对应的左侧色条：5=红 4=琥珀 3=品牌 2=蓝 1=灰 */
function getPriorityBorder(priority: number) {
  switch (priority) {
    case 5:
      return "border-l-red-500";
    case 4:
      return "border-l-amber-500";
    case 3:
      return "border-l-brand-500";
    case 2:
      return "border-l-blue-500";
    default:
      return "border-l-ink-300";
  }
}

/** 将维度 key 转为可读名称（如 career_health -> Career Health） */
function prettifyKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** 单条 AI 洞察卡片：点击标记已读，未读有品牌色底，按优先级显示左色条 */
function InsightCard({
  insight,
  onRead,
}: {
  insight: ProactiveInsight;
  onRead: (id: string) => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => !insight.is_read && onRead(insight.id)}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !insight.is_read) {
          e.preventDefault();
          onRead(insight.id);
        }
      }}
      className={cn(
        "group cursor-pointer rounded-xl border border-l-4 border-paper-200 px-4 py-3 transition-all hover:border-paper-300 hover:shadow-card-hover",
        getPriorityBorder(insight.priority),
        insight.is_read ? "bg-white" : "bg-brand-50/60",
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
            getInsightIconBg(insight.insight_type),
          )}
        >
          {getInsightIcon(insight.insight_type)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-ink-800">
              {insight.title}
            </p>
            {!insight.is_read && (
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
            )}
          </div>
          <p className="mt-0.5 text-xs leading-relaxed text-ink-500">
            {insight.content}
          </p>
          {insight.action_suggestion && (
            <p className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-brand-600 group-hover:underline">
              {insight.action_suggestion}
              <ArrowRight className="h-3 w-3" />
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
