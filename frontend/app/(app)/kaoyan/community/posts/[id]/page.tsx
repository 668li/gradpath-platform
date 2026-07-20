"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ThumbsUp,
  Eye,
  MessageSquare,
  Clock,
  Bookmark,
  Send,
  CornerDownRight,
  Star,
} from "lucide-react";
import { kaoyanCommunityApi, commentApi, bookmarksApi, ratingApi } from "@/lib/api";
import type { RatingStats } from "@/lib/api/communityRating";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import type { ExperiencePostResponse, CommentResponse } from "@/types";

export default function ExperiencePostDetailPage() {
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const postId = params.id as string;
  const user = useAuthStore((s) => s.user);

  const [post, setPost] = useState<ExperiencePostResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [liking, setLiking] = useState(false);

  const [comments, setComments] = useState<CommentResponse[]>([]);
  const [commentsTotal, setCommentsTotal] = useState(0);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [commentText, setCommentText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [replyTo, setReplyTo] = useState<CommentResponse | null>(null);
  const [likeMap, setLikeMap] = useState<Record<string, boolean>>({});

  const [bookmarked, setBookmarked] = useState(false);
  const [bookmarkId, setBookmarkId] = useState<string | null>(null);
  const [bookmarking, setBookmarking] = useState(false);

  const [ratingStats, setRatingStats] = useState<RatingStats | null>(null);
  const [myRating, setMyRating] = useState(0);
  const [ratingSubmitting, setRatingSubmitting] = useState(false);

  const loadPost = useCallback(async () => {
    try {
      const data = await kaoyanCommunityApi.experiencePosts.get(postId);
      setPost(data);
    } catch {
      toast.push("加载经验贴失败", "error");
    } finally {
      setLoading(false);
    }
  }, [postId, toast]);

  const loadComments = useCallback(async () => {
    setCommentsLoading(true);
    try {
      const data = await commentApi.listByPost(postId);
      setComments(data.items);
      setCommentsTotal(data.total);
    } catch {
      // 评论加载失败不阻断帖子阅读
    } finally {
      setCommentsLoading(false);
    }
  }, [postId]);

  const loadBookmarkStatus = useCallback(async () => {
    if (!user) return;
    try {
      const data = await bookmarksApi.list({ target_type: "post" });
      const found = data.items.find((b) => b.target_id === postId);
      if (found) {
        setBookmarked(true);
        setBookmarkId(found.id);
      }
    } catch {
      /* noop */
    }
  }, [user, postId]);

  const loadRatingStats = useCallback(async () => {
    try {
      const stats = await ratingApi.stats("experience_post", postId);
      setRatingStats(stats);
    } catch {
      /* noop */
    }
  }, [postId]);

  const loadMyRating = useCallback(async () => {
    if (!user) return;
    try {
      const ratings = await ratingApi.userRatings({ target_type: "experience_post" });
      const mine = ratings.find((r) => r.target_id === postId);
      if (mine) setMyRating(mine.score);
    } catch {
      /* noop */
    }
  }, [user, postId]);

  useEffect(() => {
    loadPost();
    loadComments();
    loadBookmarkStatus();
    loadRatingStats();
    loadMyRating();
  }, [loadPost, loadComments, loadBookmarkStatus, loadRatingStats, loadMyRating]);

  const handleLike = async () => {
    if (!user) {
      toast.push("请先登录", "error");
      return;
    }
    setLiking(true);
    try {
      const res = await kaoyanCommunityApi.experiencePosts.like(postId);
      toast.push("点赞成功", "success");
      setPost((prev) => (prev ? { ...prev, like_count: res.like_count } : prev));
    } catch {
      toast.push("点赞失败", "error");
    } finally {
      setLiking(false);
    }
  };

  const handleCommentLike = async (c: CommentResponse) => {
    if (!user) {
      toast.push("请先登录", "error");
      return;
    }
    const liked = likeMap[c.id];
    try {
      const res = await commentApi.like(c.id);
      setLikeMap((m) => ({ ...m, [c.id]: !liked }));
      setComments((prev) =>
        prev.map((x) =>
          x.id === c.id ? { ...x, like_count: res.like_count } : x,
        ),
      );
    } catch {
      toast.push("操作失败", "error");
    }
  };

  const handleToggleBookmark = async () => {
    if (!user) {
      toast.push("请先登录", "error");
      return;
    }
    setBookmarking(true);
    try {
      if (bookmarked && bookmarkId) {
        await bookmarksApi.remove(bookmarkId);
        setBookmarked(false);
        setBookmarkId(null);
        toast.push("已取消收藏", "success");
      } else {
        const res = await bookmarksApi.add({
          target_type: "post",
          target_id: postId,
        });
        setBookmarked(true);
        setBookmarkId(res.id);
        toast.push("收藏成功", "success");
      }
    } catch {
      toast.push("操作失败", "error");
    } finally {
      setBookmarking(false);
    }
  };

  const handleRate = async (score: number) => {
    if (!user) {
      toast.push("请先登录", "error");
      return;
    }
    if (score === myRating) return;
    setRatingSubmitting(true);
    try {
      await ratingApi.rate({
        target_type: "experience_post",
        target_id: postId,
        score,
      });
      setMyRating(score);
      await loadRatingStats();
      toast.push("评分成功", "success");
    } catch {
      toast.push("评分失败", "error");
    } finally {
      setRatingSubmitting(false);
    }
  };

  const handleSubmitComment = async () => {
    if (!user) {
      toast.push("请先登录", "error");
      return;
    }
    const content = commentText.trim();
    if (!content) return;
    setSubmitting(true);
    try {
      await commentApi.create({
        post_id: postId,
        content,
        parent_id: replyTo ? replyTo.id : null,
      });
      setCommentText("");
      setReplyTo(null);
      toast.push("评论成功", "success");
      await loadComments();
      setPost((prev) =>
        prev ? { ...prev, comment_count: (prev.comment_count || 0) + 1 } : prev,
      );
    } catch {
      toast.push("评论失败", "error");
    } finally {
      setSubmitting(false);
    }
  };

  // 构建嵌套结构：顶层评论 + 各自的回复
  const topLevel = comments.filter((c) => !c.parent_id);
  const repliesOf = (id: string) =>
    comments
      .filter((c) => c.parent_id === id)
      .sort((a, b) => a.created_at.localeCompare(b.created_at));

  const renderComment = (c: CommentResponse, isReply = false) => (
    <div
      key={c.id}
      className={cn(
        "flex gap-3",
        isReply && "ml-8 mt-3 border-l-2 border-paper-100 pl-4",
      )}
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
        {c.author_nickname?.[0] ?? "U"}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-ink-800">
            {c.author_nickname}
          </span>
          <span className="text-xs text-ink-400">
            {new Date(c.created_at).toLocaleDateString("zh-CN")}
          </span>
        </div>
        <p className="mt-1 whitespace-pre-line text-sm text-ink-700">
          {c.is_deleted ? (
            <span className="italic text-ink-400">[该评论已删除]</span>
          ) : (
            c.content
          )}
        </p>
        {!c.is_deleted && (
          <div className="mt-1.5 flex items-center gap-4">
            <button
              onClick={() => handleCommentLike(c)}
              className={cn(
                "flex items-center gap-1 text-xs transition-colors",
                likeMap[c.id]
                  ? "text-brand-600"
                  : "text-ink-400 hover:text-brand-600",
              )}
            >
              <ThumbsUp className="h-3.5 w-3.5" />
              {c.like_count}
            </button>
            {!isReply && (
              <button
                onClick={() => setReplyTo(c)}
                className="flex items-center gap-1 text-xs text-ink-400 hover:text-brand-600"
              >
                <CornerDownRight className="h-3.5 w-3.5" />
                回复
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
          <LoadingState text="加载经验贴..." />
        </div>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="min-h-screen bg-paper-50">
        <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
          <div className="rounded-xl border border-paper-200 bg-white p-8 text-center">
            <p className="text-ink-500">经验贴不存在或已被删除</p>
            <Button onClick={() => router.push("/kaoyan/community")} className="mt-4">
              返回社区
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
        {/* Back Button */}
        <button
          onClick={() => router.back()}
          className="mb-4 flex items-center gap-2 text-sm text-ink-500 hover:text-ink-700"
        >
          <ArrowLeft className="h-4 w-4" />
          返回列表
        </button>

        {/* Post Card */}
        <div className="rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
          {/* Header */}
          <div className="mb-4">
            <div className="flex items-start justify-between gap-3 mb-3">
              <h1 className="text-xl sm:text-2xl font-bold text-ink-900">{post.title}</h1>
              <div className="flex gap-2 shrink-0">
                <Badge color={post.category === "general" ? "green" : "blue"}>
                  {post.category === "general" ? "经验贴" : post.category}
                </Badge>
                {post.is_pinned && <Badge color="red">置顶</Badge>}
                {post.is_verified && <Badge color="green">已认证</Badge>}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm text-ink-500">
              <span>{post.is_anonymous ? "匿名用户" : `用户 ${post.user_id.slice(-4)}`}</span>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                {new Date(post.created_at).toLocaleDateString("zh-CN")}
              </span>
              <span className="flex items-center gap-1">
                <Eye className="h-3.5 w-3.5" />
                {post.view_count} 次浏览
              </span>
            </div>
          </div>

          {/* Tags */}
          {post.tags.length > 0 && (
            <div className="mb-5 flex flex-wrap gap-2">
              {post.tags.map((tag, i) => (
                <span
                  key={`${tag}-${i}`}
                  className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Content */}
          <div className="prose prose-sm max-w-none text-ink-700 whitespace-pre-line">
            {post.content}
          </div>

          {/* Footer Actions */}
          <div className="mt-8 flex items-center justify-between border-t border-paper-100 pt-5">
            <div className="flex items-center gap-4 text-sm text-ink-500">
              <span className="flex items-center gap-1">
                <MessageSquare className="h-4 w-4" />
                {commentsTotal} 条评论
              </span>
              <span className="flex items-center gap-1">
                <Eye className="h-4 w-4" />
                {post.view_count} 次浏览
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant={bookmarked ? "primary" : "secondary"}
                size="sm"
                onClick={handleToggleBookmark}
                loading={bookmarking}
              >
                <Bookmark className="h-4 w-4 mr-1.5" />
                {bookmarked ? "已收藏" : "收藏"}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleLike}
                loading={liking}
              >
                <ThumbsUp className="h-4 w-4 mr-1.5" />
                点赞 {post.like_count}
              </Button>
            </div>
          </div>
        </div>

        {/* Rating Section */}
        <div className="mt-6 rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-ink-900">
                  {ratingStats ? ratingStats.average.toFixed(1) : "-"}
                </div>
                <div className="text-xs text-ink-400">
                  {ratingStats ? `${ratingStats.count} 条评分` : "暂无评分"}
                </div>
              </div>
              {ratingStats && ratingStats.count > 0 && (
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Star
                      key={s}
                      className={cn(
                        "h-5 w-5",
                        s <= Math.round(ratingStats.average)
                          ? "fill-yellow-400 text-yellow-400"
                          : "fill-paper-200 text-paper-200",
                      )}
                    />
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm text-ink-500 mr-1">我的评分:</span>
              {[1, 2, 3, 4, 5].map((s) => (
                <button
                  key={s}
                  disabled={ratingSubmitting}
                  onClick={() => handleRate(s)}
                  className="disabled:opacity-50"
                >
                  <Star
                    className={cn(
                      "h-6 w-6 transition-colors",
                      s <= myRating
                        ? "fill-yellow-400 text-yellow-400 hover:fill-yellow-500 hover:text-yellow-500"
                        : "fill-paper-200 text-paper-300 hover:fill-yellow-200 hover:text-yellow-300",
                    )}
                  />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Comment Section */}
        <div className="mt-6 rounded-xl border border-paper-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-ink-900">
            评论区 ({commentsTotal})
          </h2>

          {/* Composer */}
          <div className="mb-6">
            {replyTo && (
              <div className="mb-2 flex items-center justify-between rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700">
                <span>回复 @{replyTo.author_nickname}</span>
                <button
                  onClick={() => setReplyTo(null)}
                  className="text-brand-500 hover:text-brand-700"
                >
                  取消
                </button>
              </div>
            )}
            <div className="flex gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink-100 text-sm font-semibold text-ink-500">
                {user?.name?.[0] ?? "U"}
              </div>
              <div className="flex-1">
                <textarea
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder={user ? "写下你的评论..." : "登录后参与评论"}
                  disabled={!user}
                  rows={3}
                  className="w-full resize-none rounded-lg border border-paper-200 px-3 py-2 text-sm text-ink-800 outline-none focus:border-brand-400 disabled:bg-paper-100"
                />
                <div className="mt-2 flex justify-end">
                  <Button
                    size="sm"
                    onClick={handleSubmitComment}
                    loading={submitting}
                    disabled={!commentText.trim()}
                  >
                    <Send className="h-4 w-4 mr-1.5" />
                    {replyTo ? "回复" : "发表评论"}
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* Comment List */}
          {commentsLoading ? (
            <LoadingState text="加载评论..." />
          ) : topLevel.length === 0 ? (
            <p className="py-6 text-center text-sm text-ink-400">
              还没有评论，来抢沙发吧
            </p>
          ) : (
            <div className="space-y-5">
              {topLevel.map((c) => (
                <div key={c.id}>
                  {renderComment(c)}
                  {repliesOf(c.id).map((r) => renderComment(r, true))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
