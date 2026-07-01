"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  Compass,
  Star,
  Clock,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  History,
} from "lucide-react";
import { decisionsApi, decisionJournalApi } from "@/lib/api";
import { formatDate, levelStars, cn } from "@/lib/utils";
import {
  DECISION_STATUS_LABEL,
  DESTINATION_DETAIL_FIELDS,
  DESTINATION_TYPE_LABEL,
} from "@/lib/constants";
import { Modal } from "@/components/ui/modal";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Badge, Button, Field, Textarea } from "@/components/ui/form-controls";
import { ListSkeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/ui/pagination";
import { useToast } from "@/components/ui/toast";
import { DestinationPie } from "@/components/charts";
import { DecisionForm } from "@/components/decision-form";
import { AIAdvicePanel } from "@/components/ai-advice";
import type {
  DecisionResponse,
  DecisionStats,
  DestinationType,
} from "@/types";

function detailSummary(decision: DecisionResponse): string {
  const fields = DESTINATION_DETAIL_FIELDS[decision.destination_type];
  const parts: string[] = [];
  for (const f of fields) {
    const v = decision.details?.[f.key];
    if (v) {
      parts.push(`${f.label}: ${v}`);
    }
  }
  return parts.join(" · ");
}

const STATUS_BADGE: Record<string, "slate" | "blue" | "green" | "amber"> = {
  planned: "slate",
  confirmed: "blue",
  executed: "green",
  changed: "amber",
};

/** 计算回溯日期距今天数；正数表示已逾期 */
function daysOverdue(reviewDate: string | null | undefined): number | null {
  if (!reviewDate) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const rd = new Date(reviewDate);
  if (Number.isNaN(rd.getTime())) return null;
  rd.setHours(0, 0, 0, 0);
  return Math.floor((today.getTime() - rd.getTime()) / 86400000);
}

/** 根据 AI 分析文本粗略判断预测与实际是否一致 */
function assessMatch(
  aiAnalysis: string | null | undefined,
): "match" | "mismatch" | "unknown" {
  if (!aiAnalysis) return "unknown";
  const positive = ["一致", "符合", "吻合", "匹配", "准确", "相符", "如预期", "契合"];
  const negative = ["差异", "不一致", "偏离", "不符", "落差", "偏差", "未达", "未实现", "截然不同"];
  const hasPos = positive.some((k) => aiAnalysis.includes(k));
  const hasNeg = negative.some((k) => aiAnalysis.includes(k));
  if (hasNeg) return "mismatch";
  if (hasPos) return "match";
  return "unknown";
}

// ===== 内联回溯评估弹窗 =====
function ReviewModal({
  open,
  decision,
  onClose,
  onCompleted,
}: {
  open: boolean;
  decision: DecisionResponse | null;
  onClose: () => void;
  onCompleted: () => void;
}) {
  const toast = useToast();
  const [actualOutcome, setActualOutcome] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DecisionResponse | null>(null);

  useEffect(() => {
    if (open) {
      setActualOutcome("");
      setReviewNotes("");
      setResult(null);
    }
  }, [open, decision?.id]);

  if (!open || !decision) return null;

  const submit = async () => {
    if (!actualOutcome.trim()) {
      toast.push("请填写实际结果", "error");
      return;
    }
    setLoading(true);
    try {
      const updated = await decisionJournalApi.completeReview(decision.id, {
        actual_outcome: actualOutcome.trim(),
        review_notes: reviewNotes.trim() || undefined,
      });
      setResult(updated);
      toast.push("回溯提交成功", "success");
      onCompleted();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "提交失败", "error");
    } finally {
      setLoading(false);
    }
  };

  const match = assessMatch(result?.ai_analysis);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={result ? "回溯分析结果" : "回溯评估"}
      className="max-w-2xl"
    >
      <div className="space-y-4">
        {/* 原始决策信息 */}
        <div className="space-y-2 rounded-lg border border-paper-300 bg-paper-50/50 p-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <Compass className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-ink-800">
                {DESTINATION_TYPE_LABEL[decision.destination_type]}
              </p>
              <p className="text-xs text-ink-400">
                {formatDate(decision.decision_date)}
              </p>
            </div>
          </div>
          {decision.reasoning && (
            <p className="text-sm text-ink-500">
              <span className="text-ink-400">理由：</span>
              {decision.reasoning}
            </p>
          )}
          {decision.prediction && (
            <p className="text-sm text-ink-500">
              <span className="text-ink-400">预测：</span>
              {decision.prediction}
            </p>
          )}
          {decision.assumptions && decision.assumptions.length > 0 && (
            <div className="text-sm text-ink-500">
              <span className="text-ink-400">关键假设：</span>
              <ul className="mt-1 space-y-0.5">
                {decision.assumptions.map((a, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-brand-500">·</span>
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {!result ? (
          <>
            <Field label="实际结果" required hint="实际结果是什么？">
              <Textarea
                value={actualOutcome}
                onChange={(e) => setActualOutcome(e.target.value)}
                placeholder="实际结果是什么？"
                className="min-h-[100px]"
              />
            </Field>
            <Field label="回溯笔记" hint="回溯笔记/学到了什么？（可选）">
              <Textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="回溯笔记/学到了什么？"
                className="min-h-[80px]"
              />
            </Field>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="secondary"
                onClick={onClose}
                disabled={loading}
              >
                取消
              </Button>
              <Button type="button" onClick={submit} loading={loading}>
                提交回溯
              </Button>
            </div>
          </>
        ) : (
          <>
            {/* 预测 vs 实际 对比 */}
            <div className="grid grid-cols-1 items-stretch gap-2 sm:grid-cols-[1fr_auto_1fr]">
              <div className="rounded-lg border border-brand-200 bg-brand-50/60 p-3">
                <p className="mb-1 text-xs font-medium text-brand-700">预测</p>
                <p className="whitespace-pre-wrap text-sm text-ink-700">
                  {decision.prediction || "（未填写预测）"}
                </p>
              </div>
              <div className="flex items-center justify-center">
                <span className="rounded-full bg-ink-100 px-2.5 py-1 text-xs font-semibold text-ink-500">
                  VS
                </span>
              </div>
              <div className="rounded-lg border border-ink-200 bg-white p-3">
                <p className="mb-1 text-xs font-medium text-ink-500">实际</p>
                <p className="whitespace-pre-wrap text-sm text-ink-700">
                  {result.actual_outcome || actualOutcome}
                </p>
              </div>
            </div>

            {/* 匹配指示 */}
            <div
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-2 text-sm",
                match === "match" && "bg-brand-50 text-brand-700",
                match === "mismatch" && "bg-amber-50 text-amber-700",
                match === "unknown" && "bg-ink-100 text-ink-500",
              )}
            >
              {match === "match" ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <AlertCircle className="h-4 w-4" />
              )}
              <span>
                {match === "match" && "预测与实际较为一致"}
                {match === "mismatch" && "预测与实际存在差异"}
                {match === "unknown" && "已完成回溯"}
              </span>
            </div>

            {/* AI 分析 */}
            {result.ai_analysis && (
              <div className="rounded-lg border border-brand-200 bg-gradient-to-br from-brand-50/70 to-paper-50 p-4">
                <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-brand-700">
                  <Sparkles className="h-4 w-4" />
                  AI 回溯分析
                </p>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-700">
                  {result.ai_analysis}
                </p>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button type="button" onClick={onClose}>
                完成
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}

export default function DecisionsPage() {
  const toast = useToast();
  const [decisions, setDecisions] = useState<DecisionResponse[]>([]);
  const [stats, setStats] = useState<DecisionStats>({});
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<DecisionResponse | null>(null);

  // 决策日志与回溯
  const [pendingReviews, setPendingReviews] = useState<DecisionResponse[]>([]);
  const [pendingLoading, setPendingLoading] = useState(true);
  const [reviewed, setReviewed] = useState<DecisionResponse[]>([]);
  const [reviewedLoading, setReviewedLoading] = useState(true);
  const [reviewTarget, setReviewTarget] = useState<DecisionResponse | null>(
    null,
  );
  const [reviewOpen, setReviewOpen] = useState(false);

  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, s] = await Promise.all([
        decisionsApi.list({ page, page_size: PAGE_SIZE }),
        decisionsApi.stats(),
      ]);
      setDecisions(list.items);
      setTotal(list.total);
      setStats(s);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast, page]);

  const loadJournal = useCallback(async () => {
    setPendingLoading(true);
    setReviewedLoading(true);
    try {
      const [pending, rev] = await Promise.all([
        decisionJournalApi.getPendingReviews(),
        decisionJournalApi.getReviewed(),
      ]);
      setPendingReviews(pending);
      setReviewed(rev);
    } catch (err) {
      toast.push(
        err instanceof Error ? err.message : "加载回溯数据失败",
        "error",
      );
    } finally {
      setPendingLoading(false);
      setReviewedLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
    loadJournal();
  }, [load, loadJournal]);

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (d: DecisionResponse) => {
    setEditing(d);
    setModalOpen(true);
  };

  const handleSaved = () => {
    setModalOpen(false);
    setEditing(null);
    load();
    loadJournal();
  };

  const handleDelete = async (d: DecisionResponse) => {
    if (!window.confirm(`确认删除「${DESTINATION_TYPE_LABEL[d.destination_type]}」决策记录？`)) {
      return;
    }
    try {
      await decisionsApi.remove(d.id);
      toast.push("删除成功", "success");
      load();
      loadJournal();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  const openReview = (d: DecisionResponse) => {
    setReviewTarget(d);
    setReviewOpen(true);
  };

  const closeReview = () => {
    setReviewOpen(false);
    setReviewTarget(null);
  };

  const handleReviewCompleted = () => {
    loadJournal();
    load();
  };

  const pieData = Object.entries(stats).map(([key, value]) => ({
    name: DESTINATION_TYPE_LABEL[key as DestinationType] ?? key,
    value,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">去向决策</h1>
          <p className="text-sm text-slate-500 mt-1">
            记录毕业去向的决策过程与理由
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" /> 新建决策
        </Button>
      </div>

      <AIAdvicePanel />

      {/* 待回溯决策 */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-brand-600" />
          <h2 className="font-semibold text-ink-800">待回溯决策</h2>
          {pendingReviews.length > 0 && (
            <Badge color="amber">{pendingReviews.length}</Badge>
          )}
        </div>
        {pendingLoading ? (
          <LoadingState />
        ) : pendingReviews.length === 0 ? (
          <EmptyState
            title="暂无待回溯决策"
            description="为决策填写预测与回溯日期后，到期的决策会出现在这里提醒你复盘"
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {pendingReviews.map((d) => {
              const overdue = daysOverdue(d.review_date);
              return (
                <div key={d.id} className="card flex flex-col gap-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                        <Compass className="h-4 w-4" />
                      </span>
                      <div className="min-w-0">
                        <h3 className="text-sm font-semibold text-ink-800">
                          {DESTINATION_TYPE_LABEL[d.destination_type]}
                        </h3>
                        <p className="mt-0.5 text-xs text-ink-400">
                          决策于 {formatDate(d.decision_date)}
                        </p>
                      </div>
                    </div>
                    {overdue !== null && overdue > 0 ? (
                      <Badge color="amber">逾期 {overdue} 天</Badge>
                    ) : (
                      <Badge color="slate">待回溯</Badge>
                    )}
                  </div>
                  {d.prediction && (
                    <p className="line-clamp-2 text-sm text-ink-500">
                      <span className="text-ink-400">预测：</span>
                      {d.prediction}
                    </p>
                  )}
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs text-ink-400">
                      计划回溯：{formatDate(d.review_date)}
                    </p>
                    <Button size="sm" onClick={() => openReview(d)}>
                      回溯评估
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 决策列表 */}
        <div className="lg:col-span-2 space-y-4">
          {loading ? (
            <ListSkeleton />
          ) : decisions.length === 0 ? (
            <EmptyState
              title="还没有决策记录"
              description="记录你的第一个毕业去向决策，沉淀决策思考"
              action={
                <Button onClick={openCreate}>
                  <Plus className="h-4 w-4" /> 创建决策
                </Button>
              }
            />
          ) : (
            decisions.map((d) => (
              <div key={d.id} className="card hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600 shrink-0">
                      <Compass className="h-5 w-5" />
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold text-slate-800">
                          {DESTINATION_TYPE_LABEL[d.destination_type]}
                        </h3>
                        <Badge color={STATUS_BADGE[d.status]}>
                          {DECISION_STATUS_LABEL[d.status]}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {formatDate(d.decision_date)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => openEdit(d)}
                      className="p-1.5 rounded-md text-slate-400 hover:bg-slate-100 hover:text-brand-600"
                      aria-label="编辑"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(d)}
                      className="p-1.5 rounded-md text-slate-400 hover:bg-red-50 hover:text-red-600"
                      aria-label="删除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {detailSummary(d) && (
                  <p className="mt-3 text-sm text-slate-600 bg-slate-50 rounded-lg px-3 py-2">
                    {detailSummary(d)}
                  </p>
                )}

                {d.reasoning && (
                  <p className="mt-2 text-sm text-slate-500 line-clamp-3">
                    <span className="text-slate-400">理由：</span>
                    {d.reasoning}
                  </p>
                )}

                <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">
                  <Star className="h-4 w-4 text-amber-400" />
                  <span>信心度</span>
                  <span className="text-amber-500 tracking-wide">
                    {levelStars(d.confidence)}
                  </span>
                  <span className="text-xs text-slate-400">{d.confidence}/5</span>
                </div>
              </div>
            ))
          )}
          {!loading && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={total}
              onPageChange={setPage}
            />
          )}
        </div>

        {/* 分布饼图 */}
        <div className="card h-fit lg:sticky lg:top-6">
          <h2 className="font-semibold text-slate-800 mb-2">去向类型分布</h2>
          {pieData.length === 0 ? (
            <EmptyState title="暂无数据" description="创建决策后将显示分布" />
          ) : (
            <DestinationPie data={pieData} />
          )}
        </div>
      </div>

      {/* 已回溯决策 */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-brand-600" />
          <h2 className="font-semibold text-ink-800">已回溯决策</h2>
          {reviewed.length > 0 && <Badge color="green">{reviewed.length}</Badge>}
        </div>
        {reviewedLoading ? (
          <LoadingState />
        ) : reviewed.length === 0 ? (
          <EmptyState
            title="暂无已回溯决策"
            description="完成回溯评估的决策将在这里沉淀为经验，对比预测与实际"
          />
        ) : (
          <div className="space-y-4">
            {reviewed.map((d) => {
              const match = assessMatch(d.ai_analysis);
              return (
                <div key={d.id} className="card space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                        <Compass className="h-4 w-4" />
                      </span>
                      <div className="min-w-0">
                        <h3 className="text-sm font-semibold text-ink-800">
                          {DESTINATION_TYPE_LABEL[d.destination_type]}
                        </h3>
                        <p className="mt-0.5 text-xs text-ink-400">
                          决策于 {formatDate(d.decision_date)}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {match === "match" && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700">
                          <CheckCircle2 className="h-3.5 w-3.5" /> 预测一致
                        </span>
                      )}
                      {match === "mismatch" && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                          <AlertCircle className="h-3.5 w-3.5" /> 预测有差异
                        </span>
                      )}
                      {match === "unknown" && <Badge color="slate">已回溯</Badge>}
                    </div>
                  </div>

                  {/* 预测 vs 实际 */}
                  <div className="grid grid-cols-1 items-stretch gap-2 sm:grid-cols-[1fr_auto_1fr]">
                    <div className="rounded-lg border border-brand-200 bg-brand-50/50 p-3">
                      <p className="mb-1 text-xs font-medium text-brand-700">预测</p>
                      <p className="whitespace-pre-wrap text-sm text-ink-700">
                        {d.prediction || "（未填写预测）"}
                      </p>
                    </div>
                    <div className="flex items-center justify-center">
                      <span className="rounded-full bg-ink-100 px-2.5 py-1 text-xs font-semibold text-ink-500">
                        VS
                      </span>
                    </div>
                    <div className="rounded-lg border border-ink-200 bg-white p-3">
                      <p className="mb-1 text-xs font-medium text-ink-500">实际</p>
                      <p className="whitespace-pre-wrap text-sm text-ink-700">
                        {d.actual_outcome || "—"}
                      </p>
                    </div>
                  </div>

                  {/* AI 分析 */}
                  {d.ai_analysis && (
                    <div className="rounded-lg border border-brand-200 bg-gradient-to-br from-brand-50/70 to-paper-50 p-3">
                      <p className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-brand-700">
                        <Sparkles className="h-4 w-4" />
                        AI 回溯分析
                      </p>
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-700">
                        {d.ai_analysis}
                      </p>
                    </div>
                  )}

                  {d.review_notes && (
                    <p className="text-sm text-ink-500">
                      <span className="text-ink-400">回溯笔记：</span>
                      {d.review_notes}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <Modal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditing(null);
        }}
        title={editing ? "编辑决策" : "新建决策"}
        className="max-w-2xl"
      >
        <DecisionForm
          initial={editing}
          onSaved={handleSaved}
          onCancel={() => {
            setModalOpen(false);
            setEditing(null);
          }}
        />
      </Modal>

      <ReviewModal
        open={reviewOpen}
        decision={reviewTarget}
        onClose={closeReview}
        onCompleted={handleReviewCompleted}
      />
    </div>
  );
}
