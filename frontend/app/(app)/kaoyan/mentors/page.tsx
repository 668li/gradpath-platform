"use client";

import { useCallback, useEffect, useState } from "react";
import { Search, Filter, Star, Users, BookOpen, TrendingUp } from "lucide-react";
import { mentorApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Input, Select, Badge } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { MentorResponse } from "@/types";

export default function MentorListPage() {
  const toast = useToast();
  const [mentors, setMentors] = useState<MentorResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [university, setUniversity] = useState("");
  const [department, setDepartment] = useState("");
  const [minRating, setMinRating] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const loadMentors = useCallback(async () => {
    setLoading(true);
    try {
      const res = await mentorApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        university: university || undefined,
        department: department || undefined,
        min_rating: minRating ? parseFloat(minRating) : undefined,
      });
      setMentors(res.items);
      setTotal(res.total);
    } catch {
      toast.push("加载导师列表失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page, search, university, department, minRating]);

  useEffect(() => {
    loadMentors();
  }, [loadMentors]);

  // 首次加载若为空且无筛选条件，自动重试一次（缓解热重载/网络抖动导致的空状态）
  useEffect(() => {
    if (
      !loading &&
      mentors.length === 0 &&
      total === 0 &&
      !search &&
      !university &&
      !department &&
      !minRating
    ) {
      const timer = setTimeout(() => loadMentors(), 800);
      return () => clearTimeout(timer);
    }
  }, [loading, mentors.length, total, search, university, department, minRating, loadMentors]);

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-brand-sm">
              <Users className="h-5 w-5" strokeWidth={2.2} />
            </div>
            <h1 className="font-display text-xl sm:text-2xl font-bold text-ink-900 tracking-tight">
              考研导师情报
            </h1>
          </div>
          <p className="text-sm text-ink-500 ml-[46px]">
            真实评价、学术信息、招生状态——打破导师信息差，选对导师少走弯路。
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
              <Input
                placeholder="搜索导师姓名..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadMentors()}
              />
            </div>
            <Select
              value={university}
              onChange={(e) => setUniversity(e.target.value)}
            >
              <option value="">全部院校</option>
              <option value="清华大学">清华大学</option>
              <option value="北京大学">北京大学</option>
              <option value="复旦大学">复旦大学</option>
              <option value="上海交通大学">上海交通大学</option>
              <option value="浙江大学">浙江大学</option>
              <option value="南京大学">南京大学</option>
              <option value="中国科学技术大学">中国科学技术大学</option>
              <option value="武汉大学">武汉大学</option>
              <option value="华中科技大学">华中科技大学</option>
              <option value="中山大学">中山大学</option>
            </Select>
            <Select
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
            >
              <option value="">全部院系</option>
              <option value="计算机">计算机相关</option>
              <option value="电子">电子相关</option>
              <option value="机械">机械相关</option>
              <option value="经济">经济相关</option>
              <option value="法学">法学相关</option>
              <option value="医学">医学相关</option>
            </Select>
            <Select
              value={minRating}
              onChange={(e) => setMinRating(e.target.value)}
            >
              <option value="">全部评分</option>
              <option value="4.5">4.5+ 优秀</option>
              <option value="4">4.0+ 良好</option>
              <option value="3.5">3.5+ 中等</option>
            </Select>
          </div>
        </div>

        {/* Stats */}
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-ink-500">
            共找到 <span className="font-semibold text-ink-700">{total}</span> 位导师
          </p>
        </div>

        {/* Mentor List */}
        {loading ? (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <LoadingState text="加载导师列表..." />
          </div>
        ) : mentors.length === 0 ? (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <EmptyState title="暂无导师数据" description="请尝试调整筛选条件" />
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {mentors.map((mentor) => (
              <MentorCard key={mentor.id} mentor={mentor} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {total > 20 && (
          <div className="mt-6 flex justify-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg border border-paper-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 hover:bg-paper-100 disabled:opacity-50"
            >
              上一页
            </button>
            <span className="flex items-center px-4 text-sm text-ink-500">
              第 {page} 页 / 共 {Math.ceil(total / 20)} 页
            </span>
            <button
              onClick={() => setPage((p) => Math.min(Math.ceil(total / 20), p + 1))}
              disabled={page >= Math.ceil(total / 20)}
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

function MentorCard({ mentor }: { mentor: MentorResponse }) {
  // 修复 P1 bug: 后端可能返回 null，导致 .toFixed()/.length 崩溃
  const avgRating = mentor.avg_rating ?? 0;
  const researchDirs = mentor.research_directions || [];
  const tags = mentor.tags || [];
  const ratingColor =
    avgRating >= 4.5
      ? "text-green-600 bg-green-50"
      : avgRating >= 4
        ? "text-blue-600 bg-blue-50"
        : avgRating >= 3.5
          ? "text-amber-600 bg-amber-50"
          : "text-ink-600 bg-ink-50";

  return (
    <a
      href={`/kaoyan/mentors/${mentor.id}`}
      className="group rounded-xl border border-paper-200 bg-white p-5 shadow-sm transition-all hover:border-brand-300 hover:shadow-md"
    >
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-ink-900 group-hover:text-brand-700 truncate">
            {mentor.name}
          </h3>
          <p className="text-sm text-ink-500 truncate">{mentor.title}</p>
        </div>
        <div className={cn("flex items-center gap-1 rounded-lg px-2 py-1", ratingColor)}>
          <Star className="h-4 w-4 fill-current" />
          <span className="text-sm font-semibold">{avgRating.toFixed(1)}</span>
        </div>
      </div>

      {/* University & Department */}
      <div className="mb-3 flex items-center gap-2 text-sm text-ink-600">
        <BookOpen className="h-4 w-4 text-ink-400" />
        <span className="truncate">{mentor.university}</span>
        <span className="text-ink-300">·</span>
        <span className="truncate">{mentor.department}</span>
      </div>

      {/* Research Directions */}
      {researchDirs.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1">
          {researchDirs.slice(0, 3).map((dir, i) => (
            <Badge key={`${dir}-${i}`} color="slate">
              {dir}
            </Badge>
          ))}
          {researchDirs.length > 3 && (
            <Badge color="slate">+{researchDirs.length - 3}</Badge>
          )}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 border-t border-paper-100 pt-3">
        <div className="text-center">
          <p className="text-xs text-ink-400">论文</p>
          <p className="text-sm font-semibold text-ink-700">{mentor.paper_count}</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-ink-400">项目</p>
          <p className="text-sm font-semibold text-ink-700">{mentor.project_count}</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-ink-400">评价</p>
          <p className="text-sm font-semibold text-ink-700">{mentor.review_count}</p>
        </div>
      </div>

      {/* Enrollment Status */}
      <div className="mt-3 flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-ink-400" />
        <span
          className={cn(
            "text-xs font-medium",
            mentor.enrollment_status === "accepting"
              ? "text-green-600"
              : mentor.enrollment_status === "not_accepting"
                ? "text-red-600"
                : "text-ink-500",
          )}
        >
          {mentor.enrollment_status === "accepting"
            ? "正在招生"
            : mentor.enrollment_status === "not_accepting"
              ? "暂停招生"
              : "招生状态未知"}
        </span>
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {tags.map((tag, i) => (
            <span
              key={`${tag}-${i}`}
              className="rounded bg-brand-50 px-1.5 py-0.5 text-xs font-medium text-brand-700"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </a>
  );
}
