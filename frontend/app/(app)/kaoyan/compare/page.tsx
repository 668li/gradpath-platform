"use client";

import { useState, useCallback } from "react";
import { Button, Input, Badge } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { SchoolRadarChart } from "@/components/charts";
import { SchoolComparisonTable } from "@/components/grad/SchoolComparisonTable";
import { useToast } from "@/components/ui/toast";
import { schoolCompareApi, schoolAnalystApi, exportV2Api } from "@/lib/api";
import type { AnalystReportResponse, CompareResponse } from "@/lib/api";
import {
  Plus,
  X,
  Search,
  BarChart3,
  Lightbulb,
  Target,
  Shield,
  Zap,
  Download,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SchoolInput {
  name: string;
  major: string;
}

const RECOMMENDATION_CONFIG = {
  reach: { label: "冲刺", color: "text-red-700 bg-red-50", icon: Zap },
  target: { label: "稳妥", color: "text-amber-700 bg-amber-50", icon: Target },
  safe: { label: "保底", color: "text-green-700 bg-green-50", icon: Shield },
};

export default function SchoolComparePage() {
  const { push: toast } = useToast();
  const [schools, setSchools] = useState<SchoolInput[]>([
    { name: "", major: "" },
    { name: "", major: "" },
  ]);
  const [userScore, setUserScore] = useState("360");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [singleReport, setSingleReport] = useState<AnalystReportResponse | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [schoolPdfLoading, setSchoolPdfLoading] = useState(false);

  const addSchool = () => {
    if (schools.length < 5) {
      setSchools([...schools, { name: "", major: "" }]);
    }
  };

  const removeSchool = (index: number) => {
    if (schools.length > 2) {
      setSchools(schools.filter((_, i) => i !== index));
    }
  };

  const updateSchool = (index: number, field: keyof SchoolInput, value: string) => {
    const updated = [...schools];
    updated[index] = { ...updated[index], [field]: value };
    setSchools(updated);
  };

  const handleCompare = useCallback(async () => {
    const validSchools = schools.filter((s) => s.name.trim() && s.major.trim());
    if (validSchools.length < 2) {
      toast("请至少填写 2 所院校的名称和专业", "error");
      return;
    }
    setLoading(true);
    setResult(null);
    setSingleReport(null);
    try {
      const res = await schoolCompareApi.compare({
        schools: validSchools,
        user_score: parseInt(userScore) || 360,
      });
      setResult(res);
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "对比请求失败，请重试", "error");
    } finally {
      setLoading(false);
    }
  }, [schools, userScore, toast]);

  const handleSingleReport = useCallback(
    async (school: SchoolInput) => {
      if (!school.name.trim() || !school.major.trim()) {
        toast("请填写院校名称和专业", "error");
        return;
      }
      setReportLoading(true);
      setSingleReport(null);
      setResult(null);
      try {
        const res = await schoolAnalystApi.getReport({
          school_name: school.name.trim(),
          major: school.major.trim(),
        });
        setSingleReport(res);
      } catch (err: unknown) {
        toast(err instanceof Error ? err.message : "分析请求失败", "error");
      } finally {
        setReportLoading(false);
      }
    },
    [toast],
  );

  const handleSchoolReportPdf = useCallback(
    async (school: SchoolInput) => {
      if (!school.name.trim()) {
        toast("请填写院校名称", "error");
        return;
      }
      setSchoolPdfLoading(true);
      try {
        await exportV2Api.schoolReport({ schoolName: school.name.trim() });
        toast("院校报告导出成功", "success");
      } catch (err: unknown) {
        toast(err instanceof Error ? err.message : "导出失败", "error");
      } finally {
        setSchoolPdfLoading(false);
      }
    },
    [toast],
  );

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-6xl px-4 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-ink-800">院校对比分析</h1>
          <p className="mt-1 text-sm text-ink-500">
            选择 2-5 所院校进行多维对比，AI 为你生成择校建议
          </p>
        </div>

        {/* Input Form */}
        <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-ink-800">选择对比院校</h2>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <label className="text-sm text-ink-500">预估初试成绩</label>
                <Input
                  type="number"
                  value={userScore}
                  onChange={(e) => setUserScore(e.target.value)}
                  className="w-24"
                  min={0}
                  max={500}
                />
              </div>
              {schools.length < 5 && (
                <Button variant="ghost" size="sm" onClick={addSchool}>
                  <Plus className="mr-1 h-4 w-4" />
                  添加院校
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-3">
            {schools.map((school, index) => (
              <div key={`${school.name}-${index}`} className="flex items-center gap-3">
                <span className="w-6 text-center text-sm font-medium text-ink-400">
                  {index + 1}
                </span>
                <Input
                  placeholder="院校名称（如：清华大学）"
                  value={school.name}
                  onChange={(e) => updateSchool(index, "name", e.target.value)}
                  className="flex-1"
                />
                <Input
                  placeholder="专业名称（如：计算机科学与技术）"
                  value={school.major}
                  onChange={(e) => updateSchool(index, "major", e.target.value)}
                  className="flex-1"
                />
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSingleReport(school)}
                    disabled={reportLoading}
                    title="单独分析"
                  >
                    <Search className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSchoolReportPdf(school)}
                    disabled={schoolPdfLoading || !school.name.trim()}
                    title="导出院校报告 PDF"
                  >
                    <FileText className="h-4 w-4" />
                  </Button>
                  {schools.length > 2 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeSchool(index)}
                      title="删除"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 flex justify-end">
            <Button onClick={handleCompare} disabled={loading}>
              {loading ? "分析中..." : "开始对比"}
            </Button>
          </div>
        </div>

        {/* Loading */}
        {(loading || reportLoading) && (
          <LoadingState text={loading ? "正在对比分析..." : "正在生成分析报告..."} />
        )}

        {/* Single School Report */}
        {singleReport && !loading && (
          <div className="space-y-6">
            <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-ink-800">
                  {singleReport.school_name} · {singleReport.major}
                </h2>
                <div className="flex items-center gap-2">
                  <Badge
                    className={cn(
                      RECOMMENDATION_CONFIG[
                        singleReport.recommendation as keyof typeof RECOMMENDATION_CONFIG
                      ]?.color,
                    )}
                  >
                    {
                      RECOMMENDATION_CONFIG[
                        singleReport.recommendation as keyof typeof RECOMMENDATION_CONFIG
                      ]?.label
                    }
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSchoolReportPdf({ name: singleReport.school_name, major: singleReport.major })}
                    disabled={schoolPdfLoading}
                    title="导出院校报告 PDF"
                  >
                    <Download className="h-4 w-4" />
                    <span className="ml-1">导出 PDF</span>
                  </Button>
                </div>
              </div>

              {/* Radar */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-ink-600 mb-3">六维雷达图</h3>
                <SchoolRadarChart
                  schools={[
                    {
                      name: singleReport.school_name,
                      scores: {
                        录取难度: singleReport.six_dimension_radar.admission_difficulty.score,
                        一志愿保护: singleReport.six_dimension_radar.first_choice_protection.score,
                        调剂友好度: singleReport.six_dimension_radar.transfer_friendliness.score,
                        压分风险: singleReport.six_dimension_radar.score_suppression_risk.score,
                        信息透明: singleReport.six_dimension_radar.info_transparency.score,
                        性价比: singleReport.six_dimension_radar.cost_effectiveness.score,
                      },
                    },
                  ]}
                  height={300}
                />
              </div>

              {/* Score Trend */}
              {singleReport.scoreline_trend.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-ink-600 mb-3">历年分数线</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-paper-200 text-left text-xs text-ink-500">
                          <th className="px-3 py-2 font-medium">年份</th>
                          <th className="px-3 py-2 font-medium text-center">复试线</th>
                          <th className="px-3 py-2 font-medium text-center">报录比</th>
                        </tr>
                      </thead>
                      <tbody>
                        {singleReport.scoreline_trend.map((t) => (
                          <tr key={t.year} className="border-b border-paper-100">
                            <td className="px-3 py-2 text-ink-700">{t.year}</td>
                            <td className="px-3 py-2 text-center font-medium text-ink-800">
                              {t.score_line ?? "—"}
                            </td>
                            <td className="px-3 py-2 text-center text-ink-500">
                              {t.competition_ratio ?? "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Dark Knowledge */}
              {singleReport.dark_knowledge_highlights.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-ink-600 mb-3 flex items-center gap-1">
                    <Lightbulb className="h-4 w-4" />
                    关键洞察
                  </h3>
                  <ul className="space-y-2">
                    {singleReport.dark_knowledge_highlights.map((tip, i) => (
                      <li
                        key={`${tip}-${i}`}
                        className="text-sm text-ink-600 bg-paper-50 rounded-lg px-3 py-2"
                      >
                        {tip}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Similar Schools */}
              {singleReport.similar_schools.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-ink-600 mb-2">相似院校</h3>
                  <div className="flex flex-wrap gap-2">
                    {singleReport.similar_schools.map((s) => (
                      <Badge key={s}>{s}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* AI Summary */}
              <div className="rounded-lg bg-brand-50 border border-brand-100 p-4">
                <h3 className="text-sm font-semibold text-brand-800 mb-2">AI 分析总结</h3>
                <p className="text-sm text-brand-700 leading-relaxed">{singleReport.summary}</p>
              </div>
            </div>
          </div>
        )}

        {/* Compare Results */}
        {result && !loading && (
          <div className="space-y-6">
            {/* Radar Comparison */}
            <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-ink-800 mb-4 flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                六维雷达对比
              </h2>
              <SchoolRadarChart
                schools={result.radar_comparison.map((r) => ({
                  name: r.name,
                  scores: r.scores,
                }))}
                height={400}
              />
            </div>

            {/* Score Comparison Table */}
            <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-ink-800 mb-4">综合对比表</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-paper-200 text-left text-xs text-ink-500">
                      <th className="px-3 py-2 font-medium">院校</th>
                      <th className="px-3 py-2 font-medium text-center">录取难度</th>
                      <th className="px-3 py-2 font-medium text-center">一志愿保护</th>
                      <th className="px-3 py-2 font-medium text-center">调剂友好</th>
                      <th className="px-3 py-2 font-medium text-center">压分风险</th>
                      <th className="px-3 py-2 font-medium text-center">信息透明</th>
                      <th className="px-3 py-2 font-medium text-center">性价比</th>
                      <th className="px-3 py-2 font-medium text-center">匹配度</th>
                      <th className="px-3 py-2 font-medium text-center">分类</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.schools.map((s) => {
                      const rec =
                        RECOMMENDATION_CONFIG[
                          s.recommendation as keyof typeof RECOMMENDATION_CONFIG
                        ];
                      return (
                        <tr
                          key={s.school_name}
                          className="border-b border-paper-100 hover:bg-paper-50/50"
                        >
                          <td className="px-3 py-3 font-medium text-ink-800">
                            {s.school_name}
                          </td>
                          <td className="px-3 py-3 text-center">
                            {s.six_dimension_radar.admission_difficulty.score}
                          </td>
                          <td className="px-3 py-3 text-center">
                            {s.six_dimension_radar.first_choice_protection.score}
                          </td>
                          <td className="px-3 py-3 text-center">
                            {s.six_dimension_radar.transfer_friendliness.score}
                          </td>
                          <td className="px-3 py-3 text-center">
                            {s.six_dimension_radar.score_suppression_risk.score}
                          </td>
                          <td className="px-3 py-3 text-center">
                            {s.six_dimension_radar.info_transparency.score}
                          </td>
                          <td className="px-3 py-3 text-center">
                            {s.six_dimension_radar.cost_effectiveness.score}
                          </td>
                          <td className="px-3 py-3 text-center">
                            <span
                              className={cn(
                                "inline-block px-2 py-0.5 rounded-full text-xs font-medium",
                                s.match_score >= 75
                                  ? "text-green-700 bg-green-50"
                                  : s.match_score >= 50
                                    ? "text-amber-700 bg-amber-50"
                                    : "text-red-700 bg-red-50",
                              )}
                            >
                              {s.match_score}%
                            </span>
                          </td>
                          <td className="px-3 py-3 text-center">
                            {rec && (
                              <span
                                className={cn(
                                  "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                                  rec.color,
                                )}
                              >
                                <rec.icon className="h-3 w-3" />
                                {rec.label}
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Recommendation Summary */}
            <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-ink-800 mb-4">择校建议</h2>
              <div className="grid grid-cols-3 gap-4 mb-6">
                {(["reach", "target", "safe"] as const).map((tier) => {
                  const config = RECOMMENDATION_CONFIG[tier];
                  const schools_list = result.recommendation_summary[tier];
                  return (
                    <div
                      key={tier}
                      className={cn(
                        "rounded-lg border p-4",
                        tier === "reach"
                          ? "border-red-200 bg-red-50"
                          : tier === "target"
                            ? "border-amber-200 bg-amber-50"
                            : "border-green-200 bg-green-50",
                      )}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <config.icon className="h-4 w-4" />
                        <span className="font-medium text-sm">{config.label}</span>
                        <Badge className={cn(config.color, "ml-auto")}>
                          {schools_list.length} 所
                        </Badge>
                      </div>
                      {schools_list.length > 0 ? (
                        <ul className="space-y-1">
                          {schools_list.map((name) => (
                            <li key={name} className="text-sm text-ink-600">
                              {name}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-xs text-ink-400">暂无</p>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* AI Summary */}
              <div className="rounded-lg bg-brand-50 border border-brand-100 p-4">
                <h3 className="text-sm font-semibold text-brand-800 mb-2">AI 综合分析</h3>
                <p className="text-sm text-brand-700 leading-relaxed">{result.ai_summary}</p>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!result && !singleReport && !loading && !reportLoading && (
          <EmptyState
            title="选择院校开始对比"
            description="填写 2-5 所院校的名称和专业，AI 将为你生成多维对比分析报告"
          />
        )}
      </div>
    </div>
  );
}
