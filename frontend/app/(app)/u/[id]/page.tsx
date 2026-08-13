"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  MessageSquare,
  ThumbsUp,
  Eye,
  Clock,
  Reply,
  GraduationCap,
  School,
  Calendar,
  Award,
} from "lucide-react";
import { userProfileApi } from "@/lib/api/user_profiles";
import { cn } from "@/lib/utils";
import { EmptyState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type {
  UserProfile,
  ExperiencePostResponse,
  QAResponse,
  QAAnswerResponse,
} from "@/types";

const STAGE_LABELS: Record<string, string> = {
  student: "在校生",
  graduating: "应届毕业生",
  early_career: "职场新人",
  experienced: "资深职场人",
};

type TabKey = "posts" | "qa" | "answers";

const TABS: { key: TabKey; label: string; icon: typeof BookOpen }[] = [
  { key: "posts", label: "经验贴", icon: BookOpen },
  { key: "qa", label: "问答", icon: MessageSquare },
  { key: "answers", label: "回答", icon: Reply },
];

export default function UserProfilePage() {
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const userId = params.id as string;

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);

  const [activeTab, setActiveTab] = useState<TabKey>("posts");
  const [posts, setPosts] = useState<ExperiencePostResponse[]>([]);
  const [qaList, setQaList] = useState<QAResponse[]>([]);
  const [answers, setAnswers] = useState<QAAnswerResponse[]>([]);
  const [tabLoading, setTabLoading] = useState(true);

  const loadProfile = useCallback(async () => {
    setProfileLoading(true);
    try {
      const data = await userProfileApi.getProfile(userId);
      setProfile(data);
    } catch {
      toast.push("加载用户信息失败", "error");
    } finally {
      setProfileLoading(false);
    }
  }, [userId, toast]);

  const loadTabData = useCallback(async () => {
    setTabLoading(true);
    try {
      if (activeTab === "posts") {
        const data = await userProfileApi.getPosts(userId);
        setPosts(data);
      } else if (activeTab === "qa") {
        const data = await userProfileApi.getQA(userId);
        setQaList(data);
      } else {
        const data = await userProfileApi.getAnswers(userId);
        setAnswers(data);
      }
    } catch {
      toast.push("加载内容失败", "error");
    } finally {
      setTabLoading(false);
    }
  }, [activeTab, userId, toast]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    loadTabData();
  }, [loadTabData]);

  const renderSkeleton = () => (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm"
        >
          <div className="h-5 w-2/3 bg-paper-100 rounded animate-pulse mb-3" />
          <div className="h-4 w-full bg-paper-100 rounded animate-pulse mb-2" />
          <div className="h-4 w-1/2 bg-paper-100 rounded animate-pulse" />
        </div>
      ))}
    </div>
  );

  if (profileLoading) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
          <button
            onClick={() => router.back()}
            className="mb-4 flex items-center gap-2 text-sm text-ink-500 hover:text-ink-700"
          >
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
          <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm mb-6">
            <div className="flex items-center gap-4">
              <div className="h-20 w-20 rounded-full bg-paper-100 animate-pulse" />
              <div className="space-y-2">
                <div className="h-6 w-40 bg-paper-100 rounded animate-pulse" />
                <div className="h-4 w-32 bg-paper-100 rounded animate-pulse" />
              </div>
            </div>
          </div>
          {renderSkeleton()}
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
          <div className="rounded-xl border border-paper-200 bg-white p-8 text-center">
            <p className="text-ink-500">用户不存在或无法访问</p>
            <Button onClick={() => router.back()} className="mt-4">
              返回
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const stageLabel = profile.current_stage
    ? STAGE_LABELS[profile.current_stage] || profile.current_stage
    : null;

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
        {/* Back Button */}
        <button
          onClick={() => router.back()}
          className="mb-4 flex items-center gap-2 text-sm text-ink-500 hover:text-ink-700"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>

        {/* Profile Header */}
        <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm mb-6">
          <div className="flex flex-col sm:flex-row sm:items-start gap-5">
            {/* Avatar */}
            {profile.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={profile.avatar_url}
                alt={profile.display_name}
                className="h-20 w-20 rounded-full object-cover border border-paper-200 shrink-0"
              />
            ) : (
              <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-brand-100 text-2xl font-bold text-brand-700">
                {profile.display_name?.[0]?.toUpperCase() || "U"}
              </div>
            )}

            {/* Name & Bio */}
            <div className="flex-1 min-w-0">
              <h1 className="text-xl sm:text-2xl font-bold text-ink-900 tracking-tight">
                {profile.display_name}
              </h1>
              {profile.bio && (
                <p className="mt-2 text-sm text-ink-600 whitespace-pre-line">
                  {profile.bio}
                </p>
              )}
              <div className="mt-3 flex items-center gap-1 text-xs text-ink-400">
                <Calendar className="h-3 w-3" />
                注册于 {new Date(profile.created_at).toLocaleDateString("zh-CN")}
              </div>
            </div>
          </div>

          {/* Info Grid */}
          {(stageLabel || profile.school || profile.major || profile.graduation_year) && (
            <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3 pt-5 border-t border-paper-100">
              {stageLabel && (
                <div className="flex items-center gap-2 text-sm">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600 shrink-0">
                    <GraduationCap className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs text-ink-400">阶段</div>
                    <div className="text-sm font-medium text-ink-800 truncate">{stageLabel}</div>
                  </div>
                </div>
              )}
              {profile.school && (
                <div className="flex items-center gap-2 text-sm">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600 shrink-0">
                    <School className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs text-ink-400">学校</div>
                    <div className="text-sm font-medium text-ink-800 truncate">{profile.school}</div>
                  </div>
                </div>
              )}
              {profile.major && (
                <div className="flex items-center gap-2 text-sm">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600 shrink-0">
                    <BookOpen className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs text-ink-400">专业</div>
                    <div className="text-sm font-medium text-ink-800 truncate">{profile.major}</div>
                  </div>
                </div>
              )}
              {profile.graduation_year && (
                <div className="flex items-center gap-2 text-sm">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600 shrink-0">
                    <Calendar className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs text-ink-400">毕业年份</div>
                    <div className="text-sm font-medium text-ink-800 truncate">{profile.graduation_year}</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Stats */}
          <div className="mt-5 grid grid-cols-4 gap-3 pt-5 border-t border-paper-100">
            <div className="text-center">
              <div className="text-xl font-bold text-ink-900">{profile.post_count}</div>
              <div className="text-xs text-ink-400">经验贴</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-ink-900">{profile.qa_count}</div>
              <div className="text-xs text-ink-400">提问</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-ink-900">{profile.answer_count}</div>
              <div className="text-xs text-ink-400">回答</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-ink-900">{profile.total_likes}</div>
              <div className="text-xs text-ink-400">获赞</div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="rounded-xl border border-paper-200 bg-white p-1 shadow-sm flex gap-1 mb-4">
          {TABS.map((tab) => {
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

        {/* Tab Content */}
        {tabLoading ? (
          renderSkeleton()
        ) : activeTab === "posts" ? (
          posts.length === 0 ? (
            <div className="rounded-xl border border-paper-200 bg-white p-8">
              <EmptyState title="暂无经验贴" description="该用户还没有发布过经验贴" />
            </div>
          ) : (
            <div className="space-y-3">
              {posts.map((post) => (
                <Link
                  key={post.id}
                  href={`/kaoyan/community/posts/${post.id}`}
                  className="block rounded-xl border border-paper-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <h3 className="font-semibold text-ink-900">{post.title}</h3>
                    <Badge color={post.category === "general" ? "green" : "blue"}>
                      {post.category === "general" ? "经验贴" : post.category}
                    </Badge>
                  </div>
                  <p className="text-sm text-ink-500 mb-3 line-clamp-2">
                    {post.summary || post.content.slice(0, 120)}
                  </p>
                  <div className="flex items-center justify-between text-xs text-ink-400">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(post.created_at).toLocaleDateString("zh-CN")}
                    </span>
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
                </Link>
              ))}
            </div>
          )
        ) : activeTab === "qa" ? (
          qaList.length === 0 ? (
            <div className="rounded-xl border border-paper-200 bg-white p-8">
              <EmptyState title="暂无提问" description="该用户还没有提出过问题" />
            </div>
          ) : (
            <div className="space-y-3">
              {qaList.map((q) => (
                <Link
                  key={q.id}
                  href={`/kaoyan/community/qa/${q.id}`}
                  className="block rounded-xl border border-paper-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
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
                </Link>
              ))}
            </div>
          )
        ) : answers.length === 0 ? (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <EmptyState title="暂无回答" description="该用户还没有回答过问题" />
          </div>
        ) : (
          <div className="space-y-3">
            {answers.map((answer) => (
              <Link
                key={answer.id}
                href={`/kaoyan/community/qa/${answer.qa_id}`}
                className="block rounded-xl border border-paper-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
              >
                {answer.is_best && (
                  <div className="mb-2">
                    <Badge color="green">
                      <Award className="h-3 w-3 mr-1" />
                      最佳回答
                    </Badge>
                  </div>
                )}
                <p className="text-sm text-ink-700 mb-3 line-clamp-3 whitespace-pre-line">
                  {answer.content}
                </p>
                <div className="flex items-center gap-4 text-xs text-ink-400">
                  <span className="flex items-center gap-1">
                    <ThumbsUp className="h-3 w-3" />
                    {answer.like_count} 赞
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(answer.created_at).toLocaleDateString("zh-CN")}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
