"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Shield,
  CheckCircle2,
  XCircle,
  Pin,
  Clock,
  Eye,
  ThumbsUp,
  MessageSquare,
  BarChart3,
  FileText,
  HelpCircle,
  Filter,
  RefreshCw,
} from "lucide-react";
import { Button, Badge, Select } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { kaoyanCommunityApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ExperiencePostResponse, QAResponse } from "@/types";

const PAGE_SIZE = 15;

type ContentTab = "all" | "posts" | "qa";
type ModerationStatus = "pending" | "approved" | "rejected";

export default function ModerationDashboardPage() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<ContentTab>("all");
  const [statusFilter, setStatusFilter] = useState<ModerationStatus>("pending");
  const [posts, setPosts] = useState<ExperiencePostResponse[]>([]);
  const [questions, setQuestions] = useState<QAResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const [stats, setStats] = useState({
    pendingPosts: 0,
    pendingQa: 0,
    approvedToday: 0,
    rejectedToday: 0,
  });

  const loadPosts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await kaoyanCommunityApi.experiencePosts.list({
        page,
        page_size: PAGE_SIZE,
        status: statusFilter === "pending" ? undefined : statusFilter,
      });
      const filtered = statusFilter === "pending"
        ? res.items.filter((p) => p.status === "pending" || (!["approved", "rejected"].includes(p.status)))
        : res.items.filter((p) => p.status === statusFilter);
      setPosts(statusFilter === "pending" ? res.items : filtered);
      setTotal(res.total);
    } catch {
      toast.push("加载经验贴失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, toast]);

  const loadQuestions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await kaoyanCommunityApi.qa.list({
        page,
        page_size: PAGE_SIZE,
      });
      setQuestions(res.items);
      setTotal(res.total);
    } catch {
      toast.push("加载问答失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page, toast]);

  useEffect(() => {
    setPage(1);
  }, [activeTab, statusFilter]);

  useEffect(() => {
    if (activeTab === "posts" || activeTab === "all") loadPosts();
    if (activeTab === "qa" || activeTab === "all") loadQuestions();
  }, [activeTab, loadPosts, loadQuestions]);

  useEffect(() => {
    (async () => {
      try {
        const postRes = await kaoyanCommunityApi.experiencePosts.list({ page: 1, page_size: 1 });
        const qaRes = await kaoyanCommunityApi.qa.list({ page: 1, page_size: 1 });
        setStats({
          pendingPosts: postRes.total,
          pendingQa: qaRes.total,
          approvedToday: 0,
          rejectedToday: 0,
        });
      } catch { /* noop */ }
    })();
  }, []);

  const handleApprove = async (postId: string) => {
    try {
      await fetch(`/api/kaoyan/experience-posts/${postId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "approved" }),
      });
      setPosts((prev) => prev.filter((p) => p.id !== postId));
      setStats((s) => ({ ...s, pendingPosts: Math.max(0, s.pendingPosts - 1), approvedToday: s.approvedToday + 1 }));
      toast.push("已通过审核", "success");
    } catch {
      toast.push("操作失败", "error");
    }
  };

  const handleReject = async (postId: string) => {
    try {
      await fetch(`/api/kaoyan/experience-posts/${postId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "rejected" }),
      });
      setPosts((prev) => prev.filter((p) => p.id !== postId));
      setStats((s) => ({ ...s, pendingPosts: Math.max(0, s.pendingPosts - 1), rejectedToday: s.rejectedToday + 1 }));
      toast.push("已拒绝", "success");
    } catch {
      toast.push("操作失败", "error");
    }
  };

  const handlePin = async (postId: string, currentPinned: boolean) => {
    try {
      await fetch(`/api/kaoyan/experience-posts/${postId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_pinned: !currentPinned }),
      });
      setPosts((prev) => prev.map((p) => p.id === postId ? { ...p, is_pinned: !currentPinned } : p));
      toast.push(currentPinned ? "已取消置顶" : "已置顶", "success");
    } catch {
      toast.push("操作失败", "error");
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const statCards = [
    { label: "待审帖子", value: stats.pendingPosts, icon: FileText, color: "text-amber-600 bg-amber-50" },
    { label: "待审问答", value: stats.pendingQa, icon: HelpCircle, color: "text-blue-600 bg-blue-50" },
    { label: "今日通过", value: stats.approvedToday, icon: CheckCircle2, color: "text-green-600 bg-green-50" },
    { label: "今日拒绝", value: stats.rejectedToday, icon: XCircle, color: "text-red-600 bg-red-50" },
  ];

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-brand-sm">
              <Shield className="h-5 w-5" strokeWidth={2.2} />
            </div>
            <h1 className="font-display text-xl sm:text-2xl font-bold text-ink-900 tracking-tight">
              内容审核
            </h1>
          </div>
          <p className="text-sm text-ink-500 ml-[46px]">
            管理社区内容质量，审核经验贴和问答。
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {statCards.map((s) => {
            const Icon = s.icon;
            return (
              <div key={s.label} className="rounded-xl border border-paper-200 bg-white p-4 shadow-sm">
                <div className="flex items-center gap-2 mb-1">
                  <div className={cn("flex h-7 w-7 items-center justify-center rounded-lg", s.color)}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <span className="text-xs text-ink-400">{s.label}</span>
                </div>
                <p className="text-2xl font-bold text-ink-900">{s.value}</p>
              </div>
            );
          })}
        </div>

        {/* Controls */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="flex gap-2 flex-1">
            <Button variant="ghost" size="sm" onClick={() => { loadPosts(); loadQuestions(); }}>
              <RefreshCw className="h-4 w-4 mr-1" />
              刷新
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-ink-400" />
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ModerationStatus)}
              className="w-32"
            >
              <option value="pending">待审核</option>
              <option value="approved">已通过</option>
              <option value="rejected">已拒绝</option>
            </Select>
          </div>
        </div>

        <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-4">
            {/* Tabs */}
            <div className="rounded-xl border border-paper-200 bg-white p-1 shadow-sm flex gap-1">
              {([
                { key: "all" as ContentTab, label: "全部", icon: BarChart3 },
                { key: "posts" as ContentTab, label: "经验贴", icon: FileText },
                { key: "qa" as ContentTab, label: "问答", icon: HelpCircle },
              ]).map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
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

            {/* Posts List */}
            {(activeTab === "all" || activeTab === "posts") && (
              <div className="space-y-3">
                {activeTab === "all" && (
                  <h3 className="text-sm font-semibold text-ink-700 flex items-center gap-1.5">
                    <FileText className="h-4 w-4" />
                    经验贴审核
                  </h3>
                )}
                {loading ? (
                  <div className="rounded-xl border border-paper-200 bg-white p-8">
                    <LoadingState text="加载内容..." />
                  </div>
                ) : posts.length === 0 ? (
                  <div className="rounded-xl border border-paper-200 bg-white p-8">
                    <EmptyState
                      title="没有待审内容"
                      description="当前没有需要审核的经验贴"
                    />
                  </div>
                ) : (
                  posts.map((post) => (
                    <div
                      key={post.id}
                      className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-ink-900 truncate">{post.title}</h3>
                            <Badge color={post.status === "approved" ? "green" : post.status === "rejected" ? "red" : "amber"}>
                              {post.status === "approved" ? "已通过" : post.status === "rejected" ? "已拒绝" : "待审核"}
                            </Badge>
                            {post.is_pinned && (
                              <Badge color="purple">
                                <Pin className="h-3 w-3 mr-0.5" />
                                置顶
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-ink-500 line-clamp-2">
                            {post.summary || post.content.slice(0, 120)}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 text-xs text-ink-400">
                          <span>{post.is_anonymous ? "匿名用户" : `用户 ${post.user_id.slice(-4)}`}</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(post.created_at).toLocaleDateString("zh-CN")}
                          </span>
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

                        <div className="flex items-center gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handlePin(post.id, post.is_pinned)}
                          >
                            <Pin className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            size="sm"
                            className="bg-green-600 hover:bg-green-700 text-white"
                            onClick={() => handleApprove(post.id)}
                          >
                            <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                            通过
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => handleReject(post.id)}
                          >
                            <XCircle className="h-3.5 w-3.5 mr-1" />
                            拒绝
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Q&A List */}
            {(activeTab === "all" || activeTab === "qa") && (
              <div className="space-y-3">
                {activeTab === "all" && (
                  <h3 className="text-sm font-semibold text-ink-700 flex items-center gap-1.5">
                    <HelpCircle className="h-4 w-4" />
                    问答审核
                  </h3>
                )}
                {loading ? (
                  <div className="rounded-xl border border-paper-200 bg-white p-8">
                    <LoadingState text="加载问答..." />
                  </div>
                ) : questions.length === 0 ? (
                  <div className="rounded-xl border border-paper-200 bg-white p-8">
                    <EmptyState
                      title="没有待审问答"
                      description="当前没有需要审核的问答"
                    />
                  </div>
                ) : (
                  questions.map((q) => (
                    <div
                      key={q.id}
                      className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm"
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
              <h3 className="text-sm font-semibold text-ink-800 mb-3">审核指南</h3>
              <ul className="space-y-2 text-xs text-ink-500">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                  内容真实、有参考价值的通过
                </li>
                <li className="flex items-start gap-2">
                  <XCircle className="h-3.5 w-3.5 text-red-500 mt-0.5 shrink-0" />
                  广告、不实信息、违规内容拒绝
                </li>
                <li className="flex items-start gap-2">
                  <Pin className="h-3.5 w-3.5 text-purple-500 mt-0.5 shrink-0" />
                  优质内容可置顶推荐
                </li>
              </ul>
            </div>

            <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-ink-800 mb-3">快速操作</h3>
              <div className="space-y-2">
                <Button variant="secondary" size="sm" className="w-full justify-start" onClick={() => { loadPosts(); loadQuestions(); }}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  刷新列表
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
