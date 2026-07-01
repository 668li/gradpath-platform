"use client";

import { useEffect, useState, useCallback } from "react";
import { PieChart, Sparkles, RotateCcw } from "lucide-react";
import { lifeWheelApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Button, Textarea } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { LifeWheelRadar } from "@/components/charts";
import type { LifeWheelDimension, LifeWheelSnapshot } from "@/types";

/** 维度默认定义（API 不可用时兜底） */
const DEFAULT_DIMENSIONS: LifeWheelDimension[] = [
  { key: "career", name: "职业发展", desc: "工作满意度、职业成长与方向感" },
  { key: "finance", name: "财务状况", desc: "收入、储蓄与财务安全感" },
  { key: "health", name: "身体健康", desc: "体能、睡眠、饮食与整体健康" },
  { key: "relationships", name: "人际关系", desc: "家人、朋友与亲密关系质量" },
  { key: "growth", name: "个人成长", desc: "学习、自我提升与心智发展" },
  { key: "fun", name: "休闲娱乐", desc: "兴趣爱好、放松与生活乐趣" },
  { key: "environment", name: "居住环境", desc: "生活空间、安全感与舒适度" },
  { key: "spirituality", name: "精神生活", desc: "意义感、内心平静与价值观契合" },
];

/** 维度图标（emoji）映射 */
const DIM_ICONS: Record<string, string> = {
  career: "💼",
  finance: "💰",
  health: "🏃",
  relationships: "👥",
  growth: "📚",
  fun: "🎨",
  environment: "🏠",
  spirituality: "🧘",
};

type Mode = "intro" | "assessment" | "result";

/** 根据分数给出等级标签与配色 */
function scoreLevel(score: number): { label: string; color: string } {
  if (score >= 8) return { label: "优秀", color: "text-brand-600" };
  if (score >= 6) return { label: "良好", color: "text-brand-500" };
  if (score >= 4) return { label: "一般", color: "text-amber-600" };
  return { label: "待提升", color: "text-red-500" };
}

/** 将 ISO 日期格式化为「2024年1月15日」 */
function formatDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
}

export default function LifeWheelPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [dimensions, setDimensions] = useState<LifeWheelDimension[]>(
    DEFAULT_DIMENSIONS,
  );
  const [mode, setMode] = useState<Mode>("intro");
  const [scores, setScores] = useState<Record<string, number>>({});
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [snapshot, setSnapshot] = useState<LifeWheelSnapshot | null>(null);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [history, setHistory] = useState<LifeWheelSnapshot[]>([]);

  /** 取得 AI 分析：快照已带分析则直接用，否则调接口生成 */
  const ensureAnalysis = useCallback(
    async (snap: LifeWheelSnapshot) => {
      if (snap.ai_analysis) {
        setAnalysis(snap.ai_analysis);
        setAnalyzing(false);
        return;
      }
      setAnalyzing(true);
      setAnalysis(null);
      try {
        const res = await lifeWheelApi.analyze(snap.id);
        setAnalysis(res.ai_analysis);
      } catch {
        toast.push("AI 分析生成失败，可稍后重试", "error");
      } finally {
        setAnalyzing(false);
      }
    },
    [toast],
  );

  useEffect(() => {
    let active = true;
    Promise.all([
      lifeWheelApi.getDimensions().catch(() => DEFAULT_DIMENSIONS),
      lifeWheelApi.getLatest().catch(() => null),
      lifeWheelApi.getHistory().catch(() => []),
    ])
      .then(([dims, latest, hist]) => {
        if (!active) return;
        setDimensions(dims && dims.length ? dims : DEFAULT_DIMENSIONS);
        setHistory(hist || []);
        if (latest) {
          setSnapshot(latest);
          setMode("result");
          ensureAnalysis(latest);
        }
      })
      .catch(() => toast.push("加载失败", "error"))
      .finally(() => setLoading(false));
    return () => {
      active = false;
    };
  }, [toast, ensureAnalysis]);

  const startAssessment = useCallback(() => {
    const init: Record<string, number> = {};
    dimensions.forEach((d) => {
      init[d.key] = 5;
    });
    setScores(init);
    setTouched(new Set());
    setNotes("");
    setMode("assessment");
  }, [dimensions]);

  const handleScoreChange = useCallback((key: string, value: number) => {
    setScores((prev) => ({ ...prev, [key]: value }));
    setTouched((prev) => {
      const next = new Set(prev);
      next.add(key);
      return next;
    });
  }, []);

  const handleBack = () => {
    if (snapshot) setMode("result");
    else setMode("intro");
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const res = await lifeWheelApi.submit({
        scores,
        notes: notes.trim() || null,
      });
      setSnapshot(res);
      setMode("result");
      setAnalysis(null);
      ensureAnalysis(res);
      // 刷新历史，把新快照纳入轨迹
      lifeWheelApi.getHistory().then(setHistory).catch(() => {});
    } catch {
      toast.push("提交失败，请重试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState />;

  // 结果展示
  if (mode === "result" && snapshot) {
    return (
      <ResultView
        snapshot={snapshot}
        dimensions={dimensions}
        analysis={analysis}
        analyzing={analyzing}
        history={history}
        onRetake={startAssessment}
      />
    );
  }

  // 介绍页
  if (mode === "intro") {
    return (
      <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
            <PieChart className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
          </div>
          <h1 className="page-title">人生平衡轮</h1>
          <p className="text-sm text-ink-400 mt-2 leading-relaxed">
            从 8 个维度审视当下生活的满意程度，
            <br />
            用雷达图看见失衡之处，借 AI 视角获得平衡建议
          </p>
        </div>

        <div className="card space-y-4">
          <div className="grid grid-cols-3 gap-3 text-center">
            <InfoBox icon="⏱️" label="约 2 分钟" />
            <InfoBox icon="🎚️" label="8 维度" />
            <InfoBox icon="🤖" label="AI 解读" />
          </div>

          <div className="rounded-lg bg-paper-50 p-4 space-y-3">
            <p className="text-sm font-medium text-ink-700">八大生活维度</p>
            <div className="grid grid-cols-2 gap-3">
              {dimensions.map((d) => (
                <DimensionCard key={d.key} dim={d} />
              ))}
            </div>
          </div>

          <Button onClick={startAssessment} className="w-full" size="md">
            <Sparkles className="h-4 w-4" />
            开始评估
          </Button>
        </div>
      </div>
    );
  }

  // 评估页
  const progress = dimensions.length
    ? (touched.size / dimensions.length) * 100
    : 0;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* 进度条 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-ink-600">
            已评估 {touched.size} / {dimensions.length} 个维度
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

      {/* 维度滑块 */}
      <div className="card space-y-5">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink-800">
            为每个维度的满意度打分
          </h2>
          <p className="text-xs text-ink-400 mt-1">
            1 分 = 非常不满意，10 分 = 非常满意。拖动滑块调整。
          </p>
        </div>
        <div className="space-y-5">
          {dimensions.map((d) => {
            const value = scores[d.key] ?? 5;
            const level = scoreLevel(value);
            return (
              <div key={d.key} className="space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-base">
                        {DIM_ICONS[d.key] ?? "🔹"}
                      </span>
                      <span className="text-sm font-medium text-ink-800">
                        {d.name}
                      </span>
                    </div>
                    <p className="text-xs text-ink-400 mt-0.5 leading-relaxed">
                      {d.desc}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <div>
                      <span
                        className={cn(
                          "font-display text-2xl font-bold",
                          level.color,
                        )}
                      >
                        {value}
                      </span>
                      <span className="text-xs text-ink-300"> / 10</span>
                    </div>
                    <p className={cn("text-[11px]", level.color)}>
                      {level.label}
                    </p>
                  </div>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  step={1}
                  value={value}
                  onChange={(e) =>
                    handleScoreChange(d.key, Number(e.target.value))
                  }
                  className="w-full cursor-pointer accent-brand-600"
                  aria-label={`${d.name} 满意度`}
                />
              </div>
            );
          })}
        </div>

        {/* 备注 */}
        <div className="space-y-1.5 pt-1">
          <label className="text-sm font-medium text-ink-700">
            本次评估备注{" "}
            <span className="text-ink-400 font-normal">（可选）</span>
          </label>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="记录当下的心境、近期重大变化或想要反思的事…"
            className="resize-y"
          />
        </div>
      </div>

      {/* 操作 */}
      <div className="flex items-center justify-between">
        <button
          onClick={handleBack}
          className="text-sm text-ink-400 hover:text-ink-600 transition-colors"
        >
          ← {snapshot ? "返回结果" : "返回介绍"}
        </button>
        <Button onClick={handleSubmit} loading={submitting} size="md">
          <Sparkles className="h-4 w-4" />
          提交评估
        </Button>
      </div>
    </div>
  );
}

function ResultView({
  snapshot,
  dimensions,
  analysis,
  analyzing,
  history,
  onRetake,
}: {
  snapshot: LifeWheelSnapshot;
  dimensions: LifeWheelDimension[];
  analysis: string | null;
  analyzing: boolean;
  history: LifeWheelSnapshot[];
  onRetake: () => void;
}) {
  const overall = snapshot.overall_score;
  const overallLevel = scoreLevel(overall);

  const radarData = dimensions.map((d) => ({
    key: d.key,
    name: d.name,
    score: snapshot.scores[d.key] ?? 0,
  }));

  const sortedDims = [...radarData].sort((a, b) => b.score - a.score);
  const highest = sortedDims[0];
  const lowest = sortedDims[sortedDims.length - 1];

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      {/* 结果头部 */}
      <div className="card text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <PieChart className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <p className="text-sm text-ink-400 mb-1">综合生活满意度</p>
        <div className="flex items-end justify-center gap-1 mb-2">
          <span className={cn("font-display text-4xl font-bold", overallLevel.color)}>
            {overall.toFixed(1)}
          </span>
          <span className="text-lg text-ink-400 mb-1">/ 10</span>
        </div>
        <span
          className={cn(
            "inline-flex items-center rounded-full bg-paper-100 px-3 py-0.5 text-xs font-medium",
            overallLevel.color,
          )}
        >
          {overallLevel.label}
        </span>
        {highest && lowest && highest.key !== lowest.key && (
          <p className="text-xs text-ink-400 mt-3 max-w-md mx-auto leading-relaxed">
            最高{" "}
            <span className="text-brand-600 font-medium">{highest.name}</span>
            （{highest.score} 分），最低{" "}
            <span className="text-amber-600 font-medium">{lowest.name}</span>
            （{lowest.score} 分）
          </p>
        )}
      </div>

      {/* 雷达图 + 维度得分 双栏 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 雷达图 */}
        <div className="card">
          <h2 className="font-display font-semibold text-ink-800 mb-2">
            平衡轮雷达图
          </h2>
          <LifeWheelRadar data={radarData} />
        </div>

        {/* 维度得分条 */}
        <div className="card space-y-3">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-display font-semibold text-ink-800">维度得分</h2>
            <span className="text-xs text-ink-400">满分 10 分</span>
          </div>
          {sortedDims.map(({ key, name, score }) => {
            const pct = (score / 10) * 100;
            const level = scoreLevel(score);
            return (
              <div key={key}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-ink-700">
                    <span className="mr-1">{DIM_ICONS[key] ?? "🔹"}</span>
                    {name}
                  </span>
                  <span className={cn("text-sm font-medium", level.color)}>
                    {score} 分
                  </span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-paper-200">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      pct >= 60
                        ? "bg-brand-500"
                        : pct >= 40
                          ? "bg-amber-400"
                          : "bg-red-400",
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* AI 分析 */}
      <div className="card space-y-3">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-50">
            <Sparkles className="h-4 w-4 text-brand-600" strokeWidth={1.8} />
          </span>
          <h2 className="font-display font-semibold text-ink-800">AI 平衡解读</h2>
        </div>
        {analyzing ? (
          <div className="flex items-center gap-2 text-sm text-ink-400 py-2">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-paper-300 border-t-brand-500" />
            正在结合你的得分生成个性化分析…
          </div>
        ) : analysis ? (
          <p className="text-sm text-ink-600 leading-relaxed whitespace-pre-line">
            {analysis}
          </p>
        ) : (
          <p className="text-sm text-ink-400">
            暂无 AI 分析，可重新评估后再试。
          </p>
        )}
      </div>

      {/* 历史记录 */}
      <div className="card space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-semibold text-ink-800">评估历史</h2>
          <span className="text-xs text-ink-400">共 {history.length} 次</span>
        </div>
        {history.length === 0 ? (
          <p className="text-sm text-ink-400 py-2">
            暂无历史记录，完成评估后这里会留下你的成长轨迹。
          </p>
        ) : (
          <ul className="divide-y divide-paper-200">
            {history.map((snap) => {
              const isCurrent = snap.id === snapshot.id;
              const lvl = scoreLevel(snap.overall_score);
              return (
                <li
                  key={snap.id}
                  className="flex items-center justify-between py-2.5"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-sm text-ink-700">
                      {formatDate(snap.snapshot_date || snap.created_at)}
                    </span>
                    {isCurrent && (
                      <span className="inline-flex items-center rounded-full bg-brand-100 px-2 py-0.5 text-[10px] font-medium text-brand-700">
                        本次
                      </span>
                    )}
                  </div>
                  <span className={cn("text-sm font-medium", lvl.color)}>
                    {snap.overall_score.toFixed(1)} 分
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* 操作 */}
      <div className="flex justify-center">
        <Button variant="secondary" onClick={onRetake}>
          <RotateCcw className="h-4 w-4" />
          重新评估
        </Button>
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

function DimensionCard({ dim }: { dim: LifeWheelDimension }) {
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-paper-200 bg-white p-2.5">
      <span className="text-lg leading-none mt-0.5">
        {DIM_ICONS[dim.key] ?? "🔹"}
      </span>
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink-800">{dim.name}</p>
        <p className="text-[11px] text-ink-400 leading-snug mt-0.5">
          {dim.desc}
        </p>
      </div>
    </div>
  );
}
