"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Briefcase,
  Users,
  Brain,
  Activity,
  Compass,
  ChevronRight,
  RotateCcw,
  Sparkles,
  TrendingUp,
  History,
  ArrowLeft,
  Check,
  ClipboardList,
  GraduationCap,
  Route,
  MapPin,
  ArrowRight,
  Zap,
  AlertTriangle,
  Target,
  Lightbulb,
  Eye,
  Timer,
} from "lucide-react";
import { assessmentApi } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { InterpretCard } from "@/components/assessment/interpret-card";
import { topRoles } from "@/components/assessment/role-match";
import { extractWarnings } from "@/components/assessment/warning-utils";
import { WarningCallout } from "@/components/assessment/warning-callout";
import type {
  AssessmentType,
  Question,
  AssessmentSubmit,
  AssessmentResponse,
  AssessmentInterpretResponse,
} from "@/types";

// ===== 测评元数据配置 =====
interface AssessmentMeta {
  type: AssessmentType;
  name: string;
  icon: typeof Briefcase;
  questionCount: string;
  description: string;
  /** true = 折叠进"更多测评"（导航收敛：主位只留霍兰德 + 大五短版） */
  more?: boolean;
  theme: {
    gradient: string;
    iconBg: string;
    iconText: string;
    hoverBorder: string;
    accent: string;
    bar: string;
    barBg: string;
    chip: string;
  };
}

const ASSESSMENTS: AssessmentMeta[] = [
  {
    type: "holland",
    name: "霍兰德职业兴趣",
    icon: Briefcase,
    questionCount: "48题",
    description: "职业兴趣6维度测评",
    theme: {
      gradient: "from-blue-50 to-blue-100",
      iconBg: "bg-blue-100",
      iconText: "text-blue-600",
      hoverBorder: "hover:border-blue-400",
      accent: "text-blue-700",
      bar: "bg-blue-500",
      barBg: "bg-blue-100",
      chip: "bg-blue-50 text-blue-700 border-blue-200",
    },
  },
  {
    type: "big_five_short",
    name: "大五短版 · 学习风格",
    icon: Timer,
    questionCount: "10题",
    description: "60 秒摸清学习节奏：5 维度各 2 题，低分辨率参考",
    theme: {
      gradient: "from-teal-50 to-teal-100",
      iconBg: "bg-teal-100",
      iconText: "text-teal-600",
      hoverBorder: "hover:border-teal-400",
      accent: "text-teal-700",
      bar: "bg-teal-500",
      barBg: "bg-teal-100",
      chip: "bg-teal-50 text-teal-700 border-teal-200",
    },
  },
  {
    type: "mbti",
    name: "MBTI 人格类型",
    icon: Users,
    questionCount: "40题",
    description: "16型人格测试",
    more: true,
    theme: {
      gradient: "from-purple-50 to-purple-100",
      iconBg: "bg-purple-100",
      iconText: "text-purple-600",
      hoverBorder: "hover:border-purple-400",
      accent: "text-purple-700",
      bar: "bg-purple-500",
      barBg: "bg-purple-100",
      chip: "bg-purple-50 text-purple-700 border-purple-200",
    },
  },
  {
    type: "big_five",
    name: "大五 OCEAN",
    icon: Brain,
    questionCount: "50题",
    description: "5维度科学人格测评",
    more: true,
    theme: {
      gradient: "from-emerald-50 to-emerald-100",
      iconBg: "bg-emerald-100",
      iconText: "text-emerald-600",
      hoverBorder: "hover:border-emerald-400",
      accent: "text-emerald-700",
      bar: "bg-emerald-500",
      barBg: "bg-emerald-100",
      chip: "bg-emerald-50 text-emerald-700 border-emerald-200",
    },
  },
  {
    type: "disc",
    name: "DISC 行为风格",
    icon: Activity,
    questionCount: "24题",
    description: "行为风格4维度测评",
    more: true,
    theme: {
      gradient: "from-orange-50 to-orange-100",
      iconBg: "bg-orange-100",
      iconText: "text-orange-600",
      hoverBorder: "hover:border-orange-400",
      accent: "text-orange-700",
      bar: "bg-orange-500",
      barBg: "bg-orange-100",
      chip: "bg-orange-50 text-orange-700 border-orange-200",
    },
  },
];

function getMeta(type: AssessmentType): AssessmentMeta {
  return ASSESSMENTS.find((a) => a.type === type) ?? ASSESSMENTS[0];
}

const TYPE_NAMES: Record<AssessmentType, string> = {
  holland: "霍兰德",
  mbti: "MBTI",
  big_five: "大五OCEAN",
  big_five_short: "大五短版",
  disc: "DISC",
};

/** 测评选择卡（主位与"更多测评"折叠区共用） */
function AssessmentCard({
  meta,
  disabled,
  onStart,
}: {
  meta: AssessmentMeta;
  disabled: boolean;
  onStart: () => void;
}) {
  const Icon = meta.icon;
  return (
    <button
      onClick={onStart}
      disabled={disabled}
      className={cn(
        "group text-left rounded-xl border border-paper-300 bg-white p-5 transition-all hover:shadow-md disabled:opacity-60",
        meta.theme.hoverBorder,
      )}
    >
      <div className="flex items-start gap-4">
        <div
          className={cn(
            "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl",
            meta.theme.iconBg,
          )}
        >
          <Icon className={cn("h-6 w-6", meta.theme.iconText)} strokeWidth={1.8} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-display font-semibold text-ink-800">{meta.name}</h3>
            <ChevronRight className="h-4 w-4 text-ink-300 group-hover:text-ink-500 transition-colors" />
          </div>
          <p className="text-sm text-ink-500 mt-1">{meta.description}</p>
          <div className="mt-3">
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
                meta.theme.chip,
              )}
            >
              <ClipboardList className="h-3 w-3" />
              {meta.questionCount}
            </span>
          </div>
        </div>
      </div>
    </button>
  );
}

// ===== 霍兰德 → 岗位匹配矩阵（灵感：职向"所以呢"转化）=====
interface HollandRole {
  role: string;
  codes: readonly string[];
  why: string;
  challenge: string;
}

const HOLLAND_ROLE_MATRIX: readonly HollandRole[] = [
  {
    role: "软件工程师",
    codes: ["RIC", "RSC", "RAS"],
    why: "你的现实型+研究型特质契合编码与系统设计所需的动手解题能力",
    challenge: "需要主动补足团队协作与跨部门沟通能力",
  },
  {
    role: "产品经理",
    codes: ["ESA", "EAS", "ECS"],
    why: "你的企业型+社会型特质匹配产品规划与跨团队推动",
    challenge: "需要在技术深度与数据决策间保持平衡",
  },
  {
    role: "数据分析师",
    codes: ["ISC", "IEC", "IAC"],
    why: "你的研究型+常规型特质适合数据建模与规律挖掘",
    challenge: "需要把分析结论转化为业务可执行的决策建议",
  },
  {
    role: "UI设计师",
    codes: ["AES", "AIS", "AER"],
    why: "你的艺术型+企业型特质契合视觉表达与体验创新",
    challenge: "需要兼顾商业约束与用户研究的客观性",
  },
  {
    role: "考研科研",
    codes: ["ISR", "IAR", "IES"],
    why: "你的研究型主导特质高度契合学术深耕与论文写作",
    challenge: "需要耐受长期不确定性并主动构建学术人脉",
  },
  {
    role: "公务员",
    codes: ["SCE", "SEC", "CSE"],
    why: "你的社会型+常规型特质适配公共服务与规则执行",
    challenge: "需要在稳定环境中主动寻找成长与价值突破口",
  },
  {
    role: "市场营销",
    codes: ["ESA", "EAS", "SEC"],
    why: "你的企业型+艺术型特质契合品牌传播与用户触达",
    challenge: "需要建立数据驱动的复盘习惯避免纯创意决策",
  },
  {
    role: "人力资源",
    codes: ["SCE", "SEC", "SAE"],
    why: "你的社会型+常规型特质匹配组织发展与员工关系",
    challenge: "需要在同理心与制度刚性之间保持平衡",
  },
  {
    role: "财务分析",
    codes: ["CSE", "CES", "ISC"],
    why: "你的常规型+研究型特质契合数据严谨与风险控制",
    challenge: "需要主动提升业务洞察与跨部门影响力",
  },
  {
    role: "教师",
    codes: ["SAE", "SEC", "SIA"],
    why: "你的社会型+艺术型特质适配知识传递与启发引导",
    challenge: "需要在长期重复教学中保持创新与耐心",
  },
];

// 匹配度计算：交集维度 / 3 * 80 + 顺序匹配 / 3 * 20（满分 100）
function calculateHollandMatch(
  userCode: string,
  roleCodes: readonly string[],
): { match: number; bestCode: string } {
  const userTop3 = userCode.slice(0, 3).toUpperCase().split("");
  if (userTop3.length < 3) return { match: 0, bestCode: roleCodes[0] ?? "" };
  let bestMatch = 0;
  let bestCode = roleCodes[0] ?? "";
  for (const code of roleCodes) {
    const roleTop3 = code.toUpperCase().split("");
    const intersection = userTop3.filter((c) => roleTop3.includes(c)).length;
    const positionMatches = userTop3.filter((c, i) => roleTop3[i] === c).length;
    const score = (intersection / 3) * 80 + (positionMatches / 3) * 20;
    if (score > bestMatch) {
      bestMatch = score;
      bestCode = code;
    }
  }
  return { match: Math.round(bestMatch), bestCode };
}

// ===== 社会赞许性检测（灵感：奕言测谎机制轻量化）=====
const STRONG_AGREE_WORDS = ["非常", "完全", "总是", "极其", "强烈", "完全符合", "非常同意", "非常符合"];

function detectSocialDesirability(
  questions: Question[],
  answers: Record<string, string>,
): { show: boolean; ratio: number; strongCount: number; total: number } {
  let total = 0;
  let strongCount = 0;
  for (const q of questions) {
    const val = answers[q.id];
    if (!val) continue;
    const opt = q.options.find((o) => o.value === val);
    if (!opt) continue;
    total++;
    if (STRONG_AGREE_WORDS.some((w) => opt.label.includes(w))) {
      strongCount++;
    }
  }
  const ratio = total > 0 ? strongCount / total : 0;
  return { show: total >= 5 && ratio > 0.8, ratio, strongCount, total };
}

type View = "select" | "quiz" | "result" | "history";

export default function AssessmentPage() {
  const toast = useToast();
  const searchParams = useSearchParams();
  const [view, setView] = useState<View>("select");
  const [selectedType, setSelectedType] = useState<AssessmentType | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<AssessmentResponse | null>(null);
  const [history, setHistory] = useState<AssessmentResponse[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  // 防止 URL 参数重复触发自动启动
  const quickStartedRef = useRef(false);

  // 加载历史记录
  useEffect(() => {
    assessmentApi
      .getHistory()
      .then(setHistory)
      .catch(() => {
        // 静默失败
      })
      .finally(() => setHistoryLoading(false));
  }, []);

  const startAssessment = useCallback(
    async (type: AssessmentType) => {
      setLoading(true);
      setAnswers({});
      setResult(null);
      try {
        const qs = await assessmentApi.getQuestions(type);
        setQuestions(qs);
        setSelectedType(type);
        setView("quiz");
      } catch {
        toast.push("题目加载失败，请重试", "error");
      } finally {
        setLoading(false);
      }
    },
    [toast],
  );

  // 支持 /assessment?type=holland 快速启动（灵感：霍兰德方舟极速测评）
  useEffect(() => {
    const typeParam = searchParams.get("type");
    if (
      typeParam === "holland" &&
      view === "select" &&
      !quickStartedRef.current &&
      !loading
    ) {
      quickStartedRef.current = true;
      startAssessment("holland");
    }
  }, [searchParams, view, loading, startAssessment]);

  const handleAnswer = useCallback((qId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [qId]: value }));
  }, []);

  const handleSubmit = async () => {
    if (!selectedType) return;
    const unanswered = questions.filter((q) => !answers[q.id]).length;
    if (unanswered > 0) {
      toast.push(`还有 ${unanswered} 道题未作答`, "error");
      return;
    }
    setSubmitting(true);
    try {
      const body: AssessmentSubmit = {
        assessment_type: selectedType,
        answers,
      };
      const res = await assessmentApi.submit(body);
      setResult(res);
      setView("result");
      // 刷新历史记录
      assessmentApi
        .getHistory()
        .then(setHistory)
        .catch(() => {});
      toast.push("测评完成！", "success");
    } catch {
      toast.push("提交失败，请重试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const retake = () => {
    setAnswers({});
    setResult(null);
    setView("quiz");
  };

  const switchAssessment = () => {
    setView("select");
    setSelectedType(null);
    setQuestions([]);
    setAnswers({});
    setResult(null);
  };

  // ---- 渲染分支 ----
  if (loading) return <LoadingState text="加载题目中…" />;

  if (view === "quiz" && selectedType) {
    return (
      <QuizView
        type={selectedType}
        questions={questions}
        answers={answers}
        onAnswer={handleAnswer}
        onSubmit={handleSubmit}
        onBack={switchAssessment}
        submitting={submitting}
      />
    );
  }

  if (view === "result" && result) {
    return (
      <ResultView
        result={result}
        questions={questions}
        answers={answers}
        onRetake={retake}
        onSwitch={switchAssessment}
      />
    );
  }

  if (view === "history") {
    return (
      <HistoryView
        history={history}
        loading={historyLoading}
        onBack={switchAssessment}
      />
    );
  }

  // 选择页
  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <Compass className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">职业测评</h1>
        <p className="text-sm text-ink-400 mt-2 leading-relaxed">
          选择一项测评，深入了解你的职业兴趣、人格特质与行为风格
        </p>
      </div>

      {/* 极速测评提示（灵感：霍兰德方舟 3-5 分钟极速测评）*/}
      <div className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 p-4">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
            <Zap className="h-4 w-4" />
          </span>
          <div className="flex-1 min-w-0 space-y-2">
            <h3 className="font-display text-sm font-semibold text-ink-800">
              时间紧张？先做极速测评
            </h3>
            <p className="text-xs text-ink-500 leading-relaxed">
              完整测评约 15-20 分钟，可获得最准确结果。如果时间紧张，可以先做霍兰德部分（3-5 分钟），后续再补充其他测评。
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              <Button
                size="sm"
                variant="primary"
                onClick={() => startAssessment("holland")}
                loading={loading}
                disabled={loading}
              >
                <Zap className="h-3.5 w-3.5" />
                快速开始（仅霍兰德）
              </Button>
              <Link
                href="/assessment?type=holland"
                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-50"
              >
                复制极速链接
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* 主位：霍兰德 + 大五短版（导航收敛——旧三套折叠进"更多测评"） */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {ASSESSMENTS.filter((a) => !a.more).map((a) => (
          <AssessmentCard
            key={a.type}
            meta={a}
            disabled={loading}
            onStart={() => startAssessment(a.type)}
          />
        ))}
      </div>

      <details className="group rounded-xl border border-paper-300 bg-white/60">
        <summary className="flex cursor-pointer select-none items-center justify-between px-5 py-3.5 text-sm font-medium text-ink-600 hover:text-ink-800">
          <span>
            更多测评（
            {ASSESSMENTS.filter((a) => a.more)
              .map((a) => TYPE_NAMES[a.type])
              .join(" / ")}
            ）
          </span>
          <ChevronRight className="h-4 w-4 transition-transform group-open:rotate-90" />
        </summary>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 px-5 pb-5">
          {ASSESSMENTS.filter((a) => a.more).map((a) => (
            <AssessmentCard
              key={a.type}
              meta={a}
              disabled={loading}
              onStart={() => startAssessment(a.type)}
            />
          ))}
        </div>
      </details>

      {/* 历史记录入口 */}
      {history.length > 0 && (
        <div className="text-center pt-2">
          <Button variant="ghost" size="sm" onClick={() => setView("history")}>
            <History className="h-4 w-4" />
            查看测评历史（{history.length}）
          </Button>
        </div>
      )}
    </div>
  );
}

// ======================================================================
// 答题视图
// ======================================================================

function QuizView({
  type,
  questions,
  answers,
  onAnswer,
  onSubmit,
  onBack,
  submitting,
}: {
  type: AssessmentType;
  questions: Question[];
  answers: Record<string, string>;
  onAnswer: (qId: string, value: string) => void;
  onSubmit: () => void;
  onBack: () => void;
  submitting: boolean;
}) {
  const meta = getMeta(type);
  const [currentIdx, setCurrentIdx] = useState(0);
  const answeredCount = questions.filter((q) => answers[q.id]).length;
  const progress = questions.length ? (answeredCount / questions.length) * 100 : 0;
  // 大五采用 Likert 5 级量表，横向排列
  const isLikert = type === "big_five" || type === "big_five_short";

  const currentQuestion = questions[currentIdx];
  const isLast = currentIdx === questions.length - 1;
  const allAnswered = answeredCount === questions.length;

  // 自适应提示：检测连续相同选项（灵感：Placify 自适应出题的轻量化变体）
  const maxConsecutiveSame = (() => {
    let maxStreak = 0;
    let currentStreak = 0;
    let currentValue: string | null = null;
    for (const q of questions) {
      const v = answers[q.id];
      if (!v) {
        currentStreak = 0;
        currentValue = null;
        continue;
      }
      if (v === currentValue) {
        currentStreak++;
      } else {
        currentStreak = 1;
        currentValue = v;
      }
      if (currentStreak > maxStreak) maxStreak = currentStreak;
    }
    return maxStreak;
  })();
  const showStreakHint = maxConsecutiveSame >= 5;

  // 作答后短暂高亮，然后自动跳转下一题
  const handleSelect = (qId: string, value: string) => {
    onAnswer(qId, value);
    if (!isLast) {
      setTimeout(() => setCurrentIdx((i) => Math.min(i + 1, questions.length - 1)), 350);
    }
  };

  // 找到第一个未作答的题目（用于"检查未答题"跳转）
  const jumpToFirstUnanswered = () => {
    const idx = questions.findIndex((q) => !answers[q.id]);
    if (idx >= 0) setCurrentIdx(idx);
  };

  if (!currentQuestion) return null;
  const selected = answers[currentQuestion.id];

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* 顶部导航 + 进度 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1 text-sm text-ink-400 hover:text-ink-600 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            返回选择
          </button>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
              meta.theme.chip,
            )}
          >
            {meta.name}
          </span>
        </div>
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-ink-600">
              第 {currentIdx + 1} / {questions.length} 题 · 已作答 {answeredCount} 题
            </span>
            <span className="text-xs text-ink-400">{Math.round(progress)}% 完成</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-paper-200">
            <div
              className={cn("h-full rounded-full transition-all duration-300", meta.theme.bar)}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* 当前题目（一题一页） */}
      <div key={currentQuestion.id} className="card space-y-4 py-8 animate-fade-in">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold",
              meta.theme.iconBg,
              meta.theme.iconText,
            )}
          >
            {currentIdx + 1}
          </span>
          <h2 className="flex-1 font-display text-lg font-semibold text-ink-800 leading-relaxed pt-1">
            {currentQuestion.question}
          </h2>
        </div>
        <div className={cn(isLikert ? "grid grid-cols-5 gap-2" : "space-y-2")}>
          {currentQuestion.options.map((opt) => {
            const isSel = selected === opt.value;
            if (isLikert) {
              return (
                <button
                  key={opt.value}
                  onClick={() => handleSelect(currentQuestion.id, opt.value)}
                  title={opt.label}
                  className={cn(
                    "flex flex-col items-center gap-1 rounded-lg border p-3 transition-all",
                    isSel
                      ? cn(meta.theme.hoverBorder, "bg-paper-50 shadow-sm")
                      : "border-paper-200 bg-white hover:bg-paper-50",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold transition-colors",
                      isSel
                        ? cn(meta.theme.bar, "text-white")
                        : "bg-paper-200 text-ink-400",
                    )}
                  >
                    {opt.value}
                  </span>
                  <span className="text-[10px] text-ink-500 text-center leading-tight line-clamp-2">
                    {opt.label}
                  </span>
                </button>
              );
            }
            return (
              <button
                key={opt.value}
                onClick={() => handleSelect(currentQuestion.id, opt.value)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-all",
                  isSel
                    ? cn(meta.theme.hoverBorder, "bg-paper-50 shadow-sm")
                    : "border-paper-300 bg-white hover:bg-paper-50",
                )}
              >
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold transition-colors",
                    isSel
                      ? cn(meta.theme.bar, "text-white")
                      : "bg-paper-200 text-ink-400",
                  )}
                >
                  {isSel ? <Check className="h-4 w-4" /> : opt.value}
                </span>
                <span
                  className={cn(
                    "text-base",
                    isSel ? cn(meta.theme.accent, "font-medium") : "text-ink-700",
                  )}
                >
                  {opt.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 自适应提示：连续相同选项（底部小字，不打断流程）*/}
      {showStreakHint && (
        <div className="flex items-center gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
          <Lightbulb className="h-3.5 w-3.5 shrink-0" />
          <span>
            你连续选择了相同选项（{maxConsecutiveSame} 题），建议偶尔停下来想想"大多数情况"下你的真实反应
          </span>
        </div>
      )}

      {/* 导航 + 提交 */}
      <div className="card flex items-center justify-between gap-3">
        <Button
          variant="secondary"
          onClick={() => setCurrentIdx((i) => Math.max(i - 1, 0))}
          disabled={currentIdx === 0}
        >
          <ArrowLeft className="h-4 w-4" />
          上一题
        </Button>

        {allAnswered ? (
          <Button onClick={onSubmit} loading={submitting} disabled={submitting}>
            <Sparkles className="h-4 w-4" />
            提交测评
          </Button>
        ) : isLast ? (
          <Button variant="secondary" onClick={jumpToFirstUnanswered}>
            <AlertTriangle className="h-4 w-4" />
            还有 {questions.length - answeredCount} 题未答，去检查
          </Button>
        ) : (
          <Button
            variant="secondary"
            onClick={() => setCurrentIdx((i) => Math.min(i + 1, questions.length - 1))}
          >
            下一题
            <ArrowRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}

// ======================================================================
// 结果视图
// ======================================================================

function ResultView({
  result,
  questions,
  answers,
  onRetake,
  onSwitch,
}: {
  result: AssessmentResponse;
  questions: Question[];
  answers: Record<string, string>;
  onRetake: () => void;
  onSwitch: () => void;
}) {
  const type = result.assessment_type as AssessmentType;
  const meta = getMeta(type);
  const scores = Object.entries(result.scores).sort((a, b) => b[1] - a[1]);
  const maxScore = Math.max(...scores.map(([, v]) => v), 1);

  // 社会赞许性检测（灵感：奕言测谎机制轻量化）
  const socialDesirability = detectSocialDesirability(questions, answers);

  // 护城河：结果页挂载即拉「测评 × 专有数据 → 专属路径」解读
  const [interpret, setInterpret] = useState<AssessmentInterpretResponse | null>(null);
  const [interpretLoading, setInterpretLoading] = useState(true);
  const [interpretError, setInterpretError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    assessmentApi
      .interpret()
      .then((d) => {
        if (!cancelled) setInterpret(d);
      })
      .catch((e: unknown) => {
        if (!cancelled) setInterpretError(e instanceof Error ? e.message : "生成失败");
      })
      .finally(() => {
        if (!cancelled) setInterpretLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // 个人档案目标方向（考研/考公）→ 职业适配榜单的身份加成依据
  const targetDirection =
    (interpret?.profile as { target_direction?: string | null } | null)?.target_direction ?? null;

  // 职业适配度：仅霍兰德测评计算（灵感：职向"所以呢"转化）
  const isHolland = type === "holland";
  const roleMatches = isHolland
    ? topRoles(
        HOLLAND_ROLE_MATRIX.map((r) => {
          const { match, bestCode } = calculateHollandMatch(result.result_code, r.codes);
          return { ...r, match, bestCode };
        }),
        targetDirection,
      )
    : [];

  // 信度/完整性警示：后端把【作答提示】折在 result_summary 末尾，这里拆出来亮成警示卡
  const { cleanSummary, warnings: answerWarnings } = extractWarnings(result.result_summary);

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* 结果头部 - 渐变背景 */}
      <div
        className={cn(
          "rounded-2xl bg-gradient-to-br p-6 text-center border border-paper-200",
          meta.theme.gradient,
        )}
      >
        <div
          className={cn(
            "inline-flex h-14 w-14 items-center justify-center rounded-2xl mb-3",
            meta.theme.iconBg,
          )}
        >
          <TrendingUp className={cn("h-7 w-7", meta.theme.iconText)} strokeWidth={1.8} />
        </div>
        <p className="text-sm text-ink-500 mb-1">你的测评结果</p>
        <h1 className={cn("font-display text-3xl font-bold mb-3", meta.theme.accent)}>
          {result.result_code}
        </h1>
        <p className="text-sm text-ink-600 max-w-xl mx-auto leading-relaxed whitespace-pre-line">
          {cleanSummary}
        </p>
      </div>

      <WarningCallout warnings={answerWarnings} />

      {/* 维度得分（柱状图） */}
      <div className="card space-y-3">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-display font-semibold text-ink-800">维度得分</h2>
          <span className="text-xs text-ink-400">{TYPE_NAMES[type]} 测评</span>
        </div>
        {scores.length > 0 ? (
          scores.map(([dim, score]) => {
            const pct = (score / maxScore) * 100;
            return (
              <div key={dim}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-ink-700">{dim}</span>
                  <span className={cn("text-sm font-semibold", meta.theme.accent)}>
                    {score} 分
                  </span>
                </div>
                <div className={cn("h-2.5 w-full overflow-hidden rounded-full", meta.theme.barBg)}>
                  <div
                    className={cn("h-full rounded-full transition-all duration-500", meta.theme.bar)}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })
        ) : (
          <p className="text-sm text-ink-400">暂无得分数据</p>
        )}
      </div>

      {/* 推荐方向 */}
      <div className="card space-y-3">
        <h2 className="font-display font-semibold text-ink-800 mb-1">推荐职业方向</h2>
        {result.recommended_directions.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {result.recommended_directions.map((dir, i) => (
              <Link
                key={`dir-${i}`}
                href="/chat"
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors hover:opacity-80",
                  meta.theme.chip,
                )}
              >
                {dir}
                <ChevronRight className="h-3 w-3" />
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-ink-400">暂无推荐方向</p>
        )}
        <p className="text-xs text-ink-400 mt-2">
          点击方向与 AI 管家深入探讨，或前往
          <Link href="/plans" className={cn("hover:underline mx-1", meta.theme.accent)}>
            职业规划
          </Link>
          查看相关模板
        </p>
      </div>

      {/* 测评 × 专有数据 → 专属路径（护城河本体） */}
      <InterpretCard data={interpret} loading={interpretLoading} error={interpretError} />

      {/* 职业适配度："所以呢"转化（灵感：职向）—— 仅霍兰德测评显示 */}
      {isHolland && roleMatches.length > 0 && (
        <div className="card space-y-3">
          <div className="flex items-center gap-2 mb-1">
            <Target className={cn("h-4 w-4", meta.theme.iconText)} />
            <h2 className="font-display font-semibold text-ink-800">职业适配度 Top 5</h2>
            <span className="text-xs text-ink-400">基于霍兰德代码 {result.result_code.slice(0, 3)}</span>
          </div>
          <p className="text-xs text-ink-500 -mt-1">
            测评标签不是终点——下面是你的兴趣代码与真实岗位的匹配度，点击深入模拟。
          </p>
          <div className="space-y-2.5">
            {roleMatches.map((r, idx) => {
              const matchColor =
                r.match >= 80
                  ? "bg-emerald-500"
                  : r.match >= 60
                    ? "bg-blue-500"
                    : r.match >= 40
                      ? "bg-amber-500"
                      : "bg-ink-300";
              return (
                <Link
                  key={r.role}
                  href={`/career-simulator?from=assessment&role=${encodeURIComponent(r.role)}`}
                  className="group block rounded-xl border border-paper-200 bg-white p-3.5 transition-all hover:border-brand-300 hover:shadow-sm"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span
                        className={cn(
                          "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                          meta.theme.iconBg,
                          meta.theme.iconText,
                        )}
                      >
                        {idx + 1}
                      </span>
                      <span className="font-display font-semibold text-ink-800 text-sm">
                        {r.role}
                      </span>
                      <span className="text-[10px] text-ink-400 font-mono">
                        {r.bestCode}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <div className="hidden sm:block w-20 h-1.5 rounded-full bg-paper-200 overflow-hidden">
                        <div
                          className={cn("h-full rounded-full transition-all", matchColor)}
                          style={{ width: `${r.match}%` }}
                        />
                      </div>
                      <span
                        className={cn(
                          "text-sm font-bold tabular-nums",
                          r.match >= 80
                            ? "text-emerald-600"
                            : r.match >= 60
                              ? "text-blue-600"
                              : r.match >= 40
                                ? "text-amber-600"
                                : "text-ink-400",
                        )}
                      >
                        {r.match}%
                      </span>
                      <ArrowRight className="h-3.5 w-3.5 text-ink-300 group-hover:text-brand-600 transition-colors" />
                    </div>
                  </div>
                  <div className="mt-2 pl-9 space-y-1">
                    <p className="text-xs text-ink-600 leading-relaxed">
                      <span className={cn("font-medium", meta.theme.accent)}>为什么匹配：</span>
                      {r.why}
                    </p>
                    <p className="text-xs text-ink-500 leading-relaxed">
                      <span className="font-medium text-amber-600">可能挑战：</span>
                      {r.challenge}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* 回答一致性分析（灵感：奕言测谎机制轻量化）*/}
      {socialDesirability.show && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Eye className="h-4 w-4 text-amber-600" />
            <h3 className="font-display text-sm font-semibold text-ink-800">回答一致性分析</h3>
          </div>
          <p className="text-xs text-ink-600 leading-relaxed">
            你对积极特质的问题倾向于全选"非常同意/完全符合"（{socialDesirability.strongCount}/
            {socialDesirability.total} 题，{Math.round(socialDesirability.ratio * 100)}%），这可能在职业匹配上产生偏差。
            建议未来回答时更关注真实状态而非理想状态。
          </p>
          <div className="flex items-center gap-1.5 pt-1">
            <AlertTriangle className="h-3 w-3 text-amber-500" />
            <span className="text-[11px] text-amber-700">
              提示：测评结果仅作参考，真实自我认知需要结合实际行为观察
            </span>
          </div>
        </div>
      )}

      {/* 下一步引导：把测评结果转化为行动 */}
      <div className="card space-y-3 border-brand-200 bg-gradient-to-br from-brand-50/60 to-paper-50">
        <div className="flex items-center gap-2">
          <Route className="h-4 w-4 text-brand-600" />
          <h2 className="font-display font-semibold text-ink-800">基于测评结果的下一步</h2>
        </div>
        <p className="text-xs text-ink-500 -mt-1">
          测评只是起点。把你的兴趣与特质代入真实职业路径，或对照能力地图找到差距。
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Link
            href="/career-simulator?from=assessment"
            className="group flex items-center gap-3 rounded-xl border border-paper-200 bg-white p-3.5 transition-all hover:border-brand-300 hover:shadow-sm"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <GraduationCap className="h-4 w-4" />
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-ink-800">模拟职业路径</p>
              <p className="text-xs text-ink-400 mt-0.5 line-clamp-1">
                把结果代入考研/就业/考公的真实发展轨迹
              </p>
            </div>
            <ArrowRight className="h-4 w-4 text-ink-300 group-hover:text-brand-600 transition-colors shrink-0" />
          </Link>
          <Link
            href="/skills?from=assessment"
            className="group flex items-center gap-3 rounded-xl border border-paper-200 bg-white p-3.5 transition-all hover:border-brand-300 hover:shadow-sm"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <MapPin className="h-4 w-4" />
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-ink-800">查看你的能力地图</p>
              <p className="text-xs text-ink-400 mt-0.5 line-clamp-1">
                对照目标职业的能力要求，找到差距
              </p>
            </div>
            <ArrowRight className="h-4 w-4 text-ink-300 group-hover:text-brand-600 transition-colors shrink-0" />
          </Link>
        </div>
      </div>

      {/* 操作 */}
      <div className="flex flex-wrap justify-center gap-3">
        <Button variant="secondary" onClick={onRetake}>
          <RotateCcw className="h-4 w-4" />
          重新测试
        </Button>
        <Button variant="primary" onClick={onSwitch}>
          <Compass className="h-4 w-4" />
          换一个测评
        </Button>
      </div>
    </div>
  );
}

// ======================================================================
// 历史记录视图
// ======================================================================

function HistoryView({
  history,
  loading,
  onBack,
}: {
  history: AssessmentResponse[];
  loading: boolean;
  onBack: () => void;
}) {
  // 按测评类型分组
  const grouped = history.reduce(
    (acc, item) => {
      const t = (item.assessment_type as AssessmentType) || "holland";
      if (!acc[t]) acc[t] = [];
      acc[t].push(item);
      return acc;
    },
    {} as Record<AssessmentType, AssessmentResponse[]>,
  );

  const typeOrder: AssessmentType[] = ["holland", "big_five_short", "mbti", "big_five", "disc"];

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1 text-sm text-ink-400 hover:text-ink-600 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          返回选择
        </button>
        <h1 className="font-display text-lg font-semibold text-ink-800">测评历史</h1>
      </div>

      {loading ? (
        <LoadingState />
      ) : history.length === 0 ? (
        <div className="card text-center py-10 text-ink-400">
          <History className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p>暂无测评记录</p>
        </div>
      ) : (
        <div className="space-y-6">
          {typeOrder.map((t) => {
            const items = grouped[t];
            if (!items || items.length === 0) return null;
            const meta = getMeta(t);
            const Icon = meta.icon;
            return (
              <div key={t} className="space-y-3">
                <div className="flex items-center gap-2">
                  <Icon className={cn("h-4 w-4", meta.theme.iconText)} />
                  <h2 className="font-display font-semibold text-ink-800">{meta.name}</h2>
                  <span className="text-xs text-ink-400">（{items.length} 条）</span>
                </div>
                <div className="space-y-2">
                  {items
                    .slice()
                    .sort(
                      (a, b) =>
                        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
                    )
                    .map((item) => (
                      <div
                        key={item.id}
                        className="card flex items-center justify-between gap-3 py-3"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={cn("font-display font-bold", meta.theme.accent)}>
                              {item.result_code}
                            </span>
                            <span
                              className={cn(
                                "inline-flex items-center rounded-full border px-2 py-0.5 text-xs",
                                meta.theme.chip,
                              )}
                            >
                              {TYPE_NAMES[t]}
                            </span>
                          </div>
                          <p className="text-xs text-ink-400 mt-1 line-clamp-1">
                            {extractWarnings(item.result_summary).cleanSummary}
                          </p>
                        </div>
                        <span className="text-xs text-ink-400 shrink-0">
                          {formatDate(item.created_at)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
