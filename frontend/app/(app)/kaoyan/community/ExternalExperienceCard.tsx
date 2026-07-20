"use client";

import { ExternalLink, Eye, ThumbsUp, Video, Globe, Newspaper } from "lucide-react";
import { Badge } from "@/components/ui/form-controls";
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

export function ExternalExperienceCard({ post, className }: ExternalExperienceCardProps) {
  const platform = getPlatformInfo(post.source_platform);
  const PlatformIcon = platform.icon;

  const handleTitleClick = () => {
    if (post.source_url) {
      window.open(post.source_url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div
      className={cn(
        "rounded-xl border border-paper-200 bg-white p-5 shadow-sm transition-all hover:shadow-md",
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
        <div
          className={cn(
            "flex shrink-0 items-center gap-1 rounded-lg border px-2 py-1 text-xs font-medium",
            platform.color,
          )}
        >
          <PlatformIcon className="h-3 w-3" />
          {platform.label}
        </div>
      </div>

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
