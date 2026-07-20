"use client";

import { useState } from "react";
import { MessageSquareWarning, X, Camera, Send } from "lucide-react";
import { useToast } from "@/components/ui/toast";
import { getSessionId } from "@/lib/tracker";
// 修复: 统一使用 @/lib/api 的 getToken 读取 access_token, 避免键名不一致
import { getToken } from "@/lib/api";

const CATEGORIES = ["卡顿", "找不到入口", "操作繁琐", "提示模糊", "逻辑别扭"] as const;
type Category = (typeof CATEGORIES)[number];

export function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState<Category | null>(null);
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { push } = useToast();

  const handleSubmit = async () => {
    if (!category) {
      push("请选择反馈类型", "error");
      return;
    }
    // 修复 P3 bug: 在 handleSubmit 内部读取 token，确保用户登录后立即可用
    const token = getToken();
    if (!token) {
      push("请先登录", "error");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          category,
          content: content || null,
          page: window.location.pathname,
          session_id: getSessionId(),
        }),
      });

      if (res.ok) {
        push("反馈已提交，谢谢！", "success");
        setOpen(false);
        setCategory(null);
        setContent("");
      } else {
        const err = await res.json().catch(() => ({}));
        push(err.detail || "提交失败", "error");
      }
    } catch {
      push("网络错误，提交失败", "error");
    } finally {
      setSubmitting(false);
    }
  };

  // 仅测试模式显示（通过环境变量控制）
  const testMode =
    typeof process !== "undefined" &&
    (process.env.NEXT_PUBLIC_TEST_MODE === "1" ||
      process.env.NEXT_PUBLIC_TEST_MODE === "true");

  if (!testMode) return null;

  return (
    <>
      {/* 悬浮按钮 */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          data-track-id="feedback:fab"
          className="fixed bottom-4 right-4 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-amber-500 text-white shadow-lg transition-transform hover:scale-105 hover:bg-amber-600"
          title="反馈问题"
        >
          <MessageSquareWarning className="h-6 w-6" />
        </button>
      )}

      {/* 反馈面板 */}
      {open && (
        <div className="fixed bottom-4 right-4 z-50 w-80 rounded-xl border border-paper-300 bg-white p-4 shadow-2xl">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-ink-800">遇到问题？</h3>
            <button
              onClick={() => setOpen(false)}
              className="text-ink-400 hover:text-ink-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* 分类选择 */}
          <div className="mb-3 flex flex-wrap gap-1.5">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                data-track-id={`feedback:cat:${cat}`}
                className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                  category === cat
                    ? "bg-amber-500 text-white"
                    : "bg-paper-200 text-ink-600 hover:bg-paper-300"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* 文字输入 */}
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="描述你遇到的问题（可选）"
            rows={3}
            className="mb-3 w-full resize-none rounded-lg border border-paper-300 p-2 text-sm text-ink-700 outline-none focus:border-brand-400"
          />

          {/* 提交按钮 */}
          <button
            onClick={handleSubmit}
            disabled={submitting}
            data-track-id="feedback:submit"
            className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand-500 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-600 disabled:opacity-50"
          >
            {submitting ? (
              "提交中..."
            ) : (
              <>
                <Send className="h-3.5 w-3.5" />
                提交反馈
              </>
            )}
          </button>
        </div>
      )}
    </>
  );
}
