"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Quote, Sparkles } from "lucide-react";
import { eventsApi } from "@/lib/api";
import { formatDate, levelStars, cn } from "@/lib/utils";
import {
  EVENT_TYPES,
  EVENT_TYPE_COLOR,
  EVENT_TYPE_LABEL,
} from "@/lib/constants";
import { Modal } from "@/components/ui/modal";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
import { Pagination } from "@/components/ui/pagination";
import { useToast } from "@/components/ui/toast";
import { EventForm } from "@/components/event-form";
import type { EventResponse, EventType } from "@/types";

type Filter = "all" | EventType;

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "全部" },
  ...EVENT_TYPES.map((t) => ({ key: t as Filter, label: EVENT_TYPE_LABEL[t] })),
];

export default function TimelinePage() {
  const toast = useToast();
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<EventResponse | null>(null);

  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await eventsApi.list({
        event_type: filter === "all" ? undefined : filter,
        page,
        page_size: PAGE_SIZE,
      });
      setEvents(list.items);
      setTotal(list.total);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [filter, page, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (e: EventResponse) => {
    setEditing(e);
    setModalOpen(true);
  };

  const handleSaved = () => {
    setModalOpen(false);
    setEditing(null);
    load();
  };

  const handleDelete = async (e: EventResponse) => {
    if (!window.confirm(`确认删除事件「${e.title}」？`)) return;
    try {
      await eventsApi.remove(e.id);
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
          <h1 className="page-title">成长时间线</h1>
          <p className="text-sm text-slate-500 mt-1">
            按时间记录你的职业成长事件
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" /> 新建事件
        </Button>
      </div>

      {/* 类型筛选 Tab */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => {
              setFilter(f.key);
              setPage(1);
            }}
            className={cn(
              "rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors",
              filter === f.key
                ? "bg-brand-600 text-white"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingState />
      ) : events.length === 0 ? (
        <EmptyState
          title="还没有事件"
          description="记录入职、晋升、项目完成等职业成长事件，附上 STAR+R 反思"
          action={
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" /> 创建事件
            </Button>
          }
        />
      ) : (
        <ol className="relative space-y-4 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
          {events.map((e) => {
            const color = EVENT_TYPE_COLOR[e.event_type];
            return (
              <li key={e.id} className="relative pl-10">
                <span
                  className="absolute left-1 top-4 flex h-[18px] w-[18px] items-center justify-center rounded-full ring-4 ring-slate-50"
                  style={{ backgroundColor: color }}
                />
                <div className="card hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold text-slate-800">{e.title}</h3>
                        <Badge color="blue">{EVENT_TYPE_LABEL[e.event_type]}</Badge>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {formatDate(e.event_date)}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => openEdit(e)}
                        className="p-1.5 rounded-md text-slate-400 hover:bg-slate-100 hover:text-brand-600"
                        aria-label="编辑"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(e)}
                        className="p-1.5 rounded-md text-slate-400 hover:bg-red-50 hover:text-red-600"
                        aria-label="删除"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {e.description && (
                    <p className="mt-2 text-sm text-slate-600">{e.description}</p>
                  )}

                  {e.reflection && (
                    <div className="mt-3 flex gap-2 rounded-lg bg-amber-50 px-3 py-2">
                      <Quote className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                      <p className="text-sm text-amber-800">
                        <span className="text-amber-500 text-xs font-medium">
                          反思 ·{" "}
                        </span>
                        {e.reflection}
                      </p>
                    </div>
                  )}

                  {e.skills_gained.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {e.skills_gained.map((s, i) => (
                        <span
                          key={i}
                          className="inline-flex items-center rounded-md bg-purple-50 px-2 py-0.5 text-xs text-purple-700"
                        >
                          <Sparkles className="h-3 w-3 mr-0.5" />
                          {s}
                        </span>
                      ))}
                    </div>
                  )}

                  {e.impact_metrics &&
                    Object.keys(e.impact_metrics).length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                        {Object.entries(e.impact_metrics).map(([k, v]) => (
                          <span key={k} className="rounded bg-slate-100 px-2 py-1">
                            <span className="text-slate-400">{k}: </span>
                            <span className="font-medium text-slate-700">
                              {String(v)}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}

                  {e.mood && (
                    <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
                      <span>心情</span>
                      <span className="text-amber-500 tracking-wide">
                        {levelStars(e.mood)}
                      </span>
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
      {!loading && (
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onPageChange={setPage}
        />
      )}

      <Modal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditing(null);
        }}
        title={editing ? "编辑事件" : "新建事件"}
        className="max-w-2xl"
      >
        <EventForm
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
