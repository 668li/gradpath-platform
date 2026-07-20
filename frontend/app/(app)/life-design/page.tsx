"use client";

import { useCallback, useEffect, useState } from "react";
import { Rocket, Sparkles, CheckCircle2, ArrowRight, ArrowLeft, Calendar, Target, Zap } from "lucide-react";
import { lifeDesignApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Input, Textarea, Field } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type {
  SprintResponse,
  SprintGoal,
  WeeklyReviewResponse,
} from "@/types";

// 领域映射
const DOMAIN_NAMES: Record<string, string> = {
  career: "职业发展",
  finance: "财务状况",
  health: "身心健康",
  relationships: "人际关系",
  growth: "个人成长",
  fun: "乐趣休闲",
  environment: "生活环境",
  spirituality: "意义灵性",
};

const DOMAIN_ICONS: Record<string, string> = {
  career: "💼",
  finance: "💰",
  health: "🏃",
  relationships: "👥",
  growth: "📚",
  fun: "🎨",
  environment: "🏠",
  spirituality: "🧘",
};

const ALL_DOMAINS = ["career", "finance", "health", "relationships", "growth"];

type Phase = "intro" | "audit" | "vision" | "sprint" | "dashboard";

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
}

function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

function ninetyDaysLater(): string {
  const d = new Date();
  d.setDate(d.getDate() + 90);
  return d.toISOString().split("T")[0];
}

export default function LifeDesignPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [phase, setPhase] = useState<Phase>("intro");
  const [activeSprint, setActiveSprint] = useState<SprintResponse | null>(null);
  const [sprints, setSprints] = useState<SprintResponse[]>([]);
  const [weeklyReviews, setWeeklyReviews] = useState<WeeklyReviewResponse[]>([]);

  // 审计相关
  const [auditQuestions, setAuditQuestions] = useState<{ domain: string; domain_name: string; question: string; answer: string }[]>([]);
  const [auditAnswers, setAuditAnswers] = useState<Record<number, string>>({});
  const [auditLoading, setAuditLoading] = useState(false);
  const [selectedDomains, setSelectedDomains] = useState<string[]>(ALL_DOMAINS);

  // 愿景相关
  const [vision, setVision] = useState<string>("");
  const [visionLoading, setVisionLoading] = useState(false);

  // 冲刺相关
  const [sprintName, setSprintName] = useState("");
  const [primaryDomain, setPrimaryDomain] = useState("career");
  const [maintenanceDomains, setMaintenanceDomains] = useState<string[]>([]);
  const [sprintGoals, setSprintGoals] = useState<SprintGoal[]>([{ title: "", measurable_result: "", deadline: null }]);
  const [sprintCreating, setSprintCreating] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [active, allSprints, reviews] = await Promise.all([
        lifeDesignApi.getActiveSprint().catch(() => null),
        lifeDesignApi.listSprints().catch(() => []),
        lifeDesignApi.listWeeklyReviews().catch(() => []),
      ]);
      setActiveSprint(active);
      setSprints(allSprints);
      setWeeklyReviews(reviews);
      if (active) setPhase("dashboard");
    } catch {
      toast.push("加载数据失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 开始审计
  const startAudit = useCallback(async () => {
    setAuditLoading(true);
    try {
      const questions = await lifeDesignApi.getAuditQuestions(selectedDomains);
      setAuditQuestions(questions.map(q => ({ ...q, answer: "" })));
      setAuditAnswers({});
      setPhase("audit");
    } catch {
      toast.push("加载审计问题失败", "error");
    } finally {
      setAuditLoading(false);
    }
  }, [selectedDomains, toast]);

  // 生成愿景
  const generateVision = useCallback(async () => {
    setVisionLoading(true);
    try {
      const qa = auditQuestions.map((q, i) => ({
        question: q.question,
        answer: auditAnswers[i] || "",
      }));
      const res = await lifeDesignApi.generateVision(qa);
      setVision(res.vision_statement);
      setPhase("vision");
    } catch {
      toast.push("AI 愿景生成失败，请重试", "error");
    } finally {
      setVisionLoading(false);
    }
  }, [auditQuestions, auditAnswers, toast]);

  // 创建冲刺
  const createSprint = useCallback(async () => {
    if (!sprintName.trim()) {
      toast.push("请填写冲刺名称", "error");
      return;
    }
    const validGoals = sprintGoals.filter(g => g.title.trim());
    if (validGoals.length === 0) {
      toast.push("请至少添加一个目标", "error");
      return;
    }
    setSprintCreating(true);
    try {
      const res = await lifeDesignApi.createSprint({
        name: sprintName,
        primary_domain: primaryDomain,
        maintenance_domains: maintenanceDomains,
        start_date: todayISO(),
        end_date: ninetyDaysLater(),
        goals: validGoals,
        vision_statement: vision || null,
        audit_qa: auditQuestions.map((q, i) => ({
          question: q.question,
          answer: auditAnswers[i] || "",
        })),
      });
      await lifeDesignApi.activateSprint(res.id);
      setActiveSprint(res);
      setPhase("dashboard");
      toast.push("冲刺创建成功！", "success");
      loadData();
    } catch {
      toast.push("创建冲刺失败，请重试", "error");
    } finally {
      setSprintCreating(false);
    }
  }, [sprintName, primaryDomain, maintenanceDomains, sprintGoals, vision, auditQuestions, auditAnswers, toast, loadData]);

  if (loading) return <LoadingState />;

  // ====== 介绍页 ======
  if (phase === "intro") {
    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
            <Rocket className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
          </div>
          <h1 className="page-title">人生设计引擎</h1>
          <p className="text-sm text-ink-400 mt-2 leading-relaxed">
            从模糊焦虑到结构化行动
            <br />
            审计现状 → 构建愿景 → 90天冲刺 → 周复盘
          </p>
        </div>

        <div className="card space-y-5">
          <div className="grid grid-cols-2 gap-3">
            <StepCard num="1" title="人生审计" desc="10个直击灵魂的问题，看清现状" icon="🔍" />
            <StepCard num="2" title="愿景构建" desc="AI 基于你的回答生成 2-3 年愿景" icon="✨" />
            <StepCard num="3" title="90天冲刺" desc="聚焦一个主攻领域，设定可衡量目标" icon="🚀" />
            <StepCard num="4" title="周复盘" desc="每周回顾，AI 教练给出反馈" icon="📋" />
          </div>

          {/* 领域选择 */}
          <div className="rounded-lg bg-paper-50 p-4 space-y-3">
            <p className="text-sm font-medium text-ink-700">选择审计聚焦领域</p>
            <div className="flex flex-wrap gap-2">
              {ALL_DOMAINS.map(d => {
                const selected = selectedDomains.includes(d);
                return (
                  <button
                    key={d}
                    onClick={() => {
                      setSelectedDomains(prev =>
                        selected ? prev.filter(x => x !== d) : [...prev, d]
                      );
                    }}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-all",
                      selected
                        ? "bg-brand-600 text-white"
                        : "bg-white text-ink-500 border border-paper-300 hover:border-brand-300",
                    )}
                  >
                    <span>{DOMAIN_ICONS[d]}</span>
                    {DOMAIN_NAMES[d]}
                  </button>
                );
              })}
            </div>
          </div>

          <Button onClick={startAudit} loading={auditLoading} className="w-full" size="md">
            <Sparkles className="h-4 w-4" />
            开始人生审计
          </Button>
        </div>

        {sprints.length > 0 && (
          <div className="card space-y-3">
            <h2 className="font-display font-semibold text-ink-800">历史冲刺</h2>
            {sprints.map(s => (
              <div key={s.id} className="flex items-center justify-between border-b border-paper-200 pb-2 last:border-0">
                <div>
                  <p className="text-sm font-medium text-ink-700">{s.name}</p>
                  <p className="text-xs text-ink-400">
                    {DOMAIN_NAMES[s.primary_domain] || s.primary_domain} · {formatDate(s.start_date)} ~ {formatDate(s.end_date)}
                  </p>
                </div>
                <span className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  s.status === "active" ? "bg-brand-100 text-brand-700" : "bg-paper-200 text-ink-500",
                )}>
                  {s.status === "active" ? "进行中" : s.status === "completed" ? "已完成" : "已规划"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ====== 审计页 ======
  if (phase === "audit") {
    const answeredCount = Object.values(auditAnswers).filter(v => v.trim()).length;
    const progress = auditQuestions.length ? (answeredCount / auditQuestions.length) * 100 : 0;

    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div>
          <div className="flex items-center justify-between mb-2">
            <h1 className="font-display text-xl font-semibold text-ink-800">人生审计</h1>
            <span className="text-xs text-ink-400">{answeredCount} / {auditQuestions.length} 已回答</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-paper-200">
            <div className="h-full rounded-full bg-brand-500 transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div className="card space-y-5">
          {auditQuestions.map((q, i) => (
            <div key={`${q.question}-${i}`} className="space-y-2">
              <div className="flex items-start gap-2">
                <span className="text-base shrink-0">{DOMAIN_ICONS[q.domain] || "🔹"}</span>
                <div>
                  <p className="text-sm font-medium text-ink-800">{q.question}</p>
                  <p className="text-[11px] text-ink-400 mt-0.5">{q.domain_name}</p>
                </div>
              </div>
              <Textarea
                value={auditAnswers[i] || ""}
                onChange={e => setAuditAnswers(prev => ({ ...prev, [i]: e.target.value }))}
                placeholder="诚实地写下你的想法…"
                className="resize-y min-h-[70px]"
              />
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between">
          <button
            onClick={() => setPhase("intro")}
            className="text-sm text-ink-400 hover:text-ink-600 transition-colors"
          >
            <ArrowLeft className="inline h-4 w-4" /> 返回
          </button>
          <Button
            onClick={generateVision}
            loading={visionLoading}
            disabled={answeredCount < 3}
            size="md"
          >
            <Sparkles className="h-4 w-4" />
            生成愿景
          </Button>
        </div>
      </div>
    );
  }

  // ====== 愿景页 ======
  if (phase === "vision") {
    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
            <Sparkles className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
          </div>
          <h1 className="page-title">你的 2-3 年愿景</h1>
          <p className="text-sm text-ink-400 mt-2">AI 基于你的审计回答生成</p>
        </div>

        <div className="card">
          <p className="text-sm text-ink-700 leading-relaxed whitespace-pre-line">
            {vision || "愿景生成中…"}
          </p>
        </div>

        <div className="card space-y-3">
          <p className="text-sm text-ink-500">这个愿景让你心动吗？</p>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => { setPhase("audit"); setVision(""); }} className="flex-1">
              <ArrowLeft className="h-4 w-4" /> 重新审计
            </Button>
            <Button onClick={() => setPhase("sprint")} className="flex-1">
              创建 90 天冲刺 <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ====== 冲刺创建页 ======
  if (phase === "sprint") {
    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
            <Rocket className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
          </div>
          <h1 className="page-title">90 天冲刺</h1>
          <p className="text-sm text-ink-400 mt-2">聚焦一个主攻领域，设定 2-3 个可衡量目标</p>
        </div>

        <div className="card space-y-5">
          <Field label="冲刺名称" required>
            <Input
              value={sprintName}
              onChange={e => setSprintName(e.target.value)}
              placeholder="例如：2024 Q3 职业突破冲刺"
            />
          </Field>

          <Field label="主攻领域" required hint="这 90 天你投入最多精力的领域">
            <div className="flex flex-wrap gap-2">
              {ALL_DOMAINS.map(d => (
                <button
                  key={d}
                  onClick={() => setPrimaryDomain(d)}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-all",
                    primaryDomain === d
                      ? "bg-brand-600 text-white"
                      : "bg-white text-ink-500 border border-paper-300 hover:border-brand-300",
                  )}
                >
                  <span>{DOMAIN_ICONS[d]}</span>
                  {DOMAIN_NAMES[d]}
                </button>
              ))}
            </div>
          </Field>

          <Field label="维护领域" hint="不主攻但需要守住底线的领域">
            <div className="flex flex-wrap gap-2">
              {ALL_DOMAINS.filter(d => d !== primaryDomain).map(d => {
                const selected = maintenanceDomains.includes(d);
                return (
                  <button
                    key={d}
                    onClick={() => {
                      setMaintenanceDomains(prev =>
                        selected ? prev.filter(x => x !== d) : [...prev, d]
                      );
                    }}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-all",
                      selected
                        ? "bg-brand-100 text-brand-700 border border-brand-300"
                        : "bg-white text-ink-500 border border-paper-300 hover:border-brand-300",
                    )}
                  >
                    <span>{DOMAIN_ICONS[d]}</span>
                    {DOMAIN_NAMES[d]}
                  </button>
                );
              })}
            </div>
          </Field>

          {/* 目标列表 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-ink-700">冲刺目标</span>
              <button
                onClick={() => setSprintGoals(prev => [...prev, { title: "", measurable_result: "", deadline: null }])}
                className="text-xs text-brand-600 hover:text-brand-700 font-medium"
              >
                + 添加目标
              </button>
            </div>
            {sprintGoals.map((goal, i) => (
              <div key={`${goal.title}-${i}`} className="rounded-lg border border-paper-200 bg-paper-50 p-3 space-y-2">
                <div className="flex items-start gap-2">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-medium text-brand-700">
                    {i + 1}
                  </span>
                  <div className="flex-1 space-y-2">
                    <Input
                      value={goal.title}
                      onChange={e => {
                        setSprintGoals(prev => prev.map((g, idx) => idx === i ? { ...g, title: e.target.value } : g));
                      }}
                      placeholder="目标标题，例如：拿到 3 个面试 offer"
                      className="text-sm"
                    />
                    <Textarea
                      value={goal.measurable_result}
                      onChange={e => {
                        setSprintGoals(prev => prev.map((g, idx) => idx === i ? { ...g, measurable_result: e.target.value } : g));
                      }}
                      placeholder="可衡量的结果，例如：投递 50 份简历，通过至少 5 轮技术面"
                      className="text-sm min-h-[50px]"
                    />
                  </div>
                  {sprintGoals.length > 1 && (
                    <button
                      onClick={() => setSprintGoals(prev => prev.filter((_, idx) => idx !== i))}
                      className="text-ink-300 hover:text-red-500 text-sm shrink-0"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <Button onClick={createSprint} loading={sprintCreating} className="w-full" size="md">
            <Rocket className="h-4 w-4" />
            启动冲刺
          </Button>
        </div>
      </div>
    );
  }

  // ====== 冲刺看板 ======
  if (phase === "dashboard" && activeSprint) {
    return <SprintDashboard
      sprint={activeSprint}
      weeklyReviews={weeklyReviews}
      vision={vision}
      onRefresh={loadData}
      onStartNew={() => {
        setActiveSprint(null);
        setPhase("intro");
      }}
    />;
  }

  return <LoadingState />;
}

// ====== 冲刺看板组件 ======
function SprintDashboard({
  sprint,
  weeklyReviews,
  vision,
  onRefresh,
  onStartNew,
}: {
  sprint: SprintResponse;
  weeklyReviews: WeeklyReviewResponse[];
  vision: string;
  onRefresh: () => void;
  onStartNew: () => void;
}) {
  const toast = useToast();
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [aiReview, setAiReview] = useState<string | null>(sprint.ai_review);
  const [generatingReview, setGeneratingReview] = useState(false);

  // 周复盘表单
  const [reviewForm, setReviewForm] = useState({
    planned_actions: "",
    actual_actions: "",
    what_worked: "",
    what_didnt_work: "",
    next_week_plan: "",
    energy_level: 3,
  });
  const [submittingReview, setSubmittingReview] = useState(false);

  const today = new Date();
  const endDate = new Date(sprint.end_date);
  const startDate = new Date(sprint.start_date);
  const totalDays = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
  const elapsedDays = Math.min(totalDays, Math.max(0, Math.ceil((today.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))));
  const remainingDays = Math.max(0, Math.ceil((endDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)));
  const progressPct = totalDays > 0 ? Math.round((elapsedDays / totalDays) * 100) : 0;

  const handleGenerateReview = async () => {
    setGeneratingReview(true);
    try {
      const res = await lifeDesignApi.generateSprintReview(sprint.id);
      setAiReview(res.ai_review);
      toast.push("AI 季度回顾已生成", "success");
    } catch {
      toast.push("生成失败，请重试", "error");
    } finally {
      setGeneratingReview(false);
    }
  };

  const handleSubmitReview = async () => {
    setSubmittingReview(true);
    try {
      const now = new Date();
      const weekStart = new Date(now);
      weekStart.setDate(now.getDate() - now.getDay() + 1);
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);

      await lifeDesignApi.createWeeklyReview({
        sprint_id: sprint.id,
        week_start: weekStart.toISOString().split("T")[0],
        week_end: weekEnd.toISOString().split("T")[0],
        ...reviewForm,
      });
      toast.push("周复盘已提交！", "success");
      setShowReviewForm(false);
      setReviewForm({
        planned_actions: "",
        actual_actions: "",
        what_worked: "",
        what_didnt_work: "",
        next_week_plan: "",
        energy_level: 3,
      });
      onRefresh();
    } catch {
      toast.push("提交失败，请重试", "error");
    } finally {
      setSubmittingReview(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* 冲刺头部 */}
      <div className="card">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h1 className="font-display text-xl font-semibold text-ink-800">{sprint.name}</h1>
            <p className="text-sm text-ink-400 mt-1">
              {DOMAIN_NAMES[sprint.primary_domain] || sprint.primary_domain}
              {sprint.maintenance_domains.length > 0 && (
                <span className="ml-2">维护：{sprint.maintenance_domains.map(d => DOMAIN_NAMES[d] || d).join("、")}</span>
              )}
            </p>
          </div>
          <span className="inline-flex items-center rounded-full bg-brand-100 px-3 py-0.5 text-xs font-medium text-brand-700">
            进行中
          </span>
        </div>

        {/* 倒计时进度条 */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-ink-500">
              <Calendar className="inline h-3.5 w-3.5" /> {formatDate(sprint.start_date)} ~ {formatDate(sprint.end_date)}
            </span>
            <span className="font-medium text-brand-600">剩余 {remainingDays} 天</span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-paper-200">
            <div className="h-full rounded-full bg-brand-500 transition-all duration-500" style={{ width: `${progressPct}%` }} />
          </div>
          <p className="text-[11px] text-ink-400 text-right">已过 {progressPct}%</p>
        </div>
      </div>

      {/* 愿景展示 */}
      {(sprint.vision_statement || vision) && (
        <div className="card space-y-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand-600" />
            <h2 className="font-display font-semibold text-ink-800">愿景</h2>
          </div>
          <p className="text-sm text-ink-600 leading-relaxed whitespace-pre-line">
            {sprint.vision_statement || vision}
          </p>
        </div>
      )}

      {/* 目标列表 */}
      <div className="card space-y-3">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-brand-600" />
          <h2 className="font-display font-semibold text-ink-800">冲刺目标</h2>
        </div>
        {sprint.goals.map((goal, i) => (
          <div key={`${goal.title}-${i}`} className="rounded-lg border border-paper-200 bg-paper-50 p-3">
            <div className="flex items-start gap-2">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-medium text-brand-700">
                {i + 1}
              </span>
              <div>
                <p className="text-sm font-medium text-ink-800">{goal.title}</p>
                <p className="text-xs text-ink-500 mt-1">{goal.measurable_result}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 周复盘 */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-brand-600" />
            <h2 className="font-display font-semibold text-ink-800">周复盘</h2>
          </div>
          {!showReviewForm && (
            <Button variant="secondary" size="sm" onClick={() => setShowReviewForm(true)}>
              写本周复盘
            </Button>
          )}
        </div>

        {showReviewForm && (
          <div className="space-y-3 rounded-lg border border-paper-200 bg-paper-50 p-4">
            <Field label="本周计划做了什么">
              <Textarea value={reviewForm.planned_actions} onChange={e => setReviewForm(prev => ({ ...prev, planned_actions: e.target.value }))} className="resize-y min-h-[60px]" />
            </Field>
            <Field label="实际做了什么">
              <Textarea value={reviewForm.actual_actions} onChange={e => setReviewForm(prev => ({ ...prev, actual_actions: e.target.value }))} className="resize-y min-h-[60px]" />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="什么有效">
                <Textarea value={reviewForm.what_worked} onChange={e => setReviewForm(prev => ({ ...prev, what_worked: e.target.value }))} className="resize-y min-h-[50px]" />
              </Field>
              <Field label="什么没效">
                <Textarea value={reviewForm.what_didnt_work} onChange={e => setReviewForm(prev => ({ ...prev, what_didnt_work: e.target.value }))} className="resize-y min-h-[50px]" />
              </Field>
            </div>
            <Field label="下周计划">
              <Textarea value={reviewForm.next_week_plan} onChange={e => setReviewForm(prev => ({ ...prev, next_week_plan: e.target.value }))} className="resize-y min-h-[50px]" />
            </Field>
            <Field label="能量水平">
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map(n => (
                  <button
                    key={n}
                    onClick={() => setReviewForm(prev => ({ ...prev, energy_level: n }))}
                    className={cn(
                      "h-9 w-9 rounded-lg text-sm font-medium transition-all",
                      reviewForm.energy_level === n
                        ? "bg-brand-600 text-white"
                        : "bg-white text-ink-500 border border-paper-300",
                    )}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </Field>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setShowReviewForm(false)} className="flex-1">取消</Button>
              <Button onClick={handleSubmitReview} loading={submittingReview} className="flex-1">提交复盘</Button>
            </div>
          </div>
        )}

        {/* 周复盘历史 */}
        {weeklyReviews.length > 0 && (
          <div className="space-y-2">
            {weeklyReviews.slice(0, 5).map(r => (
              <div key={r.id} className="rounded-lg border border-paper-200 p-3 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-ink-400">
                    {formatDate(r.week_start)} ~ {formatDate(r.week_end)}
                  </span>
                  {r.energy_level && (
                    <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-600">
                      能量 {r.energy_level}/5
                    </span>
                  )}
                </div>
                {r.actual_actions && (
                  <p className="text-sm text-ink-700"><span className="text-ink-400">实际完成：</span>{r.actual_actions}</p>
                )}
                {r.ai_analysis && (
                  <div className="mt-2 rounded-md bg-brand-50 p-2.5">
                    <p className="text-xs text-brand-700 font-medium mb-1">AI 教练反馈</p>
                    <p className="text-xs text-ink-600 leading-relaxed whitespace-pre-line">{r.ai_analysis}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI 季度回顾 */}
      <div className="card space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-brand-600" />
            <h2 className="font-display font-semibold text-ink-800">AI 季度回顾</h2>
          </div>
          <Button variant="secondary" size="sm" onClick={handleGenerateReview} loading={generatingReview}>
            {aiReview ? "重新生成" : "生成回顾"}
          </Button>
        </div>
        {aiReview ? (
          <p className="text-sm text-ink-600 leading-relaxed whitespace-pre-line">{aiReview}</p>
        ) : (
          <p className="text-sm text-ink-400">冲刺结束后，AI 将基于你的目标和周复盘生成季度回顾。</p>
        )}
      </div>

      {/* 新冲刺 */}
      <div className="text-center">
        <button
          onClick={onStartNew}
          className="text-sm text-ink-400 hover:text-brand-600 transition-colors"
        >
          <Rocket className="inline h-4 w-4" /> 创建新冲刺
        </button>
      </div>
    </div>
  );
}

function StepCard({ num, title, desc, icon }: { num: string; title: string; desc: string; icon: string }) {
  return (
    <div className="rounded-lg border border-paper-200 bg-white p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{icon}</span>
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-100 text-[10px] font-bold text-brand-700">
          {num}
        </span>
      </div>
      <p className="text-sm font-medium text-ink-800">{title}</p>
      <p className="text-[11px] text-ink-400 mt-0.5 leading-snug">{desc}</p>
    </div>
  );
}
