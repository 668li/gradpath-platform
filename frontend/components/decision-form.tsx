"use client";

import { useState, type FormEvent } from "react";
import { ChevronDown, Plus, Trash2 } from "lucide-react";
import { decisionsApi } from "@/lib/api";
import {
  DECISION_STATUSES,
  DECISION_STATUS_LABEL,
  DESTINATION_DETAIL_FIELDS,
  DESTINATION_TYPES,
  DESTINATION_TYPE_LABEL,
} from "@/lib/constants";
import { decisionSchema } from "@/lib/validations";
import { cn, todayISO } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { Button, Field, FieldError, Input, Select, Textarea } from "@/components/ui/form-controls";
import type {
  DecisionDetails,
  DecisionResponse,
  DestinationType,
} from "@/types";

interface DecisionFormProps {
  initial?: DecisionResponse | null;
  onSaved: (decision: DecisionResponse) => void;
  onCancel: () => void;
}

function emptyDetails(type: DestinationType): DecisionDetails {
  const fields = DESTINATION_DETAIL_FIELDS[type];
  const obj: DecisionDetails = {};
  fields.forEach((f) => {
    obj[f.key] = "";
  });
  return obj;
}

export function DecisionForm({ initial, onSaved, onCancel }: DecisionFormProps) {
  const toast = useToast();
  const isEdit = !!initial;

  const [decisionDate, setDecisionDate] = useState(
    initial?.decision_date ?? todayISO(),
  );
  const [destinationType, setDestinationType] = useState<DestinationType>(
    initial?.destination_type ?? "employment",
  );
  const [status, setStatus] = useState(initial?.status ?? "planned");
  const [details, setDetails] = useState<DecisionDetails>(
    initial?.details ?? emptyDetails("employment"),
  );
  const [reasoning, setReasoning] = useState(initial?.reasoning ?? "");
  const [confidence, setConfidence] = useState(initial?.confidence ?? 3);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // 决策日志字段（可选）
  const [prediction, setPrediction] = useState(initial?.prediction ?? "");
  const [assumptions, setAssumptions] = useState<string[]>(
    initial?.assumptions && initial.assumptions.length > 0
      ? [...initial.assumptions]
      : [""],
  );
  const [reviewDate, setReviewDate] = useState(initial?.review_date ?? "");
  const [journalOpen, setJournalOpen] = useState(
    !!(
      initial?.prediction ||
      initial?.review_date ||
      (initial?.assumptions && initial.assumptions.length > 0)
    ),
  );

  const handleTypeChange = (type: DestinationType) => {
    setDestinationType(type);
    // 切换类型时，保留同名字段，其余重置为新类型空字段
    const newDetails = emptyDetails(type);
    Object.keys(newDetails).forEach((k) => {
      if (details[k] !== undefined) newDetails[k] = details[k];
    });
    setDetails(newDetails);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const result = decisionSchema.safeParse({
      decision_date: decisionDate,
      destination_type: destinationType,
      status,
      confidence,
      reasoning: reasoning || undefined,
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
      // 过滤掉空字符串的 details 值
      const cleanDetails: DecisionDetails = {};
      Object.entries(details).forEach(([k, v]) => {
        if (v !== undefined && v !== "") cleanDetails[k] = v;
      });
      const payload = {
        decision_date: decisionDate,
        destination_type: destinationType,
        status,
        details: cleanDetails,
        reasoning: reasoning || null,
        confidence,
        prediction: prediction.trim() || null,
        assumptions: assumptions.map((a) => a.trim()).filter(Boolean),
        review_date: reviewDate || null,
      };
      const saved = isEdit && initial
        ? await decisionsApi.update(initial.id, payload)
        : await decisionsApi.create(payload);
      toast.push(isEdit ? "更新成功" : "创建成功", "success");
      onSaved(saved);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "保存失败", "error");
    } finally {
      setLoading(false);
    }
  };

  const detailFields = DESTINATION_DETAIL_FIELDS[destinationType];

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="决策日期" required>
          <Input
            type="date"
            value={decisionDate}
            onChange={(e) => setDecisionDate(e.target.value)}
            aria-invalid={!!errors.decision_date}
            required
          />
          <FieldError message={errors.decision_date} />
        </Field>
        <Field label="去向类型" required>
          <Select
            value={destinationType}
            onChange={(e) => handleTypeChange(e.target.value as DestinationType)}
          >
            {DESTINATION_TYPES.map((t) => (
              <option key={t} value={t}>
                {DESTINATION_TYPE_LABEL[t]}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <Field label="状态">
        <Select value={status} onChange={(e) => setStatus(e.target.value as typeof status)}>
          {DECISION_STATUSES.map((s) => (
            <option key={s} value={s}>
              {DECISION_STATUS_LABEL[s]}
            </option>
          ))}
        </Select>
      </Field>

      {/* 动态详情字段 */}
      <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-4 space-y-3">
        <p className="text-sm font-medium text-slate-600">
          {DESTINATION_TYPE_LABEL[destinationType]} 详情
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {detailFields.map((f) => (
            <Field key={f.key} label={f.label}>
              {f.type === "select" ? (
                <Select
                  value={(details[f.key] as string) ?? ""}
                  onChange={(e) =>
                    setDetails((d) => ({ ...d, [f.key]: e.target.value }))
                  }
                >
                  <option value="">请选择</option>
                  {f.options?.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </Select>
              ) : (
                <Input
                  value={(details[f.key] as string) ?? ""}
                  onChange={(e) =>
                    setDetails((d) => ({ ...d, [f.key]: e.target.value }))
                  }
                  placeholder={f.placeholder}
                />
              )}
            </Field>
          ))}
        </div>
      </div>

      <Field label="决策理由">
        <Textarea
          value={reasoning}
          onChange={(e) => setReasoning(e.target.value)}
          placeholder="为什么做出这个决策？记录你的思考过程…"
          className="min-h-[100px]"
        />
      </Field>

      <Field label={`信心度：${confidence} / 5`} hint="1=很不确定，5=非常确定">
        <input
          type="range"
          min={1}
          max={5}
          step={1}
          value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          className="w-full accent-brand-600"
        />
      </Field>

      {/* 决策日志（可选） */}
      <div className="rounded-lg border border-paper-300 bg-paper-50/40">
        <button
          type="button"
          onClick={() => setJournalOpen((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 text-left"
          aria-expanded={journalOpen}
        >
          <span className="flex items-center gap-2 text-sm font-medium text-ink-700">
            <span className="flex h-5 w-5 items-center justify-center rounded bg-brand-100 text-brand-600">
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 transition-transform",
                  journalOpen ? "" : "-rotate-90",
                )}
              />
            </span>
            决策日志（可选）
          </span>
          <span className="text-xs text-ink-400">
            {journalOpen ? "收起" : "展开"}
          </span>
        </button>
        {journalOpen && (
          <div className="space-y-4 border-t border-paper-300 px-4 py-4">
            <Field label="预测" hint="你预测这个决策会带来什么结果？">
              <Textarea
                value={prediction}
                onChange={(e) => setPrediction(e.target.value)}
                placeholder="你预测这个决策会带来什么结果？"
                className="min-h-[80px]"
              />
            </Field>

            <div>
              <span className="mb-1.5 block text-sm font-medium text-ink-700">
                关键假设
              </span>
              <p className="mb-2 text-xs text-ink-400">你的关键假设是什么？</p>
              <div className="space-y-2">
                {assumptions.map((a, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <Textarea
                      value={a}
                      onChange={(e) =>
                        setAssumptions((prev) =>
                          prev.map((x, idx) => (idx === i ? e.target.value : x)),
                        )
                      }
                      placeholder={`假设 ${i + 1}…`}
                      className="min-h-[56px]"
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setAssumptions((prev) =>
                          prev.length === 1 ? [""] : prev.filter((_, idx) => idx !== i),
                        )
                      }
                      className="mt-1 shrink-0 rounded-md p-1.5 text-ink-300 hover:bg-red-50 hover:text-red-500"
                      aria-label="删除假设"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setAssumptions((prev) => [...prev, ""])}
                className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
              >
                <Plus className="h-3.5 w-3.5" /> 添加假设
              </button>
            </div>

            <Field label="计划回溯评估日期" hint="建议1-3个月后">
              <Input
                type="date"
                value={reviewDate}
                onChange={(e) => setReviewDate(e.target.value)}
              />
            </Field>
          </div>
        )}
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={loading}>
          取消
        </Button>
        <Button type="submit" loading={loading}>
          {isEdit ? "保存修改" : "创建决策"}
        </Button>
      </div>
    </form>
  );
}
