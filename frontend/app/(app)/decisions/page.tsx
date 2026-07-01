"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Compass, Star } from "lucide-react";
import { decisionsApi } from "@/lib/api";
import { formatDate, levelStars, cn } from "@/lib/utils";
import {
  DECISION_STATUS_LABEL,
  DESTINATION_DETAIL_FIELDS,
  DESTINATION_TYPE_LABEL,
} from "@/lib/constants";
import { Modal } from "@/components/ui/modal";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
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

export default function DecisionsPage() {
  const toast = useToast();
  const [decisions, setDecisions] = useState<DecisionResponse[]>([]);
  const [stats, setStats] = useState<DecisionStats>({});
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<DecisionResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, s] = await Promise.all([
        decisionsApi.list(),
        decisionsApi.stats(),
      ]);
      setDecisions(list);
      setStats(s);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

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
  };

  const handleDelete = async (d: DecisionResponse) => {
    if (!window.confirm(`确认删除「${DESTINATION_TYPE_LABEL[d.destination_type]}」决策记录？`)) {
      return;
    }
    try {
      await decisionsApi.remove(d.id);
      toast.push("删除成功", "success");
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 决策列表 */}
        <div className="lg:col-span-2 space-y-4">
          {loading ? (
            <LoadingState />
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
    </div>
  );
}
