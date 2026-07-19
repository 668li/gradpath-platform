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
} from "lucide-react";
import { cn } from "@/lib/utils";

const RISK_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  low: { label: "低风险", color: "text-green-700", bg: "bg-green-50" },
  medium: { label: "中等风险", color: "text-amber-700", bg: "bg-amber-50" },
  high: { label: "高风险", color: "text-red-700", bg: "bg-red-50" },
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

  // Result state
  const [predictResult, setPredictResult] = useState<PredictResponse | null>(null);
  const [historyResult, setHistoryResult] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePredict = useCallback(async () => {
    const sErr = !school.trim() ? "请输入学校名称" : "";
    const mErr = !major.trim() ? "请输入专业名称" : "";
    setSchoolError(sErr);
    setMajorError(mErr);
    if (sErr || mErr) return;
    setLoading(true);
    setPredictResult(null);
    setHistoryResult(null);
    try {
      const res = await admissionApi.predict({
        school: school.trim(),
        major: major.trim(),
        score: score ? Number(score) : undefined,
      });
      setPredictResult(res);
    } catch (err: any) {
      toast(err?.message || "预测请求失败，请重试", "error");
    } finally {
      setLoading(false);
    }
  }, [school, major, score, toast]);

  const handleLoadHistory = useCallback(async () => {
    const sErr = !school.trim() ? "请输入学校名称" : "";
    const mErr = !major.trim() ? "请输入专业名称" : "";
    setSchoolError(sErr);
    setMajorError(mErr);
    if (sErr || mErr) return;
    try {
      const res = await admissionApi.history(school.trim(), major.trim());
      setHistoryResult(res);
    } catch (err: any) {
      toast(err?.message || "获取历史分数线失败", "error");
    }
  }, [school, major, toast]);

  const probability = predictResult?.probability ?? 0;
  const risk = RISK_CONFIG[predictResult?.risk_level ?? "medium"];

  const chartData: ScorePoint[] = (historyResult?.records ?? [])
    .map((r) => ({ year: r.year, score: r.score }))
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
            输入你的成绩和目标院校，AI 为你预测录取概率并提供备考建议
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
            <Field label="考试分数" hint="满分 750">
              <Input
                type="number"
                placeholder="如：380"
                min={0}
                max={750}
                value={score}
                onChange={(e) => setScore(e.target.value)}
              />
            </Field>
            <Field label="GPA" hint="满分 4.0，可选">
              <Input
                type="number"
                placeholder="如：3.5"
                min={0}
                max={4}
                step={0.1}
                value={gpa}
                onChange={(e) => setGpa(e.target.value)}
              />
            </Field>
            <Field label="本科院校" hint="可选">
              <Input
                placeholder="如：北京理工大学"
                value={undergraduate}
                onChange={(e) => setUndergraduate(e.target.value)}
              />
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

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {/* Probability */}
                <div className="text-center p-4 rounded-lg bg-paper-50">
                  <p className="text-xs text-ink-500 mb-1">录取概率</p>
                  <p
                    className={cn(
                      "text-3xl font-bold",
                      probability >= 70
                        ? "text-green-600"
                        : probability >= 40
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
                        probability >= 70
                          ? "bg-green-500"
                          : probability >= 40
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

                {/* School/Major */}
                <div className="text-center p-4 rounded-lg bg-paper-50">
                  <p className="text-xs text-ink-500 mb-1">目标院校</p>
                  <p className="text-sm font-semibold text-ink-800 mt-2">
                    {predictResult.school}
                  </p>
                  <p className="text-xs text-ink-500 mt-1">{predictResult.major}</p>
                </div>
              </div>

              {/* Suggestion */}
              {predictResult.suggestion && (
                <div className="rounded-lg bg-brand-50 border border-brand-100 p-4 mb-4">
                  <h3 className="text-sm font-semibold text-brand-800 mb-2 flex items-center gap-1">
                    <Lightbulb className="h-4 w-4" />
                    AI 建议
                  </h3>
                  <p className="text-sm text-brand-700 leading-relaxed">
                    {predictResult.suggestion}
                  </p>
                </div>
              )}

              {/* Factors */}
              {predictResult.factors && Object.keys(predictResult.factors).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-ink-600 mb-3">影响因素</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {Object.entries(predictResult.factors).map(([key, value]) => (
                      <div
                        key={key}
                        className="flex items-center justify-between rounded-lg bg-paper-50 px-3 py-2"
                      >
                        <span className="text-sm text-ink-600">{key}</span>
                        <span className="text-sm font-medium text-ink-800">
                          {typeof value === "number" ? value.toFixed(2) : String(value)}
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
                <LineChart data={chartData} height={300} emptyText="暂无分数线数据" />

                {/* Detail Table */}
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-paper-200 text-left text-xs text-ink-500">
                        <th className="px-3 py-2 font-medium">年份</th>
                        <th className="px-3 py-2 font-medium text-center">分数线</th>
                        <th className="px-3 py-2 font-medium text-center">录取人数</th>
                        <th className="px-3 py-2 font-medium text-center">最低排名</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historyResult.records.map((r) => (
                        <tr key={r.year} className="border-b border-paper-100">
                          <td className="px-3 py-2 text-ink-700">{r.year}</td>
                          <td className="px-3 py-2 text-center font-medium text-ink-800">
                            {r.score}
                          </td>
                          <td className="px-3 py-2 text-center text-ink-500">
                            {r.admission_count ?? "—"}
                          </td>
                          <td className="px-3 py-2 text-center text-ink-500">
                            {r.min_rank ?? "—"}
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
