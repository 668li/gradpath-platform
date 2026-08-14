"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import {
  Badge,
  Button,
  Field,
  Select,
  Textarea,
} from "@/components/ui/form-controls";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import {
  reportsApi,
  type ReportItem,
  type ReportTargetType,
} from "@/lib/api/admin";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 15;

const STATUS_META: Record<
  ReportItem["status"],
  { label: string; color: "amber" | "green" | "red" }
> = {
  pending: { label: "待处理", color: "amber" },
  processed: { label: "已处理", color: "green" },
  rejected: { label: "不成立", color: "red" },
};

const TARGET_LABELS: Record<ReportTargetType, string> = {
  post: "讨论帖",
  experience_post: "经验贴",
  comment: "评论",
  qa: "提问",
  qa_answer: "回答",
  user: "用户",
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(
    d.getMinutes(),
  ).padStart(2, "0")}`;
}

export default function AdminReportsPage() {
  const toast = useToast();

  const [items, setItems] = useState<ReportItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [targetFilter, setTargetFilter] = useState("");
  const [actingId, setActingId] = useState<string | null>(null);

  // 处理弹窗状态
  const [processing, setProcessing] = useState<ReportItem | null>(null);
  const [action, setAction] = useState<"processed" | "rejected">("processed");
  const [banAuthor, setBanAuthor] = useState(false);
  const [banReason, setBanReason] = useState("");
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await reportsApi.list({
        page,
        page_size: PAGE_SIZE,
        status: statusFilter || undefined,
        target_type: targetFilter || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载举报列表失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, targetFilter, toast]);

  useEffect(() => {
    setPage(1);
  }, [statusFilter, targetFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const openProcess = (item: ReportItem) => {
    setProcessing(item);
    setAction("processed");
    setBanAuthor(false);
    setBanReason("");
    setNote("");
  };

  const handleProcess = async () => {
    if (!processing) return;
    // target 为用户时处理即封禁，必须填原因
    const needBanReason =
      processing.target_type === "user" || (action === "processed" && banAuthor);
    if (needBanReason && !banReason.trim()) {
      toast.push("封禁用户/作者需填写封禁原因", "error");
      return;
    }
    setActingId(processing.id);
    try {
      await reportsApi.process(processing.id, {
        action,
        ban_author: action === "processed" ? banAuthor : false,
        ban_reason: needBanReason ? banReason.trim() : undefined,
        note: note.trim() || undefined,
      });
      toast.push("举报处理完成", "success");
      setProcessing(null);
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "处理失败", "error");
    } finally {
      setActingId(null);
    }
  };

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-xl font-semibold text-ink-800 tracking-tight">
            举报管理
          </h1>
          <p className="mt-0.5 text-sm text-ink-500">
            核实举报并处置：下架违规内容，可选联动封禁作者
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={load}>
          <RefreshCw className="h-3.5 w-3.5" />
          刷新
        </Button>
      </div>

      {/* 筛选 */}
      <div className="flex flex-wrap gap-3">
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-40"
          aria-label="按状态筛选"
        >
          <option value="">全部状态</option>
          <option value="pending">待处理</option>
          <option value="processed">已处理</option>
          <option value="rejected">不成立</option>
        </Select>
        <Select
          value={targetFilter}
          onChange={(e) => setTargetFilter(e.target.value)}
          className="w-40"
          aria-label="按对象类型筛选"
        >
          <option value="">全部对象</option>
          <option value="post">讨论帖</option>
          <option value="experience_post">经验贴</option>
          <option value="comment">评论</option>
          <option value="qa">提问</option>
          <option value="qa_answer">回答</option>
          <option value="user">用户</option>
        </Select>
      </div>

      {loading ? (
        <LoadingState text="加载中…" />
      ) : items.length === 0 ? (
        <EmptyState
          title="暂无举报"
          description={statusFilter || targetFilter ? "试试调整筛选条件" : "举报会显示在这里"}
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-paper-300 bg-white shadow-sm">
          <ul className="divide-y divide-paper-200">
            {items.map((item) => {
              const meta = STATUS_META[item.status];
              return (
                <li key={item.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge color="slate">{TARGET_LABELS[item.target_type] ?? item.target_type}</Badge>
                      <span className="text-sm font-medium text-ink-800">{item.reason}</span>
                      <Badge color={meta.color}>{meta.label}</Badge>
                    </div>
                    {item.detail && (
                      <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-ink-500">
                        {item.detail}
                      </p>
                    )}
                    <p className="mt-1.5 text-xs text-ink-400">
                      {formatTime(item.created_at)}
                      <span className="mx-1.5">·</span>
                      举报人 {item.reporter_id.slice(0, 8)}…
                      {item.processed_note && (
                        <>
                          <span className="mx-1.5">·</span>
                          备注：{item.processed_note}
                        </>
                      )}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {item.status === "pending" ? (
                      <>
                        <Button
                          size="sm"
                          variant="secondary"
                          loading={actingId === item.id}
                          onClick={() => openProcess(item)}
                        >
                          <ShieldCheck className="h-3.5 w-3.5" />
                          处理
                        </Button>
                      </>
                    ) : (
                      <span className="text-xs text-ink-400">
                        已由 {item.processed_by?.slice(0, 8) ?? "管理员"} 处理
                      </span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="border-t border-paper-200 px-5 py-3">
            <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
          </div>
        </div>
      )}

      {/* 处理弹窗 */}
      <Modal
        open={!!processing}
        onClose={() => setProcessing(null)}
        title="处理举报"
      >
        {processing && (
          <div className="space-y-4">
            <div className="rounded-xl bg-paper-100 px-4 py-3 text-sm">
              <p className="font-medium text-ink-800">
                {TARGET_LABELS[processing.target_type] ?? processing.target_type}：
                {processing.reason}
              </p>
              <p className="mt-1 text-xs text-ink-500">
                目标 ID：{processing.target_id}
                {processing.detail ? `｜详情：${processing.detail}` : ""}
              </p>
            </div>

            {processing.target_type !== "user" ? (
              <Field label="处理方式">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setAction("processed")}
                    className={cn(
                      "rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors",
                      action === "processed"
                        ? "border-brand-600 bg-brand-50 text-brand-700"
                        : "border-paper-300 text-ink-500 hover:border-ink-300",
                    )}
                  >
                    举报成立 · 下架内容
                  </button>
                  <button
                    type="button"
                    onClick={() => setAction("rejected")}
                    className={cn(
                      "rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors",
                      action === "rejected"
                        ? "border-red-600 bg-red-50 text-red-700"
                        : "border-paper-300 text-ink-500 hover:border-ink-300",
                    )}
                  >
                    举报不成立
                  </button>
                </div>
              </Field>
            ) : (
              <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
                举报对象为用户：处理将直接封禁该用户，请填写封禁原因。
              </p>
            )}

            {action === "processed" && processing.target_type !== "user" && (
              <label className="flex items-center gap-2 text-sm text-ink-700">
                <input
                  type="checkbox"
                  checked={banAuthor}
                  onChange={(e) => setBanAuthor(e.target.checked)}
                  className="h-4 w-4 rounded border-paper-300 text-brand-600 focus:ring-brand-500"
                />
                同时封禁作者
              </label>
            )}

            <Field
              label="封禁原因"
              hint={
                processing.target_type === "user" || (action === "processed" && banAuthor)
                  ? "必填，会展示给被封禁用户"
                  : "选填（仅封禁时需要）"
              }
            >
              <Textarea
                rows={2}
                value={banReason}
                onChange={(e) => setBanReason(e.target.value)}
                placeholder="如：发布违规内容、多次骚扰他人…"
                maxLength={500}
              />
            </Field>

            <Field label="处理备注">
              <Textarea
                rows={2}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="处理说明（会通知举报人）"
                maxLength={500}
              />
            </Field>

            <div className="flex justify-end gap-2 pt-1">
              <Button variant="ghost" onClick={() => setProcessing(null)}>
                取消
              </Button>
              <Button
                loading={actingId === processing.id}
                onClick={handleProcess}
                variant={action === "rejected" ? "secondary" : "danger"}
              >
                {action === "processed" ? (
                  <>
                    <ShieldCheck className="h-4 w-4" />
                    确认下架
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4" />
                    驳回举报
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
