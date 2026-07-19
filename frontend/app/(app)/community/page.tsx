"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Send,
  Users,
  Bot,
  Plus,
  MessageCircle,
  UserPlus,
  UserCheck,
  Bell,
} from "lucide-react";
import { postsApi, commentApi, followApi, communityApi, employmentApi } from "@/lib/api";
import { Button, Input, Textarea } from "@/components/ui/form-controls";
import { EmptyState } from "@/components/ui/empty";
import { ListSkeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/ui/pagination";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import { cn } from "@/lib/utils";

type Tab = "feed" | "report" | "mentors";

export default function CommunityPage() {
  const user = useAuthStore((s) => s.user);
  const [tab, setTab] = useState<Tab>("feed");

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/15 text-brand-500">
          <Users className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-800">
            社区交流
          </h1>
          <p className="text-sm text-ink-500">
            真实的考研 / 考公 / 就业交流广场：发帖、评论、关注作者、收到通知。
          </p>
        </div>
      </header>

      <div className="flex gap-1 rounded-lg bg-paper-200 p-1 w-fit">
        {([
          { id: "feed", label: "广场", icon: MessageCircle },
          { id: "report", label: "上岸报告", icon: Send },
          { id: "mentors", label: "导师评价", icon: Users },
        ] as const).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
              tab === t.id ? "bg-white text-brand-600 shadow-sm" : "text-ink-500 hover:text-ink-700",
            )}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === "feed" && <FeedTab currentUser={user} />}
      {tab === "report" && <ReportTab />}
      {tab === "mentors" && (
        <EmptyState
          title="导师评价"
          description="前往考研中心 → 导师情报查看学长学姐对导师的评价。"
          action={<Link href="/kaoyan" className="text-brand-600 underline">去考研中心</Link>}
        />
      )}
    </div>
  );
}

type FeedPost = {
  id: string;
  title?: string | null;
  content: string;
  author_id: string;
  author_name: string;
  topic_type: string;
  topic_key: string;
  created_at: string;
  replies?: any[];
};

function FeedTab({ currentUser }: { currentUser: any }) {
  const toast = useToast();
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showComposer, setShowComposer] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [posting, setPosting] = useState(false);
  const PAGE_SIZE = 10;

  const load = useCallback(() => {
    setLoading(true);
    postsApi
      .publicList({ page, page_size: PAGE_SIZE })
      .then((d) => {
        setPosts(d.items as FeedPost[]);
        setTotal(d.total);
      })
      .catch(() => toast.push("加载广场失败", "error"))
      .finally(() => setLoading(false));
  }, [page, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const submit = () => {
    if (!content.trim()) return;
    setPosting(true);
    postsApi
      .create({
        topic_type: "school_major",
        topic_key: "广场",
        title: title.trim() || undefined,
        content: content.trim(),
      })
      .then(() => {
        setTitle("");
        setContent("");
        setShowComposer(false);
        setPage(1);
        load();
        toast.push("发布成功", "success");
      })
      .catch(() => toast.push("发布失败", "error"))
      .finally(() => setPosting(false));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-500">共 {total} 条讨论</p>
        <Button size="sm" onClick={() => setShowComposer((s) => !s)}>
          <Plus className="h-4 w-4" /> 发帖
        </Button>
      </div>

      {showComposer && (
        <div className="space-y-2 rounded-xl border border-paper-300 bg-white p-4">
          <Input
            placeholder="标题（可选）"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <Textarea
            placeholder="分享你的备考经验、疑问或资讯…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setShowComposer(false)}>
              取消
            </Button>
            <Button size="sm" onClick={submit} loading={posting}>
              发布
            </Button>
          </div>
        </div>
      )}

      {loading ? (
        <ListSkeleton count={5} />
      ) : posts.length === 0 ? (
        <EmptyState title="还没有讨论" description="成为第一个发帖的人吧！" />
      ) : (
        <div className="space-y-3">
          {posts.map((p) => (
            <PostCard key={p.id} post={p} currentUser={currentUser} onChanged={load} />
          ))}
        </div>
      )}

      {total > PAGE_SIZE && (
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}

function PostCard({
  post,
  currentUser,
  onChanged,
}: {
  post: FeedPost;
  currentUser: any;
  onChanged: () => void;
}) {
  const toast = useToast();
  const [following, setFollowing] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState<any[]>([]);
  const [commentText, setCommentText] = useState("");
  const isMine = currentUser && post.author_id === currentUser.id;

  useEffect(() => {
    if (!currentUser || isMine) return;
    followApi
      .status(post.author_id)
      .then((r) => setFollowing(r.is_following))
      .catch(() => {});
  }, [currentUser, post.author_id, isMine]);

  const toggleFollow = () => {
    const op = following ? followApi.unfollow(post.author_id) : followApi.follow(post.author_id);
    op
      .then(() => setFollowing(!following))
      .catch(() => toast.push("操作失败", "error"));
  };

  const loadComments = () => {
    commentApi
      .listByPost(post.id, { limit: 50 })
      .then((d) => setComments(d.items))
      .catch(() => {});
  };

  const toggleComments = () => {
    setShowComments((s) => !s);
    if (!showComments) loadComments();
  };

  const submitComment = () => {
    if (!commentText.trim()) return;
    commentApi
      .create({ post_id: post.id, content: commentText.trim() })
      .then(() => {
        setCommentText("");
        loadComments();
        onChanged();
      })
      .catch(() => toast.push("评论失败", "error"));
  };

  return (
    <div className="rounded-xl border border-paper-300 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-ink-400">{post.author_name} · {new Date(post.created_at).toLocaleDateString("zh-CN")}</p>
          {post.title && <h3 className="font-semibold text-ink-800">{post.title}</h3>}
          <p className="mt-1 text-sm text-ink-700 whitespace-pre-wrap">{post.content}</p>
        </div>
        {!isMine && currentUser && (
          <button
            onClick={toggleFollow}
            className={cn(
              "flex flex-shrink-0 items-center gap-1 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              following
                ? "bg-paper-200 text-ink-600"
                : "bg-brand-500 text-white hover:bg-brand-600",
            )}
          >
            {following ? <UserCheck className="h-4 w-4" /> : <UserPlus className="h-4 w-4" />}
            {following ? "已关注" : "关注"}
          </button>
        )}
      </div>

      <div className="mt-3 flex items-center gap-4 text-sm text-ink-500">
        <button onClick={toggleComments} className="flex items-center gap-1 hover:text-brand-600">
          <MessageCircle className="h-4 w-4" />
          {comments.length > 0 ? comments.length : "评论"}
        </button>
      </div>

      {showComments && (
        <div className="mt-3 space-y-2 border-t border-paper-200 pt-3">
          {comments.map((c) => (
            <div key={c.id} className="text-sm">
              <span className="font-medium text-ink-700">{c.author_nickname}：</span>
              <span className="text-ink-600">{c.content}</span>
            </div>
          ))}
          {currentUser && (
            <div className="flex gap-2">
              <Input
                placeholder="写下评论…"
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
              />
              <Button size="sm" onClick={submitComment}>
                发送
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ReportTab() {
  const toast = useToast();
  const [schools, setSchools] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [myReports, setMyReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const PAGE_SIZE = 10;
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const loadMyReports = useCallback(
    (target = 1) => {
      communityApi
        .myReports({ page: target, page_size: PAGE_SIZE })
        .then((d) => {
          setMyReports(d.items);
          setTotal(d.total);
          setPage(target);
        })
        .catch(() => {});
    },
    [],
  );

  useEffect(() => {
    Promise.all([employmentApi.schools(), communityApi.stats(), communityApi.myReports({ page: 1, page_size: PAGE_SIZE })])
      .then(([s, st, mine]) => {
        setSchools(s);
        setStats(st);
        setMyReports(mine.items);
        setTotal(mine.total);
      })
      .catch((err) => toast.push(err instanceof Error ? err.message : "加载失败", "error"))
      .finally(() => setLoading(false));
  }, [toast]);

  if (loading) return <ListSkeleton count={4} />;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-paper-300 bg-white p-4">
        <h2 className="font-semibold text-ink-800">匿名分享你的毕业去向</h2>
        <p className="mt-1 text-sm text-ink-500">
          聚合后与官方数据互补，帮助学弟学妹做出更明智的决策。
        </p>
        {stats && (
          <p className="mt-2 text-sm text-ink-600">
            已收集 {stats.total_reports ?? 0} 份去向报告
          </p>
        )}
      </div>
      <div>
        <h3 className="mb-2 text-sm font-medium text-ink-700">我的提交记录</h3>
        {myReports.length === 0 ? (
          <EmptyState title="还没有提交记录" description="在上方表单分享你的去向吧。" />
        ) : (
          <div className="space-y-2">
            {myReports.map((r) => (
              <div key={r.id} className="rounded-lg border border-paper-200 px-3 py-2 text-sm text-ink-600">
                {r.school_name} · {r.destination_type} · {r.salary_range ?? "薪资未填"}
              </div>
            ))}
          </div>
        )}
        {total > PAGE_SIZE && (
          <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={loadMyReports} />
        )}
      </div>
    </div>
  );
}
