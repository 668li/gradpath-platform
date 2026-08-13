"use client";

/**
 * 灵感案例库组件 — 展示来自 Trae Work 论坛的创意方案。
 *
 * 数据来源：experience_posts 表中 source_platform='trae_forum' 的记录
 * 通过 category 区分考研/就业/考公三类
 *
 * 复用场景：
 * - 考研社区页面（category="考研灵感"）
 * - 就业中心页面（category="就业灵感"）
 * - 考公中心页面（category="考公灵感"）
 */
import { useCallback, useEffect, useState } from "react";
import {
  Lightbulb,
  Search,
  ExternalLink,
  Eye,
  ThumbsUp,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { Input } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { kaoyanCommunityApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ExperiencePostResponse } from "@/types";

interface InspirationCasesProps {
  /** 分类过滤：考研灵感 / 就业灵感 / 考公灵感 */
  category: string;
  /** 标题前缀图标颜色 */
  accentColor?: string;
}

const PAGE_SIZE = 12;

export function InspirationCases({
  category,
  accentColor = "text-amber-500",
}: InspirationCasesProps) {
  const [items, setItems] = useState<ExperiencePostResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<ExperiencePostResponse | null>(null);
  const { push } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await kaoyanCommunityApi.experiencePosts.list({
        page,
        page_size: PAGE_SIZE,
        category,
        search: search || undefined,
        source_platform: "trae_forum",
      });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      push("加载灵感案例失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page, search, category, push]);

  useEffect(() => {
    load();
  }, [load]);

  // 搜索时重置到第一页
  useEffect(() => {
    setPage(1);
  }, [search]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // 详情视图
  if (selected) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setSelected(null)}
          className="flex items-center gap-1 text-sm text-ink-500 hover:text-ink-800"
        >
          <ChevronLeft className="h-4 w-4" />
          返回列表
        </button>

        <article className="rounded-xl border border-paper-200 bg-white p-6 md:p-8">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className={cn("h-5 w-5", accentColor)} />
            <span className="text-xs font-medium text-ink-400">
              Trae Work 论坛灵感
            </span>
            {selected.tags?.length > 0 && (
              <div className="flex gap-1 ml-2">
                {selected.tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-paper-100 px-2 py-0.5 text-xs text-ink-600"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          <h1 className="font-display text-2xl font-bold text-ink-800 mb-3">
            {selected.title}
          </h1>

          {selected.summary && (
            <p className="text-ink-500 mb-4 leading-relaxed">
              {selected.summary}
            </p>
          )}

          <div className="flex items-center gap-4 text-sm text-ink-400 mb-6 pb-6 border-b border-paper-200">
            <span className="flex items-center gap-1">
              <Eye className="h-4 w-4" />
              {selected.view_count ?? 0} 浏览
            </span>
            <span className="flex items-center gap-1">
              <ThumbsUp className="h-4 w-4" />
              {selected.like_count ?? 0} 点赞
            </span>
            {selected.source_url && (
              <a
                href={selected.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-blue-500 hover:text-blue-700"
              >
                <ExternalLink className="h-4 w-4" />
                原文链接
              </a>
            )}
          </div>

          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink-700 bg-paper-50 rounded-lg p-4">
              {selected.content}
            </pre>
          </div>
        </article>
      </div>
    );
  }

  // 列表视图
  return (
    <div className="space-y-4">
      {/* 头部说明 */}
      <div className="rounded-xl bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 p-4">
        <div className="flex items-start gap-3">
          <Lightbulb className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-display font-bold text-ink-800 mb-1">
              💡 Trae Work 论坛灵感案例
            </h3>
            <p className="text-sm text-ink-600 leading-relaxed">
              精选自 Trae Work 开发者论坛的 {total} 个创意方案，每个案例都包含完整的问题分析、产品思路和落地实现。
              点击卡片查看完整方案，获取产品灵感。
            </p>
          </div>
        </div>
      </div>

      {/* 搜索框 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-400" />
        <Input
          type="search"
          placeholder="搜索灵感案例（标题、内容、标签）..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* 列表 */}
      {loading ? (
        <LoadingState text="加载灵感案例中..." />
      ) : items.length === 0 ? (
        <EmptyState
          title="暂无灵感案例"
          description={search ? `未找到匹配「${search}」的案例` : "请稍后再来"}
        />
      ) : (
        <>
          <div className="grid gap-3 md:grid-cols-2">
            {items.map((item) => (
              <button
                key={item.id}
                onClick={() => setSelected(item)}
                className="group text-left rounded-xl border border-paper-200 bg-white p-4 hover:border-amber-300 hover:shadow-md transition-all"
              >
                <div className="flex items-start gap-2 mb-2">
                  <Sparkles className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                  <h3 className="font-medium text-ink-800 line-clamp-2 group-hover:text-amber-700">
                    {item.title}
                  </h3>
                </div>

                {item.summary && (
                  <p className="text-sm text-ink-500 line-clamp-3 mb-3">
                    {item.summary}
                  </p>
                )}

                <div className="flex items-center justify-between text-xs text-ink-400">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1">
                      <Eye className="h-3 w-3" />
                      {item.view_count ?? 0}
                    </span>
                    <span className="flex items-center gap-1">
                      <ThumbsUp className="h-3 w-3" />
                      {item.like_count ?? 0}
                    </span>
                  </div>
                  {item.tags?.[0] && (
                    <span className="rounded-full bg-paper-100 px-2 py-0.5 text-ink-600">
                      {item.tags[0]}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded-lg border border-paper-200 bg-white p-2 text-ink-500 hover:bg-paper-50 disabled:opacity-40 disabled:cursor-not-allowed"
                aria-label="上一页"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm text-ink-500">
                第 {page} / {totalPages} 页 （共 {total} 条）
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded-lg border border-paper-200 bg-white p-2 text-ink-500 hover:bg-paper-50 disabled:opacity-40 disabled:cursor-not-allowed"
                aria-label="下一页"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
