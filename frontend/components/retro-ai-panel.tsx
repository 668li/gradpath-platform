"use client";

import { useState } from "react";
import {
  Sparkles,
  ChevronDown,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Star,
} from "lucide-react";
import { retrospectivesApi, type ApiError } from "@/lib/api";
import { todayISO, levelStars, cn } from "@/lib/utils";
import { Button } from "@/components/ui/form-controls";
import type { AIRetroDraft } from "@/types";

interface RetroAIPanelProps {
  /** 使用草稿时回调，同时返回所选时间段以便填充表单 */
  onUseDraft: (
    draft: AIRetroDraft,
    period: { start: string; end: string },
  ) => void;
}

/**
 * AI 复盘草稿面板：
 * - 选择时间段后调用 AI 生成复盘草稿
 * - 预览草稿内容（成就、挑战、教训、下一步、建议满意度、总结）
 * - 点击「使用此草稿」将数据回填到复盘表单
 * - 默认折叠，点击头部展开
 */
export function RetroAIPanel({ onUseDraft }: RetroAIPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [periodStart, setPeriodStart] = useState(todayISO().slice(0, 8) + "01");
  const [periodEnd, setPeriodEnd] = useState(todayISO());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<AIRetroDraft | null>(null);

  const handleGenerate = async () => {
    if (!periodStart || !periodEnd) return;
    if (periodStart > periodEnd) {
      setError("开始日期不能晚于结束日期");
      return;
    }
    setLoading(true);
    setError(null);
    setDraft(null);
    try {
      const res = await retrospectivesApi.aiDraft({
        period_start: periodStart,
        period_end: periodEnd,
      });
      setDraft(res);
    } catch (err) {
      const status = (err as ApiError).status;
      if (status === 503) {
        setError("AI 服务未配置，请联系管理员");
      } else if (status === 504) {
        setError("分析超时，请稍后重试");
      } else {
        setError(err instanceof Error ? err.message : "生成草稿失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUse = () => {
    if (!draft) return;
    onUseDraft(draft, { start: periodStart, end: periodEnd });
    // 使用后折叠并清理
    setDraft(null);
    setError(null);
    setExpanded(false);
  };

  return (
    <div className="card overflow-hidden">
      {/* 头部 / 展开切换 */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between gap-3 text-left"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <Sparkles className="h-5 w-5" />
          </span>
          <div>
            <h2 className="font-semibold text-slate-800">AI 生成复盘草稿</h2>
            <p className="text-xs text-slate-500">
              选择时间段，AI 自动生成复盘内容草稿
            </p>
          </div>
        </div>
        <ChevronDown
          className={cn(
            "h-5 w-5 text-slate-400 transition-transform",
            expanded && "rotate-180",
          )}
        />
      </button>

      {expanded && (
        <div className="mt-4 space-y-4 border-t border-slate-100 pt-4">
          {/* 时间段选择 */}
          <div className="flex flex-wrap items-end gap-3">
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">
                开始日期
              </span>
              <input
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">
                结束日期
              </span>
              <input
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <Button
              onClick={handleGenerate}
              loading={loading}
              disabled={loading}
            >
              <Sparkles className="h-4 w-4" /> AI 生成复盘草稿
            </Button>
          </div>

          {/* 加载中 */}
          {loading && (
            <div className="flex items-center gap-2 text-brand-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="animate-pulse text-sm font-medium">
                AI 分析中…
              </span>
            </div>
          )}

          {/* 错误 */}
          {error && !loading && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
              <AlertTriangle className="h-5 w-5 shrink-0 text-red-600" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* 草稿预览 */}
          {draft && !loading && (
            <div className="space-y-3">
              <div className="rounded-lg border border-brand-200 bg-brand-50/50 p-4">
                <div className="mb-3 flex items-center gap-2 text-brand-700">
                  <Sparkles className="h-4 w-4" />
                  <span className="text-sm font-semibold">AI 草稿预览</span>
                </div>

                {/* 成就 */}
                {draft.achievements.length > 0 && (
                  <div className="mb-3">
                    <p className="mb-1 text-xs font-medium text-slate-500">
                      成就
                    </p>
                    <ul className="space-y-1">
                      {draft.achievements.map((a, i) => (
                        <li
                          key={`${a}-${i}`}
                          className="flex items-start gap-1.5 text-sm text-slate-600"
                        >
                          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-500" />
                          <span>{a}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 挑战 */}
                {draft.challenges && (
                  <div className="mb-3">
                    <p className="mb-1 text-xs font-medium text-slate-500">
                      挑战
                    </p>
                    <p className="text-sm text-slate-600">{draft.challenges}</p>
                  </div>
                )}

                {/* 教训提炼 */}
                {draft.lessons_learned && (
                  <div className="mb-3">
                    <p className="mb-1 text-xs font-medium text-slate-500">
                      教训提炼
                    </p>
                    <p className="text-sm text-slate-600">
                      {draft.lessons_learned}
                    </p>
                  </div>
                )}

                {/* 下一步 */}
                {draft.next_steps.length > 0 && (
                  <div className="mb-3">
                    <p className="mb-1 text-xs font-medium text-slate-500">
                      下一步
                    </p>
                    <ul className="space-y-1">
                      {draft.next_steps.map((s, i) => (
                        <li
                          key={`${s}-${i}`}
                          className="flex items-start gap-1.5 text-sm text-slate-600"
                        >
                          <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand-500" />
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 建议满意度 */}
                <div className="mb-3 flex items-center gap-2">
                  <Star className="h-4 w-4 text-amber-400" />
                  <span className="text-xs font-medium text-slate-500">
                    建议满意度
                  </span>
                  <span className="text-amber-500 tracking-wide">
                    {levelStars(draft.suggested_satisfaction)}
                  </span>
                  <span className="text-xs text-slate-400">
                    {draft.suggested_satisfaction}/5
                  </span>
                </div>

                {/* 总结 */}
                {draft.summary && (
                  <div>
                    <p className="mb-1 text-xs font-medium text-slate-500">
                      总结
                    </p>
                    <p className="text-sm leading-relaxed text-slate-600">
                      {draft.summary}
                    </p>
                  </div>
                )}
              </div>

              <Button onClick={handleUse}>
                <CheckCircle2 className="h-4 w-4" /> 使用此草稿
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
