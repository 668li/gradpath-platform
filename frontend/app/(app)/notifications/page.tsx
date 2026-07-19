"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Bell, Check, ArrowLeft } from "lucide-react";
import { notificationsApi } from "@/lib/api";
import type { NotificationResponse } from "@/lib/api";
import { LoadingState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";

export default function NotificationsPage() {
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const [items, setItems] = useState<NotificationResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await notificationsApi.list({ page: 1, page_size: 30 });
      setItems(data.items);
      setTotal(data.total);
    } catch {
      toast.push("加载通知失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const handleRead = async (id: string) => {
    try {
      await notificationsApi.markRead(id);
      setItems((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
      );
    } catch {
      /* noop */
    }
  };

  const handleReadAll = async () => {
    try {
      await notificationsApi.markAllRead();
      setItems((prev) => prev.map((n) => ({ ...n, read: true })));
      toast.push("已全部标记为已读", "success");
    } catch {
      toast.push("操作失败", "error");
    }
  };

  if (!user) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 text-center">
        <Bell className="mx-auto h-12 w-12 text-ink-300 mb-4" />
        <p className="text-ink-500 mb-4">请先登录查看通知</p>
        <Link href="/login">
          <Button>去登录</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 md:px-6 md:py-8">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="h-5 w-5 text-brand-600" />
          <h1 className="text-xl font-bold text-ink-900">通知</h1>
          <span className="rounded-full bg-ink-100 px-2 py-0.5 text-xs text-ink-500">
            {total}
          </span>
        </div>
        <Button variant="ghost" size="sm" onClick={handleReadAll}>
          <Check className="h-4 w-4 mr-1" />
          全部已读
        </Button>
      </div>

      {loading ? (
        <LoadingState text="加载通知..." />
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-paper-200 bg-white p-8 text-center text-ink-400">
          暂无通知
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((n) => (
            <div
              key={n.id}
              className={`flex items-start gap-3 rounded-xl border p-4 transition-colors ${
                n.read
                  ? "border-paper-200 bg-white"
                  : "border-brand-200 bg-brand-50/40"
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-ink-900">{n.title}</p>
                  {!n.read && (
                    <span className="h-2 w-2 rounded-full bg-brand-500" />
                  )}
                </div>
                <p className="mt-0.5 text-sm text-ink-600">{n.content}</p>
                <p className="mt-1 text-xs text-ink-400">
                  {new Date(n.created_at).toLocaleString("zh-CN")}
                </p>
              </div>
              {n.link && (
                <Link
                  href={n.link}
                  onClick={() => !n.read && handleRead(n.id)}
                  className="shrink-0 text-xs font-medium text-brand-600 hover:text-brand-700"
                >
                  查看
                </Link>
              )}
              {!n.read && !n.link && (
                <button
                  onClick={() => handleRead(n.id)}
                  className="shrink-0 text-xs text-ink-400 hover:text-brand-600"
                >
                  标记已读
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
