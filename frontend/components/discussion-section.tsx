"use client";

import { useState, useCallback, useEffect } from "react";
import {
  MessageSquare,
  Send,
  Trash2,
  Edit2,
  CornerDownRight,
} from "lucide-react";
import { postsApi } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/form-controls";
import { useAuthStore } from "@/stores/auth";
import type { PostItem, PostTopicType } from "@/types";

interface DiscussionSectionProps {
  topicType: PostTopicType;
  topicKey: string;
  title?: string;
}

const MAX_CONTENT = 2000;
const PAGE_SIZE = 20;

/** 相对时间格式化 */
function relativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diff = now - then;
  const min = Math.floor(diff / 60000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min} 分钟前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} 小时前`;
  const day = Math.floor(hr / 24);
  if (day < 30) return `${day} 天前`;
  return new Date(iso).toLocaleDateString("zh-CN");
}

/** 作者头像首字 */
function Avatar({ name }: { name: string }) {
  const initial = name.charAt(0).toUpperCase();
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-500 text-sm font-medium text-white">
      {initial}
    </div>
  );
}

/** 帖子内容渲染（URL 转链接，换行保留） */
function renderContent(content: string) {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = content.split(urlRegex);
  return parts.map((part, i) => {
    // 用独立的非全局正则做判定，避免 g 标志 lastIndex 状态残留导致漏判
    if (/^https?:\/\//.test(part)) {
      return (
        <a
          key={`link-${i}`}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand-600 hover:underline"
        >
          {part}
        </a>
      );
    }
    // 保留换行
    const lines = part.split("\n");
    return lines.map((line, j) => (
      <span key={`${i}-${j}`}>
        {line}
        {j < lines.length - 1 && <br />}
      </span>
    ));
  });
}

/** 单条帖子卡片 */
function PostCard({
  post,
  currentUserId,
  onReply,
  onEdit,
  onDelete,
}: {
  post: PostItem;
  currentUserId: string | null;
  onReply: (postId: string, content: string) => void;
  onEdit: (postId: string, content: string) => void;
  onDelete: (postId: string) => void;
}) {
  const [showReplyBox, setShowReplyBox] = useState(false);
  const [replyContent, setReplyContent] = useState("");
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(post.content);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isAuthor = currentUserId === post.author_id;

  const handleReply = () => {
    if (!replyContent.trim()) return;
    onReply(post.id, replyContent);
    setReplyContent("");
    setShowReplyBox(false);
  };

  const handleEdit = () => {
    if (!editContent.trim()) return;
    onEdit(post.id, editContent);
    setEditing(false);
  };

  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="flex items-start gap-3">
        <Avatar name={post.author_name} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-slate-800">
              {post.author_name}
            </span>
            <span className="text-xs text-slate-400">
              {relativeTime(post.created_at)}
            </span>
          </div>

          {editing ? (
            <div className="mt-2 space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                maxLength={MAX_CONTENT}
                rows={3}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={handleEdit}>
                  保存
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    setEditing(false);
                    setEditContent(post.content);
                  }}
                >
                  取消
                </Button>
              </div>
            </div>
          ) : (
            <p className="mt-1 text-sm text-slate-600 whitespace-pre-wrap break-words">
              {renderContent(post.content)}
            </p>
          )}

          <div className="mt-2 flex items-center gap-3">
            {isAuthor && !editing && (
              <>
                <button
                  onClick={() => setEditing(true)}
                  className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-brand-600"
                >
                  <Edit2 className="h-3 w-3" /> 编辑
                </button>
                {confirmDelete ? (
                  <span className="inline-flex items-center gap-1">
                    <button
                      onClick={() => onDelete(post.id)}
                      className="text-xs text-red-500 hover:underline"
                    >
                      确认删除
                    </button>
                    <button
                      onClick={() => setConfirmDelete(false)}
                      className="text-xs text-slate-400 hover:underline"
                    >
                      取消
                    </button>
                  </span>
                ) : (
                  <button
                    onClick={() => setConfirmDelete(true)}
                    className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-red-500"
                  >
                    <Trash2 className="h-3 w-3" /> 删除
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* 回复列表 */}
      {post.replies && post.replies.length > 0 && (
        <div className="mt-3 ml-11 space-y-3">
          {post.replies.map((reply) => (
            <div key={reply.id} className="flex items-start gap-2">
              <CornerDownRight className="h-4 w-4 shrink-0 text-slate-300 mt-1" />
              <Avatar name={reply.author_name} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-xs text-slate-700">
                    {reply.author_name}
                  </span>
                  <span className="text-xs text-slate-400">
                    {relativeTime(reply.created_at)}
                  </span>
                </div>
                <p className="mt-0.5 text-sm text-slate-600 whitespace-pre-wrap break-words">
                  {renderContent(reply.content)}
                </p>
                <ReplyActions
                  reply={reply}
                  currentUserId={currentUserId}
                  onEdit={onEdit}
                  onDelete={onDelete}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 回复输入框 */}
      {showReplyBox && (
        <div className="mt-3 ml-11 space-y-2">
          <textarea
            value={replyContent}
            onChange={(e) => setReplyContent(e.target.value)}
            maxLength={MAX_CONTENT}
            rows={2}
            placeholder="写下你的回复…"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
          <div className="flex gap-2">
            <Button size="sm" onClick={handleReply}>
              <Send className="h-3 w-3" /> 发送回复
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setShowReplyBox(false)}
            >
              取消
            </Button>
          </div>
        </div>
      )}

      {/* 回复按钮 */}
      {!showReplyBox && (
        <button
          onClick={() => setShowReplyBox(true)}
          className="mt-2 ml-11 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-brand-600"
        >
          <MessageSquare className="h-3 w-3" /> 回复
        </button>
      )}
    </div>
  );
}

/** 回复的操作按钮（编辑/删除） */
function ReplyActions({
  reply,
  currentUserId,
  onEdit,
  onDelete,
}: {
  reply: PostItem;
  currentUserId: string | null;
  onEdit: (postId: string, content: string) => void;
  onDelete: (postId: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(reply.content);
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (currentUserId !== reply.author_id) return null;

  if (editing) {
    return (
      <div className="mt-1 space-y-1">
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          maxLength={MAX_CONTENT}
          rows={2}
          className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none"
        />
        <div className="flex gap-2">
          <button
            onClick={() => {
              if (editContent.trim()) {
                onEdit(reply.id, editContent);
                setEditing(false);
              }
            }}
            className="text-xs text-brand-600 hover:underline"
          >
            保存
          </button>
          <button
            onClick={() => {
              setEditing(false);
              setEditContent(reply.content);
            }}
            className="text-xs text-slate-400 hover:underline"
          >
            取消
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-1 flex items-center gap-2">
      <button
        onClick={() => setEditing(true)}
        className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-brand-600"
      >
        <Edit2 className="h-3 w-3" /> 编辑
      </button>
      {confirmDelete ? (
        <span className="inline-flex items-center gap-1">
          <button
            onClick={() => onDelete(reply.id)}
            className="text-xs text-red-500 hover:underline"
          >
            确认删除
          </button>
          <button
            onClick={() => setConfirmDelete(false)}
            className="text-xs text-slate-400 hover:underline"
          >
            取消
          </button>
        </span>
      ) : (
        <button
          onClick={() => setConfirmDelete(true)}
          className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-red-500"
        >
          <Trash2 className="h-3 w-3" /> 删除
        </button>
      )}
    </div>
  );
}

export function DiscussionSection({
  topicType,
  topicKey,
  title,
}: DiscussionSectionProps) {
  const [posts, setPosts] = useState<PostItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [newContent, setNewContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const toast = useToast();
  const { user } = useAuthStore();

  const loadPosts = useCallback(
    async (pageNum: number, append: boolean) => {
      try {
        const resp = await postsApi.list({
          topic_type: topicType,
          topic_key: topicKey,
          page: pageNum,
          page_size: PAGE_SIZE,
        });
        if (append) {
          setPosts((prev) => [...prev, ...resp.items]);
        } else {
          setPosts(resp.items);
        }
        setTotal(resp.total);
        setPage(resp.page);
      } catch (err) {
        toast.push(
          err instanceof Error ? err.message : "加载讨论失败",
          "error",
        );
      } finally {
        setLoading(false);
      }
    },
    [topicType, topicKey, toast],
  );

  // 初始加载（topicType / topicKey 变化时重新拉取）
  useEffect(() => {
    setLoading(true);
    loadPosts(1, false);
    // loadPosts 依赖 toast 等，仅在主题变化时触发首屏加载
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicType, topicKey]);

  const handleCreate = async () => {
    if (!newContent.trim()) return;
    setSubmitting(true);
    try {
      const created = await postsApi.create({
        topic_type: topicType,
        topic_key: topicKey,
        content: newContent,
      });
      setPosts((prev) => [created, ...prev]);
      setTotal((prev) => prev + 1);
      setNewContent("");
      toast.push("发布成功", "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "发布失败", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReply = async (parentId: string, content: string) => {
    try {
      const reply = await postsApi.create({
        topic_type: topicType,
        topic_key: topicKey,
        content,
        parent_id: parentId,
      });
      setPosts((prev) =>
        prev.map((p) =>
          p.id === parentId
            ? { ...p, replies: [...p.replies, reply] }
            : p,
        ),
      );
      toast.push("回复成功", "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "回复失败", "error");
    }
  };

  const handleEdit = async (postId: string, content: string) => {
    try {
      const updated = await postsApi.update(postId, content);
      // 更新顶层帖或回复
      setPosts((prev) =>
        prev.map((p) => {
          if (p.id === postId) return updated;
          return {
            ...p,
            replies: p.replies.map((r) =>
              r.id === postId ? { ...r, content: updated.content } : r,
            ),
          };
        }),
      );
      toast.push("修改成功", "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "修改失败", "error");
    }
  };

  const handleDelete = async (postId: string) => {
    try {
      await postsApi.remove(postId);
      setPosts((prev) =>
        prev
          .filter((p) => p.id !== postId)
          .map((p) => ({
            ...p,
            replies: p.replies.filter((r) => r.id !== postId),
          })),
      );
      setTotal((prev) => Math.max(0, prev - 1));
      toast.push("删除成功", "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  const loadMore = () => {
    loadPosts(page + 1, true);
  };

  return (
    <div className="card">
      <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
        <MessageSquare className="h-5 w-5 text-brand-500" />
        {title ?? "讨论区"}
        {total > 0 && (
          <span className="text-sm font-normal text-slate-400">（{total}）</span>
        )}
      </h2>

      {/* 发帖框 */}
      {user ? (
        <div className="mb-4 space-y-2">
          <textarea
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            maxLength={MAX_CONTENT}
            rows={3}
            placeholder="分享你的经验或提出问题…"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">
              {newContent.length} / {MAX_CONTENT}
            </span>
            <Button
              size="sm"
              onClick={handleCreate}
              disabled={!newContent.trim() || submitting}
            >
              <Send className="h-3 w-3" /> 发布
            </Button>
          </div>
        </div>
      ) : (
        <div className="mb-4 rounded-lg bg-slate-50 px-4 py-3 text-center text-sm text-slate-400">
          <a href="/login" className="text-brand-600 hover:underline">
            登录
          </a>
          后参与讨论
        </div>
      )}

      {/* 帖子列表 */}
      {loading ? (
        <p className="text-sm text-slate-400">加载讨论中…</p>
      ) : posts.length === 0 ? (
        <div className="py-8 text-center">
          <MessageSquare className="h-10 w-10 mx-auto text-slate-300" />
          <p className="mt-2 text-sm text-slate-400">
            还没有人讨论，来说点什么吧
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              currentUserId={user?.id ?? null}
              onReply={handleReply}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
          {/* 加载更多 */}
          {posts.length < total && (
            <div className="text-center">
              <Button variant="secondary" size="sm" onClick={loadMore}>
                加载更多
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
