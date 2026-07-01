"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Send, Trash2, BarChart3, Briefcase, Star } from "lucide-react";
import { interviewApi } from "@/lib/api";
import { Button, Input, Select } from "@/components/ui/form-controls";
import { EmptyState } from "@/components/ui/empty";
import { ListSkeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/ui/pagination";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import {
  INTERVIEW_DIMENSIONS,
  INTERVIEW_DIMENSION_LABEL,
  INTERVIEW_RESULTS,
  INTERVIEW_RESULT_LABEL,
} from "@/lib/constants";
import type {
  CompanyInfo,
  InterviewReport,
  InterviewStats,
  InterviewSubmit,
} from "@/types";

const YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025];

function encodeParam(value: string): string {
  return encodeURIComponent(btoa(unescape(encodeURIComponent(value))));
}

export default function InterviewPage() {
  const router = useRouter();
  const toast = useToast();

  const [stats, setStats] = useState<InterviewStats | null>(null);
  const [companies, setCompanies] = useState<CompanyInfo[]>([]);
  const [myReports, setMyReports] = useState<InterviewReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const PAGE_SIZE = 20;

  // 分页加载“我的面试报告”
  const loadMyReports = useCallback(
    async (targetPage: number) => {
      try {
        let target = targetPage;
        let data = await interviewApi.myReports({
          page: target,
          page_size: PAGE_SIZE,
        });
        // 若目标页为空且非首页，回退到首页
        if (data.items.length === 0 && target > 1) {
          target = 1;
          data = await interviewApi.myReports({
            page: 1,
            page_size: PAGE_SIZE,
          });
        }
        setMyReports(data.items);
        setTotal(data.total);
        setPage(target);
      } catch (err) {
        toast.push(
          err instanceof Error ? err.message : "加载失败",
          "error",
        );
      }
    },
    [toast],
  );

  // 表单状态
  const [company, setCompany] = useState("");
  const [position, setPosition] = useState("");
  const [city, setCity] = useState("");
  const [interviewYear, setInterviewYear] = useState<number>(2024);
  const [rounds, setRounds] = useState<number>(3);
  const [result, setResult] = useState("pending");
  const [dimensions, setDimensions] = useState<string[]>([]);
  const [difficulty, setDifficulty] = useState<number>(3);
  const [summary, setSummary] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [st, comps, mine] = await Promise.all([
          interviewApi.stats(),
          interviewApi.companies(),
          interviewApi.myReports({ page: 1, page_size: PAGE_SIZE }),
        ]);
        setStats(st);
        setCompanies(comps);
        setMyReports(mine.items);
        setTotal(mine.total);
      } catch (err) {
        toast.push(
          err instanceof Error ? err.message : "加载数据失败",
          "error",
        );
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast]);

  const toggleDimension = (dim: string) => {
    setDimensions((prev) =>
      prev.includes(dim) ? prev.filter((d) => d !== dim) : [...prev, dim],
    );
  };

  const refreshStats = async () => {
    try {
      const st = await interviewApi.stats();
      setStats(st);
    } catch {
      // 静默失败
    }
  };

  const handleSubmit = async () => {
    const co = company.trim();
    const pos = position.trim();
    if (!co || !pos) {
      toast.push("请填写公司和岗位", "error");
      return;
    }

    const body: InterviewSubmit = {
      company: co,
      position: pos,
      interview_year: interviewYear,
    };
    if (city.trim()) body.city = city.trim();
    if (rounds) body.rounds = rounds;
    if (result) body.result = result;
    if (dimensions.length > 0) body.dimensions = dimensions;
    if (difficulty) body.difficulty = difficulty;
    if (summary.trim()) body.summary = summary.trim();

    setSubmitting(true);
    try {
      await interviewApi.submit(body);
      toast.push("提交成功，感谢你的分享！", "success");
      setCompany("");
      setPosition("");
      setCity("");
      setSummary("");
      setDimensions([]);
      loadMyReports(page);
      refreshStats();
    } catch (err) {
      toast.push(
        err instanceof Error ? err.message : "提交失败",
        "error",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await interviewApi.remove(id);
      toast.push("已删除该记录", "success");
      loadMyReports(page);
      refreshStats();
    } catch (err) {
      toast.push(
        err instanceof Error ? err.message : "删除失败",
        "error",
      );
    }
  };

  const handleViewAggregate = () => {
    const co = company.trim();
    if (!co) {
      toast.push("请先填写公司名称", "info");
      return;
    }
    const c = encodeParam(co);
    router.push(`/interview/result?c=${c}`);
  };

  if (loading) return <ListSkeleton />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">面试经验</h1>
        <p className="text-sm text-slate-500 mt-1">
          匿名分享你的面试经历，聚合后展示“这家公司面试官实际看重什么”
        </p>
      </div>

      {/* 统计 */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-brand-600">
              {stats.total_reports}
            </p>
            <p className="text-xs text-slate-500">面试样本</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-600">
              {stats.company_count}
            </p>
            <p className="text-xs text-slate-500">覆盖公司</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-amber-600">
              {stats.position_count}
            </p>
            <p className="text-xs text-slate-500">覆盖岗位</p>
          </div>
        </div>
      )}

      {/* 提交表单 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <Briefcase className="h-4 w-4 text-brand-500" />
          匿名提交面试经验
        </h2>

        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                公司 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="如：腾讯"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                list="interview-company-list"
              />
              <datalist id="interview-company-list">
                {companies.map((c) => (
                  <option key={c.name} value={c.name} />
                ))}
              </datalist>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                岗位 <span className="text-red-500">*</span>
              </label>
              <Input
                value={position}
                onChange={(e) => setPosition(e.target.value)}
                placeholder="如：后端开发"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                城市
              </label>
              <Input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="如：深圳"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                面试年份 <span className="text-red-500">*</span>
              </label>
              <Select
                value={interviewYear}
                onChange={(e) => setInterviewYear(Number(e.target.value))}
              >
                {YEARS.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                面试轮数
              </label>
              <Select
                value={rounds}
                onChange={(e) => setRounds(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((r) => (
                  <option key={r} value={r}>
                    {r} 轮
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {/* 面试结果 */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-2">
              面试结果 <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {INTERVIEW_RESULTS.map((r) => {
                const active = result === r;
                return (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setResult(r)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-brand-300 hover:text-brand-600",
                    )}
                  >
                    {INTERVIEW_RESULT_LABEL[r] ?? r}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 考察维度多选 */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-2">
              考察维度 <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {INTERVIEW_DIMENSIONS.map((dim) => {
                const active = dimensions.includes(dim);
                return (
                  <button
                    key={dim}
                    type="button"
                    onClick={() => toggleDimension(dim)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-brand-300 hover:text-brand-600",
                    )}
                  >
                    {INTERVIEW_DIMENSION_LABEL[dim] ?? dim}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 难度评分 */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-2">
              难度评分
            </label>
            <div className="flex items-center gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setDifficulty(star)}
                  className="p-1"
                  aria-label={`${star} 星`}
                >
                  <Star
                    className={cn(
                      "h-6 w-6 transition-colors",
                      star <= difficulty
                        ? "fill-amber-400 text-amber-400"
                        : "text-slate-300 hover:text-amber-300",
                    )}
                  />
                </button>
              ))}
              <span className="text-sm text-slate-500 ml-2">
                {difficulty}/5
              </span>
            </div>
          </div>

          {/* 一句话总结 */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              一句话总结
            </label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="如：侧重算法和系统设计，三轮技术面"
              maxLength={200}
              rows={2}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Button onClick={handleSubmit} loading={submitting}>
              <Send className="h-4 w-4" /> 提交报告
            </Button>
            <Button variant="secondary" onClick={handleViewAggregate}>
              <BarChart3 className="h-4 w-4" /> 查看聚合结果
            </Button>
            <span className="text-xs text-slate-400">
              数据完全匿名，仅用于聚合统计
            </span>
          </div>
        </div>
      </div>

      {/* 我的提交记录 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">我的提交记录</h2>
        {myReports.length === 0 ? (
          <EmptyState
            title="暂无提交记录"
            description="提交你的第一份面试报告，它会出现在这里"
          />
        ) : (
          <div className="space-y-3">
            {myReports.map((r) => (
              <div
                key={r.id}
                className="rounded-lg border border-slate-100 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-slate-800">
                        {r.company} · {r.position}
                      </span>
                      <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
                        {INTERVIEW_RESULT_LABEL[r.result] ?? r.result}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      {r.interview_year}年{r.city ? ` · ${r.city}` : ""}
                      {r.rounds ? ` · ${r.rounds}轮` : ""}
                      {r.difficulty ? ` · 难度${r.difficulty}/5` : ""}
                    </p>
                    {r.dimensions.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {r.dimensions.map((d) => (
                          <span
                            key={d}
                            className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500"
                          >
                            {INTERVIEW_DIMENSION_LABEL[d] ?? d}
                          </span>
                        ))}
                      </div>
                    )}
                    {r.summary && (
                      <p className="mt-1 text-sm text-slate-600">{r.summary}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Link
                      href={`/interview/result?c=${encodeParam(r.company)}`}
                      className="text-xs text-brand-600 hover:underline"
                    >
                      查看聚合
                    </Link>
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                      aria-label="删除记录"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onPageChange={(p) => loadMyReports(p)}
        />
      </div>
    </div>
  );
}
