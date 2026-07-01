"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  ClipboardList,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";
import { retrospectivesApi } from "@/lib/api";
import { formatDate, levelStars } from "@/lib/utils";
import { PERIOD_TYPE_LABEL } from "@/lib/constants";
import { Modal } from "@/components/ui/modal";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { RetroForm } from "@/components/retro-form";
import { RetroAIPanel } from "@/components/retro-ai-panel";
import type { AIRetroDraft, RetrospectiveResponse } from "@/types";

export default function RetrospectivesPage() {
  const toast = useToast();
  const [retros, setRetros] = useState<RetrospectiveResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<RetrospectiveResponse | null>(null);
  const [aiDraftData, setAiDraftData] = useState<{
    draft: AIRetroDraft;
    periodStart: string;
    periodEnd: string;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await retrospectivesApi.list();
      setRetros(list);
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
    setAiDraftData(null);
    setModalOpen(true);
  };

  const openEdit = (r: RetrospectiveResponse) => {
    setEditing(r);
    setAiDraftData(null);
    setModalOpen(true);
  };

  const handleSaved = () => {
    setModalOpen(false);
    setEditing(null);
    setAiDraftData(null);
    load();
  };

  const handleUseDraft = (
    draft: AIRetroDraft,
    period: { start: string; end: string },
  ) => {
    setAiDraftData({
      draft,
      periodStart: period.start,
      periodEnd: period.end,
    });
    setEditing(null);
    setModalOpen(true);
  };

  const handleDelete = async (r: RetrospectiveResponse) => {
    if (!window.confirm(`确认删除复盘「${r.title}」？`)) return;
    try {
      await retrospectivesApi.remove(r.id);
      toast.push("删除成功", "success");
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">阶段复盘</h1>
          <p className="text-sm text-slate-500 mt-1">
            定期回顾，沉淀经验，规划下一步
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" /> 新建复盘
        </Button>
      </div>

      <RetroAIPanel onUseDraft={handleUseDraft} />

      {loading ? (
        <LoadingState />
      ) : retros.length === 0 ? (
        <EmptyState
          title="还没有复盘记录"
          description="创建你的第一次阶段性复盘，可基于事件自动生成草稿"
          action={
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" /> 创建复盘
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {retros.map((r) => (
            <div key={r.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50 text-purple-600 shrink-0">
                    <ClipboardList className="h-5 w-5" />
                  </span>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-slate-800 truncate">
                      {r.title}
                    </h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge color="purple">
                        {PERIOD_TYPE_LABEL[r.period_type]}
                      </Badge>
                      <span className="text-xs text-slate-400">
                        {formatDate(r.period_start)} ~ {formatDate(r.period_end)}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => openEdit(r)}
                    className="p-1.5 rounded-md text-slate-400 hover:bg-slate-100 hover:text-brand-600"
                    aria-label="编辑"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(r)}
                    className="p-1.5 rounded-md text-slate-400 hover:bg-red-50 hover:text-red-600"
                    aria-label="删除"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="mt-3 space-y-3 text-sm">
                {r.achievements.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1">
                      成就 ({r.achievements.length})
                    </p>
                    <ul className="space-y-1">
                      {r.achievements.slice(0, 3).map((a, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-1.5 text-slate-600"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0 mt-0.5" />
                          <span className="line-clamp-1">{a}</span>
                        </li>
                      ))}
                      {r.achievements.length > 3 && (
                        <li className="text-xs text-slate-400 pl-5">
                          …还有 {r.achievements.length - 3} 项
                        </li>
                      )}
                    </ul>
                  </div>
                )}

                {r.challenges && (
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1">挑战</p>
                    <p className="text-slate-600 line-clamp-2">{r.challenges}</p>
                  </div>
                )}

                {r.lessons_learned && (
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1">
                      教训提炼
                    </p>
                    <p className="text-slate-600 line-clamp-2">
                      {r.lessons_learned}
                    </p>
                  </div>
                )}

                {r.next_steps.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1">
                      下一步 ({r.next_steps.length})
                    </p>
                    <ul className="space-y-1">
                      {r.next_steps.slice(0, 2).map((s, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-1.5 text-slate-600"
                        >
                          <ArrowRight className="h-3.5 w-3.5 text-brand-500 shrink-0 mt-0.5" />
                          <span className="line-clamp-1">{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-2 text-sm text-slate-500">
                <span>满意度</span>
                <span className="text-amber-500 tracking-wide">
                  {levelStars(r.satisfaction)}
                </span>
                <span className="text-xs text-slate-400">{r.satisfaction}/5</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditing(null);
          setAiDraftData(null);
        }}
        title={editing ? "编辑复盘" : "新建复盘"}
        className="max-w-2xl"
      >
        <RetroForm
          initial={editing}
          aiDraft={aiDraftData}
          onSaved={handleSaved}
          onCancel={() => {
            setModalOpen(false);
            setEditing(null);
            setAiDraftData(null);
          }}
        />
      </Modal>
    </div>
  );
}
