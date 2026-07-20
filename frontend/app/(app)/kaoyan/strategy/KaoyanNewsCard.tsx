"use client";

import { ExternalLink, Calendar, Tag, Newspaper } from "lucide-react";
import { Badge } from "@/components/ui/form-controls";
import { cn } from "@/lib/utils";
import type { KaoyanNewsResponse } from "@/types";

interface KaoyanNewsCardProps {
  news: KaoyanNewsResponse;
  className?: string;
}

export function KaoyanNewsCard({ news, className }: KaoyanNewsCardProps) {
  const dateText = news.published_at
    ? new Date(news.published_at).toLocaleDateString("zh-CN")
    : news.crawled_at
      ? new Date(news.crawled_at).toLocaleDateString("zh-CN")
      : null;

  return (
    <a
      href={news.source_url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "group block rounded-xl border border-paper-200 bg-white p-4 shadow-sm transition-all hover:shadow-md hover:border-brand-200",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <h4 className="font-semibold text-ink-900 line-clamp-2 group-hover:text-brand-600 transition-colors">
          {news.title}
        </h4>
        <ExternalLink className="h-3.5 w-3.5 shrink-0 text-ink-300 group-hover:text-brand-500 mt-1" />
      </div>

      {news.summary && (
        <p className="text-sm text-ink-500 mb-3 line-clamp-2">{news.summary}</p>
      )}

      <div className="flex flex-wrap items-center gap-2 text-xs text-ink-400">
        <span className="flex items-center gap-1">
          <Newspaper className="h-3 w-3" />
          {news.source_platform || "网页"}
        </span>
        {dateText && (
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {dateText}
          </span>
        )}
        {news.category && news.category !== "general" && (
          <Badge color="blue" className="text-xs">
            {news.category}
          </Badge>
        )}
        {news.tags?.slice(0, 2).map((tag) => (
          <span key={tag} className="flex items-center gap-0.5">
            <Tag className="h-3 w-3" />
            {tag}
          </span>
        ))}
      </div>
    </a>
  );
}
