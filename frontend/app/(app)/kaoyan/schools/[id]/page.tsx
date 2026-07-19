"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  School,
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
  BookOpen,
  Phone,
  Mail,
  Calendar,
  BarChart3,
  Search,
  ArrowRight,
} from "lucide-react";
import { Button, Badge } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { gradIntelApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import type {
  GradYanzhaoProgram,
  GradScorelineRecord,
  GradAdjustmentInfo,
  GradSchoolDataSummary,
  GradScorelineTrend,
} from "@/types";

export default function SchoolDetailPage() {
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const universityName = decodeURIComponent(params.id as string);

  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<GradSchoolDataSummary | null>(null);
  const [programs, setPrograms] = useState<GradYanzhaoProgram[]>([]);
  const [scorelines, setScorelines] = useState<GradScorelineRecord[]>([]);
  const [adjustments, setAdjustments] = useState<GradAdjustmentInfo[]>([]);
  const [trend, setTrend] = useState<GradScorelineTrend | null>(null);
  const [selectedMajor, setSelectedMajor] = useState<string>("");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [s, p, sl, adj] = await Promise.all([
        gradIntelApi.getSchoolSummary(universityName),
        gradIntelApi.listYanzhaoPrograms({ university_name: universityName, limit: 100 }),
        gradIntelApi.listScorelines({ university_name: universityName, limit: 200 }),
        gradIntelApi.listAdjustments({ university_name: universityName, limit: 100 }),
      ]);
      setSummary(s);
      setPrograms(p);
      setScorelines(sl);
      setAdjustments(adj);

      // 默认选择第一个有分数线数据的专业
      const firstMajor = sl[0]?.major_name || p[0]?.major_name;
      if (firstMajor) {
        setSelectedMajor(firstMajor);
        try {
          const t = await gradIntelApi.getScorelineTrend({
            university_name: universityName,
            major_name: firstMajor,
          });
          setTrend(t);
        } catch {
          setTrend(null);
        }
      }
    } catch {
      toast.push("加载院校详情失败", "error");
    } finally {
      setLoading(false);
    }
  }, [universityName, toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const loadTrend = useCallback(
    async (major: string) => {
      if (!major) return;
      try {
        const t = await gradIntelApi.getScorelineTrend({
          university_name: universityName,
          major_name: major,
        });
        setTrend(t);
      } catch {
        setTrend(null);
      }
    },
    [universityName],
  );

  useEffect(() => {
    if (selectedMajor) loadTrend(selectedMajor);
  }, [selectedMajor, loadTrend]);

  const majors = useMemo(
    () => Array.from(new Set(scorelines.map((s) => s.major_name))),
    [scorelines],
  );

  const chartData = useMemo(() => {
    if (!trend) return [];
    return trend.years.map((year, i) => ({
      year,
      总分: trend.total_score_lines[i] ?? null,
      政治: trend.politics_scores[i] ?? null,
      外语: trend.foreign_language_scores[i] ?? null,
      业务课一: trend.business_1_scores[i] ?? null,
      业务课二: trend.business_2_scores[i] ?? null,
      报考人数: trend.application_counts[i] ?? null,
      录取人数: trend.enrollment_counts[i] ?? null,
    }));
  }, [trend]);

  // 计算报录比（取最近一年有数据的）
  const admissionRatio = useMemo(() => {
    const latest = scorelines
      .filter((s) => s.application_count && s.enrollment_count)
      .sort((a, b) => b.year - a.year)[0];
    if (!latest) return null;
    return {
      ratio: `${latest.application_count}:${latest.enrollment_count}`,
      application_count: latest.application_count,
      enrollment_count: latest.enrollment_count,
      year: latest.year,
    };
  }, [scorelines]);

  // 计算调剂总名额
  const adjustmentTotal = useMemo(
    () => adjustments.reduce((sum, a) => sum + (a.adjustment_quota || 0), 0),
    [adjustments],
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
          <LoadingState text="加载院校详情..." />
        </div>
      </div>
    );
  }

  if (!summary && programs.length === 0) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
          <EmptyState
            title="未找到院校数据"
            description={`暂无 ${universityName} 的相关数据`}
            action={
              <Button onClick={() => router.push("/kaoyan/schools")}>
                <ArrowLeft className="h-4 w-4 mr-1.5" />
                返回院校列表
              </Button>
            }
          />
        </div>
      </div>
    );
  }

  const trendIcon =
    summary?.scoreline_trend === "up" ? (
      <TrendingUp className="h-5 w-5 text-red-500" />
    ) : summary?.scoreline_trend === "down" ? (
      <TrendingDown className="h-5 w-5 text-green-500" />
    ) : (
      <Minus className="h-5 w-5 text-ink-400" />
    );

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
        {/* Header with Navigation */}
        <div className="mb-6">
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="ghost" size="sm" onClick={() => router.push("/kaoyan/schools")}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              返回列表
            </Button>
            <span className="text-ink-300">|</span>
            <Button variant="ghost" size="sm" onClick={() => router.push("/kaoyan/compare")}>
              院校对比
            </Button>
            <span className="text-ink-300">|</span>
            <Button variant="ghost" size="sm" onClick={() => router.push("/kaoyan/dark-knowledge")}>
              暗知识
            </Button>
          </div>
          <div className="flex items-center gap-2.5 mt-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 text-white shadow-brand-sm">
              <School className="h-6 w-6" strokeWidth={2.2} />
            </div>
            <div>
              <h1 className="font-display text-xl sm:text-2xl font-bold text-ink-900 tracking-tight">
                {universityName}
              </h1>
              <p className="text-sm text-ink-500">院校情报详情</p>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          <SummaryCard
            label="招生专业"
            value={`${summary?.program_count ?? programs.length} 个`}
            icon={BookOpen}
            color="blue"
          />
          <SummaryCard
            label="最新复试线"
            value={summary?.latest_scoreline?.toString() ?? "—"}
            icon={summary?.scoreline_trend === "up" ? TrendingUp : summary?.scoreline_trend === "down" ? TrendingDown : Minus}
            color={summary?.scoreline_trend === "up" ? "red" : summary?.scoreline_trend === "down" ? "green" : "slate"}
            sub={summary?.latest_year ? `${summary.latest_year} 年` : undefined}
          />
          <SummaryCard
            label="报录比"
            value={admissionRatio?.ratio ?? "—"}
            icon={BarChart3}
            color="cyan"
            sub={admissionRatio ? `${admissionRatio.year} 年` : undefined}
          />
          <SummaryCard
            label="调剂名额"
            value={adjustmentTotal > 0 ? `${adjustmentTotal} 人` : "—"}
            icon={Users}
            color={adjustmentTotal > 0 ? "green" : "slate"}
            sub={adjustments.length > 0 ? `${adjustments.length} 条调剂信息` : undefined}
          />
          <SummaryCard
            label="分数线趋势"
            value={
              summary?.scoreline_trend === "up"
                ? "上升"
                : summary?.scoreline_trend === "down"
                  ? "下降"
                  : "平稳"
            }
            icon={BarChart3}
            color="amber"
          />
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left: Trend Chart */}
          <div className="lg:col-span-2 space-y-6">
            <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-brand-600" />
                  <h2 className="text-base font-semibold text-ink-800">复试分数线趋势</h2>
                </div>
                <select
                  value={selectedMajor}
                  onChange={(e) => setSelectedMajor(e.target.value)}
                  className="rounded-lg border border-paper-300 bg-white px-3 py-1.5 text-sm text-ink-800 focus:border-brand-500 focus:outline-none"
                >
                  {majors.length === 0 && <option value="">暂无专业数据</option>}
                  {majors.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>

              {trend && trend.years.length > 0 ? (
                <div className="space-y-6">
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="year" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="总分" stroke="#2563eb" strokeWidth={2} connectNulls />
                        <Line type="monotone" dataKey="政治" stroke="#16a34a" strokeWidth={2} connectNulls />
                        <Line type="monotone" dataKey="外语" stroke="#ea580c" strokeWidth={2} connectNulls />
                        <Line type="monotone" dataKey="业务课一" stroke="#9333ea" strokeWidth={2} connectNulls />
                        <Line type="monotone" dataKey="业务课二" stroke="#0891b2" strokeWidth={2} connectNulls />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  {(trend.application_counts.some((v) => v !== null) ||
                    trend.enrollment_counts.some((v) => v !== null)) && (
                    <div className="h-[240px]">
                      <h3 className="text-sm font-medium text-ink-700 mb-3">报录情况</h3>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="year" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Bar dataKey="报考人数" fill="#3b82f6" />
                          <Bar dataKey="录取人数" fill="#10b981" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              ) : (
                <div className="rounded-lg bg-paper-100 p-8 text-center text-sm text-ink-500">
                  暂无该专业的历年分数线数据
                </div>
              )}
            </div>

            {/* Programs */}
            <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <BookOpen className="h-5 w-5 text-brand-600" />
                <h2 className="text-base font-semibold text-ink-800">招生专业目录</h2>
              </div>
              <div className="space-y-3">
                {programs.map((program) => (
                  <button
                    key={program.id}
                    onClick={() => {
                      setSelectedMajor(program.major_name);
                      document.getElementById("scoreline-section")?.scrollIntoView({ behavior: "smooth" });
                    }}
                    className={cn(
                      "w-full text-left rounded-lg border p-4 transition-all cursor-pointer",
                      selectedMajor === program.major_name
                        ? "border-brand-400 bg-brand-50 shadow-sm"
                        : "border-paper-200 hover:border-brand-200 hover:bg-brand-50/50",
                    )}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div>
                        <h3 className="font-semibold text-ink-900">{program.major_name}</h3>
                        <p className="text-sm text-ink-500">{program.department}</p>
                      </div>
                      <Badge color="blue">{program.degree_type}</Badge>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                      <InfoItem label="招生人数" value={program.enrollment_quota ?? "—"} />
                      <InfoItem label="学制" value={program.duration ?? "—"} />
                      <InfoItem label="学习方式" value={program.study_mode ?? "—"} />
                      <InfoItem label="学费" value={program.tuition ?? "—"} />
                    </div>
                    {program.research_directions.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {program.research_directions.slice(0, 5).map((dir) => (
                          <Badge key={dir} color="slate" className="text-xs">
                            {dir}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right: Scorelines & Adjustments */}
          <div className="space-y-6">
            <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm" id="scoreline-section">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="h-5 w-5 text-brand-600" />
                <h2 className="text-base font-semibold text-ink-800">近年复试线</h2>
              </div>
              <div className="space-y-3">
                {scorelines.slice(0, 10).map((s) => (
                  <div key={s.id} className="rounded-lg border border-paper-200 p-3 text-sm">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-ink-900">{s.major_name}</span>
                      <Badge color="slate">{s.year}</Badge>
                    </div>
                    <div className="text-ink-500">
                      总分 <span className="font-semibold text-ink-900">{s.total_score_line ?? "—"}</span>
                      {s.degree_type && <span className="ml-2">{s.degree_type}</span>}
                    </div>
                    {(s.politics_score || s.foreign_language_score) && (
                      <div className="mt-1 text-xs text-ink-400">
                        单科：政 {s.politics_score ?? "—"} / 外 {s.foreign_language_score ?? "—"}
                      </div>
                    )}
                  </div>
                ))}
                {scorelines.length === 0 && (
                  <div className="text-sm text-ink-500 text-center py-4">暂无复试线数据</div>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <Users className="h-5 w-5 text-brand-600" />
                <h2 className="text-base font-semibold text-ink-800">调剂信息</h2>
              </div>
              <div className="space-y-3">
                {adjustments.slice(0, 10).map((a) => (
                  <div key={a.id} className="rounded-lg border border-paper-200 p-3 text-sm">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-ink-900">{a.major_name}</span>
                      <Badge color={a.status === "open" ? "green" : "slate"}>
                        {a.status === "open" ? "开放中" : "已结束"}
                      </Badge>
                    </div>
                    <div className="text-ink-500">{a.department}</div>
                    {a.adjustment_quota && (
                      <div className="mt-1 text-xs text-ink-400">名额：{a.adjustment_quota} 人</div>
                    )}
                    {(a.contact_email || a.contact_phone) && (
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-ink-500">
                        {a.contact_email && (
                          <span className="flex items-center gap-1">
                            <Mail className="h-3 w-3" />
                            {a.contact_email}
                          </span>
                        )}
                        {a.contact_phone && (
                          <span className="flex items-center gap-1">
                            <Phone className="h-3 w-3" />
                            {a.contact_phone}
                          </span>
                        )}
                      </div>
                    )}
                    {a.deadline && (
                      <div className="mt-1 text-xs text-ink-400 flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        截止：{a.deadline}
                      </div>
                    )}
                  </div>
                ))}
                {adjustments.length === 0 && (
                  <div className="text-sm text-ink-500 text-center py-4">暂无调剂信息</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Navigation: Search other schools */}
        <div className="mt-8 rounded-xl border border-paper-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <Search className="h-5 w-5 text-ink-400" />
            <input
              type="text"
              placeholder="搜索其他院校..."
              className="flex-1 text-sm text-ink-800 placeholder:text-ink-400 focus:outline-none"
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.target as HTMLInputElement).value.trim()) {
                  router.push(`/kaoyan/schools?search=${encodeURIComponent((e.target as HTMLInputElement).value)}`);
                }
              }}
            />
            <Button size="sm" onClick={(e) => {
              const input = (e.currentTarget as HTMLElement).previousElementSibling as HTMLInputElement;
              if (input?.value.trim()) {
                router.push(`/kaoyan/schools?search=${encodeURIComponent(input.value)}`);
              }
            }}>
              <Search className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  icon: Icon,
  color,
  sub,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  color: "blue" | "red" | "green" | "purple" | "amber" | "slate" | "cyan";
  sub?: string;
}) {
  const colorMap = {
    blue: "bg-blue-50 text-blue-600",
    red: "bg-red-50 text-red-600",
    green: "bg-green-50 text-green-600",
    purple: "bg-purple-50 text-purple-600",
    amber: "bg-amber-50 text-amber-600",
    slate: "bg-ink-50 text-ink-600",
    cyan: "bg-cyan-50 text-cyan-600",
  };

  return (
    <div className="rounded-xl border border-paper-200 bg-white p-4 shadow-sm">
      <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg mb-3", colorMap[color])}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="text-xs text-ink-500 mb-1">{label}</div>
      <div className="text-xl font-bold text-ink-900">{value}</div>
      {sub && <div className="text-xs text-ink-400 mt-1">{sub}</div>}
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-ink-400">{label}</div>
      <div className="font-medium text-ink-900">{value}</div>
    </div>
  );
}
