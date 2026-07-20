"use client";

import { useCallback, useEffect, useState } from "react";
import { Trophy, Loader2 } from "lucide-react";
import { outcomeReportApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import { Button, Input, Textarea, Select, Field } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";

const OUTCOME_TYPES = [
  { value: "grad_civil_career", label: "上岸（考研/考公/求职）" },
  { value: "adjustment", label: "调剂" },
  { value: "failed", label: "未上岸" },
];

const ADMISSION_PATHS = [
  { value: "normal", label: "正常录取" },
  { value: "adjustment", label: "调剂录取" },
  { value: "transfer", label: "转专业" },
];

const CURRENT_YEAR = new Date().getFullYear();

export default function OutcomeReportPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [myReports, setMyReports] = useState<any[]>([]);

  const [form, setForm] = useState({
    outcome_type: "grad_civil_career",
    target_school: "",
    target_major: "",
    actual_school: "",
    actual_major: "",
    score_total: "",
    score_politics: "",
    score_english: "",
    score_major1: "",
    score_major2: "",
    admission_path: "normal",
    year: String(CURRENT_YEAR),
    confidence_before: "",
    satisfaction_after: "",
    what_i_would_do_differently: "",
    advice_for_others: "",
    is_public: "private",
  });

  const loadReports = useCallback(async () => {
    try {
      const res = await outcomeReportApi.getMine();
      setMyReports(res.items);
    } catch {
      // ignore — first time may be empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const update = (key: string, value: string) => setForm(prev => ({ ...prev, [key]: value }));

  const handleSubmit = async () => {
    if (!form.year) {
      toast.push("请填写考试年份", "error");
      return;
    }
    setSubmitting(true);
    try {
      await outcomeReportApi.submit({
        outcome_type: form.outcome_type,
        target_school: form.target_school || undefined,
        target_major: form.target_major || undefined,
        actual_school: form.actual_school || undefined,
        actual_major: form.actual_major || undefined,
        score_total: form.score_total ? Number(form.score_total) : undefined,
        score_politics: form.score_politics ? Number(form.score_politics) : undefined,
        score_english: form.score_english ? Number(form.score_english) : undefined,
        score_major1: form.score_major1 ? Number(form.score_major1) : undefined,
        score_major2: form.score_major2 ? Number(form.score_major2) : undefined,
        admission_path: form.admission_path,
        year: Number(form.year),
        confidence_before: form.confidence_before ? Number(form.confidence_before) : undefined,
        satisfaction_after: form.satisfaction_after ? Number(form.satisfaction_after) : undefined,
        what_i_would_do_differently: form.what_i_would_do_differently || undefined,
        advice_for_others: form.advice_for_others || undefined,
        is_public: form.is_public,
      });
      toast.push("上岸报告提交成功！", "success");
      // Reset form
      setForm({
        outcome_type: "grad_civil_career",
        target_school: "",
        target_major: "",
        actual_school: "",
        actual_major: "",
        score_total: "",
        score_politics: "",
        score_english: "",
        score_major1: "",
        score_major2: "",
        admission_path: "normal",
        year: String(CURRENT_YEAR),
        confidence_before: "",
        satisfaction_after: "",
        what_i_would_do_differently: "",
        advice_for_others: "",
        is_public: "private",
      });
      loadReports();
    } catch (e: unknown) {
      const detail = (e as { detail?: string })?.detail;
      toast.push(detail || "提交失败，请重试", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 mb-4">
          <Trophy className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
        </div>
        <h1 className="page-title">上岸报告</h1>
        <p className="text-sm text-ink-400 mt-2 leading-relaxed">
          分享你的考试结果，帮助后来者做出更好的决策
        </p>
      </div>

      {/* Submit Form */}
      <div className="card space-y-5">
        <h2 className="text-base font-semibold text-ink-800">提交报告</h2>

        {/* Outcome Type */}
        <Field label="结果类型" required>
          <Select value={form.outcome_type} onChange={e => update("outcome_type", e.target.value)} data-testid="outcome-type-select">
            {OUTCOME_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </Select>
        </Field>

        {/* Year */}
        <Field label="考试年份" required>
          <Input
            type="number"
            value={form.year}
            onChange={e => update("year", e.target.value)}
            min={2000}
            max={CURRENT_YEAR + 1}
            data-testid="outcome-year-input"
          />
        </Field>

        {/* Target */}
        <div className="grid grid-cols-2 gap-3">
          <Field label="目标院校">
            <Input
              value={form.target_school}
              onChange={e => update("target_school", e.target.value)}
              placeholder="如：北京大学"
              data-testid="target-school-input"
            />
          </Field>
          <Field label="目标专业">
            <Input
              value={form.target_major}
              onChange={e => update("target_major", e.target.value)}
              placeholder="如：计算机科学"
              data-testid="target-major-input"
            />
          </Field>
        </div>

        {/* Actual */}
        <div className="grid grid-cols-2 gap-3">
          <Field label="实际录取院校">
            <Input
              value={form.actual_school}
              onChange={e => update("actual_school", e.target.value)}
              placeholder="录取后填写"
              data-testid="actual-school-input"
            />
          </Field>
          <Field label="实际录取专业">
            <Input
              value={form.actual_major}
              onChange={e => update("actual_major", e.target.value)}
              placeholder="录取后填写"
              data-testid="actual-major-input"
            />
          </Field>
        </div>

        {/* Admission Path */}
        <Field label="录取方式">
          <Select value={form.admission_path} onChange={e => update("admission_path", e.target.value)}>
            {ADMISSION_PATHS.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </Select>
        </Field>

        {/* Scores */}
        <div>
          <p className="mb-2 text-sm font-medium text-ink-700">成绩（选填）</p>
          <div className="grid grid-cols-3 gap-3">
            <Field label="总分">
              <Input
                type="number"
                value={form.score_total}
                onChange={e => update("score_total", e.target.value)}
                placeholder="总分"
              />
            </Field>
            <Field label="政治">
              <Input
                type="number"
                value={form.score_politics}
                onChange={e => update("score_politics", e.target.value)}
                placeholder="政治"
              />
            </Field>
            <Field label="英语">
              <Input
                type="number"
                value={form.score_english}
                onChange={e => update("score_english", e.target.value)}
                placeholder="英语"
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <Field label="专业课一">
              <Input
                type="number"
                value={form.score_major1}
                onChange={e => update("score_major1", e.target.value)}
                placeholder="专业课一"
              />
            </Field>
            <Field label="专业课二">
              <Input
                type="number"
                value={form.score_major2}
                onChange={e => update("score_major2", e.target.value)}
                placeholder="专业课二"
              />
            </Field>
          </div>
        </div>

        {/* Confidence & Satisfaction */}
        <div className="grid grid-cols-2 gap-3">
          <Field label="考前信心（0-1）" hint="0=完全没底，1=非常有把握">
            <Input
              type="number"
              value={form.confidence_before}
              onChange={e => update("confidence_before", e.target.value)}
              min={0}
              max={1}
              step={0.1}
              placeholder="0.5"
            />
          </Field>
          <Field label="事后满意度（1-5）" hint="1=很不满意，5=非常满意">
            <Input
              type="number"
              value={form.satisfaction_after}
              onChange={e => update("satisfaction_after", e.target.value)}
              min={1}
              max={5}
              placeholder="3"
            />
          </Field>
        </div>

        {/* Reflections */}
        <Field label="如果重来，我会怎么做不同">
          <Textarea
            value={form.what_i_would_do_differently}
            onChange={e => update("what_i_would_do_differently", e.target.value)}
            placeholder="分享你的反思，帮助后来者避坑…"
            className="min-h-[100px]"
          />
        </Field>

        <Field label="给后来者的建议">
          <Textarea
            value={form.advice_for_others}
            onChange={e => update("advice_for_others", e.target.value)}
            placeholder="你觉得最重要的一条建议是什么？"
            className="min-h-[80px]"
          />
        </Field>

        {/* Public/Private Toggle */}
        <Field label="公开设置" hint="公开后将展示在上岸墙上">
          <div className="flex gap-2">
            {[
              { value: "private", label: "仅自己可见" },
              { value: "public", label: "公开到上岸墙" },
            ].map(opt => (
              <button
                key={opt.value}
                onClick={() => update("is_public", opt.value)}
                className={cn(
                  "flex-1 rounded-lg border px-4 py-2 text-sm font-medium transition-all",
                  form.is_public === opt.value
                    ? "bg-brand-600 text-white border-brand-600"
                    : "bg-white text-ink-600 border-paper-300 hover:border-ink-200",
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </Field>

        <Button onClick={handleSubmit} loading={submitting} className="w-full" size="md" data-testid="generate-button">
          提交上岸报告
        </Button>
      </div>

      {/* My Reports */}
      {myReports.length > 0 && (
        <div className="card space-y-4">
          <h2 className="text-base font-semibold text-ink-800">我的报告</h2>
          <div className="space-y-3">
            {myReports.map(r => (
              <div key={r.id} className="rounded-lg border border-paper-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-ink-800">
                    {r.target_school || "未填写院校"} · {r.target_major || "未填写专业"}
                  </span>
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full",
                    r.outcome_type === "grad_civil_career" ? "bg-green-100 text-green-700" :
                    r.outcome_type === "adjustment" ? "bg-amber-100 text-amber-700" :
                    "bg-red-100 text-red-700",
                  )}>
                    {r.outcome_type === "grad_civil_career" ? "上岸" :
                     r.outcome_type === "adjustment" ? "调剂" : "未上岸"}
                  </span>
                </div>
                <div className="text-xs text-ink-400 space-y-1">
                  <p>年份: {r.year} · {r.is_public === "public" ? "公开" : "私密"}</p>
                  {r.score_total && <p>总分: {r.score_total}</p>}
                  {r.actual_school && <p>录取: {r.actual_school} · {r.actual_major}</p>}
                </div>
                <div className="mt-3 flex justify-end">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => toast.push("分享功能即将上线", "info")}
                    data-testid="share-button"
                  >
                    分享到社区
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
