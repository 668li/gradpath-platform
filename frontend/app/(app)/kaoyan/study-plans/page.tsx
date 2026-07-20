"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BookOpen,
  Plus,
  Calendar,
  CheckCircle2,
  Circle,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import { Button, Input } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { studyPlanApi } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import type { StudyPlan } from "@/types";

export default function StudyPlansPage() {
  const toast = useToast();
  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingPlan, setEditingPlan] = useState<StudyPlan | null>(null);
  const [form, setForm] = useState({
    title: "",
    start_date: "",
    end_date: "",
    subjects: "",
    progress: 0,
  });

  const loadPlans = useCallback(async () => {
    setLoading(true);
    try {
      const res = await studyPlanApi.list();
      setPlans(res);
    } catch {
      toast.push("加载学习计划失败", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadPlans();
  }, [loadPlans]);

  const resetForm = () => {
    setForm({ title: "", start_date: "", end_date: "", subjects: "", progress: 0 });
    setEditingPlan(null);
    setShowForm(false);
  };

  const handleSubmit = async () => {
    if (!form.title.trim()) {
      toast.push("请输入计划标题", "error");
      return;
    }
    const body = {
      title: form.title.trim(),
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      subjects: form.subjects ? form.subjects.split(",").map((s) => s.trim()).filter(Boolean) : null,
      progress: form.progress,
    };
    try {
      if (editingPlan) {
        await studyPlanApi.update(editingPlan.id, body);
        toast.push("计划已更新", "success");
      } else {
        await studyPlanApi.create(body);
        toast.push("计划已创建", "success");
      }
      resetForm();
      loadPlans();
    } catch {
      toast.push("操作失败", "error");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await studyPlanApi.delete(id);
      toast.push("已删除", "success");
      loadPlans();
    } catch {
      toast.push("删除失败", "error");
    }
  };

  const handleEdit = (plan: StudyPlan) => {
    setEditingPlan(plan);
    setForm({
      title: plan.title,
      start_date: plan.start_date ?? "",
      end_date: plan.end_date ?? "",
      subjects: plan.subjects?.join(", ") ?? "",
      progress: plan.progress,
    });
    setShowForm(true);
  };

  const handleProgressUpdate = async (plan: StudyPlan, progress: number) => {
    try {
      await studyPlanApi.update(plan.id, { progress, completed: progress >= 100 });
      loadPlans();
    } catch {
      toast.push("更新进度失败", "error");
    }
  };

  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-4xl px-4 py-6 md:px-6 md:py-8">
        <div className="mb-6">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-brand-sm">
              <BookOpen className="h-5 w-5" strokeWidth={2.2} />
            </div>
            <h1 className="font-display text-xl sm:text-2xl font-bold text-ink-900 tracking-tight">
              学习计划
            </h1>
          </div>
          <p className="text-sm text-ink-500 ml-[46px]">
            制定考研复习计划，跟踪每日学习进度，稳扎稳打走向上岸。
          </p>
        </div>

        <div className="mb-6 flex justify-end">
          <Button
            onClick={() => {
              resetForm();
              setShowForm(true);
            }}
          >
            <Plus className="h-4 w-4 mr-1.5" />
            新建计划
          </Button>
        </div>

        {showForm && (
          <div className="mb-6 rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-ink-700">
                {editingPlan ? "编辑计划" : "新建学习计划"}
              </h2>
              <button onClick={resetForm} className="text-ink-400 hover:text-ink-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-ink-600">计划标题</label>
                <Input
                  placeholder="例如：英语一复习计划"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-ink-600">开始日期</label>
                <Input
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-ink-600">结束日期</label>
                <Input
                  type="date"
                  value={form.end_date}
                  onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-ink-600">
                  涉及科目（逗号分隔）
                </label>
                <Input
                  placeholder="例如：英语, 政治, 数学"
                  value={form.subjects}
                  onChange={(e) => setForm((f) => ({ ...f, subjects: e.target.value }))}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-ink-600">
                  进度：{form.progress}%
                </label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={form.progress}
                  onChange={(e) => setForm((f) => ({ ...f, progress: Number(e.target.value) }))}
                  className="w-full accent-brand-600"
                />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" onClick={resetForm}>
                取消
              </Button>
              <Button onClick={handleSubmit}>
                {editingPlan ? "保存修改" : "创建计划"}
              </Button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <LoadingState text="加载学习计划..." />
          </div>
        ) : plans.length === 0 ? (
          <div className="rounded-xl border border-paper-200 bg-white p-8">
            <EmptyState
              title="暂无学习计划"
              description="点击「新建计划」开始规划你的考研复习路径"
              action={
                <Button onClick={() => setShowForm(true)}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  新建计划
                </Button>
              }
            />
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {plans.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onProgress={handleProgressUpdate}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function PlanCard({
  plan,
  onEdit,
  onDelete,
  onProgress,
}: {
  plan: StudyPlan;
  onEdit: (p: StudyPlan) => void;
  onDelete: (id: string) => void;
  onProgress: (p: StudyPlan, v: number) => void;
}) {
  return (
    <div className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {plan.completed ? (
              <CheckCircle2 className="h-5 w-5 shrink-0 text-green-500" />
            ) : (
              <Circle className="h-5 w-5 shrink-0 text-ink-300" />
            )}
            <h3 className="font-bold text-ink-900 truncate">{plan.title}</h3>
          </div>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => onEdit(plan)}
            className="rounded-lg p-1.5 text-ink-400 hover:bg-paper-100 hover:text-ink-600"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            onClick={() => onDelete(plan.id)}
            className="rounded-lg p-1.5 text-ink-400 hover:bg-red-50 hover:text-red-600"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {(plan.start_date || plan.end_date) && (
        <div className="mb-3 flex items-center gap-1.5 text-xs text-ink-500">
          <Calendar className="h-3.5 w-3.5" />
          {plan.start_date ?? "—"}
          {plan.start_date && plan.end_date && " → "}
          {plan.end_date ?? ""}
        </div>
      )}

      {plan.subjects && plan.subjects.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-1.5">
          {plan.subjects.map((s) => (
            <span
              key={s}
              className="inline-flex items-center rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700"
            >
              {s}
            </span>
          ))}
        </div>
      )}

      <div className="mt-auto">
        <div className="mb-2 flex items-center justify-between text-xs text-ink-500">
          <span>进度</span>
          <span className="font-semibold text-ink-700">{plan.progress}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-paper-200">
          <div
            className="h-full rounded-full bg-brand-600 transition-all"
            style={{ width: `${plan.progress}%` }}
          />
        </div>
        {!plan.completed && (
          <div className="mt-3 flex gap-1.5">
            {[25, 50, 75, 100].map((v) => (
              <button
                key={v}
                onClick={() => onProgress(plan, v)}
                className="flex-1 rounded-lg bg-paper-100 py-1 text-xs font-medium text-ink-600 hover:bg-brand-50 hover:text-brand-700"
              >
                {v}%
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
