"use client";

import { useCallback, useEffect, useState } from "react";
import { Trophy, Star, Filter } from "lucide-react";
import { outcomeReportApi } from "@/lib/api";
import type { OutcomeReport, OutcomeStats } from "@/lib/api/outcome-report";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Input, Select, Field } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";

const CURRENT_YEAR = new Date().getFullYear();

export default function LandingWallPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [reports, setReports] = useState<OutcomeReport[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  const [filters, setFilters] = useState({ school: "", major: "", year: "" });
  const [showFilters, setShowFilters] = useState(false);

  // Stats for a selected school+major
  const [selectedSchool, setSelectedSchool] = useState("");
  const [selectedMajor, setSelectedMajor] = useState("");
  const [stats, setStats] = useState<OutcomeStats | null>(null);

  const loadWall = useCallback(async () => {
    setLoading(true);
    try {
      const res = await outcomeReportApi.getLandingWall({
        school: filters.school || undefined,
        major: filters.major || undefined,
        year: filters.year ? Number(filters.year) : undefined,
        page,
        page_size: 20,
      });
      setReports(res.items);
      setTotal(res.total);
    } catch {
      toast.push("加载上岸墙失败", "error");
    } finally {
      setLoading(false);
    }
  }, [filters, page, toast]);

  useEffect(() => {
    loadWall();
  }, [loadWall]);

  const loadStats = async () => {
    if (!selectedSchool || !selectedMajor) {
      toast.push("请输入院校和专业", "error");
      return;
    }
    try {
      const s = await outcomeReportApi.getStats(selectedSchool, selectedMajor);
      setStats(s);
    } catch {
      toast.push("暂无该院校+专业的统计数据", "error");
      setStats(null);
    }
  };

  const updateFilter = (key: string, value: string) => setFilters(prev => ({ ...prev, [key]: value }));

  const totalPages = Math.ceil(total / 20);

  if (loading && page === 1) return <LoadingState />;

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <Trophy className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">上岸墙</h1>
        <p className="text-sm text-ink-400 mt-2">
          看看同路人的真实结果和经验
        </p>
      </div>

      {/* Stats Lookup */}
      <div className="card space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <Star className="h-4 w-4 text-amber-500" />
          <h2 className="text-sm font-semibold text-ink-700">查看院校+专业统计</h2>
        </div>
        <div className="flex gap-3 items-end">
          <Field label="院校" className="flex-1">
            <Input
              value={selectedSchool}
              onChange={e => setSelectedSchool(e.target.value)}
              placeholder="如：北京大学"
            />
          </Field>
          <Field label="专业" className="flex-1">
            <Input
              value={selectedMajor}
              onChange={e => setSelectedMajor(e.target.value)}
              placeholder="如：计算机科学"
            />
          </Field>
          <Button onClick={loadStats} variant="secondary" size="md" className="mb-0.5">
            查看统计
          </Button>
        </div>

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
            <div className="rounded-lg bg-brand-50 p-3 text-center">
              <p className="text-2xl font-bold text-brand-700">{stats.total_outcomes}</p>
              <p className="text-xs text-ink-500">总报告数</p>
            </div>
            <div className="rounded-lg bg-green-50 p-3 text-center">
              <p className="text-2xl font-bold text-green-700">
                {stats.acceptance_rate != null ? `${(stats.acceptance_rate * 100).toFixed(0)}%` : "-"}
              </p>
              <p className="text-xs text-ink-500">录取率</p>
            </div>
            <div className="rounded-lg bg-amber-50 p-3 text-center">
              <p className="text-2xl font-bold text-amber-700">
                {stats.avg_score_total ?? "-"}
              </p>
              <p className="text-xs text-ink-500">平均分</p>
            </div>
            <div className="rounded-lg bg-purple-50 p-3 text-center">
              <p className="text-2xl font-bold text-purple-700">
                {Object.keys(stats.path_breakdown).length > 0
                  ? Object.entries(stats.path_breakdown).map(([k, v]) => `${k}:${v}`).join(" ")
                  : "-"}
              </p>
              <p className="text-xs text-ink-500">路径分布</p>
            </div>
          </div>
        )}

        {stats && stats.common_reflections.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-xs font-medium text-ink-600">过来人的反思：</p>
            {stats.common_reflections.slice(0, 3).map((r, i) => (
              <div key={`reflection-${i}`} className="rounded-lg bg-paper-50 p-3 text-xs text-ink-600 leading-relaxed">
                "{r}"
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
        >
          <Filter className="h-4 w-4" />
          筛选
        </Button>
        <span className="text-xs text-ink-400">共 {total} 条报告</span>
      </div>

      {showFilters && (
        <div className="card flex gap-3 items-end">
          <Field label="院校" className="flex-1">
            <Input
              value={filters.school}
              onChange={e => updateFilter("school", e.target.value)}
              placeholder="搜索院校…"
            />
          </Field>
          <Field label="专业" className="flex-1">
            <Input
              value={filters.major}
              onChange={e => updateFilter("major", e.target.value)}
              placeholder="搜索专业…"
            />
          </Field>
          <Field label="年份" className="w-28">
            <Select value={filters.year} onChange={e => { updateFilter("year", e.target.value); setPage(1); }}>
              <option value="">全部</option>
              {Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i).map(y => (
                <option key={y} value={String(y)}>{y}</option>
              ))}
            </Select>
          </Field>
          <Button
            variant="secondary"
            size="md"
            onClick={() => { setFilters({ school: "", major: "", year: "" }); setPage(1); }}
          >
            重置
          </Button>
        </div>
      )}

      {/* Reports Wall */}
      {reports.length === 0 ? (
        <EmptyState
          title="暂无上岸报告"
          description="成为第一个分享的人，帮助后来者！"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {reports.map(r => (
            <div
              key={r.id}
              className={cn(
                "card border-l-4 transition-all hover:shadow-md",
                r.outcome_type === "grad_civil_career" ? "border-l-green-500" :
                r.outcome_type === "adjustment" ? "border-l-amber-500" :
                "border-l-red-400",
              )}
            >
              {/* School & Major */}
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="text-sm font-semibold text-ink-800">
                    {r.target_school || "未填写院校"}
                  </p>
                  <p className="text-xs text-ink-400 mt-0.5">
                    {r.target_major || "未填写专业"} · {r.year}
                  </p>
                </div>
                <span className={cn(
                  "text-xs px-2 py-0.5 rounded-full shrink-0",
                  r.outcome_type === "grad_civil_career" ? "bg-green-100 text-green-700" :
                  r.outcome_type === "adjustment" ? "bg-amber-100 text-amber-700" :
                  "bg-red-100 text-red-700",
                )}>
                  {r.outcome_type === "grad_civil_career" ? "上岸" :
                   r.outcome_type === "adjustment" ? "调剂" : "未上岸"}
                </span>
              </div>

              {/* Actual school if different */}
              {r.actual_school && r.actual_school !== r.target_school && (
                <p className="text-xs text-brand-600 mb-2">
                  录取: {r.actual_school}{r.actual_major ? ` · ${r.actual_major}` : ""}
                </p>
              )}

              {/* Score */}
              {r.score_total && (
                <div className="flex items-center gap-3 text-xs text-ink-500 mb-2">
                  <span>总分: <strong className="text-ink-700">{r.score_total}</strong></span>
                  {r.score_politics && <span>政治{r.score_politics}</span>}
                  {r.score_english && <span>英语{r.score_english}</span>}
                  {r.score_major1 && <span>专一{r.score_major1}</span>}
                  {r.score_major2 && <span>专二{r.score_major2}</span>}
                </div>
              )}

              {/* Admission path */}
              {r.admission_path && r.admission_path !== "normal" && (
                <p className="text-xs text-ink-400 mb-1">
                  录取方式: {r.admission_path === "adjustment" ? "调剂" : "转专业"}
                </p>
              )}

              {/* Confidence & Satisfaction */}
              <div className="flex items-center gap-4 text-xs text-ink-400 mb-2">
                {r.confidence_before != null && (
                  <span>考前信心: {(r.confidence_before * 100).toFixed(0)}%</span>
                )}
                {r.satisfaction_after != null && (
                  <span>满意度: {"⭐".repeat(r.satisfaction_after)}</span>
                )}
              </div>

              {/* Reflection */}
              {r.what_i_would_do_differently && (
                <div className="rounded-lg bg-paper-50 p-3 mt-2">
                  <p className="text-xs font-medium text-ink-500 mb-1">反思</p>
                  <p className="text-xs text-ink-600 leading-relaxed">
                    {r.what_i_would_do_differently}
                  </p>
                </div>
              )}

              {/* Advice */}
              {r.advice_for_others && (
                <div className="rounded-lg bg-brand-50 p-3 mt-2">
                  <p className="text-xs font-medium text-brand-600 mb-1">建议</p>
                  <p className="text-xs text-ink-600 leading-relaxed">
                    {r.advice_for_others}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
          >
            上一页
          </Button>
          <span className="text-sm text-ink-500">{page} / {totalPages}</span>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
          >
            下一页
          </Button>
        </div>
      )}
    </div>
  );
}
