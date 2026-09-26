"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Users,
  Plus,
  MessageCircle,
  UserPlus,
  UserCheck,
  Search,
} from "lucide-react";
import { postsApi, postRepliesApi, followApi } from "@/lib/api";
import { Button, Input, Textarea } from "@/components/ui/form-controls";
import { EmptyState } from "@/components/ui/empty";
import { ListSkeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/ui/pagination";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import { cn } from "@/lib/utils";
import type { PostItem, UserResponse } from "@/types";

type DirectionTab = "all" | "kaoyan" | "employment";

export default function CommunityPage() {
  const user = useAuthStore((s) => s.user);
  const [directionTab, setDirectionTab] = useState<DirectionTab>("all");
  const router = useRouter();

  const directionTabs: { id: DirectionTab; label: string }[] = [
    { id: "all", label: "全部" },
    { id: "kaoyan", label: "考研专区" },
    { id: "employment", label: "就业专区" },
  ];

  const handleDirectionTabChange = (id: DirectionTab) => {
    if (id === "kaoyan") {
      router.push("/kaoyan/community");
      return;
    }
    setDirectionTab(id);
  };

  return (
    <div className="space-y-6">
      {/* 方向专区 Tab */}
      <div className="flex gap-0 border-b border-paper-200">
        {directionTabs.map((t) => (
          <button
            key={t.id}
            onClick={() => handleDirectionTabChange(t.id)}
            className={cn(
              "px-5 py-3 text-sm font-medium transition-all border-b-2",
              directionTab === t.id
                ? "border-brand-500 text-brand-600"
                : "border-transparent text-ink-400 hover:text-ink-600",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {directionTab === "all" && (
        <>
          <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/15 text-brand-500">
          <Users className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-800">
            社区交流
          </h1>
          <p className="text-sm text-ink-500">
            真实的考研 / 就业交流广场：发帖、评论、关注作者、收到通知。
          </p>
        </div>
      </header>

      <FeedTab currentUser={user} />
        </>
      )}

      {directionTab === "employment" && (
        <EmptyState
          title="就业专区"
          description="就业专区即将上线，敬请期待..."
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
  replies?: PostItem[];
};

function FeedTab({ currentUser }: { currentUser: UserResponse | null }) {
  const toast = useToast();
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showComposer, setShowComposer] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [posting, setPosting] = useState(false);
  const [searchText, setSearchText] = useState("");
  const PAGE_SIZE = 10;

  const load = useCallback((opts?: { silent?: boolean }) => {
    // 静默刷新（评论/点赞后）不整屏换骨架屏，避免卡片状态（展开的评论区）丢失
    if (!opts?.silent) setLoading(true);
    postsApi
      .publicList({ page, page_size: PAGE_SIZE })
      .then((d) => {
        // 修复 P0 bug: 后端可能返回 null，导致 d.items 崩溃
        if (!d) {
          setPosts([]);
          setTotal(0);
          return;
        }
        setPosts(Array.isArray(d.items) ? (d.items as FeedPost[]) : []);
        setTotal(d.total || 0);
      })
      .catch(() => {
        toast.push("加载广场失败", "error");
        setPosts([]);
        setTotal(0);
      })
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
      <div className="flex items-center justify-between gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -tranink-y-1/2 h-4 w-4 text-ink-400" />
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="搜索帖子标题或内容..."
            className="w-full rounded-lg border border-paper-300 bg-white pl-9 pr-3 py-2 text-sm text-ink-800 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          />
        </div>
        <p className="text-sm text-ink-500 whitespace-nowrap">共 {total} 条</p>
        <Button size="sm" onClick={() => setShowComposer((s) => !s)} data-testid="new-post-button">
          <Plus className="h-4 w-4" /> 发帖
        </Button>
      </div>

      {showComposer && (
        <div className="space-y-2 rounded-xl border border-paper-300 bg-white p-4">
          <Input
            placeholder="标题（可选）"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            data-testid="post-title-input"
          />
          <Textarea
            placeholder="分享你的备考经验、疑问或资讯…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            data-testid="post-content-input"
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setShowComposer(false)}>
              取消
            </Button>
            <Button size="sm" onClick={submit} loading={posting} data-testid="submit-post-button">
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
          {posts
            .filter((p) => !searchText || (p.title?.toLowerCase().includes(searchText.toLowerCase())) || p.content.toLowerCase().includes(searchText.toLowerCase()))
            .map((p) => (
            <PostCard key={p.id} post={p} currentUser={currentUser} onChanged={() => load({ silent: true })} />
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
  currentUser: UserResponse | null;
  onChanged: () => void;
}) {
  const toast = useToast();
  const [following, setFollowing] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState<PostItem[]>([]);
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
    postRepliesApi
      .list(post.id)
      .then((d) => setComments(d))
      .catch(() => {});
  };

  const toggleComments = () => {
    setShowComments((s) => !s);
    if (!showComments) loadComments();
  };

  const submitComment = () => {
    if (!commentText.trim()) return;
    postRepliesApi
      .create(
        { id: post.id, topic_type: post.topic_type, topic_key: post.topic_key },
        commentText.trim(),
      )
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
        <button onClick={toggleComments} className="flex items-center gap-1 hover:text-brand-600" data-testid={`post-comments-toggle-${post.id}`}>
          <MessageCircle className="h-4 w-4" />
          {comments.length > 0 ? comments.length : "评论"}
        </button>
      </div>

      {showComments && (
        <div className="mt-3 space-y-2 border-t border-paper-200 pt-3">
          {comments.map((c) => (
            <div key={c.id} className="text-sm" data-testid={`comment-item-${c.id}`}>
              <span className="font-medium text-ink-700">{c.author_name}：</span>
              <span className="text-ink-600">{c.content}</span>
            </div>
          ))}
          {currentUser && (
            <div className="flex gap-2">
              <Input
                placeholder="写下评论…"
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                data-testid="comment-input"
              />
              <Button size="sm" onClick={submitComment} data-testid="submit-comment-button">
                发送
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
