"use client";

import { memo, useState, type FormEvent } from "react";
import { Plus, X, Wand2 } from "lucide-react";
import { retrospectivesApi } from "@/lib/api";
import { PERIOD_TYPES, PERIOD_TYPE_LABEL } from "@/lib/constants";
import { retroSchema } from "@/lib/validations";
import { todayISO } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { Button, Field, FieldError, Input, Select, Textarea } from "@/components/ui/form-controls";
import type { AIRetroDraft, PeriodType, RetrospectiveResponse } from "@/types";

interface RetroFormProps {
  initial?: RetrospectiveResponse | null;
  aiDraft?: {
    draft: AIRetroDraft;
    periodStart: string;
    periodEnd: string;
  } | null;
  onSaved: (retro: RetrospectiveResponse) => void;
  onCancel: () => void;
}

function DynamicList({
  items,
  onChange,
  placeholder,
  emptyLabel,
}: {
  items: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
  emptyLabel: string;
}) {
  const update = (i: number, v: string) => {
    const next = [...items];
    next[i] = v;
    onChange(next);
  };
  const add = () => onChange([...items, ""]);
  const remove = (i: number) => onChange(items.filter((_, idx) => idx !== i));

  return (
    <div className="space-y-2">
      {items.length === 0 && (
        <p className="text-xs text-slate-400">{emptyLabel}</p>
      )}
      {items.map((item, i) => (
        <div key={`item-${i}`} className="flex items-center gap-2">
          <span className="text-xs text-slate-400 w-4 shrink-0">{i + 1}.</span>
          <Input
            value={item}
            onChange={(e) => update(i, e.target.value)}
            placeholder={placeholder}
            className="flex-1"
          />
          <button
            type="button"
            onClick={() => remove(i)}
            className="p-1.5 rounded-md text-slate-400 hover:bg-red-50 hover:text-red-600 shrink-0"
            aria-label="删除"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline"
      >
        <Plus className="h-3.5 w-3.5" /> 添加一项
      </button>
    </div>
  );
}

export const RetroForm = memo(function RetroForm({ initial, aiDraft, onSaved, onCancel }: RetroFormProps) {
  const toast = useToast();
  const isEdit = !!initial;

  // AI 草稿自动生成标题：取摘要前 30 字
  const aiTitle = aiDraft?.draft.summary
    ? aiDraft.draft.summary.slice(0, 30)
    : "";

  const [periodType, setPeriodType] = useState<PeriodType>(
    initial?.period_type ?? "annual",
  );
  const [periodStart, setPeriodStart] = useState(
    initial?.period_start ?? aiDraft?.periodStart ?? todayISO().slice(0, 8) + "01",
  );
  const [periodEnd, setPeriodEnd] = useState(
    initial?.period_end ?? aiDraft?.periodEnd ?? todayISO(),
  );
  const [title, setTitle] = useState(initial?.title ?? aiTitle);
  const [achievements, setAchievements] = useState<string[]>(
    initial?.achievements ?? aiDraft?.draft.achievements ?? [""],
  );
  const [challenges, setChallenges] = useState(
    initial?.challenges ?? aiDraft?.draft.challenges ?? "",
  );
  const [lessonsLearned, setLessonsLearned] = useState(
    initial?.lessons_learned ?? aiDraft?.draft.lessons_learned ?? "",
  );
  const [nextSteps, setNextSteps] = useState<string[]>(
    initial?.next_steps ?? aiDraft?.draft.next_steps ?? [""],
  );
  const [satisfaction, setSatisfaction] = useState(
    initial?.satisfaction ?? aiDraft?.draft.suggested_satisfaction ?? 3,
  );
  const [loading, setLoading] = useState(false);
  const [draftLoading, setDraftLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const generateDraft = async () => {
    if (!periodStart || !periodEnd) {
      toast.push("请先选择复盘时间段", "error");
      return;
    }
    if (periodStart > periodEnd) {
      toast.push("开始日期不能晚于结束日期", "error");
      return;
    }
    setDraftLoading(true);
    try {
      const draft = await retrospectivesApi.draft(periodStart, periodEnd);
      const suggested = draft.suggested_achievements?.length
        ? draft.suggested_achievements
        : [];
      const summaries = draft.event_summaries.map((e) => e.title);
      const merged = Array.from(new Set([...suggested, ...summaries]));
      if (merged.length === 0) {
        toast.push("该时间段内暂无事件，无法生成草稿", "info");
      } else {
        setAchievements(merged.filter(Boolean).length ? merged : [""]);
        toast.push(`已根据 ${draft.event_summaries.length} 条事件生成草稿`, "success");
      }
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "生成草稿失败", "error");
    } finally {
      setDraftLoading(false);
    }
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const result = retroSchema.safeParse({
      title: title.trim(),
      period_type: periodType,
      period_start: periodStart,
      period_end: periodEnd,
      satisfaction,
    });
    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      Object.entries(result.error.flatten().fieldErrors).forEach(
        ([key, msgs]) => {
          if (msgs && msgs.length > 0) fieldErrors[key] = msgs[0];
        },
      );
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      const cleanArr = (arr: string[]) =>
        arr.map((s) => s.trim()).filter(Boolean);
      const payload = {
        period_type: periodType,
        period_start: periodStart,
        period_end: periodEnd,
        title: title.trim(),
        achievements: cleanArr(achievements),
        challenges: challenges || null,
        lessons_learned: lessonsLearned || null,
        next_steps: cleanArr(nextSteps),
        satisfaction,
      };
      const saved = isEdit && initial
        ? await retrospectivesApi.update(initial.id, payload)
        : await retrospectivesApi.create(payload);
      toast.push(isEdit ? "更新成功" : "创建成功", "success");
      onSaved(saved);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "保存失败", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Field label="复盘类型" required>
          <Select
            value={periodType}
            onChange={(e) => setPeriodType(e.target.value as PeriodType)}
          >
            {PERIOD_TYPES.map((p) => (
              <option key={p} value={p}>
                {PERIOD_TYPE_LABEL[p]}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="开始日期" required>
          <Input
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
            aria-invalid={!!errors.period_start}
            required
          />
          <FieldError message={errors.period_start} />
        </Field>
        <Field label="结束日期" required>
          <Input
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
            aria-invalid={!!errors.period_end}
            required
          />
          <FieldError message={errors.period_end} />
        </Field>
      </div>

      <Field label="标题" required>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="如：2026 年度复盘 / Q2 季度复盘"
          aria-invalid={!!errors.title}
          required
        />
        <FieldError message={errors.title} />
      </Field>

      {/* 生成草稿 */}
      <div className="rounded-lg border border-brand-100 bg-brand-50/50 p-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-brand-700">智能生成草稿</p>
          <p className="text-xs text-brand-600/70">
            基于所选时间段内的职业事件，自动填充成就列表
          </p>
        </div>
        <Button
          type="button"
          variant="secondary"
          onClick={generateDraft}
          loading={draftLoading}
        >
          <Wand2 className="h-4 w-4" /> 生成草稿
        </Button>
      </div>

      <Field label="成就 / 收获">
        <DynamicList
          items={achievements}
          onChange={setAchievements}
          placeholder="如：完成核心项目 X，提升性能 30%"
          emptyLabel="点击下方添加你的成就"
        />
      </Field>

      <Field label="挑战">
        <Textarea
          value={challenges}
          onChange={(e) => setChallenges(e.target.value)}
          placeholder="这段时间遇到的主要挑战…"
          className="min-h-[80px]"
        />
      </Field>

      <Field label="教训提炼">
        <Textarea
          value={lessonsLearned}
          onChange={(e) => setLessonsLearned(e.target.value)}
          placeholder="从这些经历中学到了什么…"
          className="min-h-[80px]"
        />
      </Field>

      <Field label="下一步规划">
        <DynamicList
          items={nextSteps}
          onChange={setNextSteps}
          placeholder="如：深入学习系统设计"
          emptyLabel="点击下方添加下一步行动"
        />
      </Field>

      <Field label={`满意度：${satisfaction} / 5`} hint="1=很不满意，5=非常满意">
        <input
          type="range"
          min={1}
          max={5}
          step={1}
          value={satisfaction}
          onChange={(e) => setSatisfaction(Number(e.target.value))}
          className="w-full accent-brand-600"
        />
      </Field>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={loading}>
          取消
        </Button>
        <Button type="submit" loading={loading}>
          {isEdit ? "保存修改" : "创建复盘"}
        </Button>
      </div>
    </form>
  );
});
