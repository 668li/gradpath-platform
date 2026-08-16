"use client";

import { ExternalLink, Eye, ThumbsUp, Video, Globe, Newspaper, AlertTriangle, Target } from "lucide-react";
import { Badge } from "@/components/ui/form-controls";
import { SourceBadge } from "@/components/ui/source-badge";
import { QualityBadge } from "@/components/ui/quality-badge";
import { QualityFeedback } from "@/components/kaoyan/quality-feedback";
import { cn } from "@/lib/utils";
import type { ExperiencePostResponse } from "@/types";

interface ExternalExperienceCardProps {
  post: ExperiencePostResponse;
  className?: string;
}

const platformConfig: Record<string, { label: string; icon: typeof Video; color: string }> = {
  bilibili: { label: "B站", icon: Video, color: "text-pink-600 bg-pink-50 border-pink-200" },
  zhihu: { label: "知乎", icon: Newspaper, color: "text-blue-600 bg-blue-50 border-blue-200" },
  xiaohongshu: { label: "小红书", icon: Newspaper, color: "text-red-600 bg-red-50 border-red-200" },
  tieba: { label: "贴吧", icon: Globe, color: "text-orange-600 bg-orange-50 border-orange-200" },
  crawler: { label: "网页", icon: Globe, color: "text-green-600 bg-green-50 border-green-200" },
};

function getPlatformInfo(platform: string) {
  return (
    platformConfig[platform] || {
      label: platform ? platform.charAt(0).toUpperCase() + platform.slice(1) : "外部",
      icon: Globe,
      color: "text-ink-600 bg-paper-100 border-paper-200",
    }
  );
}

/** Phase I 证据链字段名 → 中文标签（提取依据展示） */
const EVIDENCE_LABELS: Record<string, string> = {
  subject: "学科",
  stage: "阶段",
  school: "院校",
  target_score: "目标分",
  methods: "方法",
  audience: "适用人群",
};

export function ExternalExperienceCard({ post, className }: ExternalExperienceCardProps) {
  const platform = getPlatformInfo(post.source_platform);
  const PlatformIcon = platform.icon;
  // Phase G 结构化摘要（决策数据卡：学科/院校/目标分，抽不到不渲染）
  const meta = post.structured_meta || {};
  const isPromo = Boolean(post.is_promotion);
  const structuredChips: string[] = [];
  if (meta.subject) structuredChips.push(`学科 ${meta.subject}`);
  if (meta.school) structuredChips.push(meta.school);
  if (meta.target_score) structuredChips.push(`目标 ${meta.target_score} 分`);
  if (meta.audience) structuredChips.push(meta.audience);

  const handleTitleClick = () => {
    if (post.source_url) {
      window.open(post.source_url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div
      className={cn(
        "rounded-xl border border-paper-200 bg-white p-5 shadow-sm transition-all hover:shadow-md",
        isPromo && "border-amber-200",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <h3
          onClick={handleTitleClick}
          className={cn(
            "font-semibold text-ink-900 line-clamp-2",
            post.source_url && "cursor-pointer hover:text-brand-600",
          )}
        >
          {post.title}
        </h3>
        <div className="flex shrink-0 items-center gap-1.5">
          <div
            className={cn(
              "flex items-center gap-1 rounded-lg border px-2 py-1 text-xs font-medium",
              platform.color,
            )}
          >
            <PlatformIcon className="h-3 w-3" />
            {platform.label}
          </div>
          <SourceBadge sourceUrl={post.source_url} sourcePlatform={post.source_platform} showPlatform={false} />
        </div>
      </div>

      {/* Phase G：质量徽章 + 疑似软广标注（标注不隐藏，让用户知情）；Phase I：双键反馈 */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <QualityBadge grade={post.quality_grade} score={post.quality_score} reasons={post.quality_reasons} />
        {isPromo && (
          <span
            className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-xs font-medium text-amber-700"
            title={post.promotion_reason ? `命中：${post.promotion_reason}` : "疑似广告/引流内容"}
          >
            <AlertTriangle className="h-3 w-3" />
            疑似推广
          </span>
        )}
        <div className="ml-auto">
          <QualityFeedback targetType="experience_post" targetId={post.id} />
        </div>
      </div>

      {/* Phase I 证据链：structured_meta.evidence 非空时展示「提取依据」原文证据 */}
      {meta.evidence && Object.keys(meta.evidence).length > 0 && (
        <details className="mb-2 rounded-md border border-paper-200 bg-paper-50 px-2 py-1.5 text-xs text-ink-600">
          <summary className="cursor-pointer font-medium text-ink-700">
            提取依据（原文证据 · 置信度）
          </summary>
          <ul className="mt-1 space-y-0.5">
            {Object.entries(meta.evidence).map(([field, snippet]) => (
              <li key={field}>
                {EVIDENCE_LABELS[field] ?? field} · 原文「{snippet}」
                {meta.confidence?.[field] != null && (
                  <span className="text-ink-400">
                    {" "}
                    · 置信度 {Math.round(meta.confidence![field] * 100)}%
                  </span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}

      {structuredChips.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 mb-2">
          {structuredChips.map((chip) => (
            <span
              key={chip}
              className="inline-flex items-center gap-1 rounded-md border border-paper-200 bg-paper-50 px-1.5 py-0.5 text-xs text-ink-600"
            >
              <Target className="h-3 w-3 text-brand-500" />
              {chip}
            </span>
          ))}
        </div>
      )}

      <p className="text-sm text-ink-500 mb-3 line-clamp-2">
        {post.summary || post.content.slice(0, 120)}
      </p>

      <div className="flex flex-wrap items-center gap-2 mb-3">
        {post.category && post.category !== "general" && (
          <Badge color="green">{post.category}</Badge>
        )}
        {post.tags?.map((tag) => (
          <Badge key={tag} color="slate" className="text-xs">
            {tag}
          </Badge>
        ))}
      </div>

      <div className="flex items-center justify-between text-xs text-ink-400">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Eye className="h-3 w-3" />
            {post.external_view_count || post.view_count || 0}
          </span>
          <span className="flex items-center gap-1">
            <ThumbsUp className="h-3 w-3" />
            {post.external_like_count || post.like_count || 0}
          </span>
        </div>
        {post.source_url ? (
          <a
            href={post.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 font-medium text-brand-600 hover:text-brand-700"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="h-3 w-3" />
            查看原链接
          </a>
        ) : null}
      </div>
    </div>
  );
}
