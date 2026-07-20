"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Tag,
  Search,
  BookOpen,
  MessageSquare,
  Clock,
  Eye,
  ThumbsUp,
  Flame,
  X,
} from "lucide-react";
import { Button, Input, Badge } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { kaoyanCommunityApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ExperiencePostResponse } from "@/types";

const PAGE_SIZE = 12;

const POPULAR_TAGS = [
  "408", "计算机考研", "数学", "英语", "政治",
  "择校", "复试", "调剂", "双非逆袭", "经验分享",
  "时间规划", "心态调整", "导师选择", "参考书目", "真题",
];

interface TagCount {
  tag: string;
  count: number;
}

export default function TagsPage() {
  const router = useRouter();
  const toast = useToast();
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [posts, setPosts] = useState<ExperiencePostResponse[]>([]);
  const [tagCounts, setTagCounts] = useState<TagCount[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const loadTagCounts = useCallback(async () => {
    try {
      const res = await kaoyanCommunityApi.experiencePosts.list({
        page: 1,
        page_size: 200,
      });
      const counts: Record<string, number> = {};
      res.items.forEach((post) => {
        post.tags.forEach((tag) => {
          counts[tag] = (counts[tag] || 0) + 1;
        });
      });
      const sorted = Object.entries(counts)
        .map(([tag, count]) => ({ tag, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 50);
      setTagCounts(sorted);
    } catch {
      toast.push("加载标签失败", "error");
    }
  }, [toast]);

  const loadPosts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await kaoyanCommunityApi.experiencePosts.list({
        page,
        page_size: PAGE_SIZE,
        tag: selectedTag || undefined,
        search: search || undefined,
      });
      setPosts(res.items);
      setTotal(res.total);
    } catch {
      toast.push("加载经验贴失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page, selectedTag, search, toast]);

  useEffect(() => {
    loadTagCounts();
  }, [loadTagCounts]);

  useEffect(() => {
    setPage(1);
  }, [selectedTag, search]);

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const getTagSize = (count: number, maxCount: number) => {
    const ratio = count / maxCount;
    if (ratio > 0.8) return "text-lg font-bold";
    if (ratio > 0.5) return "text-base font-semibold";
    if (ratio > 0.3) return "text-sm font-medium";
    return "text-xs";
  };

  const maxCount = Math.max(...tagCounts.map((t) => t.count), 1);

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-brand-sm">
              <Tag className="h-5 w-5" strokeWidth={2.2} />
            </div>
            <h1 className="font-display text-xl sm:text-2xl font-bold text-ink-900 tracking-tight">
              标签浏览
            </h1>
          </div>
          <p className="text-sm text-ink-500 ml-[46px]">
            按标签发现考研经验，找到你关注的内容。
          </p>
        </div>

        {/* Search */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索标签或内容..."
              className="pl-9"
            />
          </div>
        </div>

        <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
          {/* Sidebar: Tag Cloud */}
          <div className="space-y-4">
            {/* Tag Cloud */}
            <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-ink-800 flex items-center gap-1.5">
                  <Tag className="h-4 w-4 text-brand-600" />
                  标签云
                </h3>
                {selectedTag && (
                  <button
                    onClick={() => setSelectedTag(null)}
                    className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1"
                  >
                    <X className="h-3 w-3" />
                    清除筛选
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {tagCounts.length === 0 ? (
                  <p className="text-xs text-ink-400">暂无标签数据</p>
                ) : (
                  tagCounts.map((tc) => (
                    <button
                      key={tc.tag}
                      onClick={() => setSelectedTag(selectedTag === tc.tag ? null : tc.tag)}
                      className={cn(
                        "inline-flex items-center rounded-full px-3 py-1 transition-all",
                        selectedTag === tc.tag
                          ? "bg-brand-600 text-white shadow-brand-sm"
                          : "bg-paper-100 text-ink-600 hover:bg-brand-50 hover:text-brand-700",
                        getTagSize(tc.count, maxCount),
                      )}
                    >
                      {tc.tag}
                      <span className={cn(
                        "ml-1.5 text-xs",
                        selectedTag === tc.tag ? "text-brand-200" : "text-ink-400",
                      )}>
                        {tc.count}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Popular Tags */}
            <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-ink-800 mb-3">热门标签</h3>
              <div className="space-y-2">
                {POPULAR_TAGS.slice(0, 10).map((tag, idx) => (
                  <div
                    key={tag}
                    className="flex items-center gap-2 text-sm text-ink-600 hover:text-brand-700 cursor-pointer"
                    onClick={() => setSelectedTag(tag)}
                  >
                    <span
                      className={cn(
                        "flex h-5 w-5 items-center justify-center rounded text-xs font-medium",
                        idx < 3 ? "bg-amber-100 text-amber-700" : "bg-paper-100 text-ink-400",
                      )}
                    >
                      {idx + 1}
                    </span>
                    <span className="line-clamp-1">{tag}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2 space-y-4">
            {/* Active Filter */}
            {selectedTag && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-brand-50 border border-brand-200">
                <Tag className="h-4 w-4 text-brand-600" />
                <span className="text-sm text-brand-700 font-medium">
                  正在浏览: {selectedTag}
                </span>
                <span className="text-xs text-brand-500">
                  ({total} 条结果)
                </span>
                <button
                  onClick={() => setSelectedTag(null)}
                  className="ml-auto text-brand-600 hover:text-brand-700"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}

            {/* Posts */}
            {loading ? (
              <div className="rounded-xl border border-paper-200 bg-white p-8">
                <LoadingState text="加载经验贴..." />
              </div>
            ) : posts.length === 0 ? (
              <div className="rounded-xl border border-paper-200 bg-white p-8">
                <EmptyState
                  title="暂无经验贴"
                  description={selectedTag
                    ? `没有标签为「${selectedTag}」的经验贴`
                    : search
                      ? "未找到匹配内容，换个关键词试试"
                      : "暂无经验贴"}
                />
              </div>
            ) : (
              posts.map((post) => (
                <div
                  key={post.id}
                  className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => router.push(`/kaoyan/community/posts/${post.id}`)}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <h3 className="font-semibold text-ink-900">{post.title}</h3>
                    {post.is_pinned && (
                      <span className="flex items-center gap-1 text-xs text-red-500 shrink-0">
                        <Flame className="h-3 w-3" />
                        置顶
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-ink-500 mb-3 line-clamp-2">
                    {post.summary || post.content.slice(0, 120)}
                  </p>
                  {post.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {post.tags.map((tag) => (
                        <Badge
                          key={tag}
                          color={tag === selectedTag ? "green" : "slate"}
                          className="cursor-pointer"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedTag(tag);
                          }}
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center justify-between text-xs text-ink-400">
                    <div className="flex items-center gap-3">
                      <span>{post.is_anonymous ? "匿名用户" : `用户 ${post.user_id.slice(-4)}`}</span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(post.created_at).toLocaleDateString("zh-CN")}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <Eye className="h-3 w-3" />
                        {post.view_count}
                      </span>
                      <span className="flex items-center gap-1">
                        <ThumbsUp className="h-3 w-3" />
                        {post.like_count}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="h-3 w-3" />
                        {post.comment_count}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}

            {/* Pagination */}
            {!loading && totalPages > 1 && (
              <div className="flex justify-center gap-2 pt-2">
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
      </div>
    </div>
  );
}
