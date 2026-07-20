"use client";

import { useCallback, useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  BookOpen,
  Target,
  Calendar,
  Brain,
  ArrowRight,
  Sparkles,
  Clock,
  BarChart3,
  School,
  RefreshCw,
  ChevronRight,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Users,
  Award,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Newspaper,
} from "lucide-react";
import { Button, Input, Select, Badge, Field, Textarea } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { gradIntelApi, assessmentApi, kaoyanNewsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { PositioningResponse, PositioningCreateRequest, AssessmentResponse, KaoyanNewsResponse } from "@/types";
import { KaoyanNewsCard } from "./KaoyanNewsCard";

const strategyCards = [
  {
    icon: Target,
    title: "智能选校匹配",
    desc: "基于你的背景、目标和风险偏好，推荐冲/稳/保三档院校",
    action: "开始匹配",
    href: "#match",
    color: "bg-blue-500",
  },
  {
    icon: Calendar,
    title: "备考时间规划",
    desc: "距离考试还有多少天？我们帮你拆解到每周的复习任务",
    action: "生成计划",
    href: "#plan",
    color: "bg-green-500",
  },
  {
    icon: Brain,
    title: "薄弱科目诊断",
    desc: "分析历年真题分布，定位你的高频失分点",
    action: "诊断分析",
    href: "#weakness",
    color: "bg-purple-500",
  },
  {
    icon: BarChart3,
    title: "学习资源推荐",
    desc: "针对目标院校专业课的教材、真题、笔记推荐",
    action: "查看资源",
    href: "#resources",
    color: "bg-orange-500",
  },
];

export default function StrategyPage() {
  const router = useRouter();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<"match" | "plan" | "diagnosis">("match");
  const [latestPositioning, setLatestPositioning] = useState<PositioningResponse | null>(null);
  const [assessment, setAssessment] = useState<AssessmentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [loadingPhase, setLoadingPhase] = useState<"idle" | "schools" | "analysis">("idle");
  const [elapsedTime, setElapsedTime] = useState(0);
  const [showTimeout, setShowTimeout] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const phaseTimerRef = useRef<NodeJS.Timeout | null>(null);

  const [form, setForm] = useState<PositioningCreateRequest>({
    undergrad_tier: "",
    undergrad_major: "",
    gpa: null,
    gpa_rank: "",
    english_level: "",
    english_score: null,
    research_experience: "",
    competitions: [],
    awards: "",
    internships: "",
    target_school: "",
    target_major: "",
    target_region: "",
    other_info: "",
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [pos, assess] = await Promise.all([
        gradIntelApi.getLatestPositioning().catch(() => null),
        assessmentApi.getResult().catch(() => null),
      ]);
      setLatestPositioning(pos);
      setAssessment(assess);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  const [news, setNews] = useState<KaoyanNewsResponse[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);
  const [newsError, setNewsError] = useState<string | null>(null);

  const loadNews = useCallback(async () => {
    setNewsLoading(true);
    setNewsError(null);
    try {
      const res = await kaoyanNewsApi.list({ page: 1, page_size: 10 });
      setNews(res.items);
    } catch {
      setNewsError("加载最新资讯失败，请稍后重试");
    } finally {
      setNewsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    loadNews();
  }, [loadData, loadNews]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (phaseTimerRef.current) clearTimeout(phaseTimerRef.current);
    };
  }, []);

  const handleSubmit = async (bypassCache: boolean = false) => {
    if (!form.undergrad_tier) {
      toast.push("请选择本科层次", "error");
      return;
    }
    
    setSubmitting(true);
    setLoadingPhase("schools");
    setElapsedTime(0);
    setShowTimeout(false);
    
    // 启动计时器
    timerRef.current = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);
    
    // 1.5秒后切换到分析阶段
    phaseTimerRef.current = setTimeout(() => {
      setLoadingPhase("analysis");
    }, 1500);
    
    try {
      const res = await gradIntelApi.createPositioning(form, bypassCache);
      
      // 清除定时器
      if (timerRef.current) clearInterval(timerRef.current);
      if (phaseTimerRef.current) clearTimeout(phaseTimerRef.current);
      
      setLatestPositioning(res);
      setLoadingPhase("idle");
      toast.push("选校匹配完成", "success");
    } catch (error) {
      // 清除定时器
      if (timerRef.current) clearInterval(timerRef.current);
      if (phaseTimerRef.current) clearTimeout(phaseTimerRef.current);
      
      setLoadingPhase("idle");
      toast.push("匹配失败，请稍后重试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  // 超时提示（超过15秒）
  useEffect(() => {
    if (elapsedTime >= 15 && submitting && !showTimeout) {
      setShowTimeout(true);
    }
  }, [elapsedTime, submitting, showTimeout]);

  const daysToExam = useDaysToExam();

  // 根据目标院校难度生成动态备考时间规划
  const generateStudyPlan = (positioning: PositioningResponse | null) => {
    if (!positioning) return [];

    const reachSchools = positioning.reach_schools || [];
    const targetSchools = positioning.target_schools || [];
    const safetySchools = positioning.safety_schools || [];

    // 计算整体难度（基于冲刺档院校概率）
    const avgReachProb = reachSchools.length > 0
      ? reachSchools.reduce((sum, s) => sum + s.probability, 0) / reachSchools.length
      : 0;

    // 根据难度调整备考时间
    const difficulty = avgReachProb < 25 ? "hard" : avgReachProb < 40 ? "medium" : "easy";

    if (difficulty === "hard") {
      return [
        { phase: "基础阶段", range: "3-5 月", focus: "教材通读 + 单词/公式积累 + 专业课基础", weeks: 9 },
        { phase: "强化阶段", range: "6-8 月", focus: "真题精练 + 错题本建立 + 专业课深入", weeks: 13 },
        { phase: "提升阶段", range: "9-10 月", focus: "模拟考试 + 查漏补缺 + 重点突破", weeks: 9 },
        { phase: "冲刺阶段", range: "11 月", focus: "高频考点 + 真题回顾 + 心态调整", weeks: 4 },
        { phase: "决胜阶段", range: "12 月", focus: "全真模拟 + 心态调整 + 高频考点复习", weeks: 4 },
      ];
    } else if (difficulty === "medium") {
      return [
        { phase: "基础阶段", range: "3-6 月", focus: "教材通读 + 单词/公式积累", weeks: 17 },
        { phase: "强化阶段", range: "7-9 月", focus: "真题精练 + 错题本建立", weeks: 13 },
        { phase: "冲刺阶段", range: "10-11 月", focus: "模拟考试 + 查漏补缺", weeks: 9 },
        { phase: "决胜阶段", range: "12 月", focus: "心态调整 + 高频考点复习", weeks: 4 },
      ];
    } else {
      return [
        { phase: "基础阶段", range: "4-6 月", focus: "教材通读 + 单词积累", weeks: 13 },
        { phase: "强化阶段", range: "7-9 月", focus: "真题精练 + 重点突破", weeks: 13 },
        { phase: "冲刺阶段", range: "10-11 月", focus: "模拟考试 + 查漏补缺", weeks: 9 },
        { phase: "决胜阶段", range: "12 月", focus: "心态调整 + 高频考点", weeks: 4 },
      ];
    }
  };

  const studyPlan = generateStudyPlan(latestPositioning);

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-brand-sm">
              <BookOpen className="h-5 w-5" strokeWidth={2.2} />
            </div>
            <h1 className="font-display text-xl sm:text-2xl font-bold text-ink-900 tracking-tight">
              备考策略
            </h1>
          </div>
          <p className="text-sm text-ink-500 ml-[46px]">
            个性化备考方案、智能选校匹配、科学时间规划——让复习少走弯路。
          </p>
        </div>

        {/* Strategy Cards */}
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 mb-8">
          {strategyCards.map((card) => {
            const Icon = card.icon;
            return (
              <div
                key={card.title}
                className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
              >
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-lg text-white mb-3",
                    card.color,
                  )}
                >
                  <Icon className="h-5 w-5" strokeWidth={2} />
                </div>
                <h3 className="font-semibold text-ink-900 mb-1.5">{card.title}</h3>
                <p className="text-xs text-ink-500 mb-4 leading-relaxed">{card.desc}</p>
                <Button
                  size="sm"
                  variant="secondary"
                  className="w-full"
                  onClick={() => {
                    const el = document.querySelector(card.href);
                    el?.scrollIntoView({ behavior: "smooth" });
                  }}
                >
                  {card.action}
                  <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
                </Button>
              </div>
            );
          })}
        </div>

        {/* Main Workspace */}
        <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
          {/* Left: Interactive Tool */}
          <div id="match" className="lg:col-span-2 rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-5">
              <Sparkles className="h-4 w-4 text-brand-600" />
              <h2 className="text-base font-semibold text-ink-800">智能备考工作台</h2>
            </div>

            <div className="flex flex-col gap-2 mb-5 p-1 bg-paper-100 rounded-lg sm:flex-row sm:w-fit">
              {[
                { key: "match", label: "选校匹配" },
                { key: "plan", label: "时间规划" },
                { key: "diagnosis", label: "薄弱诊断" },
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key as typeof activeTab)}
                  className={cn(
                    "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                    activeTab === tab.key
                      ? "bg-white text-brand-700 shadow-sm"
                      : "text-ink-500 hover:text-ink-700",
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {loading ? (
              <LoadingState text="加载备考数据..." />
            ) : activeTab === "match" ? (
              <div className="space-y-5">
                {assessment && (
                  <div className="rounded-lg bg-purple-50 border border-purple-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Brain className="h-4 w-4 text-purple-600" />
                      <span className="text-sm font-semibold text-purple-900">测评结果联动</span>
                    </div>
                    <p className="text-sm text-purple-800 mb-2">
                      你的 {assessment.assessment_type.toUpperCase()} 测评结果为
                      <span className="font-bold mx-1">{assessment.result_code}</span>
                      — {assessment.result_summary}
                    </p>
                    {assessment.recommended_directions.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {assessment.recommended_directions.map((dir) => (
                          <Badge key={dir} color="purple">
                            {dir}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {!latestPositioning ? (
                  <div className="space-y-4">
                    <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
                      <p className="text-sm text-amber-800">
                        填写你的本科背景、目标和意向地区，AI 将基于真实院校数据输出
                        冲/稳/保三档推荐。
                      </p>
                    </div>

                    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
                      <Field label="本科层次" required>
                        <Select
                          value={form.undergrad_tier}
                          onChange={(e) => setForm({ ...form, undergrad_tier: e.target.value })}
                        >
                          <option value="">请选择</option>
                          <option value="985">985</option>
                          <option value="211">211</option>
                          <option value="双一流">双一流</option>
                          <option value="一本">一本</option>
                          <option value="二本">二本</option>
                          <option value="三本">三本</option>
                          <option value="专升本">专升本</option>
                        </Select>
                      </Field>
                      <Field label="本科专业">
                        <Input
                          value={form.undergrad_major || ""}
                          onChange={(e) => setForm({ ...form, undergrad_major: e.target.value || null })}
                          placeholder="如：计算机科学与技术"
                        />
                      </Field>
                      <Field label="目标专业">
                        <Input
                          value={form.target_major || ""}
                          onChange={(e) => setForm({ ...form, target_major: e.target.value || null })}
                          placeholder="如：软件工程"
                        />
                      </Field>
                      <Field label="目标院校">
                        <Input
                          value={form.target_school || ""}
                          onChange={(e) => setForm({ ...form, target_school: e.target.value || null })}
                          placeholder="如：清华大学、北京大学"
                        />
                      </Field>
                      <Field label="目标地区">
                        <Input
                          value={form.target_region || ""}
                          onChange={(e) => setForm({ ...form, target_region: e.target.value || null })}
                          placeholder="如：北京、江浙沪"
                        />
                      </Field>
                      <Field label="GPA">
                        <Input
                          type="number"
                          step="0.01"
                          max={4}
                          value={form.gpa ?? ""}
                          onChange={(e) =>
                            setForm({ ...form, gpa: e.target.value ? parseFloat(e.target.value) : null })
                          }
                          placeholder="如：3.5"
                        />
                      </Field>
                      <Field label="GPA 排名">
                        <Select
                          value={form.gpa_rank || ""}
                          onChange={(e) => setForm({ ...form, gpa_rank: e.target.value || null })}
                        >
                          <option value="">请选择</option>
                          <option value="前 5%">前 5%</option>
                          <option value="前 10%">前 10%</option>
                          <option value="前 20%">前 20%</option>
                          <option value="前 30%">前 30%</option>
                          <option value="中等">中等</option>
                          <option value="偏下">偏下</option>
                        </Select>
                      </Field>
                      <Field label="英语水平">
                        <Select
                          value={form.english_level || ""}
                          onChange={(e) => setForm({ ...form, english_level: e.target.value || null })}
                        >
                          <option value="">请选择</option>
                          <option value="CET-6 500+">CET-6 500+</option>
                          <option value="CET-6 425-500">CET-6 425-500</option>
                          <option value="CET-4">CET-4</option>
                          <option value="雅思 6.5+">雅思 6.5+</option>
                          <option value="托福 90+">托福 90+</option>
                          <option value="暂未过级">暂未过级</option>
                        </Select>
                      </Field>
                      <Field label="英语分数（如已知）">
                        <Input
                          type="number"
                          value={form.english_score ?? ""}
                          onChange={(e) =>
                            setForm({
                              ...form,
                              english_score: e.target.value ? parseInt(e.target.value) : null,
                            })
                          }
                          placeholder="如：520"
                        />
                      </Field>
                    </div>

                    <Field label="获奖情况">
                      <Textarea
                        value={form.awards || ""}
                        onChange={(e) =>
                          setForm({ ...form, awards: e.target.value || null })
                        }
                        placeholder="如：国家奖学金、数学建模竞赛一等奖、英语竞赛等"
                      />
                    </Field>

                    <Field label="科研 / 竞赛 / 项目经历">
                      <Textarea
                        value={form.research_experience || ""}
                        onChange={(e) =>
                          setForm({ ...form, research_experience: e.target.value || null })
                        }
                        placeholder="简要描述论文、大创、竞赛获奖等经历"
                      />
                    </Field>

                    <Field label="实习 / 工作经历">
                      <Textarea
                        value={form.internships || ""}
                        onChange={(e) => setForm({ ...form, internships: e.target.value || null })}
                        placeholder="如有相关实习，可填写公司与岗位"
                      />
                    </Field>

                    <Field label="补充信息">
                      <Textarea
                        value={form.other_info || ""}
                        onChange={(e) => setForm({ ...form, other_info: e.target.value || null })}
                        placeholder="如：已确定导师意向、二战考生、在职备考等"
                      />
                    </Field>

                    <Button onClick={() => handleSubmit(false)} loading={submitting} className="w-full">
                      <Sparkles className="h-4 w-4 mr-1.5" />
                      生成选校推荐
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-5">
                    {/* 加载状态覆盖层 */}
                    {submitting && (
                      <div className="rounded-xl border border-brand-200 bg-gradient-to-br from-brand-50 to-white p-8 shadow-sm">
                        <div className="flex flex-col items-center justify-center space-y-4">
                          {/* 加载动画 */}
                          <div className="relative">
                            <div className="absolute inset-0 rounded-full bg-brand-200 animate-ping opacity-20"></div>
                            <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-brand-100">
                              <Loader2 className="h-8 w-8 text-brand-600 animate-spin" />
                            </div>
                          </div>
                          
                          {/* 进度文案 */}
                          <div className="text-center space-y-2">
                            <p className="text-base font-semibold text-ink-900">
                              {loadingPhase === "schools" && "正在匹配院校数据..."}
                              {loadingPhase === "analysis" && "AI 正在分析你的背景与院校数据..."}
                            </p>
                            <p className="text-sm text-ink-500">
                              {loadingPhase === "schools" && "正在查询冲/稳/保三档院校"}
                              {loadingPhase === "analysis" && "正在生成个性化评估报告"}
                            </p>
                          </div>
                          
                          {/* 计时器 */}
                          <div className="flex items-center gap-2 text-xs text-ink-400">
                            <Clock className="h-3.5 w-3.5" />
                            <span>已用时 {elapsedTime} 秒</span>
                          </div>
                          
                          {/* 超时提示（超过15秒） */}
                          {showTimeout && (
                            <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 max-w-md">
                              <div className="flex items-start gap-2">
                                <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                                <div className="text-left">
                                  <p className="text-sm font-semibold text-amber-900 mb-1">
                                    AI 响应时间较长
                                  </p>
                                  <p className="text-xs text-amber-800 mb-2">
                                    可能是网络拥堵或 AI 服务繁忙。您可以继续等待，或稍后重新生成。
                                  </p>
                                  <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => handleSubmit(true)}
                                    disabled={submitting}
                                    className="text-xs"
                                  >
                                    <RefreshCw className="h-3 w-3 mr-1" />
                                    重新生成
                                  </Button>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-base font-semibold text-ink-900">你的选校匹配结果</h3>
                        <p className="text-sm text-ink-500">
                          综合上岸概率：
                          <span className="font-bold text-brand-600">
                            {latestPositioning.success_probability ?? "—"}%
                          </span>
                        </p>
                      </div>
                      <Button 
                        variant="secondary" 
                        size="sm" 
                        onClick={() => setLatestPositioning(null)}
                        disabled={submitting}
                      >
                        <RefreshCw className="h-4 w-4 mr-1.5" />
                        重新匹配
                      </Button>
                    </div>

                    {/* 降级模式提示 */}
                    {latestPositioning.ai_assessment === null && (
                      <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
                        <div className="flex items-start gap-2">
                          <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                          <div className="flex-1">
                            <p className="text-sm font-semibold text-amber-900 mb-1">
                              AI 服务暂时不可用
                            </p>
                            <p className="text-sm text-amber-800 mb-2">
                              当前显示的是基于规则的静态推荐。您可以稍后点击"重新匹配"获取 AI 个性化分析。
                            </p>
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => handleSubmit(true)}
                              disabled={submitting}
                            >
                              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                              重新生成 AI 分析
                            </Button>
                          </div>
                        </div>
                      </div>
                    )}

                    {latestPositioning.ai_assessment && (
                      <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
                        <p className="text-sm text-blue-800 whitespace-pre-line">
                          {latestPositioning.ai_assessment}
                        </p>
                      </div>
                    )}

                    <SchoolSection
                      title="冲刺档"
                      color="red"
                      schools={latestPositioning.reach_schools}
                      icon={TrendingUp}
                    />
                    <SchoolSection
                      title="稳妥档"
                      color="blue"
                      schools={latestPositioning.target_schools}
                      icon={CheckCircle2}
                    />
                    <SchoolSection
                      title="保底档"
                      color="green"
                      schools={latestPositioning.safety_schools}
                      icon={Award}
                    />

                    {/* 风险评估面板 */}
                    <RiskAssessmentPanel positioning={latestPositioning} />

                    {latestPositioning.risk_warnings.length > 0 && (
                      <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <AlertTriangle className="h-4 w-4 text-amber-600" />
                          <span className="text-sm font-semibold text-amber-900">风险提示</span>
                        </div>
                        <ul className="list-disc list-inside text-sm text-amber-800 space-y-1">
                          {latestPositioning.risk_warnings.map((w, i) => (
                            <li key={`${w}-${i}`}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : activeTab === "plan" ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3 rounded-lg border border-paper-200 p-4">
                  <Clock className="h-5 w-5 text-ink-400" />
                  <div>
                    <p className="text-sm font-medium text-ink-900">距离考研初试</p>
                    <p className="text-xs text-ink-500">
                      {daysToExam > 0 ? (
                        <>
                          还有 <span className="font-bold text-brand-600">{daysToExam}</span> 天，合理分配各科复习时间
                        </>
                      ) : (
                        "请设置目标考试年份，自动生成倒计时与阶段规划"
                      )}
                    </p>
                  </div>
                </div>

                {latestPositioning && studyPlan.length > 0 && (
                  <div className="rounded-lg bg-green-50 border border-green-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Calendar className="h-4 w-4 text-green-600" />
                      <span className="text-sm font-semibold text-green-900">
                        根据你的目标院校难度，已为你定制备考计划
                      </span>
                    </div>
                    <p className="text-xs text-green-800">
                      基于冲刺档院校录取概率，你的备考难度为：
                      <span className="font-bold mx-1">
                        {studyPlan[0].weeks > 15 ? "较高" : studyPlan[0].weeks > 10 ? "中等" : "较低"}
                      </span>
                      ，建议备考周期为
                      <span className="font-bold mx-1">
                        {studyPlan.reduce((sum, p) => sum + p.weeks, 0)} 周
                      </span>
                    </p>
                  </div>
                )}

                <div className="space-y-3">
                  {studyPlan.length > 0 ? (
                    studyPlan.map((item, idx) => (
                      <div key={item.phase} className="flex gap-4">
                        <div className="flex flex-col items-center">
                          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-brand-700 text-xs font-semibold">
                            {idx + 1}
                          </div>
                          {idx < studyPlan.length - 1 && (
                            <div className="w-px flex-1 bg-paper-200 my-1" />
                          )}
                        </div>
                        <div className="pb-5">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-semibold text-ink-900">{item.phase}</span>
                            <span className="text-xs text-ink-400">{item.range}</span>
                            <Badge color="slate" className="text-xs">{item.weeks} 周</Badge>
                          </div>
                          <p className="text-xs text-ink-500">{item.focus}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-sm text-ink-500">
                      请先完成选校匹配，AI 将根据目标院校难度为你生成个性化备考计划
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
                  <p className="text-sm text-blue-800">
                    薄弱科目诊断将基于你的模考成绩、目标院校专业课难度和历年真题考点分布，
                    生成个性化的提分优先级建议。
                  </p>
                </div>
                <EmptyState
                  title="暂无成绩数据"
                  description="完成选校匹配后，可导入模考成绩进行薄弱科目诊断，AI 将为你生成个性化提分建议"
                  action={
                    <Button variant="secondary" size="sm" onClick={() => setActiveTab("match")}>
                      前往选校匹配
                    </Button>
                  }
                />
              </div>
            )}
          </div>

          {/* Right: Quick Stats */}
          <div className="space-y-4">
            <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-ink-800 mb-3">备考工具箱</h3>
              <div className="space-y-1">
                {[
                  { label: "院校对比表", href: "/kaoyan/schools" },
                  { label: "调剂信息追踪", href: "/kaoyan/schools" },
                  { label: "复试经验库", href: "/kaoyan/community" },
                ].map((tool) => (
                  <div
                    key={tool.label}
                    onClick={() => router.push(tool.href)}
                    className="flex items-center justify-between text-sm text-ink-600 py-2 px-3 rounded-lg hover:bg-paper-100 cursor-pointer transition-colors"
                  >
                    {tool.label}
                    <ChevronRight className="h-3.5 w-3.5 text-ink-400" />
                  </div>
                ))}
              </div>
            </div>

            {/* Latest News */}
            <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Newspaper className="h-4 w-4 text-brand-600" />
                  <h3 className="text-sm font-semibold text-ink-800">最新资讯</h3>
                </div>
                <button
                  onClick={loadNews}
                  disabled={newsLoading}
                  className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 disabled:text-ink-300"
                >
                  <RefreshCw className={cn("h-3 w-3", newsLoading && "animate-spin")} />
                  刷新
                </button>
              </div>

              {newsLoading ? (
                <LoadingState text="加载资讯..." />
              ) : newsError ? (
                <div className="space-y-3">
                  <p className="text-sm text-red-600">{newsError}</p>
                  <Button size="sm" variant="secondary" onClick={loadNews}>
                    重试
                  </Button>
                </div>
              ) : news.length === 0 ? (
                <EmptyState
                  title="暂无资讯"
                  description="暂无最新考研资讯，点击刷新重新获取"
                  className="py-6"
                />
              ) : (
                <div className="space-y-3">
                  {news.slice(0, 8).map((item) => (
                    <KaoyanNewsCard key={item.id} news={item} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SchoolSection({
  title,
  color,
  schools,
  icon: Icon,
}: {
  title: string;
  color: "red" | "blue" | "green";
  schools: { name: string; major: string; tier: string; reason: string; probability: number }[];
  icon: typeof TrendingUp;
}) {
  const colorMap = {
    red: "border-red-200 bg-red-50",
    blue: "border-blue-200 bg-blue-50",
    green: "border-green-200 bg-green-50",
  };
  const badgeMap = {
    red: "red",
    blue: "blue",
    green: "green",
  } as const;

  return (
    <div className={cn("rounded-lg border p-4", colorMap[color])}>
      <div className="flex items-center gap-2 mb-3">
        <Icon className="h-4 w-4 text-ink-600" />
        <h4 className="text-sm font-semibold text-ink-900">{title}</h4>
      </div>
      {schools.length === 0 ? (
        <p className="text-sm text-ink-500">暂无推荐数据</p>
      ) : (
        <div className="space-y-3">
          {schools.map((school, idx) => (
            <div
              key={`${school.name}-${idx}`}
              className="rounded-lg border border-paper-200 bg-white p-3 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <div>
                  <span className="font-semibold text-ink-900">{school.name}</span>
                  <span className="ml-2 text-xs text-ink-500">{school.major}</span>
                </div>
                <Badge color={badgeMap[color]}>{school.probability}%</Badge>
              </div>
              <p className="text-xs text-ink-500 mb-1">{school.reason}</p>
              {school.tier && <Badge color="slate" className="text-xs">{school.tier}</Badge>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RiskAssessmentPanel({ positioning }: { positioning: PositioningResponse }) {
  const reachSchools = positioning.reach_schools || [];
  const targetSchools = positioning.target_schools || [];
  const safetySchools = positioning.safety_schools || [];

  // 计算风险指标
  const avgReachProb = reachSchools.length > 0
    ? reachSchools.reduce((sum, s) => sum + s.probability, 0) / reachSchools.length
    : 0;

  const avgTargetProb = targetSchools.length > 0
    ? targetSchools.reduce((sum, s) => sum + s.probability, 0) / targetSchools.length
    : 0;

  const avgSafetyProb = safetySchools.length > 0
    ? safetySchools.reduce((sum, s) => sum + s.probability, 0) / safetySchools.length
    : 0;

  // 估算报录比（基于概率反推）
  const estimateRatio = (prob: number) => {
    if (prob >= 80) return "< 3:1";
    if (prob >= 60) return "3:1 - 5:1";
    if (prob >= 40) return "5:1 - 8:1";
    if (prob >= 20) return "8:1 - 12:1";
    return "> 12:1";
  };

  // 估算复试淘汰率
  const estimateRetestElimination = (prob: number) => {
    if (prob >= 80) return "< 10%";
    if (prob >= 60) return "10% - 20%";
    if (prob >= 40) return "20% - 35%";
    if (prob >= 20) return "35% - 50%";
    return "> 50%";
  };

  return (
    <div className="rounded-lg bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 p-4">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="h-4 w-4 text-slate-700" />
        <h4 className="text-sm font-semibold text-slate-900">风险评估</h4>
      </div>

      <div className="grid gap-3 grid-cols-1 sm:grid-cols-3">
        {/* 冲刺档风险 */}
        <div className="rounded-lg bg-white p-3 border border-red-200">
          <div className="flex items-center gap-1.5 mb-2">
            <TrendingUp className="h-3.5 w-3.5 text-red-600" />
            <span className="text-xs font-semibold text-red-900">冲刺档</span>
          </div>
          <div className="space-y-1.5">
            <div>
              <p className="text-xs text-slate-600">平均录取概率</p>
              <p className="text-sm font-bold text-red-600">{avgReachProb.toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-xs text-slate-600">预估报录比</p>
              <p className="text-sm font-semibold text-slate-900">{estimateRatio(avgReachProb)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-600">复试淘汰率</p>
              <p className="text-sm font-semibold text-slate-900">{estimateRetestElimination(avgReachProb)}</p>
            </div>
          </div>
        </div>

        {/* 稳妥档风险 */}
        <div className="rounded-lg bg-white p-3 border border-blue-200">
          <div className="flex items-center gap-1.5 mb-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-blue-600" />
            <span className="text-xs font-semibold text-blue-900">稳妥档</span>
          </div>
          <div className="space-y-1.5">
            <div>
              <p className="text-xs text-slate-600">平均录取概率</p>
              <p className="text-sm font-bold text-blue-600">{avgTargetProb.toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-xs text-slate-600">预估报录比</p>
              <p className="text-sm font-semibold text-slate-900">{estimateRatio(avgTargetProb)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-600">复试淘汰率</p>
              <p className="text-sm font-semibold text-slate-900">{estimateRetestElimination(avgTargetProb)}</p>
            </div>
          </div>
        </div>

        {/* 保底档风险 */}
        <div className="rounded-lg bg-white p-3 border border-green-200">
          <div className="flex items-center gap-1.5 mb-2">
            <Award className="h-3.5 w-3.5 text-green-600" />
            <span className="text-xs font-semibold text-green-900">保底档</span>
          </div>
          <div className="space-y-1.5">
            <div>
              <p className="text-xs text-slate-600">平均录取概率</p>
              <p className="text-sm font-bold text-green-600">{avgSafetyProb.toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-xs text-slate-600">预估报录比</p>
              <p className="text-sm font-semibold text-slate-900">{estimateRatio(avgSafetyProb)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-600">复试淘汰率</p>
              <p className="text-sm font-semibold text-slate-900">{estimateRetestElimination(avgSafetyProb)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 p-3 rounded-lg bg-amber-50 border border-amber-200">
        <div className="flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-amber-800">
            <p className="font-semibold mb-1">风险说明</p>
            <p>
              以上数据基于 AI 模型估算，仅供参考。实际报录比和复试淘汰率因院校、专业、年份而异，
              建议查阅目标院校官网或咨询学长学姐获取准确数据。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function useDaysToExam() {
  const [days, setDays] = useState(0);
  useEffect(() => {
    const now = new Date();
    const year = now.getMonth() >= 11 ? now.getFullYear() + 1 : now.getFullYear() + 1;
    const examDate = new Date(`${year}-12-21`);
    const diff = Math.ceil((examDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    setDays(diff > 0 ? diff : 0);
  }, []);
  return days;
}
