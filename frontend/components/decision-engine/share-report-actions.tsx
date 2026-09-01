"use client";

// frontend/components/decision-engine/share-report-actions.tsx
// 报告分享按钮区 — 生成防枚举分享链接 + 复制可粘贴到小红书/考研群的文字版报告摘要。
// 分享页匿名渲染：不含姓名与登录信息，含你的预估分与条件（提示用户知悉）。

import { useMemo, useState } from "react";
import { Check, Copy, Link2, Loader2, Share2 } from "lucide-react";
import { pathDecisionApi } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import type { DecisionEngineResponse } from "@/types/path-comparison";

/** 派生一段可粘贴的文字版报告摘要（不编造、只聚合已有结论） */
function buildShareText(result: DecisionEngineResponse): string {
  const input = result.input ?? {};
  const lines: string[] = [];
  lines.push("【我的报考决策报告 · GradPath】");
  lines.push(
    `${String(input.major ?? "我的专业")} · ${String(input.graduation_year ?? 2026)} 届 · 三路对比`,
  );

  const rows = result.metrics.map((m) => {
    const label: Record<string, string> = {
      kaoyan: "考研",
      civil_service: "考公",
      employment: "就业",
    };
    return `  · ${label[m.path_type] ?? m.target_role}: 覆盖度 ${m.match_score}/100（${m.risk_level === "low" ? "低风险" : m.risk_level === "medium" ? "中风险" : "高风险"}）`;
  });
  if (rows.length) lines.push(...rows);

  if (result.position_analysis?.personalized_level) {
    lines.push(`考公个人竞争力：${result.position_analysis.personalized_level}`);
  }
  const hardHits =
    (result.position_analysis?.avoid_positions?.length ?? 0) +
    (result.school_analysis?.avoid_schools?.length ?? 0);
  if (hardHits > 0) {
    lines.push(`硬伤提醒：${hardHits} 处「预估分明显低于目标线」的诚实劝退`);
  }
  if (result.recommendation) {
    lines.push(`综合建议：${result.recommendation.replace(/\n+/g, " ")}`);
  }
  lines.push("");
  lines.push("每个数字都基于真实数据并可溯源 · 数据覆盖有限时如实标注");
  return lines.join("\n");
}

export function ShareReportActions({ result }: { result: DecisionEngineResponse }) {
  const toast = useToast();
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedText, setCopiedText] = useState(false);

  const shareText = useMemo(() => buildShareText(result), [result]);

  const handleGenerate = async () => {
    setCreating(true);
    try {
      const resp = await pathDecisionApi.createShare(result.id);
      setShareUrl(resp.url);
      toast.success("分享链接已生成");
    } catch {
      toast.error("生成失败，请稍后重试");
    } finally {
      setCreating(false);
    }
  };

  const handleCopyLink = async () => {
    if (!shareUrl) return;
    const full = `${window.location.origin}${shareUrl}`;
    try {
      await navigator.clipboard.writeText(full);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch {
      toast.error("复制失败，请手动复制");
    }
  };

  const handleCopyText = async () => {
    try {
      await navigator.clipboard.writeText(shareText);
      setCopiedText(true);
      setTimeout(() => setCopiedText(false), 2000);
    } catch {
      toast.error("复制失败，请稍后重试");
    }
  };

  return (
    <section className="rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-600 to-fuchsia-600 text-white">
          <Share2 className="h-4 w-4" />
        </span>
        <div>
          <h3 className="text-base font-semibold text-ink-900">分享这份报告</h3>
          <p className="text-xs text-ink-500">
            生成匿名链接发给同学，或复制文字版发到小红书 / 考研群
          </p>
        </div>
      </div>

      {/* 链接区 */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {!shareUrl ? (
          <button
            type="button"
            onClick={handleGenerate}
            disabled={creating}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {creating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Link2 className="h-4 w-4" />
            )}
            {creating ? "生成中…" : "生成分享链接"}
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={handleCopyLink}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              {copiedLink ? (
                <Check className="h-4 w-4" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
              {copiedLink ? "链接已复制" : "复制分享链接"}
            </button>
            <span className="max-w-full truncate text-xs text-ink-400">
              {typeof window !== "undefined" ? window.location.origin : ""}
              {shareUrl}
            </span>
          </>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={handleCopyText}
          className="inline-flex items-center gap-1.5 rounded-lg border border-brand-200 bg-brand-50 px-3.5 py-2 text-sm font-medium text-brand-700 hover:bg-brand-100"
        >
          {copiedText ? (
            <Check className="h-4 w-4" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
          {copiedText ? "文案已复制" : "复制文字版报告"}
        </button>
      </div>

      <p className="mt-3 rounded-lg bg-amber-50/70 px-3 py-2 text-[11px] leading-relaxed text-amber-700">
        分享页匿名渲染，不包含你的姓名与登录信息；但会展示你填写的专业、条件与预估分——请确认这些信息你愿意分享。
        链接使用防枚举 token，取消分享请联系我们关闭。
      </p>
    </section>
  );
}
