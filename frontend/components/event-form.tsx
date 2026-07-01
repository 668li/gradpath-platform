"use client";

import { useState, type FormEvent } from "react";
import { ChevronDown } from "lucide-react";
import { eventsApi } from "@/lib/api";
import { EVENT_TYPES, EVENT_TYPE_LABEL } from "@/lib/constants";
import { eventSchema } from "@/lib/validations";
import { cn, todayISO } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { Button, Field, FieldError, Input, Select, Textarea } from "@/components/ui/form-controls";
import type { EventResponse, EventType } from "@/types";

interface EventFormProps {
  initial?: EventResponse | null;
  onSaved: (event: EventResponse) => void;
  onCancel: () => void;
}

function metricsToText(metrics: Record<string, unknown> | null): string {
  if (!metrics) return "";
  return Object.entries(metrics)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join("\n");
}

function textToMetrics(text: string): Record<string, unknown> | null {
  const obj: Record<string, unknown> = {};
  text.split("\n").forEach((line) => {
    const t = line.trim();
    if (!t) return;
    const idx = t.indexOf(":");
    if (idx === -1) return;
    const k = t.slice(0, idx).trim();
    const v = t.slice(idx + 1).trim();
    if (k) obj[k] = v;
  });
  return Object.keys(obj).length ? obj : null;
}

export function EventForm({ initial, onSaved, onCancel }: EventFormProps) {
  const toast = useToast();
  const isEdit = !!initial;

  const [eventDate, setEventDate] = useState(initial?.event_date ?? todayISO());
  const [eventType, setEventType] = useState<EventType>(initial?.event_type ?? "onboard");
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [situation, setSituation] = useState(initial?.situation ?? "");
  const [task, setTask] = useState(initial?.task ?? "");
  const [action, setAction] = useState(initial?.action ?? "");
  const [result, setResult] = useState(initial?.result ?? "");
  const [reflection, setReflection] = useState(initial?.reflection ?? "");
  const [skillsText, setSkillsText] = useState(
    (initial?.skills_gained ?? []).join(", "),
  );
  const [metricsText, setMetricsText] = useState(
    metricsToText(initial?.impact_metrics ?? null),
  );
  const [mood, setMood] = useState(initial?.mood ?? 0);
  const [starOpen, setStarOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const parsed = eventSchema.safeParse({
      title: title.trim(),
      event_type: eventType,
      event_date: eventDate,
    });
    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {};
      Object.entries(parsed.error.flatten().fieldErrors).forEach(
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
      const skills = skillsText
        .split(/[,，]/)
        .map((s) => s.trim())
        .filter(Boolean);
      const payload = {
        event_date: eventDate,
        event_type: eventType,
        title: title.trim(),
        description: description || null,
        situation: situation || null,
        task: task || null,
        action: action || null,
        result: result || null,
        reflection: reflection || null,
        skills_gained: skills,
        impact_metrics: textToMetrics(metricsText),
        mood: mood === 0 ? null : mood,
      };
      const saved = isEdit && initial
        ? await eventsApi.update(initial.id, payload)
        : await eventsApi.create(payload);
      toast.push(isEdit ? "更新成功" : "创建成功", "success");
      onSaved(saved);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "保存失败", "error");
    } finally {
      setLoading(false);
    }
  };

  const starFields: { label: string; value: string; set: (v: string) => void }[] = [
    { label: "情境 (Situation)", value: situation, set: setSituation },
    { label: "任务 (Task)", value: task, set: setTask },
    { label: "行动 (Action)", value: action, set: setAction },
    { label: "结果 (Result)", value: result, set: setResult },
    { label: "反思 (Reflection)", value: reflection, set: setReflection },
  ];

  const hasStarContent = starFields.some((f) => f.value);

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="事件日期" required>
          <Input
            type="date"
            value={eventDate}
            onChange={(e) => setEventDate(e.target.value)}
            aria-invalid={!!errors.event_date}
            required
          />
          <FieldError message={errors.event_date} />
        </Field>
        <Field label="事件类型" required>
          <Select
            value={eventType}
            onChange={(e) => setEventType(e.target.value as EventType)}
          >
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {EVENT_TYPE_LABEL[t]}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <Field label="标题" required>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="如：入职某公司 / 完成核心项目"
          aria-invalid={!!errors.title}
          required
        />
        <FieldError message={errors.title} />
      </Field>

      <Field label="描述">
        <Textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="简要描述这个事件…"
        />
      </Field>

      {/* STAR+R 折叠区 */}
      <div className="rounded-lg border border-slate-200">
        <button
          type="button"
          onClick={() => setStarOpen((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <span>
            STAR+R 反思{" "}
            <span className="text-xs text-slate-400 font-normal">（可选）</span>
            {hasStarContent && (
              <span className="ml-2 inline-flex h-1.5 w-1.5 rounded-full bg-brand-500" />
            )}
          </span>
          <ChevronDown
            className={cn("h-4 w-4 transition-transform", starOpen && "rotate-180")}
          />
        </button>
        {starOpen && (
          <div className="space-y-3 px-4 pb-4">
            {starFields.map((f) => (
              <Field key={f.label} label={f.label}>
                <Textarea
                  value={f.value}
                  onChange={(e) => f.set(e.target.value)}
                  placeholder={`记录${f.label}…`}
                  className="min-h-[60px]"
                />
              </Field>
            ))}
          </div>
        )}
      </div>

      <Field label="习得技能" hint="多个技能用逗号分隔">
        <Input
          value={skillsText}
          onChange={(e) => setSkillsText(e.target.value)}
          placeholder="如：React, 系统设计, 沟通"
        />
      </Field>

      <Field label="量化影响" hint="每行一个，格式「指标: 值」，如：revenue: +20%">
        <Textarea
          value={metricsText}
          onChange={(e) => setMetricsText(e.target.value)}
          placeholder="revenue: +20%&#10;users: 1000"
          className="min-h-[60px] font-mono text-xs"
        />
      </Field>

      <Field label={`心情：${mood === 0 ? "未设置" : `${mood} / 5`}`} hint="1=低落，5=极佳">
        <input
          type="range"
          min={0}
          max={5}
          step={1}
          value={mood}
          onChange={(e) => setMood(Number(e.target.value))}
          className="w-full accent-brand-600"
        />
      </Field>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={loading}>
          取消
        </Button>
        <Button type="submit" loading={loading}>
          {isEdit ? "保存修改" : "创建事件"}
        </Button>
      </div>
    </form>
  );
}
