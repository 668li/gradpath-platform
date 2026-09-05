"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Users,
  MessageSquare,
  BookOpen,
  ThumbsUp,
  Eye,
  Plus,
  Flame,
  Clock,
  Search,
  HelpCircle,
} from "lucide-react";
import { Button, Input, Badge } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { kaoyanCommunityApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ExperiencePostResponse, QAResponse } from "@/types";
import { QualityBadge } from "@/components/ui/quality-badge";

const tabs = [
  { key: "experience", label: "经验贴", icon: BookOpen },
  { key: "qa", label: "问答互助", icon: MessageSquare },
];

const PAGE_SIZE = 10;

function CommunityPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const toast = useToast();
  const initialTab = searchParams.get("tab") === "qa" ? "qa" : "experience";
  const [activeTab, setActiveTab] = useState<"experience" | "qa">(initialTab);
  const [search, setSearch] = useState("");
  const [posts, setPosts] = useState<ExperiencePostResponse[]>([]);
  const [questions, setQuestions] = useState<QAResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const loadPosts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await kaoyanCommunityApi.experiencePosts.list({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        source_platform: "user",
      });
      setPosts(res.items);
      setTotal(res.total);
    } catch {
      toast.push("加载经验贴失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page, search, toast]);

  const loadQuestions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await kaoyanCommunityApi.qa.list({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
      });
      setQuestions(res.items);
      setTotal(res.total);
    } catch {
      toast.push("加载问答失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page, search, toast]);

  useEffect(() => {
    setPage(1);
  }, [activeTab, search]);

  useEffect(() => {
    if (activeTab === "experience") {
      loadPosts();
    } else if (activeTab === "qa") {
      loadQuestions();
    }
  }, [activeTab, loadPosts, loadQuestions]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

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
              考研社区
            </h1>
          </div>
          <p className="text-sm text-ink-500 ml-[46px]">
            经验分享、问答互助、资料交流——考研路上不孤单。
          </p>
        </div>

        {/* Search + Action */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -tranink-y-1/2 text-ink-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索经验贴、问答、资料..."
              className="pl-9"
            />
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={() => router.push("/kaoyan/community/qa/new")}
            >
              <HelpCircle className="h-4 w-4 mr-1.5" />
              提问题
            </Button>
            <Button onClick={() => router.push("/kaoyan/community/posts/new")}>
              <Plus className="h-4 w-4 mr-1.5" />
              写经验
            </Button>
          </div>
        </div>

        <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-4">
            {/* Tabs */}
            <div className="rounded-xl border border-paper-200 bg-white p-1 shadow-sm flex flex-col sm:flex-row gap-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key as typeof activeTab)}
                    className={cn(
                      "flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium rounded-lg transition-colors",
                      activeTab === tab.key
                        ? "bg-brand-50 text-brand-700"
                        : "text-ink-500 hover:bg-paper-100 hover:text-ink-700",
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Experience Posts */}
            {activeTab === "experience" && (
              <div className="space-y-3">
                {loading ? (
                  <div className="rounded-xl border border-paper-200 bg-white p-8">
                    <LoadingState text="加载经验贴..." />
                  </div>
                ) : posts.length === 0 ? (
                  <div className="rounded-xl border border-paper-200 bg-white p-8">
                    <EmptyState
                      title="暂无经验贴"
                      description={search ? "未找到匹配内容，换个关键词试试" : "成为第一个分享经验的人吧"}
                      action={
                        <Button onClick={() => router.push("/kaoyan/community/posts/new")}>
                          <Plus className="h-4 w-4 mr-1.5" />
                          写经验
                        </Button>
                      }
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
                        <div className="flex shrink-0 items-center gap-2">
                          <QualityBadge grade={post.quality_grade} score={post.quality_score} />
                          <Badge color={post.category === "问答" ? "blue" : "green"}>
                            {post.category === "general" ? "经验贴" : post.category}
                          </Badge>
                        </div>
                      </div>
                      <p className="text-sm text-ink-500 mb-3 line-clamp-2">
                        {post.summary || post.content.slice(0, 120)}
                      </p>
                      <div className="flex items-center justify-between text-xs text-ink-400">
                        <div className="flex items-center gap-3">
                          {post.is_anonymous ? (
                            <span>匿名用户</span>
                          ) : (
                            <Link href={`/u/${post.user_id}`} className="hover:text-brand-600 hover:underline transition-colors" onClick={(e) => e.stopPropagation()}>
                              {post.author_name || `用户 ${post.user_id.slice(-4)}`}
                            </Link>
                          )}
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(post.created_at).toLocaleDateString("zh-CN")}
                          </span>
                          {post.is_pinned && (
                            <span className="flex items-center gap-1 text-red-500">
                              <Flame className="h-3 w-3" />
                              置顶
                            </span>
                          )}
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
              </div>
            )}

            {/* Q&A */}
            {activeTab === "qa" && (
              <div className="space-y-3">
                {loading ? (
                  <div className="rounded-xl border border-paper-200 bg-white p-8">
                    <LoadingState text="加载问答..." />
                  </div>
                ) : questions.length === 0 ? (
                  <div className="rounded-xl border border-paper-200 bg-white p-8">
                    <EmptyState
                      title="暂无问题"
                      description={search ? "未找到匹配内容，换个关键词试试" : "提出你的第一个考研问题吧"}
                      action={
                        <Button onClick={() => router.push("/kaoyan/community/qa/new")}>
                          <Plus className="h-4 w-4 mr-1.5" />
                          提问题
                        </Button>
                      }
                    />
                  </div>
                ) : (
                  questions.map((q) => (
                    <div
                      key={q.id}
                      className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => router.push(`/kaoyan/community/qa/${q.id}`)}
                    >
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <h3 className="font-semibold text-ink-900">{q.title}</h3>
                        {q.is_resolved ? (
                          <Badge color="green">已解决</Badge>
                        ) : (
                          <Badge color="blue">待回答</Badge>
                        )}
                      </div>
                      <p className="text-sm text-ink-500 mb-3 line-clamp-2">{q.content}</p>
                      <div className="flex items-center gap-4 text-xs text-ink-400">
                        <span className="flex items-center gap-1">
                          <MessageSquare className="h-3 w-3" />
                          {q.answer_count} 个回答
                        </span>
                        <span className="flex items-center gap-1">
                          <Eye className="h-3 w-3" />
                          {q.view_count} 次浏览
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(q.created_at).toLocaleDateString("zh-CN")}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
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

          {/* Sidebar */}
          <div className="space-y-4">
            <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-ink-800 mb-3">社区规范</h3>
              <ul className="space-y-2 text-xs text-ink-500">
                <li>• 禁止发布不实信息和广告</li>
                <li>• 尊重他人，理性讨论</li>
                <li>• 分享资料请标注来源</li>
                <li>• 经验内容请基于真实经历</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CommunityPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-paper-50 flex items-center justify-center"><LoadingState text="加载中..." /></div>}>
      <CommunityPageContent />
    </Suspense>
  );
}
