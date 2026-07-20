"use client";

import { useEffect, useMemo, useState, useRef, memo } from "react";
import { useRouter } from "next/navigation";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  School,
  Search,
  Filter,
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
  BookOpen,
  ArrowRight,
  BarChart3,
} from "lucide-react";
import { Button, Input, Select, Badge } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { gradIntelApi, useApi } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import type { GradYanzhaoProgram, GradSchoolDataSummary, GradScorelineRecord } from "@/types";

// 优化：PAGE_SIZE 提升，配合虚拟滚动减少分页交互
const PAGE_SIZE = 100;
const SCHOOLS_PER_ROW = 3;
const ROW_ESTIMATE_SIZE = 280;

interface SchoolStats {
  university_name: string;
  admission_ratio: string | null; // 报录比
  avg_scoreline: number | null; // 平均复试线
  has_adjustment: boolean; // 是否有调剂
  adjustment_total: number; // 调剂总名额
}

export default function SchoolsPage() {
  const router = useRouter();
  const toast = useToast();
  const [summaries, setSummaries] = useState<Record<string, GradSchoolDataSummary>>({});
  const [stats, setStats] = useState<Record<string, SchoolStats>>({});
  const [search, setSearch] = useState("");
  const [major, setMajor] = useState("");
  const [degreeType, setDegreeType] = useState("");
  const [adjustmentOnly, setAdjustmentOnly] = useState(false);
  const [page, setPage] = useState(1);

  // 主列表：SWR 自动按 URL 重新请求（搜索/筛选/分页变化时自动触发）
  const programsUrl = useMemo(() => {
    const params = new URLSearchParams();
    if (search) params.set("university_name", search);
    if (major) params.set("major_name", major);
    if (degreeType) params.set("degree_type", degreeType);
    params.set("limit", String(PAGE_SIZE));
    params.set("offset", String((page - 1) * PAGE_SIZE));
    return `/api/grad-intel/yanzhao-programs?${params.toString()}`;
  }, [search, major, degreeType, page]);

  const {
    data: programs,
    error,
    isLoading: loading,
    mutate,
  } = useApi<GradYanzhaoProgram[]>(programsUrl, { fallbackData: [] });

  // 错误提示
  useEffect(() => {
    if (error) toast.push("加载院校数据失败", "error");
  }, [error, toast]);

  // 重置分页：搜索/筛选变化时回到第 1 页
  useEffect(() => {
    setPage(1);
  }, [search, major, degreeType]);

  // 院校卡片聚合数据：主列表变更后并发拉取每个院校的 summary/scorelines/adjustments
  useEffect(() => {
    if (!programs || programs.length === 0) {
      setSummaries({});
      setStats({});
      return;
    }

    let cancelled = false;
    const uniqueUniversities = Array.from(new Set(programs.map((p) => p.university_name)));
    const summaryMap: Record<string, GradSchoolDataSummary> = {};
    const statsMap: Record<string, SchoolStats> = {};

    Promise.all(
      uniqueUniversities.map(async (name) => {
        const [summary, scorelines, adjustments] = await Promise.all([
          gradIntelApi.getSchoolSummary(name).catch((): GradSchoolDataSummary => ({
            university_name: name,
            program_count: programs.filter((p) => p.university_name === name).length,
            latest_year: null,
            latest_scoreline: null,
            scoreline_trend: "stable" as const,
            has_adjustment: false,
            adjustment_count: 0,
          })),
          gradIntelApi.listScorelines({ university_name: name, limit: 100 }).catch(() => [] as GradScorelineRecord[]),
          gradIntelApi.listAdjustments({ university_name: name, limit: 100 }).catch(() => []),
        ]);

        summaryMap[name] = summary;

        // 计算报录比（取最近一年有数据的）
        const latestScoreline = scorelines
          .filter((s) => s.application_count && s.enrollment_count)
          .sort((a, b) => b.year - a.year)[0];
        const admissionRatio = latestScoreline
          ? `${latestScoreline.application_count}:${latestScoreline.enrollment_count}`
          : null;

        // 计算平均复试线（取最近3年）
        const recentScorelines = scorelines
          .filter((s) => s.total_score_line)
          .sort((a, b) => b.year - a.year)
          .slice(0, 3);
        const avgScoreline =
          recentScorelines.length > 0
            ? Math.round(
                recentScorelines.reduce((sum, s) => sum + (s.total_score_line || 0), 0) /
                  recentScorelines.length,
              )
            : null;

        // 调剂总名额
        const adjustmentTotal = adjustments.reduce(
          (sum, a) => sum + (a.adjustment_quota || 0),
          0,
        );

        statsMap[name] = {
          university_name: name,
          admission_ratio: admissionRatio,
          avg_scoreline: avgScoreline,
          has_adjustment: adjustments.length > 0,
          adjustment_total: adjustmentTotal,
        };
      }),
    ).then(() => {
      if (!cancelled) {
        setSummaries(summaryMap);
        setStats(statsMap);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [programs]);

  const programsList = programs ?? [];
  const total = programsList.length === PAGE_SIZE ? page * PAGE_SIZE + 1 : page * PAGE_SIZE;

  const schools = useMemo(() => {
    const map = new Map<string, GradYanzhaoProgram[]>();
    programsList.forEach((p) => {
      if (!map.has(p.university_name)) map.set(p.university_name, []);
      map.get(p.university_name)!.push(p);
    });
    let result = Array.from(map.entries()).map(([name, list]) => ({ name, programs: list }));

    // 调剂筛选
    if (adjustmentOnly) {
      result = result.filter(({ name }) => stats[name]?.has_adjustment);
    }

    return result;
  }, [programsList, adjustmentOnly, stats]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // 手动刷新（搜索按钮 / 回车）
  const reload = () => mutate();

  // 虚拟滚动：按 3 列分组院校为行
  const parentRef = useRef<HTMLDivElement>(null);
  const schoolRows = useMemo(() => {
    const rows: { name: string; programs: GradYanzhaoProgram[] }[][] = [];
    for (let i = 0; i < schools.length; i += SCHOOLS_PER_ROW) {
      rows.push(schools.slice(i, i + SCHOOLS_PER_ROW));
    }
    return rows;
  }, [schools]);
  const rowVirtualizer = useVirtualizer({
    count: schoolRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_ESTIMATE_SIZE,
    overscan: 4,
  });

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-brand-sm">
              <School className="h-5 w-5" strokeWidth={2.2} />
            </div>
            <h1 className="font-display text-xl sm:text-2xl font-bold text-ink-900 tracking-tight">
              院校情报
            </h1>
          </div>
          <p className="text-sm text-ink-500 ml-[46px]">
            真实报录比、复试线、调剂信息——用数据打破择校信息差。
          </p>
        </div>

        {/* Search & Filter */}
        <div className="mb-6 rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="h-4 w-4 text-ink-400" />
            <h2 className="text-sm font-semibold text-ink-700">搜索与筛选</h2>
          </div>
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            <div className="sm:col-span-2 lg:col-span-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
                <Input
                  placeholder="搜索院校名称..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && reload()}
                  className="pl-9"
                />
              </div>
            </div>
            <div className="relative">
              <BookOpen className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
              <Input
                placeholder="搜索专业..."
                value={major}
                onChange={(e) => setMajor(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && reload()}
                className="pl-9"
              />
            </div>
            <Select value={degreeType} onChange={(e) => setDegreeType(e.target.value)}>
              <option value="">全部学位类型</option>
              <option value="学术学位">学术学位</option>
              <option value="专业学位">专业学位</option>
            </Select>
            <Button onClick={reload}>
              <Search className="h-4 w-4 mr-1.5" />
              查询院校
            </Button>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <button
              onClick={() => setAdjustmentOnly(!adjustmentOnly)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                adjustmentOnly
                  ? "bg-brand-600 text-white"
                  : "bg-paper-100 text-ink-700 hover:bg-paper-200",
              )}
            >
              <Users className="h-4 w-4" />
              仅显示有调剂院校
            </button>
            {adjustmentOnly && (
              <span className="text-xs text-ink-500">
                已筛选 {schools.length} 所有调剂名额的院校
              </span>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-ink-500">
            共找到 <span className="font-semibold text-ink-700">{schools.length}</span> 所院校
          </p>
        </div>

        {/* School List（虚拟滚动） */}
        {loading ? (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <LoadingState text="加载院校数据..." />
          </div>
        ) : schools.length === 0 ? (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <EmptyState
              title="暂无院校数据"
              description="请尝试调整筛选条件，或等待真实数据爬取完成"
              action={
                <Button variant="secondary" onClick={() => router.push("/kaoyan")}>
                  返回考研首页
                </Button>
              }
            />
          </div>
        ) : (
          <div
            ref={parentRef}
            style={{ height: "720px", overflow: "auto" }}
            className="rounded-xl"
          >
            <div
              style={{
                height: `${rowVirtualizer.getTotalSize()}px`,
                position: "relative",
                width: "100%",
              }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const row = schoolRows[virtualRow.index];
                return (
                  <div
                    key={virtualRow.index}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 pb-4"
                  >
                    {row.map(({ name, programs: list }) => (
                      <SchoolCardMemo
                        key={name}
                        name={name}
                        programs={list}
                        summary={summaries[name]}
                        stats={stats[name]}
                        onClick={() => router.push(`/kaoyan/schools/${encodeURIComponent(name)}`)}
                      />
                    ))}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Pagination */}
        {!loading && schools.length > 0 && (
          <div className="mt-6 flex justify-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg border border-paper-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 hover:bg-paper-100 disabled:opacity-50"
            >
              上一页
            </button>
            <span className="flex items-center px-4 text-sm text-ink-500">
              第 {page} 页 / 共 {totalPages} 页
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-lg border border-paper-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 hover:bg-paper-100 disabled:opacity-50"
            >
              下一页
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function SchoolCard({
  name,
  programs,
  summary,
  stats,
  onClick,
}: {
  name: string;
  programs: GradYanzhaoProgram[];
  summary?: GradSchoolDataSummary;
  stats?: SchoolStats;
  onClick: () => void;
}) {
  const majors = Array.from(new Set(programs.map((p) => p.major_name))).slice(0, 3);
  const trendIcon =
    summary?.scoreline_trend === "up" ? (
      <TrendingUp className="h-4 w-4 text-red-500" />
    ) : summary?.scoreline_trend === "down" ? (
      <TrendingDown className="h-4 w-4 text-green-500" />
    ) : (
      <Minus className="h-4 w-4 text-ink-400" />
    );

  return (
    <div
      onClick={onClick}
      className="group cursor-pointer rounded-xl border border-paper-200 bg-white p-5 shadow-sm transition-all hover:border-brand-300 hover:shadow-md"
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-ink-900 group-hover:text-brand-700 truncate">
            {name}
          </h3>
          <p className="text-sm text-ink-500 truncate">
            {programs[0]?.department} 等 {programs.length} 个专业方向
          </p>
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          <School className="h-5 w-5" />
        </div>
      </div>

      {/* 关键指标展示 */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-paper-100 p-3">
          <div className="flex items-center gap-1.5 text-xs text-ink-500 mb-1">
            <BarChart3 className="h-3.5 w-3.5" />
            复试线
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-ink-900">
              {summary?.latest_scoreline ?? stats?.avg_scoreline ?? "—"}
            </span>
            {summary?.latest_scoreline && trendIcon}
          </div>
        </div>
        <div className="rounded-lg bg-paper-100 p-3">
          <div className="flex items-center gap-1.5 text-xs text-ink-500 mb-1">
            <Users className="h-3.5 w-3.5" />
            报录比
          </div>
          <div className="text-lg font-bold text-ink-900">
            {stats?.admission_ratio ?? "—"}
          </div>
        </div>
      </div>

      {/* 调剂信息标签 */}
      {stats?.has_adjustment && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2">
          <Users className="h-4 w-4 text-green-600" />
          <span className="text-sm font-medium text-green-700">
            有调剂名额 {stats.adjustment_total > 0 && `(${stats.adjustment_total}人)`}
          </span>
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        {majors.map((m) => (
          <Badge key={m} color="blue">
            {m}
          </Badge>
        ))}
      </div>

      <div className="flex items-center text-sm font-medium text-brand-600 group-hover:text-brand-700">
        查看近 3 年数据
        <ArrowRight className="h-4 w-4 ml-1.5 group-hover:translate-x-1 transition-transform" />
      </div>
    </div>
  );
}

const SchoolCardMemo = memo(SchoolCard);
