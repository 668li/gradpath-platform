"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
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
} from "lucide-react";
import { assessmentApi } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type {
  AssessmentType,
  Question,
  AssessmentSubmit,
  AssessmentResponse,
} from "@/types";

// ===== 测评元数据配置 =====
interface AssessmentMeta {
  type: AssessmentType;
  name: string;
  icon: typeof Briefcase;
  questionCount: string;
  description: string;
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
    type: "mbti",
    name: "MBTI 人格类型",
    icon: Users,
    questionCount: "40题",
    description: "16型人格测试",
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
  disc: "DISC",
};

type View = "select" | "quiz" | "result" | "history";

export default function AssessmentPage() {
  const toast = useToast();
  const [view, setView] = useState<View>("select");
  const [selectedType, setSelectedType] = useState<AssessmentType | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<AssessmentResponse | null>(null);
  const [history, setHistory] = useState<AssessmentResponse[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {ASSESSMENTS.map((a) => {
          const Icon = a.icon;
          return (
            <button
              key={a.type}
              onClick={() => startAssessment(a.type)}
              className={cn(
                "group text-left rounded-xl border border-paper-300 bg-white p-5 transition-all hover:shadow-md",
                a.theme.hoverBorder,
              )}
            >
              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl",
                    a.theme.iconBg,
                  )}
                >
                  <Icon className={cn("h-6 w-6", a.theme.iconText)} strokeWidth={1.8} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-display font-semibold text-ink-800">{a.name}</h3>
                    <ChevronRight className="h-4 w-4 text-ink-300 group-hover:text-ink-500 transition-colors" />
                  </div>
                  <p className="text-sm text-ink-500 mt-1">{a.description}</p>
                  <div className="mt-3">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
                        a.theme.chip,
                      )}
                    >
                      <ClipboardList className="h-3 w-3" />
                      {a.questionCount}
                    </span>
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

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
  const answeredCount = questions.filter((q) => answers[q.id]).length;
  const progress = questions.length ? (answeredCount / questions.length) * 100 : 0;
  // 大五采用 Likert 5 级量表，横向排列
  const isLikert = type === "big_five";

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
              已作答 {answeredCount} / {questions.length} 题
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

      {/* 题目列表（全部显示，可滚动） */}
      <div className="space-y-4">
        {questions.map((q, idx) => {
          const selected = answers[q.id];
          return (
            <div key={q.id} className="card space-y-3">
              <div className="flex items-start gap-3">
                <span
                  className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                    meta.theme.iconBg,
                    meta.theme.iconText,
                  )}
                >
                  {idx + 1}
                </span>
                <h2 className="flex-1 font-display text-base font-semibold text-ink-800 leading-relaxed pt-0.5">
                  {q.question}
                </h2>
              </div>
              <div className={cn(isLikert ? "grid grid-cols-5 gap-2" : "space-y-2")}>
                {q.options.map((opt) => {
                  const isSel = selected === opt.value;
                  if (isLikert) {
                    return (
                      <button
                        key={opt.value}
                        onClick={() => onAnswer(q.id, opt.value)}
                        title={opt.label}
                        className={cn(
                          "flex flex-col items-center gap-1 rounded-lg border p-2 transition-all",
                          isSel
                            ? cn(meta.theme.hoverBorder, "bg-paper-50 shadow-sm")
                            : "border-paper-200 bg-white hover:bg-paper-50",
                        )}
                      >
                        <span
                          className={cn(
                            "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors",
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
                      onClick={() => onAnswer(q.id, opt.value)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-xl border p-3 text-left transition-all",
                        isSel
                          ? cn(meta.theme.hoverBorder, "bg-paper-50 shadow-sm")
                          : "border-paper-300 bg-white hover:bg-paper-50",
                      )}
                    >
                      <span
                        className={cn(
                          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-colors",
                          isSel
                            ? cn(meta.theme.bar, "text-white")
                            : "bg-paper-200 text-ink-400",
                        )}
                      >
                        {isSel ? <Check className="h-3.5 w-3.5" /> : opt.value}
                      </span>
                      <span
                        className={cn(
                          "text-sm",
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
          );
        })}
      </div>

      {/* 提交 */}
      <div className="card flex flex-col sm:flex-row items-center justify-between gap-3">
        <span className="text-sm text-ink-500">
          {answeredCount < questions.length
            ? `还有 ${questions.length - answeredCount} 题未作答`
            : "全部完成，可以提交了！"}
        </span>
        <Button
          onClick={onSubmit}
          loading={submitting}
          disabled={submitting}
          className="w-full sm:w-auto"
        >
          <Sparkles className="h-4 w-4" />
          提交测评
        </Button>
      </div>
    </div>
  );
}

// ======================================================================
// 结果视图
// ======================================================================

function ResultView({
  result,
  onRetake,
  onSwitch,
}: {
  result: AssessmentResponse;
  onRetake: () => void;
  onSwitch: () => void;
}) {
  const type = result.assessment_type as AssessmentType;
  const meta = getMeta(type);
  const scores = Object.entries(result.scores).sort((a, b) => b[1] - a[1]);
  const maxScore = Math.max(...scores.map(([, v]) => v), 1);

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
          {result.result_summary}
        </p>
      </div>

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

  const typeOrder: AssessmentType[] = ["holland", "mbti", "big_five", "disc"];

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
                            {item.result_summary}
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
