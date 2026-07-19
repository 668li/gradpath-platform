"use client";

import { useEffect, useState, useCallback } from "react";
import { Brain, Clock, Eye, Bookmark, ChevronLeft, ChevronRight, ExternalLink, X, Sparkles } from "lucide-react";
import { learningMethodsApi } from "@/lib/api";
import type { LearningMethod, LearningMethodTag, LearningMethodStats } from "@/lib/api";
import { Badge } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { BarChart } from "@/components/charts";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const TAG_COLORS: Record<string, "slate" | "green" | "amber" | "red" | "blue" | "purple"> = {
  记忆: "blue",
  理解: "green",
  应用: "purple",
  "费曼学习法": "amber",
  间隔重复: "red",
  思维导图: "blue",
  刻意练习: "green",
  番茄工作法: "amber",
};

function getTagColor(name: string) {
  return TAG_COLORS[name] || "slate";
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function LearningMethodsPage() {
  const [methods, setMethods] = useState<LearningMethod[]>([]);
  const [recommended, setRecommended] = useState<LearningMethod[]>([]);
  const [tags, setTags] = useState<LearningMethodTag[]>([]);
  const [stats, setStats] = useState<LearningMethodStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [selected, setSelected] = useState<LearningMethod | null>(null);
  const pageSize = 10;

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [listRes, recRes, tagRes, statsRes] = await Promise.all([
        learningMethodsApi.list({ page, page_size: pageSize, tag: activeTag || undefined }),
        learningMethodsApi.recommend(5),
        learningMethodsApi.tags(),
        learningMethodsApi.stats(),
      ]);
      setMethods(listRes.items || []);
      setTotal(listRes.total || 0);
      setRecommended(recRes || []);
      setTags(tagRes || []);
      setStats(statsRes || null);
    } catch {
      toast.error("加载学习方法失败");
    } finally {
      setLoading(false);
    }
  }, [page, activeTag]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleTagClick = (tagName: string | null) => {
    setActiveTag(tagName === activeTag ? null : tagName);
    setPage(1);
  };

  const handleBookmark = async (id: string) => {
    try {
      await learningMethodsApi.bookmark(id);
      toast.success("收藏成功");
    } catch {
      toast.error("收藏失败");
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  const rankingData = (stats?.category_counts || []).map((c) => ({
    name: c.category,
    count: c.count,
  }));

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-ink-800 flex items-center justify-center gap-2">
          <Brain className="h-7 w-7 text-brand-500" />
          学习方法库
        </h1>
        <p className="text-sm text-ink-500 mt-1">科学方法，高效学习</p>
      </div>

      {/* Recommended Section */}
      {!loading && recommended.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-ink-800 mb-3 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-amber-500" />
            为你推荐
          </h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {recommended.map((item) => (
              <div
                key={item.id}
                onClick={() => setSelected(item)}
                className="rounded-xl border border-paper-300 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
              >
                {/* AI推荐理由 */}
                {item.reason && (
                  <div className="mb-3 rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700 border border-brand-100">
                    <Sparkles className="h-3 w-3 inline mr-1" />
                    {item.reason}
                  </div>
                )}
                <h3 className="text-base font-semibold text-ink-800 leading-tight group-hover:text-brand-600 transition-colors line-clamp-2">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm text-ink-500 line-clamp-2">{item.summary}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {(item.tags || []).slice(0, 3).map((t) => (
                    <Badge key={t} color={getTagColor(t)}>{t}</Badge>
                  ))}
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-ink-400">
                  <span>{item.source}</span>
                  <span>{formatDate(item.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Tag Filter */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
        <button
          onClick={() => handleTagClick(null)}
          className={cn(
            "flex-shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
            activeTag === null
              ? "bg-brand-500 text-white"
              : "bg-paper-200 text-ink-600 hover:bg-paper-300"
          )}
        >
          全部
        </button>
        {tags.map((tag) => (
          <button
            key={tag.id}
            onClick={() => handleTagClick(tag.name)}
            className={cn(
              "flex-shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap",
              activeTag === tag.name
                ? "bg-brand-500 text-white"
                : "bg-paper-200 text-ink-600 hover:bg-paper-300"
            )}
          >
            {tag.name}
            <span className="ml-1 text-xs opacity-70">({tag.count})</span>
          </button>
        ))}
      </div>

      <div className="flex gap-6">
        {/* Main Content */}
        <div className="flex-1 min-w-0">
          {loading ? (
            <LoadingState text="加载中…" />
          ) : methods.length === 0 ? (
            <EmptyState title="暂无学习方法" description="请稍后再来看看" />
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                {methods.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-xl border border-paper-300 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
                    onClick={() => setSelected(item)}
                  >
                    <h3 className="text-base font-semibold text-ink-800 leading-tight group-hover:text-brand-600 transition-colors line-clamp-2">
                      {item.title}
                    </h3>
                    <p className="mt-2 text-sm text-ink-500 line-clamp-2">{item.summary}</p>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {(item.tags || []).slice(0, 4).map((t) => (
                        <Badge key={t} color={getTagColor(t)}>{t}</Badge>
                      ))}
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-ink-400">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <Eye className="h-3 w-3" />
                          {item.view_count}
                        </span>
                        <span>{item.source}</span>
                      </div>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDate(item.created_at)}
                      </span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleBookmark(item.id);
                      }}
                      className="mt-2 flex items-center gap-1 text-xs text-ink-400 hover:text-brand-500 transition-colors"
                    >
                      <Bookmark className="h-3.5 w-3.5" />
                      收藏
                    </button>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 mt-6">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium border border-paper-300 bg-white text-ink-600 hover:bg-paper-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    上一页
                  </button>
                  <span className="text-sm text-ink-500">
                    {page} / {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium border border-paper-300 bg-white text-ink-600 hover:bg-paper-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    下一页
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Sidebar Stats */}
        <div className="hidden lg:block w-72 flex-shrink-0">
          <div className="rounded-xl border border-paper-300 bg-white p-5 shadow-sm sticky top-6">
            <h3 className="text-sm font-semibold text-ink-800 mb-3">分类统计</h3>
            {rankingData.length > 0 ? (
              <BarChart ranking={rankingData} title="分类" topN={10} height={250} />
            ) : (
              <p className="text-sm text-ink-400">暂无统计数据</p>
            )}
            {stats && (
              <div className="mt-4 pt-4 border-t border-paper-200">
                <p className="text-xs text-ink-500">
                  共 <span className="font-semibold text-ink-700">{stats.total}</span> 篇方法
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-ink-900/50 backdrop-blur-sm"
            onClick={() => setSelected(null)}
          />
          <div className="relative w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-2xl bg-white shadow-2xl">
            <div className="sticky top-0 flex items-center justify-between border-b border-paper-200 bg-white px-6 py-4 rounded-t-2xl">
              <h2 className="text-lg font-semibold text-ink-800 pr-8">{selected.title}</h2>
              <button
                onClick={() => setSelected(null)}
                className="absolute right-4 top-4 p-1 rounded-lg text-ink-400 hover:text-ink-700 hover:bg-paper-200 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div className="flex flex-wrap gap-1.5">
                {(selected.tags || []).map((t) => (
                  <Badge key={t} color={getTagColor(t)}>{t}</Badge>
                ))}
              </div>
              <div className="flex items-center gap-4 text-sm text-ink-500">
                <span>{selected.source}</span>
                <span className="flex items-center gap-1">
                  <Eye className="h-3.5 w-3.5" />
                  {selected.view_count} 次阅读
                </span>
                <span>{formatDate(selected.created_at)}</span>
              </div>
              <div className="prose prose-sm max-w-none text-ink-700 leading-relaxed whitespace-pre-wrap">
                {selected.content || selected.summary}
              </div>
              <div className="flex items-center gap-3 pt-4 border-t border-paper-200">
                <button
                  onClick={() => handleBookmark(selected.id)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-paper-300 text-sm font-medium text-ink-600 hover:bg-paper-100 transition-colors"
                >
                  <Bookmark className="h-4 w-4" />
                  收藏
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
