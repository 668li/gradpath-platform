"use client";

import { useState, useCallback } from "react";
import { Button, Input, Field, FieldError } from "@/components/ui/form-controls";
import { LineChart, type ScorePoint } from "@/components/charts";
import { useToast } from "@/components/ui/toast";
import { admissionApi, type PredictResponse, type HistoryResponse } from "@/lib/api/admission";
import {
  Target,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Lightbulb,
  BarChart3,
  Users,
  Gauge,
} from "lucide-react";
import { cn } from "@/lib/utils";

const RISK_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  low: { label: "低风险", color: "text-green-700", bg: "bg-green-50" },
  medium: { label: "中等风险", color: "text-amber-700", bg: "bg-amber-50" },
  high: { label: "高风险", color: "text-red-700", bg: "bg-red-50" },
};

const CONFIDENCE_CONFIG: Record<string, { label: string; color: string }> = {
  high: { label: "高置信度", color: "text-green-600" },
  medium: { label: "中置信度", color: "text-amber-600" },
  low: { label: "低置信度", color: "text-red-600" },
};

const IMPACT_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  positive: { label: "正向", color: "text-green-700", bg: "bg-green-50" },
  negative: { label: "负向", color: "text-red-700", bg: "bg-red-50" },
  neutral: { label: "中性", color: "text-ink-600", bg: "bg-paper-100" },
};

export default function AdmissionPredictPage() {
  const { push: toast } = useToast();

  // Form state
  const [school, setSchool] = useState("");
  const [major, setMajor] = useState("");
  const [score, setScore] = useState("");
  const [gpa, setGpa] = useState("");
  const [undergraduate, setUndergraduate] = useState("");

  // Field error state
  const [schoolError, setSchoolError] = useState("");
  const [majorError, setMajorError] = useState("");
  const [scoreError, setScoreError] = useState("");
  const [gpaError, setGpaError] = useState("");
  const [undergradError, setUndergradError] = useState("");

  // Result state
  const [predictResult, setPredictResult] = useState<PredictResponse | null>(null);
  const [historyResult, setHistoryResult] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePredict = useCallback(async () => {
    const sErr = !school.trim() ? "请输入学校名称" : "";
    const mErr = !major.trim() ? "请输入专业名称" : "";
    const scErr = !score ? "请输入考试分数" : "";
    const gpaErr = !gpa ? "请输入 GPA" : "";
    const uErr = !undergraduate.trim() ? "请输入本科院校" : "";
    setSchoolError(sErr);
    setMajorError(mErr);
    setScoreError(scErr);
    setGpaError(gpaErr);
    setUndergradError(uErr);
    if (sErr || mErr || scErr || gpaErr || uErr) return;

    setLoading(true);
    setPredictResult(null);
    setHistoryResult(null);
    try {
      const res = await admissionApi.predict({
        school_name: school.trim(),
        major: major.trim(),
        user_score: Number(score),
        user_gpa: Number(gpa),
        user_university: undergraduate.trim(),
      });
      setPredictResult(res);
      // 同时加载历史分数线
      try {
        const hist = await admissionApi.history(school.trim(), major.trim());
        setHistoryResult(hist);
      } catch {
        // 历史数据加载失败不影响预测结果展示
      }
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "预测请求失败，请重试", "error");
    } finally {
      setLoading(false);
    }
  }, [school, major, score, gpa, undergraduate, toast]);

  const handleLoadHistory = useCallback(async () => {
    const sErr = !school.trim() ? "请输入学校名称" : "";
    const mErr = !major.trim() ? "请输入专业名称" : "";
    setSchoolError(sErr);
    setMajorError(mErr);
    if (sErr || mErr) return;
    try {
      const res = await admissionApi.history(school.trim(), major.trim());
      setHistoryResult(res);
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "获取历史分数线失败", "error");
    }
  }, [school, major, toast]);

  const probability = predictResult?.probability ?? 0;
  const risk = RISK_CONFIG[predictResult?.risk_level ?? "medium"];
  const confidence = CONFIDENCE_CONFIG[predictResult?.confidence ?? "low"];

  const chartData: ScorePoint[] = (historyResult?.records ?? [])
    .map((r) => ({ year: r.year, score: r.total_score_line ?? 0 }))
    .filter((r) => r.score > 0)
    .sort((a, b) => a.year - b.year);

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-4xl px-4 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-ink-800 flex items-center gap-2">
            <Target className="h-6 w-6 text-brand-600" />
            录取概率预测
          </h1>
          <p className="mt-1 text-sm text-ink-500">
            输入你的成绩和目标院校，基于历史数据智能预测录取概率，提供备考建议
          </p>
        </div>

        {/* Form Card */}
        <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm mb-6">
          <h2 className="text-lg font-semibold text-ink-800 mb-4">基本信息</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="学校名称" required>
              <Input
                placeholder="如：清华大学"
                value={school}
                onChange={(e) => { setSchool(e.target.value); setSchoolError(""); }}
                aria-invalid={!!schoolError}
              />
              <FieldError message={schoolError} />
            </Field>
            <Field label="专业名称" required>
              <Input
                placeholder="如：计算机科学与技术"
                value={major}
                onChange={(e) => { setMajor(e.target.value); setMajorError(""); }}
                aria-invalid={!!majorError}
              />
              <FieldError message={majorError} />
            </Field>
            <Field label="考试分数" required hint="满分 750">
              <Input
                type="number"
                placeholder="如：380"
                min={0}
                max={750}
                value={score}
                onChange={(e) => { setScore(e.target.value); setScoreError(""); }}
                aria-invalid={!!scoreError}
              />
              <FieldError message={scoreError} />
            </Field>
            <Field label="GPA" required hint="满分 4.0">
              <Input
                type="number"
                placeholder="如：3.5"
                min={0}
                max={4}
                step={0.1}
                value={gpa}
                onChange={(e) => { setGpa(e.target.value); setGpaError(""); }}
                aria-invalid={!!gpaError}
              />
              <FieldError message={gpaError} />
            </Field>
            <Field label="本科院校" required>
              <Input
                placeholder="如：北京理工大学"
                value={undergraduate}
                onChange={(e) => { setUndergraduate(e.target.value); setUndergradError(""); }}
                aria-invalid={!!undergradError}
              />
              <FieldError message={undergradError} />
            </Field>
          </div>

          <div className="mt-6 flex items-center gap-3">
            <Button onClick={handlePredict} disabled={loading}>
              {loading ? "预测中..." : "开始预测"}
            </Button>
            <Button variant="secondary" onClick={handleLoadHistory}>
              查看历史分数线
            </Button>
          </div>
        </div>

        {/* Predict Result */}
        {predictResult && (
          <div className="space-y-6">
            {/* Probability Card */}
            <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-ink-800 mb-4">预测结果</h2>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                {/* Probability */}
                <div className="text-center p-4 rounded-lg bg-paper-50">
                  <p className="text-xs text-ink-500 mb-1">录取概率</p>
                  <p
                    className={cn(
                      "text-3xl font-bold",
                      probability >= 0.7
                        ? "text-green-600"
                        : probability >= 0.4
                          ? "text-amber-600"
                          : "text-red-600",
                    )}
                  >
                    {(probability * 100).toFixed(1)}%
                  </p>
                  <div className="mt-2 h-2 rounded-full bg-paper-200 overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-500",
                        probability >= 0.7
                          ? "bg-green-500"
                          : probability >= 0.4
                            ? "bg-amber-500"
                            : "bg-red-500",
                      )}
                      style={{ width: `${probability * 100}%` }}
                    />
                  </div>
                </div>

                {/* Risk Level */}
                <div className="text-center p-4 rounded-lg bg-paper-50">
                  <p className="text-xs text-ink-500 mb-1">风险等级</p>
                  <div className="flex items-center justify-center gap-2 mt-2">
                    {predictResult.risk_level === "high" ? (
                      <AlertTriangle className={cn("h-5 w-5", risk.color)} />
                    ) : predictResult.risk_level === "low" ? (
                      <CheckCircle2 className={cn("h-5 w-5", risk.color)} />
                    ) : (
                      <TrendingUp className={cn("h-5 w-5", risk.color)} />
                    )}
                    <span
                      className={cn(
                        "inline-flex items-center px-3 py-1 rounded-full text-sm font-medium",
                        risk.bg,
                        risk.color,
                      )}
                    >
                      {risk.label}
                    </span>
                  </div>
                </div>

                {/* Confidence */}
                <div className="text-center p-4 rounded-lg bg-paper-50">
                  <p className="text-xs text-ink-500 mb-1">数据置信度</p>
                  <div className="flex items-center justify-center gap-2 mt-2">
                    <Gauge className={cn("h-5 w-5", confidence.color)} />
                    <span className={cn("text-sm font-medium", confidence.color)}>
                      {confidence.label}
                    </span>
                  </div>
                  <p className="text-xs text-ink-400 mt-1">
                    {predictResult.confidence === "high"
                      ? "历史数据充足"
                      : predictResult.confidence === "medium"
                        ? "有一定参考价值"
                        : "数据较少，仅供参考"}
                  </p>
                </div>

                {/* School/Major */}
                <div className="text-center p-4 rounded-lg bg-paper-50">
                  <p className="text-xs text-ink-500 mb-1">目标院校</p>
                  <p className="text-sm font-semibold text-ink-800 mt-2">
                    {predictResult.school_name}
                  </p>
                  <p className="text-xs text-ink-500 mt-1">{predictResult.major}</p>
                </div>
              </div>

              {/* Recommendation */}
              {predictResult.recommendation && (
                <div className="rounded-lg bg-brand-50 border border-brand-100 p-4 mb-4">
                  <h3 className="text-sm font-semibold text-brand-800 mb-2 flex items-center gap-1">
                    <Lightbulb className="h-4 w-4" />
                    AI 建议
                  </h3>
                  <p className="text-sm text-brand-700 leading-relaxed">
                    {predictResult.recommendation}
                  </p>
                </div>
              )}

              {/* Factors */}
              {predictResult.factors && predictResult.factors.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-ink-600 mb-3">影响因素分析</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {predictResult.factors.map((f, i) => {
                      const impact = IMPACT_CONFIG[f.impact] || IMPACT_CONFIG.neutral;
                      return (
                        <div
                          key={i}
                          className="flex items-center justify-between rounded-lg bg-paper-50 px-3 py-2"
                        >
                          <span className="text-sm text-ink-600">{f.factor}</span>
                          <div className="flex items-center gap-2">
                            <span className={cn("text-xs px-2 py-0.5 rounded-full", impact.bg, impact.color)}>
                              {impact.label}
                            </span>
                            <span className="text-xs font-medium text-ink-400">
                              权重 {(f.weight * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Similar Cases */}
              {predictResult.similar_cases && predictResult.similar_cases.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-ink-600 mb-3 flex items-center gap-1">
                    <Users className="h-4 w-4" />
                    相似案例（历年考生录取结果）
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {predictResult.similar_cases.map((c, i) => (
                      <div
                        key={i}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm",
                          c.outcome === "admitted"
                            ? "bg-green-50 text-green-700"
                            : c.outcome === "rejected"
                              ? "bg-red-50 text-red-700"
                              : "bg-amber-50 text-amber-700",
                        )}
                      >
                        <span className="font-medium">{c.user_score} 分</span>
                        <span className="text-xs">
                          {c.outcome === "admitted" ? "录取" : c.outcome === "rejected" ? "未录取" : "候补"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* History Scoreline */}
            {historyResult && chartData.length > 0 && (
              <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-ink-800 mb-4 flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  历年分数线趋势
                </h2>

                {/* Statistics summary */}
                {historyResult.statistics && (
                  <div className="mb-4 flex flex-wrap gap-3 text-xs">
                    {historyResult.statistics.year_span && (
                      <span className="rounded-lg bg-paper-100 px-3 py-1 text-ink-600">
                        数据跨度：{historyResult.statistics.year_span}
                      </span>
                    )}
                    {historyResult.statistics.avg_score != null && (
                      <span className="rounded-lg bg-paper-100 px-3 py-1 text-ink-600">
                        均分：{historyResult.statistics.avg_score}
                      </span>
                    )}
                    {historyResult.statistics.max_score != null && (
                      <span className="rounded-lg bg-paper-100 px-3 py-1 text-ink-600">
                        最高：{historyResult.statistics.max_score}
                      </span>
                    )}
                    {historyResult.statistics.min_score != null && (
                      <span className="rounded-lg bg-paper-100 px-3 py-1 text-ink-600">
                        最低：{historyResult.statistics.min_score}
                      </span>
                    )}
                    {historyResult.statistics.avg_admission_rate != null && (
                      <span className="rounded-lg bg-paper-100 px-3 py-1 text-ink-600">
                        平均录取率：{historyResult.statistics.avg_admission_rate}%
                      </span>
                    )}
                  </div>
                )}

                <LineChart data={chartData} height={300} emptyText="暂无分数线数据" />

                {/* Detail Table */}
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-paper-200 text-left text-xs text-ink-500">
                        <th className="px-3 py-2 font-medium">年份</th>
                        <th className="px-3 py-2 font-medium text-center">分数线</th>
                        <th className="px-3 py-2 font-medium text-center">录取人数</th>
                        <th className="px-3 py-2 font-medium text-center">报考人数</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historyResult.records.map((r) => (
                        <tr key={r.year} className="border-b border-paper-100">
                          <td className="px-3 py-2 text-ink-700">{r.year}</td>
                          <td className="px-3 py-2 text-center font-medium text-ink-800">
                            {r.total_score_line ?? "—"}
                          </td>
                          <td className="px-3 py-2 text-center text-ink-500">
                            {r.enrollment_count ?? "—"}
                          </td>
                          <td className="px-3 py-2 text-center text-ink-500">
                            {r.application_count ?? "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty State */}
        {!predictResult && !loading && (
          <div className="rounded-xl border border-paper-200 bg-white p-12 shadow-sm text-center">
            <Target className="h-12 w-12 text-ink-300 mx-auto mb-3" />
            <p className="text-sm text-ink-500">
              填写你的成绩和目标院校信息，开始预测录取概率
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
