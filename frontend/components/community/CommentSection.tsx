"use client";

import { useCallback, useEffect, useState } from "react";
import { MessageSquare, ThumbsUp, CornerDownRight } from "lucide-react";
import { commentApi } from "@/lib/api";
import { Button } from "@/components/ui/form-controls";
import { LoadingState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import type { CommentResponse } from "@/types";

interface CommentSectionProps {
  postId: string;
}

export default function CommentSection({ postId }: CommentSectionProps) {
  const toast = useToast();
  const user = useAuthStore((s) => s.user);

  const [comments, setComments] = useState<CommentResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [replyTo, setReplyTo] = useState<CommentResponse | null>(null);

  const loadComments = useCallback(async () => {
    try {
      const data = await commentApi.listByPost(postId, { limit: 50 });
      setComments(data.items);
      setTotal(data.total);
    } catch {
      toast.push("加载评论失败", "error");
    } finally {
      setLoading(false);
    }
  }, [postId, toast]);

  useEffect(() => {
    loadComments();
  }, [loadComments]);

  const handleSubmit = async () => {
    if (!user) {
      toast.push("请先登录", "error");
      return;
    }
    if (!content.trim()) {
      toast.push("请输入评论内容", "error");
      return;
    }
    setSubmitting(true);
    try {
      const newComment = await commentApi.create({
        post_id: postId,
        content: content.trim(),
        parent_id: replyTo?.id || null,
      });
      setContent("");
      setReplyTo(null);
      if (newComment.parent_id) {
        setComments((prev) =>
          prev.map((c) =>
            c.id === newComment.parent_id ? { ...c } : c,
          ),
        );
      }
      await loadComments();
      toast.push("评论成功", "success");
    } catch {
      toast.push("评论失败", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleLike = async (commentId: string) => {
    if (!user) {
      toast.push("请先登录", "error");
      return;
    }
    try {
      const res = await commentApi.like(commentId);
      setComments((prev) =>
        prev.map((c) => (c.id === commentId ? { ...c, like_count: res.like_count } : c)),
      );
    } catch {
      toast.push("点赞失败", "error");
    }
  };

  const handleDelete = async (commentId: string) => {
    if (!user) return;
    try {
      await commentApi.delete(commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
      setTotal((prev) => prev - 1);
      toast.push("已删除", "success");
    } catch {
      toast.push("删除失败", "error");
    }
  };

  return (
    <div className="mt-6 rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 flex items-center gap-2 text-base font-semibold text-ink-800">
        <MessageSquare className="h-4 w-4" />
        评论 {total > 0 && <span className="text-sm font-normal text-ink-400">({total})</span>}
      </h3>

      {/* 输入框 */}
      <div className="mb-5">
        {replyTo && (
          <div className="mb-2 flex items-center gap-2 rounded bg-brand-50 px-3 py-1.5 text-xs text-brand-700">
            <CornerDownRight className="h-3 w-3" />
            回复 {replyTo.author_nickname}
            <button onClick={() => setReplyTo(null)} className="ml-auto text-ink-400 hover:text-ink-600">
              取消
            </button>
          </div>
        )}
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={user ? (replyTo ? `回复 ${replyTo.author_nickname}...` : "写下你的评论...") : "请先登录后评论"}
          className="w-full resize-none rounded-lg border border-paper-200 px-3 py-2.5 text-sm text-ink-800 placeholder:text-ink-400 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
          rows={3}
          disabled={!user}
        />
        <div className="mt-2 flex justify-end">
          <Button size="sm" onClick={handleSubmit} loading={submitting} disabled={!content.trim()}>
            发表评论
          </Button>
        </div>
      </div>

      {/* 评论列表 */}
      {loading ? (
        <LoadingState text="加载评论..." />
      ) : comments.length === 0 ? (
        <p className="py-6 text-center text-sm text-ink-400">暂无评论，快来抢沙发吧</p>
      ) : (
        <div className="space-y-4">
          {comments.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              currentUserId={user?.id}
              onReply={setReplyTo}
              onLike={handleLike}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CommentItem({
  comment,
  currentUserId,
  onReply,
  onLike,
  onDelete,
}: {
  comment: CommentResponse;
  currentUserId?: string;
  onReply: (c: CommentResponse) => void;
  onLike: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="border-b border-paper-100 pb-4 last:border-b-0 last:pb-0">
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-medium text-brand-700">
          {comment.author_nickname?.charAt(0) || "匿"}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-ink-700">{comment.author_nickname}</span>
            <span className="text-xs text-ink-400">
              {new Date(comment.created_at).toLocaleDateString("zh-CN")}
            </span>
          </div>
          <p className="mt-1 whitespace-pre-line text-sm text-ink-600">{comment.content}</p>
          <div className="mt-2 flex items-center gap-4 text-xs text-ink-400">
            <button
              onClick={() => onReply(comment)}
              className="hover:text-brand-600"
            >
              回复
            </button>
            <button
              onClick={() => onLike(comment.id)}
              className="flex items-center gap-1 hover:text-brand-600"
            >
              <ThumbsUp className="h-3 w-3" />
              {comment.like_count > 0 && comment.like_count}
            </button>
            {currentUserId === comment.user_id && (
              <button
                onClick={() => onDelete(comment.id)}
                className="hover:text-red-500"
              >
                删除
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
