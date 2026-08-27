"use client";

// frontend/components/decision-engine/outcome-form.tsx
// 结果回传表单 — 记录「当时选了哪条路、结果如何」（决策飞轮闭环第一圈）

import { useState } from "react";
import { CheckCircle2, History, Send } from "lucide-react";
import { Badge, Button, Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import { pathDecisionApi } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import type { DecisionOutcomeInfo, DecisionOutcomeSubmit } from "@/types/path-comparison";

const PATH_OPTIONS = [
  { value: "civil_service", label: "考公" },
  { value: "kaoyan", label: "考研深造" },
  { value: "employment", label: "直接就业" },
];

const STATUS_OPTIONS: { value: DecisionOutcomeSubmit["outcome_status"]; label: string }[] = [
  { value: "following", label: "已走上该路径（进行中）" },
  { value: "pending", label: "正在备考 / 求职" },
  { value: "achieved", label: "已达成（上岸 / 入职）" },
  { value: "abandoned", label: "已放弃 / 改道" },
];

const STATUS_BADGE: Record<string, { label: string; color: "blue" | "green" | "amber" | "slate" }> = {
  pending: { label: "进行中", color: "blue" },
  following: { label: "已选择", color: "green" },
  achieved: { label: "已达成", color: "green" },
  abandoned: { label: "已放弃", color: "slate" },
};

interface OutcomeFormProps {
  decisionId: string;
  outcome: DecisionOutcomeInfo | null | undefined;
  onSaved: (outcome: DecisionOutcomeInfo) => void;
}

export function OutcomeForm({ decisionId, outcome, onSaved }: OutcomeFormProps) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedPath, setSelectedPath] = useState("");
  const [selectedLabel, setSelectedLabel] = useState("");
  const [outcomeStatus, setOutcomeStatus] = useState("");
  const [actualOutcome, setActualOutcome] = useState("");
  const [satisfaction, setSatisfaction] = useState("");

  const canSubmit = selectedPath && outcomeStatus;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    try {
      const payload: DecisionOutcomeSubmit = {
        selected_path: selectedPath as DecisionOutcomeSubmit["selected_path"],
        selected_label:
          selectedLabel ||
          PATH_OPTIONS.find((o) => o.value === selectedPath)?.label,
        outcome_status: outcomeStatus as DecisionOutcomeSubmit["outcome_status"],
        actual_outcome: actualOutcome.trim() || undefined,
        satisfaction: satisfaction ? Number(satisfaction) : undefined,
      };
      const resp = await pathDecisionApi.submitOutcome(decisionId, payload);
      onSaved(resp.outcome ?? payload);
      toast.success("选择与结果已记录，飞轮开始积累你的样本");
      setOpen(false);
    } catch {
      toast.error("回传失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  if (outcome?.outcome_status) {
    const badge = STATUS_BADGE[outcome.outcome_status] ?? STATUS_BADGE.pending;
    return (
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50/50 px-4 py-3">
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
        <div className="flex-1 min-w-0 text-sm text-ink-700">
          已记录选择：<span className="font-medium">{outcome.selected_label ?? outcome.selected_path}</span>
          {outcome.actual_outcome && <span className="text-ink-500"> · {outcome.actual_outcome}</span>}
        </div>
        <Badge color={badge.color}>{badge.label}</Badge>
      </div>
    );
  }

  return (
    <details open={open} onToggle={(e) => setOpen(e.currentTarget.open)} className="rounded-xl border border-dashed border-paper-300 bg-paper-50/40 p-4">
      <summary className="flex cursor-pointer select-none items-center gap-2 text-sm font-medium text-ink-700">
        <History className="h-4 w-4 text-brand-600" />
        记录我的选择（结果回传）
        <span className="ml-auto text-xs font-normal text-ink-400">
          为后来人积累真实上岸/入面样本，不做任何公开展示
        </span>
      </summary>
      <form onSubmit={handleSubmit} className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <Field label="我选择了哪条路" required>
          <Select value={selectedPath} onChange={(e) => setSelectedPath(e.target.value)}>
            <option value="">请选择</option>
            {PATH_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </Select>
        </Field>
        <Field label="现在的状态" required>
          <Select value={outcomeStatus} onChange={(e) => setOutcomeStatus(e.target.value)}>
            <option value="">请选择</option>
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </Select>
        </Field>
        <Field label="实际结果描述" className="md:col-span-2" hint="如：进面未上岸 / 25 考研上岸 XX 大学 / 已入职 XX 公司">
          <Textarea
            value={actualOutcome}
            onChange={(e) => setActualOutcome(e.target.value)}
            placeholder="选填，写清楚时间线最有参考价值"
            maxLength={200}
          />
        </Field>
        <Field label="目标角色（选填）">
          <Input
            value={selectedLabel}
            onChange={(e) => setSelectedLabel(e.target.value)}
            placeholder="如：省考行政执法岗"
          />
        </Field>
        <Field label="综合满意度（1-5）">
          <Input
            type="number"
            min={1}
            max={5}
            value={satisfaction}
            onChange={(e) => setSatisfaction(e.target.value)}
            placeholder="选填"
          />
        </Field>
        <div className="flex items-end md:col-span-2">
          <Button type="submit" loading={saving} disabled={!canSubmit}>
            <Send className="h-4 w-4" />
            提交记录
          </Button>
        </div>
      </form>
    </details>
  );
}