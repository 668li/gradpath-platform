"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Compass, ChevronRight, RotateCcw, Sparkles, TrendingUp } from "lucide-react";
import { assessmentApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { HollandRadar } from "@/components/charts";
import type { AssessmentQuestion, AssessmentResult } from "@/types";

/** 霍兰德 6 维度全量名称表（用于补全 0 分维度） */
const HOLLAND_DIMS: { code: string; name: string }[] = [
  { code: "R", name: "实际型" },
  { code: "I", name: "研究型" },
  { code: "A", name: "艺术型" },
  { code: "S", name: "社会型" },
  { code: "E", name: "企业型" },
  { code: "C", name: "常规型" },
];

export default function AssessmentPage() {
  const toast = useToast();
  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [existingResult, setExistingResult] = useState<AssessmentResult | null>(null);
  const [mode, setMode] = useState<"intro" | "quiz" | "result">("intro");

  useEffect(() => {
    Promise.all([
      assessmentApi.getQuestions(),
      assessmentApi.getResult().catch(() => null),
    ])
      .then(([qs, prev]) => {
        setQuestions(qs);
        if (prev) setExistingResult(prev);
      })
      .catch(() => toast.push("加载失败", "error"))
      .finally(() => setLoading(false));
  }, [toast]);

  const handleAnswer = useCallback(
    (qId: string, value: string) => {
      const newAnswers = { ...answers, [qId]: value };
      setAnswers(newAnswers);

      // 自动进入下一题
      if (currentQ < questions.length - 1) {
        setTimeout(() => setCurrentQ(currentQ + 1), 300);
      } else {
        // 最后一题，自动提交
        handleSubmit(newAnswers);
      }
    },
    [answers, currentQ, questions],
  );

  const handleSubmit = async (finalAnswers: Record<string, string>) => {
    setSubmitting(true);
    try {
      const res = await assessmentApi.submit(finalAnswers);
      setResult(res);
      setMode("result");
    } catch {
      toast.push("提交失败，请重试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const startQuiz = () => {
    setAnswers({});
    setCurrentQ(0);
    setResult(null);
    setMode("quiz");
  };

  if (loading) return <LoadingState />;

  // 结果展示
  if (mode === "result" && result) {
    return <ResultView result={result} onRetake={startQuiz} />;
  }

  // 之前有结果 — 展示历史结果 + 重新测试入口
  if (mode === "intro" && existingResult) {
    return <ResultView result={existingResult} onRetake={startQuiz} />;
  }

  // 介绍页
  if (mode === "intro") {
    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
            <Compass className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
          </div>
          <h1 className="page-title">霍兰德职业兴趣测评</h1>
          <p className="text-sm text-ink-400 mt-2 leading-relaxed">
            通过 12 道情景选择题，发现你的职业兴趣类型，
            <br />
            获得个性化的职业方向推荐
          </p>
        </div>

        <div className="card space-y-4">
          <div className="grid grid-cols-3 gap-3 text-center">
            <InfoBox icon="⏱️" label="约 3 分钟" />
            <InfoBox icon="📝" label="12 道题" />
            <InfoBox icon="🎯" label="6 维度" />
          </div>

          <div className="rounded-lg bg-paper-50 p-4 space-y-2">
            <p className="text-sm font-medium text-ink-700">测评维度</p>
            <div className="grid grid-cols-2 gap-2 text-xs text-ink-500">
              <DimItem code="R" name="实际型" />
              <DimItem code="I" name="研究型" />
              <DimItem code="A" name="艺术型" />
              <DimItem code="S" name="社会型" />
              <DimItem code="E" name="企业型" />
              <DimItem code="C" name="常规型" />
            </div>
          </div>

          <Button onClick={startQuiz} className="w-full" size="md">
            <Sparkles className="h-4 w-4" />
            开始测评
          </Button>
        </div>
      </div>
    );
  }

  // 答题页
  const q = questions[currentQ];
  const progress = ((currentQ + 1) / questions.length) * 100;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* 进度条 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-ink-600">
            第 {currentQ + 1} / {questions.length} 题
          </span>
          <span className="text-xs text-ink-400">
            {Math.round(progress)}% 完成
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-paper-200">
          <div
            className="h-full rounded-full bg-brand-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* 题目 */}
      <div className="card space-y-4">
        <h2 className="font-display text-lg font-semibold text-ink-800">
          {q.question}
        </h2>
        <div className="space-y-3">
          {q.options.map((opt) => {
            const selected = answers[q.id] === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => handleAnswer(q.id, opt.value)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-all",
                  selected
                    ? "border-brand-500 bg-brand-50 shadow-brand-sm"
                    : "border-paper-300 bg-white hover:border-brand-300 hover:bg-paper-50",
                )}
              >
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold transition-colors",
                    selected
                      ? "bg-brand-600 text-white"
                      : "bg-paper-200 text-ink-400",
                  )}
                >
                  {opt.value}
                </span>
                <span
                  className={cn(
                    "text-sm",
                    selected ? "text-brand-700 font-medium" : "text-ink-700",
                  )}
                >
                  {opt.label}
                </span>
                {selected && (
                  <ChevronRight className="ml-auto h-4 w-4 text-brand-500" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* 导航 */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => currentQ > 0 && setCurrentQ(currentQ - 1)}
          disabled={currentQ === 0}
          className="text-sm text-ink-400 hover:text-ink-600 disabled:opacity-30 transition-colors"
        >
          ← 上一题
        </button>
        {submitting && (
          <span className="text-sm text-brand-600">提交中…</span>
        )}
      </div>
    </div>
  );
}

function ResultView({
  result,
  onRetake,
}: {
  result: AssessmentResult;
  onRetake: () => void;
}) {
  const maxScore = Math.max(...Object.values(result.scores), 1);

  // 补全所有 6 维度（0 分维度也要显示）
  const allDims = HOLLAND_DIMS.map((d) => ({
    ...d,
    score: result.scores[d.code] ?? 0,
  }));
  const sortedDims = [...allDims].sort((a, b) => b.score - a.score);

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* 结果头部 */}
      <div className="card text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <TrendingUp className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <p className="text-sm text-ink-400 mb-1">你的职业兴趣类型</p>
        <h1 className="font-display text-3xl font-bold text-brand-700 mb-2">
          {result.result_code}
        </h1>
        <p className="text-sm text-ink-500 max-w-md mx-auto leading-relaxed whitespace-pre-line">
          {result.result_summary}
        </p>
      </div>

      {/* 雷达图 + 维度得分 双栏 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 雷达图 */}
        <div className="card">
          <h2 className="font-display font-semibold text-ink-800 mb-2">兴趣雷达图</h2>
          <HollandRadar data={allDims} />
        </div>

        {/* 维度得分条 */}
        <div className="card space-y-3">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-display font-semibold text-ink-800">维度得分</h2>
            <span className="text-xs text-ink-400">满分 {maxScore} 分</span>
          </div>
          {sortedDims.map(({ code, name, score }) => {
            const pct = (score / maxScore) * 100;
            return (
              <div key={code}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-ink-700">
                    {code} · {name}
                  </span>
                  <span className={cn(
                    "text-sm font-medium",
                    score > 0 ? "text-brand-600" : "text-ink-300",
                  )}>
                    {score} 分
                  </span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-paper-200">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      pct > 66 ? "bg-brand-500" : pct > 33 ? "bg-brand-400" : pct > 0 ? "bg-brand-300" : "bg-transparent",
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 推荐方向 */}
      <div className="card space-y-3">
        <h2 className="font-display font-semibold text-ink-800 mb-2">推荐职业方向</h2>
        <div className="flex flex-wrap gap-2">
          {result.recommended_directions.map((dir, i) => (
            <Link
              key={i}
              href="/chat"
              className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-brand-50 px-3 py-1.5 text-sm font-medium text-brand-700 transition-colors hover:bg-brand-100"
            >
              {dir}
              <ChevronRight className="h-3 w-3" />
            </Link>
          ))}
        </div>
        <p className="text-xs text-ink-400 mt-2">
          点击方向与 AI 管家深入探讨，或前往
          <Link href="/plans" className="text-brand-600 hover:underline mx-1">
            职业规划
          </Link>
          查看相关模板
        </p>
      </div>

      {/* 操作 */}
      <div className="flex justify-center gap-3">
        <Button variant="secondary" onClick={onRetake}>
          <RotateCcw className="h-4 w-4" />
          重新测评
        </Button>
        <Link href="/profile">
          <Button variant="secondary">
            完善职业画像
          </Button>
        </Link>
      </div>
    </div>
  );
}

function InfoBox({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="rounded-lg bg-paper-50 p-3">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-xs text-ink-500">{label}</div>
    </div>
  );
}

function DimItem({ code, name }: { code: string; name: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="flex h-5 w-5 items-center justify-center rounded bg-brand-100 text-[10px] font-bold text-brand-600">
        {code}
      </span>
      <span>{name}</span>
    </div>
  );
}
