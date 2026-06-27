"use client";

import { useState, type FormEvent } from "react";
import { decisionsApi } from "@/lib/api";
import {
  DECISION_STATUSES,
  DECISION_STATUS_LABEL,
  DESTINATION_DETAIL_FIELDS,
  DESTINATION_TYPES,
  DESTINATION_TYPE_LABEL,
} from "@/lib/constants";
import { todayISO } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { Button, Field, Input, Select, Textarea } from "@/components/ui/form-controls";
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
    if (!decisionDate) {
      toast.push("请选择决策日期", "error");
      return;
    }
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
            required
          />
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
