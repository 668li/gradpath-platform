"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  User,
  BookOpen,
  MessageSquare,
  Bookmark,
  ThumbsUp,
  Eye,
  Clock,
  Plus,
  BarChart3,
  FileText,
  HelpCircle,
  Star,
} from "lucide-react";
import { Button, Badge } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { kaoyanCommunityApi, authApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ExperiencePostResponse, QAResponse, UserResponse } from "@/types";

type CommunityTab = "posts" | "questions" | "bookmarks";

export default function CommunityProfilePage() {
  const router = useRouter();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<CommunityTab>("posts");
  const [user, setUser] = useState<UserResponse | null>(null);
  const [posts, setPosts] = useState<ExperiencePostResponse[]>([]);
  const [questions, setQuestions] = useState<QAResponse[]>([]);
  const [bookmarks, setBookmarks] = useState<ExperiencePostResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    postCount: 0,
    questionCount: 0,
    totalLikes: 0,
    totalViews: 0,
  });

  const loadUser = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      toast.push("获取用户信息失败", "error");
    }
  }, [toast]);

  const loadPosts = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const res = await kaoyanCommunityApi.experiencePosts.list({
        page: 1,
        page_size: 100,
      });
      const userPosts = res.items.filter((p) => p.user_id === user.id);
      setPosts(userPosts);
      setStats((s) => ({
        ...s,
        postCount: userPosts.length,
        totalLikes: userPosts.reduce((sum, p) => sum + p.like_count, 0),
        totalViews: userPosts.reduce((sum, p) => sum + p.view_count, 0),
      }));
    } catch {
      toast.push("加载帖子失败", "error");
    } finally {
      setLoading(false);
    }
  }, [user, toast]);

  const loadQuestions = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const res = await kaoyanCommunityApi.qa.list({
        page: 1,
        page_size: 100,
      });
      const userQuestions = res.items.filter((q) => q.user_id === user.id);
      setQuestions(userQuestions);
      setStats((s) => ({ ...s, questionCount: userQuestions.length }));
    } catch {
      toast.push("加载问答失败", "error");
    } finally {
      setLoading(false);
    }
  }, [user, toast]);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    if (!user) return;
    if (activeTab === "posts") loadPosts();
    else if (activeTab === "questions") loadQuestions();
  }, [activeTab, user, loadPosts, loadQuestions]);

  const tabs = [
    { key: "posts" as CommunityTab, label: "我的帖子", icon: FileText, count: stats.postCount },
    { key: "questions" as CommunityTab, label: "我的问题", icon: HelpCircle, count: stats.questionCount },
    { key: "bookmarks" as CommunityTab, label: "我的收藏", icon: Star, count: bookmarks.length },
  ];

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-brand-sm">
              <User className="h-5 w-5" strokeWidth={2.2} />
            </div>
            <h1 className="font-display text-xl sm:text-2xl font-bold text-ink-900 tracking-tight">
              社区主页
            </h1>
          </div>
          <p className="text-sm text-ink-500 ml-[46px]">
            管理你在社区的帖子、问题和收藏。
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            { label: "发布帖子", value: stats.postCount, icon: FileText, color: "text-brand-600 bg-brand-50" },
            { label: "提出问题", value: stats.questionCount, icon: HelpCircle, color: "text-blue-600 bg-blue-50" },
            { label: "获得点赞", value: stats.totalLikes, icon: ThumbsUp, color: "text-amber-600 bg-amber-50" },
            { label: "总浏览量", value: stats.totalViews, icon: Eye, color: "text-green-600 bg-green-50" },
          ].map((s) => {
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

        {/* User Info */}
        {user && (
          <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm mb-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-brand-600">
                <User className="h-6 w-6" />
              </div>
              <div>
                <h2 className="font-semibold text-ink-900">{user.name}</h2>
                <p className="text-sm text-ink-500">{user.email}</p>
                {user.current_stage && (
                  <Badge color="blue" className="mt-1">{user.current_stage}</Badge>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="rounded-xl border border-paper-200 bg-white p-1 shadow-sm flex gap-1 mb-6">
          {tabs.map((tab) => {
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
                {tab.count > 0 && (
                  <span className="ml-1 text-xs bg-paper-200 text-ink-500 px-1.5 py-0.5 rounded-full">
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Content */}
        {loading ? (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <LoadingState text="加载中..." />
          </div>
        ) : activeTab === "posts" ? (
          posts.length === 0 ? (
            <div className="rounded-xl border border-paper-200 bg-white p-8">
              <EmptyState
                title="暂无帖子"
                description="成为第一个分享经验的人吧"
                action={
                  <Button onClick={() => router.push("/kaoyan/community/posts/new")}>
                    <Plus className="h-4 w-4 mr-1.5" />
                    写经验
                  </Button>
                }
              />
            </div>
          ) : (
            <div className="space-y-3">
              {posts.map((post) => (
                <div
                  key={post.id}
                  className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => router.push(`/kaoyan/community/posts/${post.id}`)}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <h3 className="font-semibold text-ink-900">{post.title}</h3>
                    <Badge color={post.status === "approved" ? "green" : "amber"}>
                      {post.status === "approved" ? "已发布" : "审核中"}
                    </Badge>
                  </div>
                  <p className="text-sm text-ink-500 mb-3 line-clamp-2">
                    {post.summary || post.content.slice(0, 120)}
                  </p>
                  <div className="flex items-center gap-4 text-xs text-ink-400">
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
                </div>
              ))}
            </div>
          )
        ) : activeTab === "questions" ? (
          questions.length === 0 ? (
            <div className="rounded-xl border border-paper-200 bg-white p-8">
              <EmptyState
                title="暂无问题"
                description="提出你的第一个考研问题吧"
                action={
                  <Button onClick={() => router.push("/kaoyan/community/qa/new")}>
                    <Plus className="h-4 w-4 mr-1.5" />
                    提问题
                  </Button>
                }
              />
            </div>
          ) : (
            <div className="space-y-3">
              {questions.map((q) => (
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
                      <Clock className="h-3 w-3" />
                      {new Date(q.created_at).toLocaleDateString("zh-CN")}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="h-3 w-3" />
                      {q.answer_count} 个回答
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye className="h-3 w-3" />
                      {q.view_count} 次浏览
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )
        ) : (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <EmptyState
              title="暂无收藏"
              description="浏览社区时收藏感兴趣的内容"
              action={
                <Button onClick={() => router.push("/kaoyan/community")}>
                  <BookOpen className="h-4 w-4 mr-1.5" />
                  浏览社区
                </Button>
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}
