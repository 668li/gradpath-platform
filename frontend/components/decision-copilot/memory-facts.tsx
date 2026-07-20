"use client";

import { memo, useState } from "react";
import { Brain, Plus, Trash2, ThumbsUp, ThumbsDown, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button, Field, Input, Select } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { userMemoryApi } from "@/lib/api";
import type { PulseMemoryFact, MemoryFactType } from "@/types";

interface Props {
  items: PulseMemoryFact[];
  loading?: boolean;
  onRefresh?: () => void;
}

const FACT_TYPE_LABEL: Record<MemoryFactType, string> = {
  preference: "偏好",
  background: "背景",
  goal: "目标",
  constraint: "约束",
  behavior: "行为",
  fact: "事实",
};

const FACT_TYPE_COLOR: Record<MemoryFactType, string> = {
  preference: "bg-purple-50 text-purple-700 border-purple-200",
  background: "bg-blue-50 text-blue-700 border-blue-200",
  goal: "bg-emerald-50 text-emerald-700 border-emerald-200",
  constraint: "bg-amber-50 text-amber-700 border-amber-200",
  behavior: "bg-rose-50 text-rose-700 border-rose-200",
  fact: "bg-paper-100 text-ink-700 border-paper-200",
};

/** AI 记忆面板 — 长期记忆护城河 */
export const MemoryFactsSection = memo(function MemoryFactsSection({ items, loading, onRefresh }: Props) {
  const toast = useToast();
  const [adding, setAdding] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    fact_type: "preference" as MemoryFactType,
    fact_key: "",
    fact_value: "",
  });

  const handleAdd = async () => {
    if (!form.fact_key.trim() || !form.fact_value.trim()) {
      toast.error("请填写完整的键和值");
      return;
    }
    setSubmitting(true);
    try {
      await userMemoryApi.add(form);
      toast.success("已添加");
      setForm({ fact_type: "preference", fact_key: "", fact_value: "" });
      setAdding(false);
      onRefresh?.();
    } catch {
      toast.error("添加失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleFeedback = async (factId: string, feedback: "positive" | "negative") => {
    try {
      await userMemoryApi.feedback(factId, { feedback });
      toast.success("已记录反馈");
      onRefresh?.();
    } catch {
      toast.error("反馈失败");
    }
  };

  const handleDelete = async (factId: string) => {
    if (!confirm("确认删除这条记忆？删除后 AI 将不再使用它")) return;
    try {
      await userMemoryApi.remove(factId);
      toast.success("已删除");
      onRefresh?.();
    } catch {
      toast.error("删除失败");
    }
  };

  if (loading) return <LoadingState text="加载 AI 记忆…" />;

  return (
    <section className="card space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-brand-600" />
          <h3 className="font-display font-semibold text-ink-800">AI 记忆</h3>
          {items.length > 0 && (
            <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-600">
              {items.length} 条
            </span>
          )}
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setAdding((v) => !v)}
          className="!px-2 !py-0.5"
        >
          {adding ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
          {adding ? "取消" : "添加"}
        </Button>
      </div>

      {adding && (
        <div className="rounded-lg border border-brand-200 bg-brand-50/30 p-3 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <Field label="类型">
              <Select
                value={form.fact_type}
                onChange={(e) =>
                  setForm({ ...form, fact_type: e.target.value as MemoryFactType })
                }
              >
                {Object.entries(FACT_TYPE_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="键">
              <Input
                value={form.fact_key}
                onChange={(e) => setForm({ ...form, fact_key: e.target.value })}
                placeholder="如：偏好城市"
                maxLength={100}
              />
            </Field>
          </div>
          <Field label="值">
            <Input
              value={form.fact_value}
              onChange={(e) => setForm({ ...form, fact_value: e.target.value })}
              placeholder="如：上海"
              maxLength={500}
            />
          </Field>
          <Button size="sm" onClick={handleAdd} loading={submitting} className="w-full">
            保存
          </Button>
        </div>
      )}

      {items.length === 0 ? (
        <EmptyState
          title="AI 还没记住你的信息"
          description="与 AI 对话或主动添加，AI 会记住你的偏好与背景，未来对话更精准"
        />
      ) : (
        <ul className="space-y-1.5">
          {items.slice(0, 8).map((fact) => (
            <li
              key={fact.id}
              className={cn(
                "rounded-lg border border-paper-200 bg-white px-3 py-2 transition-all hover:border-paper-300",
                fact.user_feedback === "negative" && "opacity-60",
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className={cn(
                        "rounded-full border px-1.5 py-0.5 text-[10px] font-medium",
                        FACT_TYPE_COLOR[fact.fact_type] ?? FACT_TYPE_COLOR.fact,
                      )}
                    >
                      {FACT_TYPE_LABEL[fact.fact_type] ?? fact.fact_type}
                    </span>
                    <span className="text-xs font-semibold text-ink-700">
                      {fact.fact_key}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-ink-600 line-clamp-2">
                    {fact.fact_value}
                  </p>
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-ink-400">
                    <span>置信度 {fact.confidence}</span>
                    <span>·</span>
                    <span>使用 {fact.use_count} 次</span>
                    {fact.source && (
                      <>
                        <span>·</span>
                        <span className="truncate">来源：{fact.source}</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-0.5 shrink-0">
                  <button
                    onClick={() => handleFeedback(fact.id, "positive")}
                    className="p-1 rounded hover:bg-emerald-50 text-ink-400 hover:text-emerald-600 transition-colors"
                    title="准确"
                  >
                    <ThumbsUp className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => handleFeedback(fact.id, "negative")}
                    className="p-1 rounded hover:bg-red-50 text-ink-400 hover:text-red-600 transition-colors"
                    title="不准确"
                  >
                    <ThumbsDown className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => handleDelete(fact.id)}
                    className="p-1 rounded hover:bg-paper-100 text-ink-400 hover:text-red-500 transition-colors"
                    title="删除"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
});
