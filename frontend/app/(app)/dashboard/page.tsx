"use client";

import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  Compass,
  Crosshair,
  History as TimelineIcon,
  Network,
  ClipboardList,
  Plus,
  ArrowRight,
  Bot,
  Flame,
  Sparkles,
  Lightbulb,
  AlertTriangle,
  AlertCircle,
  Clock,
  Target,
  ListChecks,
  TrendingUp,
  Calendar,
} from "lucide-react";
import {
  proactiveInsightsApi,
  useApi,
  darkKnowledgePushApi,
  microActionApi,
} from "@/lib/api";
import { streaksApi } from "@/lib/api/gamification";
import { formatDate, cn } from "@/lib/utils";
import {
  DESTINATION_TYPE_LABEL,
  EVENT_TYPE_LABEL,
} from "@/lib/constants";
import { StatCard } from "@/components/stat-card";
import { EmptyState } from "@/components/ui/empty";
import { Button, Badge } from "@/components/ui/form-controls";
import {
  StreakBar,
  StreakCalendar,
  StreakActions,
} from "@/components/streak";
import {
  PulseOverviewSection,
  ActiveDecisionsSection,
} from "@/components/decision-copilot";
import type {
  DashboardOverview,
  ReminderItem,
  StreakStats,
  ProactiveInsightSummary,
  PulseFull,
  AssessmentResponse,
  CareerPlan,
  WeeklyRecap,
  GamificationProfile,
} from "@/types";
import type { MicroActionPlanResponse } from "@/types/micro-action";
import type { OnboardingStatusResponse } from "@/types/decision-copilot";
import { useToast } from "@/components/ui/toast";
import {
  DashboardSkeleton,
  TimelineList,
  InsightCard,
  CareerGalaxy,
  CareerFitScoreCard,
  calculateCareerFitScore,
  DarkKnowledgeCard,
  MicroActionCard,
  OnboardingQuest,
  NextStepRecommender,
  CollapsibleSection,
  PeerMirrorCard,
  DarkKnowledgeGapCard,
} from "@/components/dashboard";
import type { UserState } from "@/components/dashboard";

// 个人情报总览（/api/dashboard/personal-intel）— 字段与后端 personal_intel_service 返回一致
interface PersonalIntel {
  profile_completeness: number;
  directions: { name: string; progress: number; hint?: string }[];
  competitiveness_radar: { axis: string; value: number }[];
  risks: string[];
  profile_gaps: string[];
}

/** 计算距今多少天（用于"上次更新"显示） */
function daysAgo(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  const diff = Date.now() - d.getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}

export default function DashboardPage() {
  const toast = useToast();
  const [generating, setGenerating] = useState(false);

  // 第一批：核心数据（overview + streak + reminders + pulse）— SWR 并行获取
  const { data, error: overviewError, isLoading: overviewLoading } = useApi<DashboardOverview>("/api/dashboard/overview");
  const { data: streakData, error: streakError, isLoading: streakLoading, mutate: mutateStreak } = useApi<StreakStats>("/api/streaks/stats");
  const { data: remindersData, error: remindersError, isLoading: remindersLoading } = useApi<ReminderItem[]>("/api/career-plans/reminders");
  const { data: pulseData, error: pulseError, isLoading: pulseLoading, mutate: mutatePulse } = useApi<PulseFull>("/api/decision-pulse");

  const coreLoading = overviewLoading || streakLoading || remindersLoading || pulseLoading;

  // 数组兜底，避免 undefined 导致渲染崩溃
  const streakStats = streakData ?? null;
  const reminders = remindersData ?? [];

  // 决策副驾驶看板数据（护城河）— 从 pulseData 派生
  const pulseOverview = pulseData?.overview ?? null;
  const pulseActiveDecisions = pulseData?.active_decisions ?? [];

  // 今日行动 — 纯前端聚合三中心数据，提取今日优先级助推（不新增 API）
  const todayActions = useMemo(() => {
    const actions: Array<{
      key: string;
      title: string;
      href: string;
      source: string;
      badgeColor: "blue" | "purple" | "amber" | "green" | "red";
      duration?: number;
    }> = [];

    const dc = data?.decisions_count ?? 0;
    const rc = data?.retrospectives_count ?? 0;
    const sc = data?.skills_count ?? 0;

    // 新用户引导动作
    if (dc === 0) {
      actions.push({ key: "first-decision", title: "建立你的第一个去向决策", href: "/decisions", source: "决策中心", badgeColor: "blue", duration: 3 });
    }
    if (rc === 0) {
      actions.push({ key: "first-retro", title: "完成第一次阶段复盘", href: "/retrospectives", source: "成长档案", badgeColor: "purple", duration: 5 });
    }
    if (sc === 0) {
      actions.push({ key: "first-wheel", title: "绘制你的人生平衡轮", href: "/life-wheel", source: "成长档案", badgeColor: "amber", duration: 2 });
    }

    // 老用户：决策待回溯项（有 scheduled review_date 的活跃决策）
    if (dc > 0) {
      const pendingReview = pulseActiveDecisions.find((d) => d.review_date);
      if (pendingReview) {
        actions.push({
          key: `review-${pendingReview.id}`,
          title: `回溯你的决策：${pendingReview.destination_type}`,
          href: "/decisions",
          source: "决策中心",
          badgeColor: "blue",
        });
      }
    }

    // 计划提醒动作（取前 2 条）
    reminders.slice(0, 2).forEach((r) => {
      actions.push({
        key: `reminder-${r.plan_id}-${r.milestone_index}`,
        title: r.milestone_title || r.plan_goal,
        href: "/plans",
        source: "提醒",
        badgeColor: r.type === "overdue" ? "red" : "green",
      });
    });

    // 老用户兜底：以上皆空且 reminders 也空 → 通用建议动作
    if (actions.length === 0) {
      actions.push({ key: "suggest-retro", title: "做一次阶段复盘梳理近期进展", href: "/retrospectives", source: "成长档案", badgeColor: "purple", duration: 5 });
    }

    return actions;
  }, [data, reminders, pulseActiveDecisions]);

  // 第二批：次要数据 — 等核心数据就绪后再触发（保持两批加载语义）
  const batch1Ready = !coreLoading;
  const { data: insightsSummary, mutate: mutateInsights } = useApi<ProactiveInsightSummary>(batch1Ready ? "/api/proactive-insights/summary" : null);
  const { data: personalIntel } = useApi<PersonalIntel>(batch1Ready ? "/api/dashboard/personal-intel" : null);
  const { data: weeklyRecap } = useApi<WeeklyRecap>(batch1Ready ? "/api/dashboard/weekly-recap" : null);
  const { data: gamificationProfile } = useApi<GamificationProfile>(batch1Ready ? "/api/gamification/profile" : null);

  // 第三批：星系/活档案/微行动依赖数据 — 复用 batch1Ready 闸门
  const { data: assessmentHistory } = useApi<AssessmentResponse[]>(batch1Ready ? "/api/assessment/history" : null);
  const { data: microPlanData, mutate: mutateMicroPlan } = useApi<MicroActionPlanResponse | null>(batch1Ready ? "/api/micro-actions/plans/current" : null);

  // 新手引导：onboarding 状态 + 职业规划列表（用于 NextStepRecommender）
  const { data: onboardingStatusData } = useApi<OnboardingStatusResponse>(batch1Ready ? "/api/onboarding/status" : null);
  const { data: careerPlansData } = useApi<CareerPlan[]>(batch1Ready ? "/api/career-plans" : null);

  // 模拟器使用记录（localStorage 兜底，无对应历史 API）
  const [hasSimulation, setHasSimulation] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const stored = localStorage.getItem("gradpath_simulated_paths");
      const parsed = stored ? JSON.parse(stored) : [];
      setHasSimulation(Array.isArray(parsed) && parsed.length > 0);
    } catch {
      setHasSimulation(false);
    }
  }, []);

  // Career Fit Score 活档案 — 5 维度聚合计算（必须在条件返回之前调用以保持 hooks 顺序稳定）
  const careerFitScore = useMemo(() => calculateCareerFitScore({
    assessmentCount: assessmentHistory?.length ?? 0,
    skillsCount: data?.skills_count ?? 0,
    decisionsCount: data?.decisions_count ?? 0,
    completedMilestones: weeklyRecap?.total_milestones_done ?? 0,
    retrospectivesCount: data?.retrospectives_count ?? 0,
  }), [assessmentHistory, data?.skills_count, data?.decisions_count, weeklyRecap, data?.retrospectives_count]);

  // "上次更新" — 取最近一次活动日期（必须在条件返回之前调用）
  const lastUpdatedDays = useMemo(() => {
    if (!data) return null;
    const candidates = [
      data.latest_retrospective?.period_end,
      data.recent_events[0]?.event_date,
      data.latest_decision?.decision_date,
      microPlanData?.started_at,
    ].filter(Boolean) as string[];
    if (candidates.length === 0) return null;
    const days = candidates.map(daysAgo).filter((d): d is number => d !== null);
    return days.length > 0 ? Math.min(...days) : null;
  }, [data, microPlanData]);

  // 新手引导：用户状态聚合（必须在条件返回之前调用以保持 hooks 顺序稳定）
  const userState: UserState = useMemo(() => ({
    hasOnboarding: onboardingStatusData?.completed ?? false,
    hasAssessment: (assessmentHistory?.length ?? 0) > 0,
    hasSimulation,
    hasDecision: (data?.decisions_count ?? 0) > 0,
    hasPlan: (careerPlansData?.length ?? 0) > 0,
  }), [onboardingStatusData, assessmentHistory, hasSimulation, data?.decisions_count, careerPlansData]);

  // 错误提示（核心接口失败时提示用户）— 使用 ref 持有 toast 避免依赖不稳定导致无限更新
  const toastRef = useRef(toast);
  useEffect(() => { toastRef.current = toast; }, [toast]);
  useEffect(() => {
    if (overviewError) toastRef.current.push(overviewError.message || "加载看板失败", "error");
  }, [overviewError]);
  useEffect(() => {
    if (pulseError) toastRef.current.push(pulseError.message || "加载决策副驾驶数据失败", "error");
  }, [pulseError]);

  if (coreLoading) return <DashboardSkeleton />;
  if (!data) return null;

  const isEmpty =
    data.decisions_count === 0 &&
    data.events_count === 0 &&
    data.skills_count === 0 &&
    data.retrospectives_count === 0;

  const insights = insightsSummary?.latest_insights ?? [];
  const unreadInsightCount =
    insightsSummary?.unread_count ??
    insights.filter((i) => !i.is_read).length;

  // 暗知识推送 — 从 pulse 派生未读列表
  const darkKnowledgeFeed = pulseData?.dark_knowledge_feed ?? [];
  const unreadDarkKnowledge = darkKnowledgeFeed.find((k) => !k.is_read) ?? null;

  // 微行动计划
  const microPlan = microPlanData ?? null;

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

  // 暗知识"已了解" — 标记已读并刷新 pulse
  const handleDarkKnowledgeRead = async (pushId: string) => {
    mutatePulse(
      (prev) => prev ? {
        ...prev,
        dark_knowledge_feed: prev.dark_knowledge_feed.map((k) =>
          k.push_id === pushId ? { ...k, is_read: true, read_at: new Date().toISOString() } : k,
        ),
      } : prev,
      { revalidate: false },
    );
    try {
      await darkKnowledgePushApi.markRead(pushId);
    } catch {
      mutatePulse();
    }
  };

  // 微行动快速完成 — 传入默认记录并刷新
  const handleMicroTaskQuickComplete = async (taskId: string) => {
    try {
      await microActionApi.completeTask(taskId, { user_response: "通过看板快速完成" });
      toast.success("任务已完成");
      mutateMicroPlan();
    } catch {
      toast.push("操作失败，请重试", "error");
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

      {/* 新手任务清单 — 10 个核心任务引导新用户上手 */}
      <OnboardingQuest />

      {/* 智能下一步推荐 — 基于用户当前进度推荐 1-3 个行动 */}
      <NextStepRecommender state={userState} />

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

      {/* 报考条件账本摘要 — 北极星「条件完成率」的看板视图 */}
      {data.condition_ledger && (
        <section className="card p-5 animate-fade-in">
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Crosshair className="h-5 w-5 text-brand-600" />
              <h2 className="text-lg font-semibold text-ink-800">报考条件账本</h2>
            </div>
            <Link href="/skills" className="text-xs text-brand-600 hover:underline">
              去核对
            </Link>
          </div>
          <p className="text-sm text-ink-800">
            {data.condition_ledger.dept_name} · {data.condition_ledger.position_name}
            <span className="ml-2 text-[11px] text-ink-400">
              {data.condition_ledger.exam_source === "province"
                ? "省考"
                : data.condition_ledger.exam_source === "kaoyan"
                  ? "考研"
                  : "国考"}{" "}
              {data.condition_ledger.position_code}
            </span>
          </p>
          <div className="mt-2 flex items-center gap-3">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-paper-200">
              <div
                className="h-full rounded-full bg-brand-500 transition-all"
                style={{ width: `${data.condition_ledger.rate}%` }}
              />
            </div>
            <span className="shrink-0 text-sm font-bold text-brand-600">
              {data.condition_ledger.rate}%
            </span>
            <span className="shrink-0 text-[11px] text-ink-400">
              已满足 {data.condition_ledger.met}/{data.condition_ledger.total}
            </span>
          </div>
        </section>
      )}

      {/* 今日行动 — AI 从三中心聚合的今日优先级助推 */}
      <section className="card p-5 animate-fade-in">
        <div className="mb-4 flex items-center gap-2">
          <Target className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-ink-800">今日行动</h2>
        </div>
        {todayActions.length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-ink-400">
            <Sparkles className="h-4 w-4 text-brand-500" />
            <span>暂无紧急待办，保持节奏 — 或去做一次阶段复盘梳理思路。</span>
            <Link href="/retrospectives" className="text-brand-600 hover:underline">去复盘</Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {todayActions.map((action) => (
              <li key={action.key} className="flex items-center gap-3">
                <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-brand-500" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-ink-800 truncate">{action.title}</p>
                </div>
                <Badge color={action.badgeColor}>{action.source}</Badge>
                {action.duration && (
                  <span className="text-xs text-ink-400 whitespace-nowrap">约 {action.duration} 分钟</span>
                )}
                <Link
                  href={action.href}
                  className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 transition-colors whitespace-nowrap"
                >
                  去做 <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </li>
            ))}
          </ul>
        )}

        {/* 三中心入口（轻量） */}
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-paper-100 pt-3">
          <Link
            href="/actions"
            className="inline-flex items-center gap-1.5 rounded-full bg-paper-100 px-3 py-1 text-xs font-medium text-ink-600 hover:bg-paper-200 transition-colors"
          >
            <ListChecks className="h-3.5 w-3.5 text-brand-600" />
            行动任务中心
          </Link>
          <Link
            href="/growth/archive"
            className="inline-flex items-center gap-1.5 rounded-full bg-paper-100 px-3 py-1 text-xs font-medium text-ink-600 hover:bg-paper-200 transition-colors"
          >
            <TrendingUp className="h-3.5 w-3.5 text-brand-600" />
            成长档案
          </Link>
          <Link
            href="/retrospectives"
            className="inline-flex items-center gap-1.5 rounded-full bg-paper-100 px-3 py-1 text-xs font-medium text-ink-600 hover:bg-paper-200 transition-colors"
          >
            <Calendar className="h-3.5 w-3.5 text-brand-600" />
            阶段复盘
          </Link>
        </div>
      </section>

      {/* 决策副驾驶护城河看板 */}
      <PulseOverviewSection overview={pulseOverview} loading={pulseLoading} />

      {/* 决策副驾驶：活跃决策 */}
      <ActiveDecisionsSection items={pulseActiveDecisions} loading={pulseLoading} />

      {/* 创意功能：同路人镜像 — 和你同阶段的人怎么选、结果如何 */}
      <PeerMirrorCard />

      {/* 职业星系可视化 — 全局视角（下移：先看行动，再看全景） */}
      <CareerGalaxy
        timeline={data.timeline}
        latestDecision={data.latest_decision}
        microPlan={microPlan}
      />

      {/* Career Fit Score 活档案 */}
      <CareerFitScoreCard
        score={careerFitScore}
        lastUpdatedDays={lastUpdatedDays}
      />

      {/* ===== 详细数据（折叠） ===== */}
      <CollapsibleSection title="详细数据面板" subtitle="情报总览、连续打卡、等级进度">
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
                {personalIntel.directions?.map((d) => (
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
                {personalIntel.competitiveness_radar?.map((r) => (
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

      {/* 连续打卡 — 增强版 */}
      {streakStats && (
        <StreakBar
          stats={streakStats}
          onRestDay={async () => {
            await streaksApi.restDay();
            mutateStreak();
          }}
          restDayLoading={false}
        />
      )}
      {streakStats && (
        <StreakCalendar records={streakStats.recent_records} />
      )}
      {streakStats && (
        <StreakActions
          stats={streakStats}
          onCheckin={() => mutateStreak()}
        />
      )}

      {/* 成长档案 — 游戏化概览 */}
      {gamificationProfile && (
        <div className="card overflow-hidden animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-400 to-purple-500 text-white">
              <Target className="h-6 w-6" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2">
                <span className="font-display text-lg font-bold text-ink-800">
                  {gamificationProfile.level_name ?? "萌新"}
                </span>
                <span className="text-xs text-ink-400">
                  Lv.{gamificationProfile.level ?? 1}
                </span>
              </div>
              <div className="mt-1 h-2 w-full rounded-full bg-paper-200">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-brand-400 to-purple-400 transition-all"
                  style={{ width: `${Math.min(gamificationProfile.progress?.percent ?? 0, 100)}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-ink-400">
                {gamificationProfile.xp ?? 0}XP · 距下一级还差 {Math.max(0, (gamificationProfile.progress?.needed ?? 0) - (gamificationProfile.progress?.current ?? 0))}XP
              </p>
            </div>
            {gamificationProfile.earned_badges?.length > 0 && (
              <div className="flex -space-x-2">
                {gamificationProfile.earned_badges.slice(0, 5).map((b, i) => (
                  <div
                    key={i}
                    className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100 border-2 border-white text-xs"
                    title={b.name ?? b}
                  >
                    {b.icon ?? "🏅"}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      </CollapsibleSection>

      {/* ===== AI 洞察与成长记录（折叠） ===== */}
      <CollapsibleSection title="AI 洞察与成长记录" subtitle="暗知识、微行动、AI 洞察、时间线">
      {/* 增强 3：暗知识推送 — AI 洞察区域附近 */}
      <DarkKnowledgeCard
        item={unreadDarkKnowledge}
        onMarkRead={handleDarkKnowledgeRead}
      />

      {/* 创意功能：暗知识缺口雷达 — 你还没看到但同路人都看的关键信息 */}
      <DarkKnowledgeGapCard />

      {/* 增强 4：本周成长微行动 */}
      <MicroActionCard
        plan={microPlan}
        onQuickComplete={handleMicroTaskQuickComplete}
      />

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
      {/* 本周回顾 */}
      {weeklyRecap && (
        <div className="card overflow-hidden animate-fade-in">
          <div className="flex items-center justify-between">
            <h2 className="font-display font-semibold text-ink-800 flex items-center gap-2">
              <Target className="h-4 w-4 text-brand-600" />
              本周回顾
            </h2>
            <Link
              href="/retrospectives/weekly"
              className="text-sm text-brand-600 hover:text-brand-700 transition-colors inline-flex items-center"
            >
              完整周报 <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-brand-50 p-3">
              <p className="font-display text-xl font-bold text-brand-700">
                {weeklyRecap.completed_this_week ?? 0}
              </p>
              <p className="text-xs text-brand-500">本周完成里程碑</p>
            </div>
            <div className="rounded-lg bg-paper-100 p-3">
              <p className="font-display text-xl font-bold text-ink-700">
                {weeklyRecap.logs_this_week ?? 0}
              </p>
              <p className="text-xs text-ink-400">新增执行日志</p>
            </div>
          </div>
          {weeklyRecap.upcoming_deadlines?.length > 0 && (
            <div className="mt-3 space-y-1.5">
              <p className="text-xs font-medium text-ink-500">即将到期</p>
              {weeklyRecap.upcoming_deadlines.slice(0, 3).map((d, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-ink-600 truncate max-w-[200px]">
                    {d.milestone_title}
                  </span>
                  <span className="shrink-0 font-medium text-amber-600">
                    {d.days_remaining}天后
                  </span>
                </div>
              ))}
            </div>
          )}
          <p className="mt-3 text-xs text-ink-400 italic">
            {weeklyRecap.encouragement}
          </p>
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

      </CollapsibleSection>
    </div>
  );
}
