"use client";

import { useState } from "react";
import { ChevronDown, CheckCircle2, AlertTriangle, Plus, ShieldCheck } from "lucide-react";
import { decisionEvidenceApi, useApi } from "@/lib/api";
import type {
  DecisionEvidence,
  DecisionHypothesis,
  EvidenceReadiness,
} from "@/types/decision-evidence";
import { Badge, Button, Input, Textarea } from "@/components/ui/form-controls";

export function DecisionEvidencePanel({ decisionId }: { decisionId: string }) {
  const [open, setOpen] = useState(false);
  const [newHypothesis, setNewHypothesis] = useState("");
  const [newEvidenceClaim, setNewEvidenceClaim] = useState("");
  const [newEvidenceTitle, setNewEvidenceTitle] = useState("");
  const [addingHypothesis, setAddingHypothesis] = useState(false);
  const [addingEvidence, setAddingEvidence] = useState(false);
  const [saving, setSaving] = useState(false);

  const hypothesesKey = open ? `/api/decisions/${decisionId}/hypotheses` : null;
  const readinessKey = open ? `/api/decisions/${decisionId}/evidence-readiness` : null;
  const evidenceKey = open ? `/api/decisions/${decisionId}/evidence` : null;

  const { data: hypotheses, mutate: mutateHypotheses } =
    useApi<DecisionHypothesis[]>(hypothesesKey);
  const { data: readiness, mutate: mutateReadiness } =
    useApi<EvidenceReadiness>(readinessKey);
  const { data: evidence, mutate: mutateEvidence } =
    useApi<DecisionEvidence[]>(evidenceKey);

  const refresh = async () => {
    await Promise.all([mutateHypotheses(), mutateReadiness(), mutateEvidence()]);
  };

  const submitHypothesis = async () => {
    const statement = newHypothesis.trim();
    if (!statement) return;
    setSaving(true);
    try {
      await decisionEvidenceApi.createHypothesis(decisionId, {
        statement,
        importance: 3,
        confidence: 0.5,
        status: "open",
      });
      setNewHypothesis("");
      setAddingHypothesis(false);
      await refresh();
    } finally {
      setSaving(false);
    }
  };

  const submitEvidence = async () => {
    const title = newEvidenceTitle.trim();
    const claim = newEvidenceClaim.trim();
    if (!title || !claim) return;
    setSaving(true);
    try {
      const target = (hypotheses ?? []).find((h) => h.status === "open") ?? hypotheses?.[0];
      await decisionEvidenceApi.createEvidence(decisionId, {
        hypothesis_id: target?.id ?? null,
        title,
        claim,
        source_type: "user",
        reliability: 2,
        stance: "neutral",
      });
      setNewEvidenceTitle("");
      setNewEvidenceClaim("");
      setAddingEvidence(false);
      await refresh();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-paper-300 bg-paper-50/60">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className="flex min-w-0 items-center gap-2">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <ShieldCheck className="h-3.5 w-3.5" />
          </span>
          <span className="text-xs font-medium text-ink-700">证据链</span>
          {readiness && (
            <Badge color={readiness.coverage >= 0.7 ? "green" : readiness.coverage > 0 ? "amber" : "red"}>
              {Math.round(readiness.coverage * 100)}% 已覆盖
            </Badge>
          )}
        </span>
        <ChevronDown className={`h-4 w-4 text-ink-400 transition-transform ${open ? "" : "-rotate-90"}`} />
      </button>

      {open && (
        <div className="space-y-3 border-t border-paper-300 px-3 py-3">
          {!readiness ? (
            <p className="text-xs text-ink-400">正在读取当前决策的证据缺口…</p>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-lg bg-white p-2">
                  <div className="text-sm font-semibold text-ink-800">{readiness.hypotheses_total}</div>
                  <div className="text-[11px] text-ink-400">关键假设</div>
                </div>
                <div className="rounded-lg bg-white p-2">
                  <div className="text-sm font-semibold text-brand-700">{readiness.hypotheses_with_evidence}</div>
                  <div className="text-[11px] text-ink-400">已有证据</div>
                </div>
                <div className="rounded-lg bg-white p-2">
                  <div className="text-sm font-semibold text-amber-700">{readiness.hypotheses_unverified}</div>
                  <div className="text-[11px] text-ink-400">待验证</div>
                </div>
              </div>

              {readiness.hypotheses_unverified > 0 && (
                <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-2.5 text-xs text-amber-800">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>这个决定现在还不该追求“正确率”，先验证关键假设。</span>
                </div>
              )}

              {(hypotheses ?? []).length > 0 && (
                <div className="space-y-2">
                  {(hypotheses ?? []).slice(0, 5).map((hypothesis) => (
                    <div key={hypothesis.id} className="rounded-lg bg-white px-3 py-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs leading-relaxed text-ink-700">{hypothesis.statement}</p>
                        {hypothesis.status === "validated" ? (
                          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand-600" />
                        ) : (
                          <Badge color={hypothesis.status === "invalidated" ? "red" : "slate"}>
                            {hypothesis.status === "open" ? "待验证" : hypothesis.status}
                          </Badge>
                        )}
                      </div>
                      {hypothesis.validation_action && (
                        <p className="mt-1 text-[11px] text-ink-400">
                          下一步：{hypothesis.validation_action}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {evidence && evidence.length > 0 && (
                <p className="text-[11px] text-ink-400">
                  当前记录了 {evidence.length} 条证据；系统不会把“证据多”直接等同于“决策正确”。
                </p>
              )}

              {addingHypothesis ? (
                <div className="space-y-2 rounded-lg bg-white p-3">
                  <Input
                    value={newHypothesis}
                    onChange={(e) => setNewHypothesis(e.target.value)}
                    placeholder="例如：目标研发岗普遍要求硕士学历"
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <Button size="sm" loading={saving} onClick={submitHypothesis}>保存假设</Button>
                    <Button size="sm" variant="ghost" onClick={() => setAddingHypothesis(false)}>取消</Button>
                  </div>
                </div>
              ) : addingEvidence ? (
                <div className="space-y-2 rounded-lg bg-white p-3">
                  <Input
                    value={newEvidenceTitle}
                    onChange={(e) => setNewEvidenceTitle(e.target.value)}
                    placeholder="证据标题"
                  />
                  <Textarea
                    value={newEvidenceClaim}
                    onChange={(e) => setNewEvidenceClaim(e.target.value)}
                    placeholder="具体观察到什么？例如：20 个目标岗位中 12 个写明硕士优先"
                    className="min-h-[72px]"
                  />
                  <div className="flex gap-2">
                    <Button size="sm" loading={saving} onClick={submitEvidence}>记录证据</Button>
                    <Button size="sm" variant="ghost" onClick={() => setAddingEvidence(false)}>取消</Button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => setAddingHypothesis(true)}>
                    <Plus className="h-3.5 w-3.5" /> 添加假设
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => setAddingEvidence(true)}>
                    <Plus className="h-3.5 w-3.5" /> 记录证据
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
