"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Inbox,
  CheckCircle2,
  XCircle,
  Copy,
  Clock,
  ExternalLink,
  Filter,
  RefreshCw,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { Button, Badge, Select, Textarea } from "@/components/ui/form-controls";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import { researchQueueApi, type ResearchQueueItem } from "@/lib/api/research-queue";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 15;

type ReviewStatus = "PENDING" | "APPROVED" | "REJECTED" | "DUPLICATED";

// credibility 三级色标（P2 会抽成 SourceBadge 组件复用，这里先内联）
const CREDIBILITY_META: Record<string, { label: string; color: "green" | "blue" | "amber" }> = {
  official_verified: { label: "官方来源", color: "green" },
  user_reported: { label: "社区报告", color: "blue" },
  model_inferred: { label: "AI 推断", color: "amber" },
};

function CredibilityBadge({ value }: { value: string }) {
  const meta = CREDIBILITY_META[value] ?? { label: value, color: "amber" as const };
  return <Badge color={meta.color}>{meta.label}</Badge>;
}

const STATUS_META: Record<ReviewStatus, { label: string; color: "amber" | "green" | "red" | "purple" }> = {
  PENDING: { label: "待审核", color: "amber" },
  APPROVED: { label: "已通过", color: "green" },
  REJECTED: { label: "已驳回", color: "red" },
  DUPLICATED: { label: "已重复", color: "purple" },
};

export default function ResearchQueuePage() {
  const toast = useToast();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const hydrated = useAuthStore((s) => s.hydrated);

  const [items, setItems] = useState<ResearchQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>("PENDING");
  const [sourcePlatform, setSourcePlatform] = useState("");
  const [actingId, setActingId] = useState<number | null>(null);

  // 驳回 / 标记重复的 Modal 状态
  const [rejectTarget, setRejectTarget] = useState<ResearchQueueItem | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [duplicateTarget, setDuplicateTarget] = useState<ResearchQueueItem | null>(null);
  const [duplicateOf, setDuplicateOf] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    try {
      const res = await researchQueueApi.list({
        page,
        page_size: PAGE_SIZE,
        review_status: reviewStatus,
        source_platform: sourcePlatform || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载审核队列失败", "error");
    } finally {
      setLoading(false);
    }
  }, [page, reviewStatus, sourcePlatform, toast]);

  useEffect(() => {
    setPage(1);
  }, [reviewStatus, sourcePlatform]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  // 非管理员重定向
  useEffect(() => {
    if (hydrated && user && !user.is_admin) {
      router.replace("/dashboard");
    }
  }, [hydrated, user, router]);

  // 操作成功后从当前列表移除该条（审核状态机只允许 PENDING→终态）
  const removeItem = (queueId: number) => {
    setItems((prev) => prev.filter((i) => i.queue_id !== queueId));
    setTotal((t) => Math.max(0, t - 1));
  };

  const handleApprove = async (item: ResearchQueueItem) => {
    setActingId(item.queue_id);
    try {
      const res = await researchQueueApi.approve(item.queue_id);
      removeItem(item.queue_id);
      toast.push(
        res.promoted > 0 ? "已通过审核并入库" : "已通过审核（未落业务表）",
        "success",
      );
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "审核通过失败", "error");
    } finally {
      setActingId(null);
    }
  };

  const handleReject = async () => {
    if (!rejectTarget) return;
    setActingId(rejectTarget.queue_id);
    try {
      await researchQueueApi.reject(rejectTarget.queue_id, {
        reject_reason: rejectReason.trim() || undefined,
      });
      removeItem(rejectTarget.queue_id);
      toast.push("已驳回该条", "success");
      setRejectTarget(null);
      setRejectReason("");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "驳回失败", "error");
    } finally {
      setActingId(null);
    }
  };

  const handleDuplicate = async () => {
    if (!duplicateTarget) return;
    setActingId(duplicateTarget.queue_id);
    try {
      await researchQueueApi.duplicate(duplicateTarget.queue_id, {
        duplicate_of: duplicateOf.trim() || undefined,
      });
      removeItem(duplicateTarget.queue_id);
      toast.push("已标记为重复", "success");
      setDuplicateTarget(null);
      setDuplicateOf("");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "标记重复失败", "error");
    } finally {
      setActingId(null);
    }
  };

  const copyUrl = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      toast.push("已复制来源链接", "success");
    } catch {
      toast.push("复制失败，请手动选择复制", "error");
    }
  };

  // ===== 权限校验 =====
  if (!hydrated || !user) {
    return <LoadingState text="加载中…" />;
  }
  if (!user.is_admin) {
    return <LoadingState text="无权访问，正在跳转…" />;
  }

  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">调研数据审核</h1>
          <p className="text-sm text-ink-500 mt-1">
            审核外部采集条目（经验帖 / 考研资讯 / 暗知识），通过后统一入库
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={loadQueue} disabled={loading}>
          <RefreshCw className={cn("h-4 w-4 mr-1", loading && "animate-spin")} />
          刷新
        </Button>
      </div>

      {/* 筛选 */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-paper-200 bg-white p-3 shadow-sm">
        <span className="flex items-center gap-1.5 text-sm text-ink-500">
          <Filter className="h-4 w-4" />
          筛选
        </span>
        <Select
          value={reviewStatus}
          onChange={(e) => setReviewStatus(e.target.value as ReviewStatus)}
          className="w-32"
        >
          <option value="PENDING">待审核</option>
          <option value="APPROVED">已通过</option>
          <option value="REJECTED">已驳回</option>
          <option value="DUPLICATED">已重复</option>
        </Select>
        <Select value={sourcePlatform} onChange={(e) => setSourcePlatform(e.target.value)} className="w-36">
          <option value="">全部平台</option>
          <option value="bilibili">B 站</option>
          <option value="web">网页</option>
          <option value="rss">RSS</option>
        </Select>
        <span className="text-sm text-ink-400 ml-auto">共 {total} 条</span>
      </div>

      {/* 列表 */}
      {loading ? (
        <div className="rounded-xl border border-paper-200 bg-white p-8">
          <LoadingState text="加载审核队列..." />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-paper-200 bg-white p-8">
          <EmptyState
            title="队列为空"
            description={
              reviewStatus === "PENDING"
                ? "当前没有待审核的采集条目，运行爬虫后新条目会自动进入队列"
                : "该状态下没有条目"
            }
          />
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const acting = actingId === item.queue_id;
            const statusMeta = STATUS_META[item.review_status as ReviewStatus] ?? STATUS_META.PENDING;
            const expanded = expandedId === item.queue_id;
            return (
              <div key={item.queue_id} className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h3 className="font-semibold text-ink-900 truncate">{item.title || "（无标题）"}</h3>
                      <Badge color={statusMeta.color}>{statusMeta.label}</Badge>
                      <CredibilityBadge value={item.credibility} />
                      <Badge color="slate">{item.source_platform}</Badge>
                    </div>
                    <p className="text-sm text-ink-500 line-clamp-2">{item.content}</p>
                  </div>
                </div>

                {/* 元信息 */}
                <div className="flex flex-wrap items-center gap-3 text-xs text-ink-400 mt-2">
                  <span className="flex items-center gap-1">
                    <Inbox className="h-3 w-3" />
                    {item.crawler_name}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(item.created_time).toLocaleString("zh-CN")}
                  </span>
                  <span className="flex items-center gap-1 min-w-0">
                    <ExternalLink className="h-3 w-3 shrink-0" />
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="truncate text-brand-600 hover:underline max-w-[280px]"
                      title={item.source_url}
                    >
                      {item.source_url}
                    </a>
                  </span>
                </div>

                {/* 操作区 */}
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-paper-100">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setExpandedId(expanded ? null : item.queue_id)}
                  >
                    {expanded ? "收起内容" : "查看全文"}
                  </Button>
                  {item.review_status === "PENDING" && (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        className="bg-green-600 hover:bg-green-700 text-white"
                        onClick={() => handleApprove(item)}
                        disabled={acting}
                        loading={acting}
                      >
                        <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                        通过
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => setRejectTarget(item)}
                        disabled={acting}
                      >
                        <XCircle className="h-3.5 w-3.5 mr-1" />
                        驳回
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setDuplicateTarget(item)}
                        disabled={acting}
                      >
                        <Copy className="h-3.5 w-3.5 mr-1" />
                        重复
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => copyUrl(item.source_url)}>
                        复制链接
                      </Button>
                    </div>
                  )}
                </div>

                {/* 展开的内容预览 */}
                {expanded && (
                  <div className="mt-3 rounded-lg bg-paper-50 border border-paper-200 p-4">
                    <p className="text-sm text-ink-700 whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto">
                      {item.content}
                    </p>
                  </div>
                )}
              </div>
            );
          })}

          {/* 分页 */}
          {totalPages > 1 && (
            <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
          )}
        </div>
      )}

      {/* 驳回 Modal */}
      <Modal open={!!rejectTarget} onClose={() => setRejectTarget(null)} title="驳回该条目">
        <div className="space-y-4">
          <p className="text-sm text-ink-500">
            {rejectTarget?.title || "（无标题）"} — 驳回后该条进入已驳回状态，不会入库。
          </p>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-ink-700">驳回原因</label>
            <Textarea
              rows={3}
              placeholder="例如：信息不实 / 无来源佐证 / 违规内容（可选，建议填写）"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              maxLength={500}
            />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="secondary" onClick={() => setRejectTarget(null)}>取消</Button>
            <Button
              variant="danger"
              onClick={handleReject}
              disabled={actingId === rejectTarget?.queue_id}
              loading={actingId === rejectTarget?.queue_id}
            >
              确认驳回
            </Button>
          </div>
        </div>
      </Modal>

      {/* 标记重复 Modal */}
      <Modal open={!!duplicateTarget} onClose={() => setDuplicateTarget(null)} title="标记为重复">
        <div className="space-y-4">
          <p className="text-sm text-ink-500">
            {duplicateTarget?.title || "（无标题）"} — 该条将被标记为重复，不会入库。
          </p>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-ink-700">重复来源 URL 或说明</label>
            <Textarea
              rows={2}
              placeholder="例如：https://...（可选）"
              value={duplicateOf}
              onChange={(e) => setDuplicateOf(e.target.value)}
              maxLength={500}
            />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="secondary" onClick={() => setDuplicateTarget(null)}>取消</Button>
            <Button
              onClick={handleDuplicate}
              disabled={actingId === duplicateTarget?.queue_id}
              loading={actingId === duplicateTarget?.queue_id}
            >
              确认标记
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
